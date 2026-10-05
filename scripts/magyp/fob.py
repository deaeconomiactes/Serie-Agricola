"""FOB v1: stdlib, captura acotada, trazabilidad y publicación fail-closed."""
import csv
import hashlib
import io
import json
import os
import re
import tempfile
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .contracts import PublishResult, RawManifest, ValidationResult

SOURCE = "magyp_fob"
ENDPOINT = "https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/ws/ssma/precios_fob.php"
ORIGIN = "https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/fob_oficiales/_archivos/000021_Precios%20Fob%20Api.php"
PARSER_VERSION = "fob-1.0.0"
SCHEMA_VERSION = "v1"
MAX_BYTES = 1_500_000
REQUIRED = {"fecha", "circular", "posicion", "precio", "mesDesde", "añoDesde", "mesHasta", "añoHasta"}
NORMALIZED_FIELDS = [
    "source", "observation_date", "capture_timestamp", "capture_id", "observation_id", "record_id", "row_number",
    "circular", "position_raw", "price_raw", "observation_date_raw", "shipment_month_from", "shipment_year_from",
    "shipment_month_to", "shipment_year_to", "raw_sha256", "raw_manifest", "source_url", "schema_version",
]
ANALYTICAL_FIELDS = ["date", "position", "shipment_window", "circular", "price", "source", "observation_id",
                     "record_id", "capture_id", "capture_timestamp", "raw_sha256", "source_url", "schema_version"]
DASHBOARD_FIELDS = ["date", "position", "shipment_window", "circular", "price", "source", "observation_id",
                    "record_id", "capture_id", "updated_at_utc", "raw_sha256", "source_url", "schema_version"]


class PipelineError(RuntimeError):
    """Mensaje fijo/sanitizado; no incluir cuerpos HTTP ni secretos."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def technical_id(*values):
    return digest(json_bytes(list(values)))


def parse_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Fecha debe ser ISO YYYY-MM-DD")
    return date.fromisoformat(value)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def price_number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("invalid_price")
    # API JSON numérica o decimal textual con punto; no interpretar separadores locales.
    text = str(value)
    if len(text) > 60 or not re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", text):
        raise ValueError("invalid_price")
    try:
        number = Decimal(text)
        if not number.is_finite() or number < 0 or abs(number.adjusted()) > 20:
            raise ValueError("invalid_price")
        return format(number, "f")
    except InvalidOperation as exc:
        raise ValueError("invalid_price") from exc


def shipment(row):
    keys = ["mesDesde", "añoDesde", "mesHasta", "añoHasta"]
    values = []
    for key in keys:
        value = row[key]
        if isinstance(value, bool) or not isinstance(value, (int, str)) or not re.fullmatch(r"\d{1,4}", str(value)):
            raise ValueError("invalid_shipment_window")
        values.append(int(value))
    mf, yf, mt, yt = values
    if not (1 <= mf <= 12 and 1 <= mt <= 12 and 1 <= yf <= 9999 and 1 <= yt <= 9999):
        raise ValueError("invalid_shipment_window")
    if (yf, mf) > (yt, mt):
        raise ValueError("invalid_shipment_window")
    return values


def load_calendar(path=None):
    if path is None:
        return {"source_url": "", "sha256": "", "non_publication_dates": {}}
    data = Path(path).read_bytes()
    obj = json.loads(data)
    if set(obj) != {"source_url", "non_publication_dates"} or not isinstance(obj["non_publication_dates"], dict):
        raise PipelineError("Calendario: schema inválido")
    if not isinstance(obj["source_url"], str) or not obj["source_url"].startswith("https://"):
        raise PipelineError("Calendario: requiere referencia HTTPS validada por el operador")
    for day, reason in obj["non_publication_dates"].items():
        parse_date(day)
        if not isinstance(reason, str) or not reason.strip():
            raise PipelineError("Calendario: motivo ausente")
    return {**obj, "sha256": digest(data)}


def validate_response(body, status, requested_date, calendar=None):
    """La validez depende del cuerpo, nunca del content-type declarado."""
    day = parse_date(requested_date)
    if status != 200:
        return ValidationResult(False, "service_error", errors=("http_not_200",)), []
    try:
        # Rechazar miembros repetidos JSON, no permitir que el parser los oculte.
        def unique_members(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("repeated_json_member")
                result[key] = value
            return result
        obj = json.loads(body.decode("utf-8-sig"), parse_float=Decimal, object_pairs_hook=unique_members)
    except (ValueError, UnicodeDecodeError):
        kind = "unexpected_html" if body.lstrip().startswith(b"<") else "invalid_json"
        return ValidationResult(False, kind, errors=(kind,)), []
    if not isinstance(obj, dict) or "posts" not in obj:
        return ValidationResult(False, "schema_error", errors=("posts_missing",)), []
    if set(obj) != {"posts"} or not isinstance(obj["posts"], list):
        return ValidationResult(False, "schema_error", errors=("schema_changed",)), []
    rows = obj["posts"]
    if not rows:
        explained = day.weekday() >= 5 or requested_date in (calendar or {}).get("non_publication_dates", {})
        return ValidationResult(explained, "no_publication" if explained else "unexpected_empty",
                                errors=() if explained else ("unexpected_empty",)), []
    seen_rows, seen_keys = set(), set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != REQUIRED:
            return ValidationResult(False, "schema_error", errors=("schema_changed",)), []
        try:
            if not isinstance(row["fecha"], str):
                raise ValueError("invalid_date")
            observed = datetime.fromisoformat(row["fecha"]).date()
            if observed != day:
                raise ValueError("date_mismatch")
        except (ValueError, TypeError):
            return ValidationResult(False, "invalid_observation", errors=("invalid_or_mismatched_date",)), []
        try:
            price = price_number(row["precio"])
            window = shipment(row)
        except ValueError as exc:
            return ValidationResult(False, "invalid_observation", errors=(str(exc),)), []
        if not isinstance(row["posicion"], str) or not row["posicion"].strip() or len(row["posicion"]) > 100:
            return ValidationResult(False, "invalid_observation", errors=("invalid_position",)), []
        if isinstance(row["circular"], bool) or not isinstance(row["circular"], (int, str)) or not str(row["circular"]).strip():
            return ValidationResult(False, "invalid_observation", errors=("invalid_circular",)), []
        # Posición y circular se conservan textuales, sin strip ni conversión NCM.
        key = technical_id(SOURCE, requested_date, row["posicion"], window, str(row["circular"]))
        exact = technical_id([str(row[k]) for k in sorted(REQUIRED)])
        if exact in seen_rows:
            return ValidationResult(False, "duplicate", errors=("exact_duplicate",)), []
        if key in seen_keys:
            return ValidationResult(False, "duplicate", errors=("conflicting_identity",)), []
        seen_rows.add(exact)
        seen_keys.add(key)
    return ValidationResult(True, "valid", len(rows)), rows


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Una redirección cambia el contrato: requiere revisión, no seguirla.


def http_get(url):
    request = Request(url, headers={"User-Agent": "Serie-Agricola-MAGyP-FOB/1.0", "Accept": "application/json"})
    try:
        with build_opener(NoRedirect()).open(request, timeout=25) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read(MAX_BYTES + 1)
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), b""  # No almacenar páginas de error/sesión.
    except (URLError, TimeoutError, OSError):
        return None, "", b""


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".fob-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if Path(temporary).read_bytes() != data:
            raise PipelineError("Verificación del archivo temporal falló; replace bloqueado")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def csv_bytes(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


class FobPipeline:
    def __init__(self, data_root=None, raw_root=None):
        self.data = Path(data_root or Path(__file__).resolve().parents[2] / "data").resolve()
        self.raw = Path(raw_root or os.environ.get("MAGYP_RAW_ROOT", self.data / "raw" / "magyp")).resolve() / "fob"
        self.normalized = self.data / "normalized" / "magyp" / "fob"
        self.analytical = self.data / "analytical" / "commodities" / "fob.csv"
        self.dashboard = self.data / "dashboard" / "commodities" / "fob.csv"
        self.state_path = self.normalized / "pipeline_state.json"
        self.pointer = self.normalized / "latest.json"

    def state(self):
        if not self.state_path.exists():
            raise PipelineError("Falta captura: ejecutar fetch_fob.py primero")
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def set_state(self, **values):
        atomic_write(self.state_path, json_bytes(values))

    @contextmanager
    def locked(self):
        self.normalized.mkdir(parents=True, exist_ok=True)
        lock = self.normalized / ".pipeline.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise PipelineError("Pipeline ocupado; revisar lock si una corrida fue interrumpida") from exc
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write(str(os.getpid()))
            yield
        finally:
            lock.unlink(missing_ok=True)

    def fetch(self, requested_date, calendar=None, transport=http_get):
        parse_date(requested_date)
        calendar = calendar or load_calendar()
        parameters = {"Fecha": parse_date(requested_date).strftime("%d/%m/%Y")}
        url = ENDPOINT + "?" + urlencode(parameters)
        with self.locked():
            capture_time = utc_now()
            capture_id = capture_time.replace(":", "").replace("-", "") + "_" + uuid.uuid4().hex
            # Invalidar ANTES de la red: también bloquea publicación si el proceso se interrumpe.
            self.set_state(stage="fetching", capture_id=capture_id, requested_date=requested_date)
            try:
                status, content_type, body = transport(url)
                print(f"[FETCH] FOB {requested_date} HTTP {status if status is not None else 'unavailable'}")
                if len(body) > MAX_BYTES:
                    result = ValidationResult(False, "service_error", errors=("response_too_large",))
                else:
                    result, _ = validate_response(body, status, requested_date, calendar)
                print(f"[VALIDATE] {result.classification}: {result.record_count} registros")
                retain = result.valid
                manifest = RawManifest(SOURCE, requested_date, capture_time, capture_id, url, ORIGIN, "GET", parameters,
                                       status, content_type, "utf-8-sig" if retain else "unverified", len(body), digest(body),
                                       PARSER_VERSION, SCHEMA_VERSION, "response.json" if retain else None, result, calendar)
                # Cada captura tiene un directorio nuevo; se hace visible sólo al terminar ambos archivos.
                self.raw.mkdir(parents=True, exist_ok=True)
                temporary = Path(tempfile.mkdtemp(prefix=".capture-", dir=self.raw))
                try:
                    if retain:
                        (temporary / "response.json").write_bytes(body)
                    (temporary / "manifest.json").write_bytes(json_bytes(manifest.to_dict()))
                    temporary.rename(self.raw / capture_id)
                finally:
                    for child in temporary.glob("*"):
                        child.unlink()
                    if temporary.exists():
                        temporary.rmdir()
                stage = "fetched" if result.valid and result.record_count else "no_publication" if result.valid else "failed"
                self.set_state(stage=stage, capture_id=capture_id, requested_date=requested_date,
                               classification=result.classification)
                if not result.valid:
                    raise PipelineError("Captura rechazada: " + ",".join(result.errors))
                return manifest
            except Exception:
                self.set_state(stage="failed", capture_id=capture_id, requested_date=requested_date)
                raise

    def validated_captures(self):
        captures = []
        for path in sorted(self.raw.glob("*/manifest.json")):
            if path.parent.name.startswith("."):
                continue
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if manifest["source"] != SOURCE or manifest["schema_version"] != SCHEMA_VERSION or manifest["parser_version"] != PARSER_VERSION:
                raise PipelineError("Manifest/parser no compatible: migración explícita requerida")
            if not manifest["validation"]["valid"] or manifest["validation"]["classification"] == "no_publication":
                continue
            if manifest["response_file"] != "response.json" or manifest["capture_id"] != path.parent.name:
                raise PipelineError("Manifest RAW inconsistente")
            body = (path.parent / "response.json").read_bytes()
            if digest(body) != manifest["sha256"] or len(body) != manifest["size_bytes"]:
                raise PipelineError("Integridad RAW: hash/tamaño no coincide")
            result, rows = validate_response(body, manifest["status"], manifest["requested_date"], manifest["calendar"])
            if not result.valid or result.record_count != manifest["validation"]["record_count"]:
                raise PipelineError("Revalidación RAW rechazada")
            try:
                stamp = datetime.fromisoformat(manifest["captured_at_utc"].replace("Z", "+00:00"))
                if stamp.utcoffset() != timezone.utc.utcoffset(stamp):
                    raise ValueError()
            except (ValueError, TypeError):
                raise PipelineError("Timestamp RAW no es UTC válido")
            captures.append((manifest, rows))
        return sorted(captures, key=lambda pair: (pair[0]["captured_at_utc"], pair[0]["capture_id"]))

    def normalize(self):
        with self.locked():
            state = self.state()
            if state["stage"] == "no_publication":
                print("[NORMALIZE] Sin publicación explicada; conservar salidas")
                return ValidationResult(True, "no_publication")
            if state["stage"] not in {"fetched", "normalized", "published"}:
                raise PipelineError("Captura fallida/incompleta: normalización bloqueada")
            try:
                captures = self.validated_captures()
                if not captures or state["capture_id"] not in {m["capture_id"] for m, _ in captures}:
                    raise PipelineError("La captura actual no tiene RAW validado")
                records = []
                for manifest, rows in captures:
                    for ordinal, row in enumerate(rows, 1):
                        mf, yf, mt, yt = shipment(row)
                        observation_id = technical_id(SOURCE, manifest["requested_date"], row["posicion"],
                                                      [mf, yf, mt, yt], str(row["circular"]))
                        records.append(dict(zip(NORMALIZED_FIELDS, [
                            SOURCE, manifest["requested_date"], manifest["captured_at_utc"], manifest["capture_id"],
                            observation_id, technical_id(observation_id, manifest["capture_id"], manifest["sha256"]), ordinal,
                            str(row["circular"]), row["posicion"], str(row["precio"]), row["fecha"], mf, yf, mt, yt,
                            manifest["sha256"], manifest["capture_id"] + "/manifest.json", manifest["url"], SCHEMA_VERSION,
                        ])))
                data = csv_bytes(NORMALIZED_FIELDS, records)
                fingerprint = digest(data)
                output = self.normalized / (fingerprint + ".csv")
                if not output.exists():
                    atomic_write(output, data)
                elif output.read_bytes() != data:
                    raise PipelineError("Snapshot normalizado inconsistente")
                atomic_write(self.pointer, json_bytes({"file": output.name, "sha256": fingerprint, "record_count": len(records),
                                                      "captures": [m["capture_id"] for m, _ in captures],
                                                      "parser_version": PARSER_VERSION, "schema_version": SCHEMA_VERSION}))
                self.set_state(**{**state, "stage": "normalized", "normalized_sha256": fingerprint})
                print(f"[NORMALIZE] {len(records)} registros válidos (todas las versiones)")
                return ValidationResult(True, "valid", len(records))
            except Exception:
                self.set_state(**{**state, "stage": "failed_normalization"})
                raise

    def build(self, output_validator=None):
        with self.locked():
            state = self.state()
            if state["stage"] == "no_publication":
                print("[PUBLISH] Sin publicación explicada; último dashboard conservado")
                return PublishResult(False, False, 0, str(self.dashboard), "no_publication")
            if state["stage"] not in {"normalized", "published"}:
                raise PipelineError("Normalización ausente/fallida: publicación bloqueada")
            try:
                pointer = json.loads(self.pointer.read_text(encoding="utf-8"))
                expected = state["normalized_sha256"]
                if pointer["sha256"] != expected or pointer["file"] != expected + ".csv":
                    raise PipelineError("Pointer normalizado inconsistente")
                data = (self.normalized / pointer["file"]).read_bytes()
                if digest(data) != expected:
                    raise PipelineError("Integridad normalizada inválida")
                captures = self.validated_captures()
                if pointer["captures"] != [m["capture_id"] for m, _ in captures]:
                    raise PipelineError("RAW cambió: normalizar nuevamente")
                records = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
                if not records or len(records) != pointer["record_count"] or list(records[0]) != NORMALIZED_FIELDS:
                    raise PipelineError("Schema/conteo normalizado inválido")
                latest = {}
                for manifest, _ in captures:
                    latest[manifest["requested_date"]] = manifest["capture_id"]
                # Una captura revisada reemplaza el conjunto completo del día en vistas actuales.
                # Todas las versiones siguen intactas en RAW y NORMALIZED, incluidas posiciones retiradas.
                current = [r for r in records if latest[r["observation_date"]] == r["capture_id"]]
                current.sort(key=lambda r: (r["observation_date"], r["position_raw"], r["shipment_year_from"],
                                            r["shipment_month_from"], r["circular"], r["observation_id"]))
                analytical, dashboard = [], []
                for row in current:
                    window = f'{int(row["shipment_year_from"]):04d}-{int(row["shipment_month_from"]):02d}/{int(row["shipment_year_to"]):04d}-{int(row["shipment_month_to"]):02d}'
                    common = [row["observation_date"], row["position_raw"], window, row["circular"], price_number(row["price_raw"]),
                              row["source"], row["observation_id"], row["record_id"], row["capture_id"], row["capture_timestamp"],
                              row["raw_sha256"], row["source_url"], row["schema_version"]]
                    analytical.append(dict(zip(ANALYTICAL_FIELDS, common)))
                    dashboard.append(dict(zip(DASHBOARD_FIELDS, common)))
                analytical_data = csv_bytes(ANALYTICAL_FIELDS, analytical)
                dashboard_data = csv_bytes(DASHBOARD_FIELDS, dashboard)
                validate_output(analytical_data, ANALYTICAL_FIELDS, len(current))
                validate_output(dashboard_data, DASHBOARD_FIELDS, len(current))
                if self.dashboard.exists():
                    previous_data = self.dashboard.read_bytes()
                    previous = list(csv.DictReader(io.StringIO(previous_data.decode("utf-8"))))
                    validate_output(previous_data, DASHBOARD_FIELDS, len(previous))
                    if not {r["date"] for r in previous}.issubset({r["observation_date"] for r in current}):
                        raise PipelineError("Faltan fechas RAW del dashboard anterior: recuperar almacenamiento durable antes de publicar")
                if output_validator:
                    output_validator(dashboard_data)
                print(f"[VALIDATE] {len(current)} registros actuales; sin agrupación ni diccionario inferido")
                changed = not self.dashboard.exists() or self.dashboard.read_bytes() != dashboard_data
                # Se prepara/valida todo antes de reemplazar; dashboard es el último replace.
                if not self.analytical.exists() or self.analytical.read_bytes() != analytical_data:
                    atomic_write(self.analytical, analytical_data)
                if changed:
                    atomic_write(self.dashboard, dashboard_data)
                self.set_state(**{**state, "stage": "published", "dashboard_sha256": digest(dashboard_data)})
                print(f"[PUBLISH] fob.csv {'actualizado' if changed else 'sin cambios'}")
                return PublishResult(True, changed, len(current), str(self.dashboard), "validated")
            except Exception:
                self.set_state(**{**state, "stage": "failed_build"})
                raise


def validate_output(data, fields, count):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    if reader.fieldnames != fields:
        raise PipelineError("Schema de salida inválido")
    rows = list(reader)
    if not rows or len(rows) != count:
        raise PipelineError("Salida vacía/conteo inválido")
    if len({r["record_id"] for r in rows}) != len(rows) or len({r["observation_id"] for r in rows}) != len(rows):
        raise PipelineError("Identidades repetidas en salida")
    for row in rows:
        parse_date(row["date"])
        price_number(row["price"])
        if row["source"] != SOURCE or row["schema_version"] != SCHEMA_VERSION or not row["source_url"].startswith(ENDPOINT + "?"):
            raise PipelineError("Fuente/schema de salida inválido")
        if not re.fullmatch(r"\d{4}-\d{2}/\d{4}-\d{2}", row["shipment_window"]):
            raise PipelineError("Ventana de salida inválida")
        for key in ("record_id", "observation_id", "raw_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}", row[key]):
                raise PipelineError("Trazabilidad de salida inválida")
