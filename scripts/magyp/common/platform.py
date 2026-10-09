"""Primitivas sin estado de sesión para pipelines oficiales reproducibles."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse


class PipelineError(ValueError):
    pass


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    record_count: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublishResult:
    published: bool
    files: tuple[str, ...]
    record_count: int


@dataclass(frozen=True)
class RawManifest:
    source: str
    source_family: str
    endpoint: str
    request_method: str | None
    public_parameters: dict
    captured_at_utc: str
    http_status: int | None
    content_type: str | None
    encoding: str | None
    byte_size: int
    sha256: str
    schema_version: str
    parser_version: str
    record_count: int
    validation_status: str
    capture_id: str
    acquisition_mode: str
    currency: str | None = None
    price_unit: str | None = None
    context_evidence_url: str | None = None
    response_url: str | None = None
    currency_evidence: str = "contextual"
    acquisition_classification: str | None = None
    request_count: int | None = None


class SourceFetcher(Protocol):
    def fetch(self, requested_date: str) -> tuple[bytes, RawManifest]: ...


class Normalizer(Protocol):
    def normalize(self, payload: bytes, manifest: RawManifest) -> list[dict]: ...


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_id(value) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str,
                             separators=(",", ":")).encode("utf-8"))


def official_url(url: str) -> str:
    p = urlparse(url)
    if (p.scheme != "https" or p.hostname not in {"ssma.magyp.gob.ar", "www.magyp.gob.ar"}
            or p.username or p.password or p.port not in (None, 443) or p.fragment):
        raise PipelineError("URL fuera de la allowlist HTTPS oficial")
    return url


def validate_manifest(m: RawManifest, payload: bytes) -> None:
    if (m.source not in {"mcba", "corrientes", "grains_internal", "grains_board", "grains_fas",
                         "grains_fob", "sio_grains", "futures", "sio_meats"}
            or m.source_family not in {"market_price_observation", "commodity_reference_price",
                                      "transaction_event", "livestock_transaction_event"}):
        raise PipelineError("Fuente/familia no registrada")
    official_url(m.endpoint)
    if urlparse(m.endpoint).query:
        raise PipelineError("Endpoint del manifest debe ser estable y sin estado de sesión")
    if m.response_url:
        official_url(m.response_url)
        if urlparse(m.response_url).query:
            raise PipelineError("URL de respuesta con estado de sesión rechazada")
    if set(m.public_parameters) != {"date_from", "date_to"}:
        raise PipelineError("Parámetros de request no autorizados para persistencia")
    for value in m.public_parameters.values():
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            raise PipelineError("Fecha pública inválida") from e
    start = datetime.strptime(m.public_parameters.get("date_from", ""), "%Y-%m-%d")
    end = datetime.strptime(m.public_parameters.get("date_to", ""), "%Y-%m-%d")
    if start > end or (end - start).days > 6:
        raise PipelineError("Ventana RAW limitada a 1–7 días")
    if m.schema_version.endswith("v1") and start != end:
        raise PipelineError("Contrato legado v1 limitado a un día")
    if m.currency_evidence not in {"documented", "contextual", "unknown"}:
        raise PipelineError("Evidencia de moneda inválida")
    if m.byte_size != len(payload) or m.sha256 != sha256(payload):
        raise PipelineError("RAW no coincide con tamaño/SHA-256 del manifest")
    try:
        stamp = datetime.fromisoformat(m.captured_at_utc.replace("Z", "+00:00"))
        if stamp.utcoffset().total_seconds() != 0:
            raise ValueError("UTC requerido")
    except (ValueError, AttributeError) as e:
        raise PipelineError("Timestamp UTC inválido") from e
    if not re.fullmatch(r"[A-Za-z0-9_-]+", m.capture_id):
        raise PipelineError("capture_id inválido")
    if m.validation_status != "validated" or m.record_count <= 0:
        raise PipelineError("Captura sin validación o vacía")
    if m.http_status is not None and m.http_status != 200:
        raise PipelineError("HTTP no exitoso")
    if m.acquisition_mode == "http_export" and m.http_status != 200:
        raise PipelineError("Captura HTTP sin status verificado")


def store_raw(root: Path, payload: bytes, manifest: RawManifest) -> Path:
    validate_manifest(manifest, payload)
    folder = root / "raw" / manifest.source / manifest.capture_id
    folder.mkdir(parents=True, exist_ok=False)
    # Create exclusively. No overwrite even if another caller uses the same ID.
    with (folder / "response.xlsx").open("xb") as f:
        f.write(payload)
    with (folder / "manifest.json").open("x", encoding="utf-8", newline="\n") as f:
        json.dump(asdict(manifest), f, ensure_ascii=False, indent=2)
        f.write("\n")
    return folder


def load_raw(folder: Path) -> tuple[bytes, RawManifest]:
    try:
        m = RawManifest(**json.loads((folder / "manifest.json").read_text(encoding="utf-8")))
        payload = (folder / "response.xlsx").read_bytes()
        validate_manifest(m, payload)
        if m.capture_id != folder.name:
            raise PipelineError("capture_id no coincide con carpeta")
        return payload, m
    except (OSError, TypeError, json.JSONDecodeError) as e:
        raise PipelineError("Captura RAW incompleta o manifest inválido") from e


def csv_bytes(rows: list[dict], fields: list[str]) -> bytes:
    s = io.StringIO(newline="")
    writer = csv.DictWriter(s, fieldnames=fields, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (list, dict))
                         else v for k, v in row.items()})
    return s.getvalue().encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".stage-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        if path.exists() and path.read_bytes() == payload:
            return
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    atomic_write(path, ("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                               for r in rows)).encode("utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    try:
        rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
    except (OSError, json.JSONDecodeError) as e:
        raise PipelineError("Dataset ausente o JSONL inválido") from e
    if not rows:
        raise PipelineError("Dataset vacío: se conserva la última salida válida")
    return rows


def publish_bundle(folder: Path, outputs: dict[str, bytes], count: int) -> PublishResult:
    """Validación previa + reemplazo atómico por archivo + rollback ante errores Python.

    _SUCCESS es el marcador del conjunto; lectores deben verificar sus hashes.
    Un corte de proceso entre reemplazos puede dejar una generación incompleta,
    detectable por el marcador. No se promete atomicidad multiarchivo del SO.
    """
    if not count or not outputs:
        raise PipelineError("Publicación vacía rechazada")
    for name, body in outputs.items():
        if Path(name).name != name or not body:
            raise PipelineError("Salida inválida")
        parsed = list(csv.reader(io.StringIO(body.decode("utf-8"))))
        if not parsed or not parsed[0] or any(len(r) != len(parsed[0]) for r in parsed):
            raise PipelineError("CSV de publicación inválido")
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / ".publish.lock"
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as e:
        raise PipelineError("Otra publicación en curso; verificar lock antes de reintentar") from e
    os.close(lock_fd)
    marker = json.dumps({"files": {n: sha256(b) for n, b in outputs.items()},
                         "record_count": count}, sort_keys=True, indent=2).encode("utf-8")
    bundle = dict(outputs, **{"_SUCCESS.json": marker})
    previous = {n: (folder / n).read_bytes() if (folder / n).exists() else None for n in bundle}
    try:
        for name, body in bundle.items():
            atomic_write(folder / name, body)
    except Exception:
        for name, body in previous.items():
            if body is None:
                (folder / name).unlink(missing_ok=True)
            else:
                atomic_write(folder / name, body)
        raise
    finally:
        lock.unlink(missing_ok=True)
    return PublishResult(True, tuple(outputs), count)
