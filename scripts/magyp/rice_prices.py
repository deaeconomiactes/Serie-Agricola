"""Capture, validate and publish the official MAGyP rice-price series.

RAW HTML captures are retained locally and uploaded by the GitHub Actions
workflow. Dashboard CSVs are replaced only after the complete source snapshot
passes schema, coverage, unit, date and monotonic-history checks.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import io
import json
import os
import re
import sys
import tempfile
import time
import traceback
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.magyp.grains import references as ref

INTERNAL_URL = (
    "https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/regionales/"
    "_archivos/000010_Precios%20Locales/000020_Arroz/"
    "000001_Precios%20de%20Arroz%20C%C3%A1scara%20Internos.php?accion=imp"
)
FOB_URL = (
    "https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/regionales/"
    "_archivos/000020_Precios%20Internacionales/000052_Arroz/"
    "000001_Arroz%20Mensual%20U%24S%20x%20Ton%20FOB.php"
)
BCRA_LANDING = "https://www.bcra.gob.ar/tipo-cambio-referencia-comunicacion-a-3500-tcnpm/"
BCRA_URL = "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/com3500.xls"
VERSION = "magyp-references-v1"
STATUS_VERSION = "magyp-rice-prices-status-v1"
PARSER_VERSION = "magyp-rice-prices-v1"
INTERNAL_BASE_TYPE = "Precio interno arroz cáscara"
INTERNAL_KG_TYPE = "Precio interno arroz cáscara · conversión de unidad"
INTERNAL_USD_TYPE = "Precio interno arroz cáscara · equivalencia USD/A3500"
FOB_TYPE = "Referencia internacional FOB arroz"
MONTHS = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
          "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}
FOB_LABELS_2017_2024 = ["Usa2/4", "Thai100", "Thai5", "Tai Parb", "Inde 5", "Viet5",
                       "Uru5", "Inde 25", "Thai25", "Viet25", "Pak 25", "A1Super"]
FOB_LABELS_2025_ON = ["Usa2/4", "Thai100", "Tai Parb", "Inde 5", "Viet5", "Uru5",
                      "Thai25", "Viet25", "Pak 25", "A1Super"]
RICE_FIELDS = [
    "rice_variety_raw", "fob_origin_quality_raw", "price_raw_source",
    "price_original_ars_qq", "fx_a3500_monthly_avg", "fx_a3500_observations",
    "fx_a3500_first_date", "fx_a3500_last_date", "fx_a3500_raw_sha256",
    "fx_a3500_source_url", "conversion_method", "duplicate_source_rows", "source_marker",
    "source_locator",
]
FIELDS = list(ref.FIELDS) + RICE_FIELDS
STATES = {"UPDATED", "NO_PUBLICATION", "SOURCE_UNAVAILABLE", "PIPELINE_ERROR"}
MAX_PAGE_BYTES = 2_000_000


class RiceError(ValueError):
    """Fixed diagnostic suitable for workflow logs; response bodies are excluded."""


class SourceUnavailable(RiceError):
    pass


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def stable_id(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return sha256(encoded)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".rice-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(payload)
            stream.flush()
        if not path.exists() or path.read_bytes() != payload:
            Path(name).replace(path)
    finally:
        if Path(name).exists():
            Path(name).unlink()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def normalized_text(value: str) -> str:
    value = unicodedata.normalize("NFD", html.unescape(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.upper().replace("\xa0", " ").split())


class RicePage(HTMLParser):
    """Extract public table cells and the official year selector only."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self.options: list[tuple[str, str]] = []
        self.text: list[str] = []
        self.depth = 0
        self.table = None
        self.row = None
        self.cell = None
        self.option_value = None
        self.option_text = None
        self.ignore = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self.ignore += 1
        if tag == "table":
            if self.depth == 0:
                self.table = []
            self.depth += 1
        elif tag == "tr" and self.depth == 1:
            self.row = []
        elif tag in {"td", "th"} and self.depth == 1 and self.row is not None:
            self.cell = []
        elif tag == "option":
            self.option_value = attrs.get("value", "")
            self.option_text = []

    def handle_data(self, data):
        if self.ignore:
            return
        clean = " ".join(data.replace("\xa0", " ").split())
        if clean:
            self.text.append(clean)
            if self.cell is not None:
                self.cell.append(clean)
            if self.option_text is not None:
                self.option_text.append(clean)

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignore = max(0, self.ignore - 1)
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if any(value.strip() for value in self.row):
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.depth:
            self.depth -= 1
            if self.depth == 0:
                if self.table:
                    self.tables.append(self.table)
                self.table = None
        elif tag == "option" and self.option_text is not None:
            self.options.append((self.option_value or "", " ".join(self.option_text)))
            self.option_value = None
            self.option_text = None


@dataclass(frozen=True)
class Download:
    body: bytes
    status: int
    content_type: str
    url: str


def download(url: str) -> Download:
    request = Request(url, headers={
        "User-Agent": "SerieAgricola rice-prices/1.0",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    })
    try:
        with urlopen(request, timeout=40) as response:
            body = response.read(MAX_PAGE_BYTES + 1)
            if response.status != 200:
                raise SourceUnavailable(f"HTTP {response.status}; última salida válida preservada")
            if len(body) > MAX_PAGE_BYTES:
                raise RiceError("Página oficial excede el tamaño permitido")
            return Download(body, response.status, response.headers.get("Content-Type", ""),
                            response.geturl())
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise SourceUnavailable(f"Fuente MAGyP temporalmente no disponible; última salida válida preservada ({type(exc).__name__})") from None


def _response(value, url: str) -> Download:
    if isinstance(value, Download):
        return value
    if isinstance(value, bytes):
        return Download(value, 200, "text/html; charset=utf-8", url)
    if isinstance(value, tuple):
        body, *rest = value
        return Download(body, rest[0] if rest else 200,
                        rest[1] if len(rest) > 1 else "text/html; charset=utf-8",
                        rest[2] if len(rest) > 2 else url)
    raise RiceError("Descarga inyectada inválida")


def parse_page(payload: bytes) -> RicePage:
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_PAGE_BYTES:
        raise RiceError("Respuesta HTML vacía o demasiado grande")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeError:
        raise RiceError("Codificación oficial no reconocida") from None
    page = RicePage()
    try:
        page.feed(text)
        page.close()
    except Exception:
        raise RiceError("HTML oficial no parseable") from None
    return page


def capture_raw(data_root: Path, family: str, label: str, response: Download,
                captured_at: str) -> dict:
    digest = sha256(response.body)
    capture_id = captured_at.replace(":", "").replace("-", "").replace(".", "") + "_" + uuid.uuid4().hex[:12]
    folder = data_root / "raw" / "rice_prices" / family / capture_id
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "response.html").write_bytes(response.body)
    manifest = {
        "schema_version": PARSER_VERSION, "source_family": family,
        "label": label, "source_url": response.url,
        "captured_at_utc": captured_at, "http_status": response.status,
        "content_type": response.content_type, "bytes": len(response.body),
        "raw_sha256": digest, "capture_id": capture_id,
        "validation_status": "CAPTURED", "private_state_stored": False,
    }
    atomic_write(folder / "manifest.json", json_bytes(manifest))
    return {**manifest, "folder": folder}


def finish_capture(capture: dict, status: str, count: int, diagnostic: str = "") -> None:
    manifest = {key: value for key, value in capture.items() if key != "folder"}
    manifest.update(validation_status=status, validated_record_count=count)
    if diagnostic:
        manifest["diagnostic_note"] = diagnostic
    atomic_write(capture["folder"] / "manifest.json", json_bytes(manifest))


def parse_number(raw: str, style: str) -> tuple[str, str]:
    value = " ".join((raw or "").replace("\xa0", " ").split())
    if value in {"", "-", "—", "S/C", "SC", "N/D"}:
        return "", "missing"
    if value.endswith("*") and style == "ar":
        value = value[:-1].strip()
    if style == "ar":
        if not re.fullmatch(r"\d+(?:\.\d{3})*(?:,\d+)?", value):
            raise RiceError("Formato numérico MAGyP interno cambió")
        canonical = value.replace(".", "").replace(",", ".")
    elif style == "us":
        if not re.fullmatch(r"\d+(?:,\d{3})*(?:\.\d+)?", value):
            raise RiceError("Formato numérico MAGyP FOB cambió")
        canonical = value.replace(",", "")
    else:
        raise RiceError("Regla numérica desconocida")
    try:
        number = Decimal(canonical)
    except InvalidOperation:
        raise RiceError("Precio oficial inválido") from None
    if not number.is_finite() or number < 0:
        raise RiceError("Precio no finito o negativo")
    return format(number, "f"), "positive" if number > 0 else "zero"


def parse_internal(payload: bytes, as_of: date) -> list[dict]:
    page = parse_page(payload)
    if "PESOS ARGENTINOS POR QUINTAL" not in normalized_text(" ".join(page.text)):
        raise RiceError("La unidad/quintal de la fuente interna cambió")
    headers = []
    for table_index, table in enumerate(page.tables):
        for row_index, row in enumerate(table):
            clean = [normalized_text(cell) for cell in row]
            if len(clean) >= 3 and clean[0] in {"ANO/MES", "ANO / MES"} and clean[1:3] == ["LARGO FINO", "LARGO ANCHO"]:
                headers.append((table_index, row_index))
    if len(headers) != 1:
        raise RiceError("Tabla interna de arroz no identificada o duplicada")
    table_index, header_row = headers[0]
    cells = []
    seen = {}
    for offset, row in enumerate(page.tables[table_index][header_row + 1:], start=header_row + 1):
        if not row or not re.fullmatch(r"\d{4}/\d{1,2}", row[0].strip()):
            continue
        if len(row) != 3:
            raise RiceError("Cantidad de columnas de arroz interno cambió")
        year, month = map(int, row[0].split("/"))
        if not 1 <= month <= 12:
            raise RiceError("Mes de arroz interno inválido")
        period = date(year, month, 1).isoformat()
        locator = f"table[{table_index}]/row[{offset}]/{row[0]}"
        raw_values = (row[1], row[2])
        if period in seen:
            previous, existing_values = seen[period]
            if raw_values != existing_values:
                raise RiceError("Filas duplicadas/conflictivas en arroz interno")
            previous.setdefault("duplicate_source_rows", []).append(locator)
            continue
        parsed_values = [("LARGO FINO", row[1], *parse_number(row[1], "ar")),
                         ("LARGO ANCHO", row[2], *parse_number(row[2], "ar"))]
        if date(year, month, 1) > as_of:
            if any(status != "missing" for _, _, _, status in parsed_values):
                raise RiceError("Período de arroz interno posterior a la fecha de control")
            continue
        cell = {
            "fecha": period, "periodo_ym": period[:7],
            "values": parsed_values,
            "source_locator": locator, "duplicate_source_rows": [],
        }
        seen[period] = (cell, raw_values)
        cells.append(cell)
    if len(cells) < 1 or not any(status == "positive" for cell in cells for _, _, _, status in cell["values"]):
        raise RiceError("La tabla interna no contiene precios positivos")
    return cells


def canonical_historical_url(value: str) -> str:
    absolute = urljoin(FOB_URL, value)
    parts = urlsplit(absolute)
    decoded_path = unquote(parts.path)
    if (parts.hostname not in {"www.magyp.gob.ar", "magyp.gob.ar"}
            or "/000052_Arroz/000002_Hist" not in decoded_path
            or not re.search(r"\d{6}_\d{4}\.php$", decoded_path)):
        raise RiceError("Vínculo de histórico FOB fuera del catálogo MAGyP esperado")
    path = quote(decoded_path, safe="/-_.%")
    return urlunsplit(("https", "www.magyp.gob.ar", path, "", ""))


def parse_fob_page(payload: bytes, expected_year: int | None = None):
    page = parse_page(payload)
    body_text = normalized_text(" ".join(page.text))
    # MAGyP's current page uses both "U$S/Ton FOB" and "U$S/Ton. FOB".
    if "ARROZ" not in body_text or "FOB" not in body_text or "TON" not in body_text:
        raise RiceError("Definición FOB de arroz no identificada")
    found = []
    for table_index, table in enumerate(page.tables):
        for row_index, row in enumerate(table):
            if len(row) > 1 and re.fullmatch(r"20\d{2}", row[0].strip()):
                year = int(row[0])
                if expected_year is not None and year != expected_year:
                    raise RiceError("Año en página histórica FOB no coincide con el catálogo")
                labels = row[1:]
                expected_labels = FOB_LABELS_2017_2024 if 2017 <= year <= 2024 else FOB_LABELS_2025_ON
                if [normalized_text(value) for value in labels] != [normalized_text(x) for x in expected_labels]:
                    raise RiceError("Origen/calidad FOB cambió respecto de las etiquetas históricas verificadas")
                found.append((table_index, row_index, year, table, labels))
    if len(found) != 1:
        raise RiceError("Tabla anual FOB de arroz no identificada o duplicada")
    table_index, header_row, year, table, labels = found[0]
    if "OSIRIZ/INFOARRO" not in body_text:
        raise RiceError("Atribución de origen Osiriz/InfoArro no reconocida")
    months = {}
    values = []
    for row_index, row in enumerate(table[header_row + 1:], start=header_row + 1):
        if not row:
            continue
        match = re.fullmatch(r"([A-Z]{3})(?:\s+(\d{2,4}))?", normalized_text(row[0]))
        if not match or match.group(1) not in MONTHS:
            continue
        month_label, year_label = match.groups()
        if year_label and int(year_label[-2:]) != year % 100:
            raise RiceError("Año rotulado en mes FOB no coincide con la tabla")
        month = MONTHS[month_label]
        if month in months:
            raise RiceError("Mes duplicado en la tabla FOB")
        if len(row) != len(labels) + 1:
            raise RiceError("Cantidad de columnas FOB cambió")
        months[month] = row_index
        for col, (label, raw) in enumerate(zip(labels, row[1:]), start=1):
            price, status = parse_number(raw, "us")
            values.append({
                "fecha": date(year, month, 1).isoformat(),
                "periodo_ym": f"{year:04d}-{month:02d}",
                "origin_quality": label, "price_raw": raw,
                "price": price, "value_status": status,
                "source_locator": f"table[{table_index}]/row[{row_index}]/column[{col}]",
            })
    if not months:
        raise RiceError("La tabla FOB no declara meses")
    if not any(row["value_status"] == "positive" for row in values):
        raise RiceError("La tabla FOB no contiene precios positivos")
    history_options = []
    for value, label in page.options:
        match = re.fullmatch(r"20\d{2}", label.strip())
        if match:
            history_options.append((int(label), canonical_historical_url(value)))
    return year, values, history_options, labels


def monthly_a3500(path: Path, as_of: date) -> tuple[dict, dict]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise RiceError("Serie BCRA A3500 local no disponible o inválida") from None
    if (document.get("schema_version") != "bcra-a3500-v1"
            or document.get("source_url") != BCRA_URL
            or not re.fullmatch(r"[a-f0-9]{64}", str(document.get("raw_sha256", "")))
            or not isinstance(document.get("rates"), list) or not document["rates"]):
        raise RiceError("Contrato de la serie BCRA A3500 cambió")
    rates = {}
    previous = None
    for row in document["rates"]:
        if not isinstance(row, list) or len(row) != 2:
            raise RiceError("Fila de la serie BCRA A3500 inválida")
        try:
            day = date.fromisoformat(row[0])
            value = Decimal(str(row[1]))
        except (ValueError, TypeError, InvalidOperation):
            raise RiceError("Fecha/cotización BCRA inválida") from None
        if (day.isoformat() != row[0] or day > as_of or (previous and day <= previous)
                or not value.is_finite() or value <= 0):
            raise RiceError("Orden/valor de la serie BCRA A3500 inválido")
        previous = day
        rates.setdefault(day.strftime("%Y-%m"), []).append((day, value))
    months = sorted(rates)
    if len(months) < 2:
        raise RiceError("Cobertura mensual BCRA A3500 insuficiente")
    first_month, latest_month = months[0], months[-1]
    averages = {}
    for month in months:
        # First month is partial because the bundled A3500 starts on 2022-05-17;
        # last month may still be in progress. Neither is treated as a monthly rate.
        if month <= first_month or month >= latest_month:
            continue
        items = rates[month]
        average = sum((item[1] for item in items), Decimal(0)) / Decimal(len(items))
        averages[month] = {
            "average": average.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            "count": len(items), "first_date": items[0][0].isoformat(),
            "last_date": items[-1][0].isoformat(),
        }
    return averages, {
        "sha256": str(document["raw_sha256"]), "url": document["source_url"],
        "landing": document.get("source"), "first_month": first_month,
        "latest_month": latest_month, "latest_date": previous.isoformat(),
    }


def _base_row(family: str, day: str, commodity: str, market: str, kind: str,
              currency: str, unit: str, raw: str, price: str, value_status: str,
              source_url: str, capture: dict, locator: str, condition: str = "",
              extra: dict | None = None) -> dict:
    row = {field: "" for field in FIELDS}
    row.update({
        "row_kind": "observation", "fecha": day, "periodo_ym": day[:7],
        "commodity": commodity, "fuente": "MAGyP", "mercado": market,
        "tipo_precio": kind, "moneda": currency, "unidad": unit,
        "frecuencia": "mensual", "condicion_comercial": condition,
        "price_raw": raw, "price": price, "value_status": value_status,
        "currency_evidence": "documented", "source_url": source_url,
        "updated_at_utc": capture["captured_at_utc"],
        "raw_sha256": capture["raw_sha256"], "capture_id": capture["capture_id"],
        "schema_version": VERSION, "coverage_note": "",
        "source_locator": locator,
    })
    series_identity = [family, commodity, market, kind, currency, unit, condition]
    row["series_id"] = stable_id(series_identity)
    row["observation_id"] = stable_id([row["series_id"], day])
    row["record_id"] = stable_id([row["observation_id"], row["capture_id"], row["raw_sha256"]])
    if extra:
        row.update(extra)
    return row


def _internal_rows(cells: list[dict], capture: dict, fx_months: dict,
                   fx_meta: dict) -> list[dict]:
    result = []
    for cell in cells:
        day, period = cell["fecha"], cell["periodo_ym"]
        for variety, raw, source_price, source_status in cell["values"]:
            commodity = f"Arroz cáscara — {variety.lower()}"
            extra = {
                "rice_variety_raw": variety, "price_raw_source": raw,
                "price_original_ars_qq": source_price,
                "source_locator": cell["source_locator"],
                "duplicate_source_rows": "|".join(cell.get("duplicate_source_rows", [])),
                "source_marker": "*" if raw.strip().endswith("*") else "",
                "fx_a3500_raw_sha256": fx_meta["sha256"],
                "fx_a3500_source_url": fx_meta["url"],
            }
            base = _base_row("rice_internal", day, commodity,
                "Mercado interno · plaza no informada", INTERNAL_BASE_TYPE,
                "ARS", "QQ", raw, source_price, source_status, INTERNAL_URL,
                capture, cell["source_locator"], variety, extra)
            base["coverage_note"] = (
                "Precio interno mensual de arroz cáscara; MAGyP no identifica una plaza/provincia "
                "en esta tabla. No es arroz elaborado ni necesariamente una cotización de productores correntinos."
            )
            if raw.strip().endswith("*"):
                base["coverage_note"] += " La fuente marca este valor con * y no explica el marcador en la tabla; se conserva en bruto."
            if cell.get("duplicate_source_rows"):
                base["coverage_note"] += " La tabla repitió una fila idéntica del mismo mes; se cuenta una sola vez y se conserva su ubicación duplicada."
            result.append(base)
            if source_status != "positive":
                continue
            price = Decimal(source_price)
            kg_value = format(price / Decimal(100), "f")
            kg = _base_row("rice_internal", day, commodity,
                "Mercado interno · plaza no informada", INTERNAL_KG_TYPE,
                "ARS", "KG", kg_value, kg_value, "positive", INTERNAL_URL,
                capture, cell["source_locator"], variety, {
                    **extra, "conversion_method": "1 QQ métrico = 100 KG; ARS/KG = ARS/QQ ÷ 100",
                })
            kg["coverage_note"] = "Conversión de unidad aritmética de la observación original en ARS/QQ; 1 quintal métrico = 100 kg."
            result.append(kg)
            fx = fx_months.get(period)
            if fx:
                fx_value = format(fx["average"], "f")
                usd_value = format((price / fx["average"]).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP), "f")
                usd = _base_row("rice_internal", day, commodity,
                    "Mercado interno · plaza no informada", INTERNAL_USD_TYPE,
                    "USD", "QQ", usd_value, usd_value, "positive", INTERNAL_URL,
                    capture, cell["source_locator"], variety, {
                        **extra, "fx_a3500_monthly_avg": fx_value,
                        "fx_a3500_observations": fx["count"],
                        "fx_a3500_first_date": fx["first_date"],
                        "fx_a3500_last_date": fx["last_date"],
                        "conversion_method": (
                            "USD/QQ = ARS/QQ ÷ media aritmética de cotizaciones diarias BCRA A3500 "
                            "publicadas en el mismo mes calendario; sin conversión para meses parciales"
                        ),
                    })
                usd["coverage_note"] = (
                    "Equivalencia calculada con promedio mensual simple de cotizaciones diarias A3500 del mismo mes; "
                    "no es precio USD publicado por MAGyP ni promedio mensual oficial del BCRA."
                )
                result.append(usd)
    return result


def _fob_rows(values: list[dict], capture: dict) -> list[dict]:
    result = []
    for item in values:
        label = item["origin_quality"]
        row = _base_row("rice_fob", item["fecha"], f"Arroz FOB · {label}",
            "Mercado internacional", FOB_TYPE, "USD", "TN",
            item["price_raw"], item["price"], item["value_status"],
            capture["source_url"], capture, item["source_locator"], label,
            {"fob_origin_quality_raw": label, "price_raw_source": item["price_raw"]})
        row["coverage_note"] = (
            "Referencia mensual internacional FOB en USD por tonelada, publicada por MAGyP; "
            "la página atribuye la serie a Osiriz/InfoArro. Se conserva la etiqueta original de origen/calidad."
        )
        result.append(row)
    return result


def build_bundle(observations: list[dict]) -> bytes:
    positives = [row for row in observations if row["value_status"] == "positive"]
    if not positives:
        raise RiceError("No hay observaciones positivas para publicar")
    output = [{**row, "row_kind": "observation"} for row in observations]
    monthly = []
    by_series = {}
    for row in positives:
        key = (row["series_id"], row["periodo_ym"])
        if key in {(item["series_id"], item["periodo_ym"]) for item in monthly}:
            raise RiceError("Serie mensual duplicada en la salida")
        item = {**row, "row_kind": "mensual", "operaciones": 1,
                "precio_mediana": row["price"], "precio_promedio": row["price"],
                "precio_min": row["price"], "precio_max": row["price"],
                "coverage_note": row["coverage_note"]}
        monthly.append(item)
        by_series.setdefault(row["series_id"], []).append(item)
    for series in by_series.values():
        series.sort(key=lambda row: row["periodo_ym"])
        lookup = {row["periodo_ym"]: Decimal(row["price"]) for row in series}
        for row in series:
            year, month = map(int, row["periodo_ym"].split("-"))
            previous_month = f"{(year * 12 + month - 2) // 12:04d}-{(year * 12 + month - 2) % 12 + 1:02d}"
            prior_year = f"{year - 1:04d}-{month:02d}"
            row["variacion_mensual_pct"] = ref.pct(row["price"], lookup.get(previous_month))
            row["variacion_interanual_pct"] = ref.pct(row["price"], lookup.get(prior_year))
            row["estado"] = ref.state(row["variacion_mensual_pct"])
        last = series[-1]
        output.append({**last, "row_kind": "ultimos",
            "periodo_ultimo": last["periodo_ym"], "fecha_ultima": last["fecha"],
            "precio_mediana_ultimo_periodo": last["price"], "operaciones_ultimo_periodo": 1})
    output.extend(monthly)
    output.extend({**row, "row_kind": "semaforo"} for row in monthly)
    summary = {
        "row_kind": "resumen", "fecha_min": min(row["fecha"] for row in positives),
        "fecha_max": max(row["fecha"] for row in positives),
        "filas_dashboard": len(positives),
        "fecha_actualizacion_dashboard": max(row["updated_at_utc"] for row in positives),
        "source_url": positives[0]["source_url"], "schema_version": VERSION,
    }
    output.append(summary)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter=";", lineterminator="\n",
                            extrasaction="raise")
    writer.writeheader()
    writer.writerows(output)
    payload = stream.getvalue().encode("utf-8")
    validate_bundle(payload)
    return payload


def validate_bundle(payload: bytes) -> list[dict]:
    try:
        rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""), delimiter=";"))
    except (UnicodeError, csv.Error):
        raise RiceError("CSV de arroz ilegible") from None
    if not rows or set(rows[0]) != set(FIELDS):
        raise RiceError("Schema del CSV de arroz inválido")
    summaries = [row for row in rows if row["row_kind"] == "resumen"]
    observations = [row for row in rows if row["row_kind"] == "observation"]
    if len(summaries) != 1 or not observations:
        raise RiceError("Dashboard de arroz incompleto")
    if any(row["schema_version"] != VERSION for row in rows):
        raise RiceError("Versión de dashboard de arroz desconocida")
    ids = set()
    for row in observations:
        if row["row_kind"] not in {"observation"}:
            raise RiceError("Tipo de fila de arroz inválido")
        if (not re.fullmatch(r"[a-f0-9]{64}", row["raw_sha256"])
                or not re.fullmatch(r"[a-f0-9]{64}", row["series_id"])
                or not re.fullmatch(r"[a-f0-9]{64}", row["observation_id"])
                or row["observation_id"] in ids or not row["record_id"]):
            raise RiceError("Identidad/trazabilidad de arroz inválida")
        ids.add(row["observation_id"])
        try:
            if date.fromisoformat(row["fecha"]).isoformat() != row["fecha"]:
                raise ValueError()
        except ValueError:
            raise RiceError("Fecha de arroz inválida") from None
        if row["periodo_ym"] != row["fecha"][:7] or row["frecuencia"] != "mensual":
            raise RiceError("Período/frecuencia de arroz inválidos")
        value, state = ref.number(row["price"], "json") if row["price"] else ("", "missing")
        if state != row["value_status"]:
            raise RiceError("Precio/estado de arroz incoherentes")
        if row["fuente"] != "MAGyP" or not row["source_url"].startswith("https://www.magyp.gob.ar/"):
            raise RiceError("Fuente MAGyP de arroz inválida")
    positive_count = sum(row["value_status"] == "positive" for row in observations)
    if positive_count <= 0 or int(summaries[0]["filas_dashboard"]) != positive_count:
        raise RiceError("Conteo positivo del dashboard de arroz no coincide")
    if any(row["row_kind"] not in {"observation", "mensual", "ultimos", "semaforo", "resumen"} for row in rows):
        raise RiceError("Vista desconocida en el dashboard de arroz")
    for row in rows:
        if row["row_kind"] in {"mensual", "ultimos", "semaforo"}:
            if ref.number(row["precio_mediana"], "json")[1] != "positive":
                raise RiceError("Vista mensual de arroz sin precio positivo")
    return rows


def read_bundle(path: Path) -> list[dict]:
    if not path.exists():
        return []
    payload = path.read_bytes()
    if path.suffix == ".gz" or payload.startswith(b"\x1f\x8b"):
        payload = gzip.decompress(payload)
    return validate_bundle(payload)


def gzip_bundle(payload: bytes) -> bytes:
    """Return a deterministic compressed CSV after validating its full schema."""
    validate_bundle(payload)
    packed = gzip.compress(payload, mtime=0)
    validate_bundle(gzip.decompress(packed))
    return packed


def _base_signature(rows: list[dict], family: str) -> dict:
    result = {}
    for row in rows:
        if row["row_kind"] != "observation":
            continue
        if family == "rice_internal" and row["tipo_precio"] != INTERNAL_BASE_TYPE:
            continue
        if family == "rice_fob" and row["tipo_precio"] != FOB_TYPE:
            continue
        key = (row["periodo_ym"], row["rice_variety_raw"] or row["fob_origin_quality_raw"])
        result[key] = (row["value_status"], row["price"])
    return result


def _check_history(previous: list[dict], incoming: list[dict], family: str) -> None:
    old = _base_signature(previous, family)
    new = _base_signature(incoming, family)
    if old and not old.keys() <= new.keys():
        raise RiceError("La captura reduce períodos/series históricas; última salida válida preservada")
    for key, (status, value) in old.items():
        new_status, _new_value = new[key]
        if status == "positive" and new_status != "positive":
            raise RiceError("La captura reemplaza un precio histórico por una celda vacía/cero; última salida preservada")


def _value_signature(rows: list[dict]) -> str:
    values = []
    for row in rows:
        if row["row_kind"] != "observation":
            continue
        values.append((row["series_id"], row["fecha"], row["price"], row["value_status"],
                       row["price_raw_source"], row["fx_a3500_monthly_avg"]))
    return stable_id(sorted(values))


def _current_state(path: Path, family: str, requested: date, attempted: str,
                   previous_state: dict, status: str, diagnostic: str,
                   evidence: list[dict], rows: list[dict]) -> dict:
    positive = [row for row in rows if row["row_kind"] == "observation" and row["value_status"] == "positive"]
    last_date = max((row["fecha"] for row in positive), default=previous_state.get("last_valid_date"))
    old_success = previous_state.get("last_successful_update")
    success = attempted if status in {"UPDATED", "NO_PUBLICATION"} else old_success
    latest_month = last_date[:7] if last_date else None
    current_published = bool(latest_month and latest_month >= requested.strftime("%Y-%m"))
    record = {
        "source_family": family, "source": "MAGyP", "status": status,
        "publication_status": ("NOT_CHECKED" if status in {"SOURCE_UNAVAILABLE", "PIPELINE_ERROR"}
                               else "PUBLISHED" if current_published else "NO_PUBLICATION"),
        "requested_date": requested.isoformat(), "attempted_at": attempted,
        "last_observation_date": last_date, "last_valid_date": last_date,
        "last_successful_update": success,
        "frequency": "mensual", "automatic_update": True,
        "raw_evidence": evidence or previous_state.get("raw_evidence", []),
        "diagnostic_note": diagnostic or None,
    }
    if family == "rice_internal":
        record.update(source_url=INTERNAL_URL, market="Mercado interno · plaza no informada",
                      currency=["ARS", "USD"], unit=["QQ", "KG"],
                      notes="Arroz cáscara largo fino y largo ancho; USD es equivalencia A3500 derivada.")
    else:
        record.update(source_url=FOB_URL, market="Mercado internacional FOB",
                      currency=["USD"], unit=["TN"],
                      notes="Serie mensual separada; conserva origen/calidad según la etiqueta de MAGyP.")
    if status in {"SOURCE_UNAVAILABLE", "PIPELINE_ERROR"} and not last_date:
        record["last_valid_date"] = previous_state.get("last_valid_date")
        record["last_observation_date"] = previous_state.get("last_observation_date")
    return record


def update_internal(data_root: Path, as_of: date, fetcher=download,
                    bcra_path: Path | None = None) -> tuple[str, dict]:
    data_root = Path(data_root)
    dashboard = data_root / "dashboard" / "commodities" / "rice_internal.csv.gz"
    status_path = data_root / "reports" / "RICE_PRICES_STATUS.json"
    previous = read_bundle(dashboard)
    old_status = json.loads(status_path.read_text("utf-8")) if status_path.exists() else {}
    previous_state = old_status.get("sources", {}).get("rice_internal", {})
    attempted = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    evidence = []
    capture = None
    try:
        response = _response(fetcher(INTERNAL_URL), INTERNAL_URL)
        if response.status != 200 or len(response.body) > MAX_PAGE_BYTES:
            raise SourceUnavailable("Respuesta MAGyP interna no disponible; última salida válida preservada")
        capture = capture_raw(data_root, "rice_internal", "actual", response, attempted)
        evidence.append({key: capture[key] for key in ("label", "source_url", "capture_id", "raw_sha256", "bytes")})
        cells = parse_internal(response.body, as_of)
        duplicate_rows = sum(len(cell.get("duplicate_source_rows", [])) for cell in cells)
        capture["identical_duplicate_source_rows"] = duplicate_rows
        fx_path = bcra_path or ROOT / "data" / "carnes" / "dashboard" / "bcra_a3500.json"
        fx_months, fx_meta = monthly_a3500(fx_path, as_of)
        observations = _internal_rows(cells, capture, fx_months, fx_meta)
        _check_history(previous, observations, "rice_internal")
        new_payload = build_bundle(observations)
        new_rows = validate_bundle(new_payload)
        if previous and _value_signature(previous) == _value_signature(new_rows):
            status = "NO_PUBLICATION"
            finish_capture(capture, status, len(cells))
            rows = previous
        else:
            status = "UPDATED"
            finish_capture(capture, status, len(cells))
            atomic_write(dashboard, gzip_bundle(new_payload))
            rows = new_rows
        record = _current_state(dashboard, "rice_internal", as_of, attempted,
                                previous_state, status, "", evidence, rows)
        record["identical_duplicate_source_rows"] = duplicate_rows
        if duplicate_rows:
            record["notes"] += f" La tabla fuente contenía {duplicate_rows} fila(s) mensual(es) repetida(s) con valores idénticos; se deduplican y quedan localizables en RAW/CSV."
        return status, record
    except SourceUnavailable as error:
        if capture:
            finish_capture(capture, "SOURCE_UNAVAILABLE", 0, str(error))
        return "SOURCE_UNAVAILABLE", _current_state(dashboard, "rice_internal", as_of,
            attempted, previous_state, "SOURCE_UNAVAILABLE", str(error), evidence, previous)
    except Exception as error:
        diagnostic = str(error) if isinstance(error, RiceError) else f"{type(error).__name__}: {error}"
        if not isinstance(error, RiceError):
            traceback.print_exc()
        if capture:
            finish_capture(capture, "PIPELINE_ERROR", 0, diagnostic)
        return "PIPELINE_ERROR", _current_state(dashboard, "rice_internal", as_of,
            attempted, previous_state, "PIPELINE_ERROR", diagnostic, evidence, previous)


def update_fob(data_root: Path, as_of: date, fetcher=download) -> tuple[str, dict]:
    data_root = Path(data_root)
    dashboard = data_root / "dashboard" / "commodities" / "rice_fob.csv.gz"
    status_path = data_root / "reports" / "RICE_PRICES_STATUS.json"
    previous = read_bundle(dashboard)
    old_status = json.loads(status_path.read_text("utf-8")) if status_path.exists() else {}
    previous_state = old_status.get("sources", {}).get("rice_fob", {})
    attempted = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    captures = []
    evidence = []
    try:
        current_response = _response(fetcher(FOB_URL), FOB_URL)
        if current_response.status != 200 or len(current_response.body) > MAX_PAGE_BYTES:
            raise SourceUnavailable("Respuesta MAGyP FOB no disponible; última salida válida preservada")
        current_capture = capture_raw(data_root, "rice_fob", "actual", current_response, attempted)
        captures.append(current_capture)
        evidence.append({key: current_capture[key] for key in ("label", "source_url", "capture_id", "raw_sha256", "bytes")})
        year, current_values, options, _labels = parse_fob_page(current_response.body)
        listed = dict(options)
        expected_years = list(range(2017, year + 1))
        if sorted(set(listed)) != expected_years:
            raise RiceError("El catálogo histórico FOB no cubre todos los años verificados desde 2017")
        all_values = list(current_values)
        response_by_year = {year: current_response}
        capture_by_year = {year: current_capture}
        for historical_year in expected_years[:-1]:
            url = listed[historical_year]
            historical_response = _response(fetcher(url), url)
            if historical_response.status != 200 or len(historical_response.body) > MAX_PAGE_BYTES:
                raise SourceUnavailable(f"Histórico FOB {historical_year} temporalmente no disponible; última salida válida preservada")
            historical_capture = capture_raw(data_root, "rice_fob", str(historical_year),
                                             historical_response, attempted)
            captures.append(historical_capture)
            evidence.append({key: historical_capture[key] for key in ("label", "source_url", "capture_id", "raw_sha256", "bytes")})
            try:
                found_year, values, _, _labels = parse_fob_page(historical_response.body, historical_year)
            except Exception as error:
                finish_capture(historical_capture, "PIPELINE_ERROR", 0,
                               str(error) if isinstance(error, RiceError) else "Error interno de validación")
                raise
            response_by_year[found_year] = historical_response
            capture_by_year[found_year] = historical_capture
            all_values.extend(values)
            time.sleep(0.15)
        observations = []
        for item in all_values:
            if item["value_status"] != "missing" and date.fromisoformat(item["fecha"]) > as_of:
                raise RiceError("Observación FOB posterior a la fecha de control")
            capture = capture_by_year[int(item["fecha"][:4])]
            observations.extend(_fob_rows([item], capture))
        _check_history(previous, observations, "rice_fob")
        new_payload = build_bundle(observations)
        new_rows = validate_bundle(new_payload)
        if previous and _value_signature(previous) == _value_signature(new_rows):
            status = "NO_PUBLICATION"
            rows = previous
        else:
            status = "UPDATED"
            atomic_write(dashboard, gzip_bundle(new_payload))
            rows = new_rows
        for capture in captures:
            finish_capture(capture, status, sum(1 for row in observations if row["capture_id"] == capture["capture_id"]))
        return status, _current_state(dashboard, "rice_fob", as_of, attempted,
                                      previous_state, status, "", evidence, rows)
    except SourceUnavailable as error:
        for capture in captures:
            finish_capture(capture, "SOURCE_UNAVAILABLE", 0, str(error))
        return "SOURCE_UNAVAILABLE", _current_state(dashboard, "rice_fob", as_of,
            attempted, previous_state, "SOURCE_UNAVAILABLE", str(error), evidence, previous)
    except Exception as error:
        diagnostic = str(error) if isinstance(error, RiceError) else f"{type(error).__name__}: {error}"
        if not isinstance(error, RiceError):
            traceback.print_exc()
        for capture in captures:
            manifest_path = capture["folder"] / "manifest.json"
            manifest = json.loads(manifest_path.read_text("utf-8"))
            if manifest.get("validation_status") == "CAPTURED":
                finish_capture(capture, "PIPELINE_ERROR", 0, diagnostic)
        return "PIPELINE_ERROR", _current_state(dashboard, "rice_fob", as_of,
            attempted, previous_state, "PIPELINE_ERROR", diagnostic, evidence, previous)


def validate_publication(data_root: Path) -> dict:
    data_root = Path(data_root)
    internal = read_bundle(data_root / "dashboard" / "commodities" / "rice_internal.csv.gz")
    fob = read_bundle(data_root / "dashboard" / "commodities" / "rice_fob.csv.gz")
    status = json.loads((data_root / "reports" / "RICE_PRICES_STATUS.json").read_text("utf-8"))
    if status.get("schema_version") != STATUS_VERSION or set(status.get("sources", {})) != {"rice_internal", "rice_fob"}:
        raise RiceError("Estado RICE_PRICES_STATUS incompleto")
    for key, expected in (("rice_internal", INTERNAL_BASE_TYPE), ("rice_fob", FOB_TYPE)):
        record = status["sources"][key]
        if record.get("source_family") != key or record.get("status") not in STATES:
            raise RiceError("Estado operacional de arroz inválido")
        observations = [row for row in (internal if key == "rice_internal" else fob)
                        if row["row_kind"] == "observation" and row["tipo_precio"].startswith(expected)]
        if not observations or any(not row["source_url"] or not row["raw_sha256"] for row in observations):
            raise RiceError("Observaciones publicadas de arroz sin trazabilidad")
    return status


def update(data_root: Path, as_of: date, fetcher=download,
           bcra_path: Path | None = None, sources=None) -> dict:
    data_root = Path(data_root)
    status_path = data_root / "reports" / "RICE_PRICES_STATUS.json"
    try:
        prior = json.loads(status_path.read_text("utf-8")) if status_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        prior = {}
    state = {key: dict(value) for key, value in prior.get("sources", {}).items()
             if key in {"rice_internal", "rice_fob"}}
    selected = set(sources or ["internal", "fob"])
    for source in ("internal", "fob"):
        if source not in selected:
            continue
        key = f"rice_{source}"
        try:
            if source == "internal":
                result, record = update_internal(data_root, as_of, fetcher, bcra_path)
            else:
                result, record = update_fob(data_root, as_of, fetcher)
        except Exception as error:
            diagnostic = str(error) if isinstance(error, RiceError) else f"{type(error).__name__}: {error}"
            traceback.print_exc()
            result = "PIPELINE_ERROR"
            record = {
                **state.get(key, {}), "source_family": key, "source": "MAGyP",
                "status": result, "requested_date": as_of.isoformat(),
                "attempted_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "last_valid_date": state.get(key, {}).get("last_valid_date"),
                "last_observation_date": state.get(key, {}).get("last_observation_date"),
                "diagnostic_note": diagnostic,
            }
        state[key] = record
        print(f"[RICE] {key} {result} last={record.get('last_observation_date')} "
              f"{record.get('diagnostic_note') or ''}".rstrip())
    document = {
        "schema_version": STATUS_VERSION,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sources": {key: state[key] for key in ("rice_internal", "rice_fob") if key in state},
    }
    atomic_write(status_path, json_bytes(document))
    if selected == {"internal", "fob"}:
        return document
    return document


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-web", action="store_true")
    # Actions passes an explicit Argentina-local --as-of; date.today() keeps the
    # local CLI usable on Windows without requiring an external IANA tzdata package.
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--data-root", type=Path, default=ROOT / "data" / "magyp")
    parser.add_argument("--bcra-file", type=Path, default=ROOT / "data" / "carnes" / "dashboard" / "bcra_a3500.json")
    parser.add_argument("--source", choices=["all", "internal", "fob"], default="all")
    parser.add_argument("--validate", action="store_true", help="Valida ambos bundles y el estado sin red")
    args = parser.parse_args(argv)
    if args.validate:
        validate_publication(args.data_root)
        print("[VALIDATE] CSV y estado de arroz válidos")
        return 0
    if not args.allow_web:
        parser.error("Use --allow-web para consultar páginas oficiales MAGyP")
    selected = None if args.source == "all" else [args.source]
    state = update(args.data_root, args.as_of, download, args.bcra_file, selected)
    required = [args.data_root / "dashboard" / "commodities" / name
                for name in ("rice_internal.csv.gz", "rice_fob.csv.gz")]
    if all(path.exists() for path in required):
        validate_publication(args.data_root)
    else:
        print("[VALIDATE] Falta una salida inicial sin versión previa válida; revisar estado por fuente.", file=sys.stderr)
        return 1
    failed = any(row["status"] in {"SOURCE_UNAVAILABLE", "PIPELINE_ERROR"}
                 for key, row in state["sources"].items()
                 if selected is None or key.endswith(selected[0]))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
