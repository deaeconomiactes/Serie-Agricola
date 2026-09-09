#!/usr/bin/env python3
"""Utilidades compartidas para el pipeline de commodities locales mensuales."""

from __future__ import annotations

import csv
import json
from html import unescape
from html.parser import HTMLParser
import re
import unicodedata
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


csv.field_size_limit(2**31 - 1)

ROOT = Path(__file__).resolve().parent
DEFAULT_RAW_DIR = ROOT / "data" / "commodities_local_mensual" / "raw"
DEFAULT_PROCESSED_DIR = ROOT / "data" / "commodities_local_mensual" / "processed"
DEFAULT_DASHBOARD_DIR = ROOT / "data" / "commodities_local_mensual" / "dashboard"
DEFAULT_REPORT_DIR = ROOT / "data" / "commodities_local_mensual" / "reports"
DEFAULT_CONFIG_PATH = ROOT / "data" / "commodities_local_mensual" / "fuentes_local_mensual_config.json"
DEFAULT_CONFIG_EXAMPLE_PATH = ROOT / "data" / "commodities_local_mensual" / "fuentes_local_mensual_config.example.json"

INTEGRATED_FIELDS = [
    "fecha", "año", "mes", "periodo_ym", "commodity", "fuente", "mercado",
    "tipo_precio", "moneda", "unidad", "precio", "frecuencia", "archivo_origen",
    "fecha_integracion", "observaciones",
]

HEADER_ALIASES = {
    "fecha": ["fecha", "date", "fecha observacion", "fecha mercado", "fecha precio", "fecha de mercado"],
    "periodo": ["periodo", "periodo ym", "periodo mensual", "mes", "month", "fecha mes", "mes año", "month year"],
    "año": ["año", "ano", "year"],
    "mes": ["mes", "month", "numero mes", "n mes"],
    "commodity": ["commodity", "producto", "grano", "grano oleaginosa", "especie", "producto agricola"],
    "fuente": ["fuente", "source", "organismo", "institucion", "institución", "origen fuente"],
    "mercado": ["mercado", "market", "ambito", "ámbito", "plaza", "mercado referencia"],
    "tipo_precio": ["tipo precio", "tipo de precio", "tipo", "price type", "referencia", "concepto"],
    "moneda": ["moneda", "currency", "divisa", "moneda precio"],
    "unidad": ["unidad", "unit", "unidad precio", "unidad del precio", "unidad medida"],
    "precio": ["precio", "price", "valor", "valor precio", "cotizacion", "cotización", "precio tn", "precio/t", "precio tonelada", "precio interno", "fas", "fob"],
    "frecuencia": ["frecuencia", "frequency", "periodicidad"],
    "observaciones": ["observaciones", "observacion", "observación", "notes", "nota", "comentarios"],
}

HEADER_HINT_KEYS = {item for aliases in HEADER_ALIASES.values() for item in aliases}
MONTH_NAMES = {
    "enero": 1, "ene": 1, "january": 1, "jan": 1,
    "febrero": 2, "feb": 2, "february": 2,
    "marzo": 3, "mar": 3, "march": 3,
    "abril": 4, "abr": 4, "april": 4, "apr": 4,
    "mayo": 5, "may": 5,
    "junio": 6, "jun": 6, "june": 6,
    "julio": 7, "jul": 7, "july": 7,
    "agosto": 8, "ago": 8, "august": 8, "aug": 8,
    "septiembre": 9, "setiembre": 9, "sep": 9, "sept": 9, "september": 9,
    "octubre": 10, "oct": 10, "october": 10,
    "noviembre": 11, "nov": 11, "november": 11,
    "diciembre": 12, "dic": 12, "december": 12, "dec": 12,
}


class _HTMLTableParser(HTMLParser):
    """Parser pequeño y tolerante para las tablas HTML publicadas por la fuente."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[dict[str, Any]]]] = []
        self._table_depth = 0
        self._current_table: list[list[dict[str, Any]]] | None = None
        self._current_row: list[dict[str, Any]] | None = None
        self._current_cell: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {key.lower(): value for key, value in attrs}
        if tag == "table":
            if self._table_depth == 0:
                self._current_table = []
            self._table_depth += 1
            return
        if self._table_depth != 1 or self._current_table is None:
            return
        if tag == "tr":
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None:
            self._current_cell = {
                "parts": [],
                "colspan": max(1, int(attributes.get("colspan") or "1")) if str(attributes.get("colspan") or "1").isdigit() else 1,
                "rowspan": max(1, int(attributes.get("rowspan") or "1")) if str(attributes.get("rowspan") or "1").isdigit() else 1,
            }
        elif tag == "br" and self._current_cell is not None:
            self._current_cell["parts"].append(" ")

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell["parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._table_depth == 1 and tag in {"td", "th"} and self._current_cell is not None and self._current_row is not None:
            value = unescape(" ".join(self._current_cell.pop("parts"))).strip()
            self._current_cell["value"] = re.sub(r"\s+", " ", value)
            self._current_row.append(self._current_cell)
            self._current_cell = None
        elif self._table_depth == 1 and tag == "tr" and self._current_table is not None:
            if self._current_row:
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table" and self._table_depth:
            self._table_depth -= 1
            if self._table_depth == 0 and self._current_table is not None:
                if self._current_table:
                    self.tables.append(self._current_table)
                self._current_table = None


def _expand_html_table(table: list[list[dict[str, Any]]]) -> list[list[str]]:
    """Expande colspan/rowspan para convertir una tabla visual en una matriz."""
    expanded: list[list[str]] = []
    active: dict[int, tuple[str, int]] = {}
    for raw_row in table:
        row: list[str] = []
        column = 0

        def fill_active() -> None:
            nonlocal column
            while column in active:
                value, remaining = active[column]
                row.append(value)
                if remaining <= 1:
                    del active[column]
                else:
                    active[column] = (value, remaining - 1)
                column += 1

        for cell in raw_row:
            fill_active()
            value = text(cell.get("value", ""))
            colspan = max(1, int(cell.get("colspan", 1)))
            rowspan = max(1, int(cell.get("rowspan", 1)))
            for offset in range(colspan):
                row.append(value)
                if rowspan > 1:
                    active[column + offset] = (value, rowspan - 1)
            column += colspan
        fill_active()
        if row:
            expanded.append(row)
    width = max((len(row) for row in expanded), default=0)
    return [row + [""] * (width - len(row)) for row in expanded]


def read_html_tables(path: Path) -> list[list[list[str]]]:
    parser = _HTMLTableParser()
    parser.feed(_read_text(path))
    return [_expand_html_table(table) for table in parser.tables]


def read_html_text(path: Path) -> str:
    parser = HTMLParser(convert_charrefs=True)
    parts: list[str] = []
    parser.handle_data = lambda data: parts.append(data)  # type: ignore[method-assign]
    parser.feed(_read_text(path))
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def load_source_config(path: Path | None = None) -> tuple[dict[str, Any], Path | None]:
    candidates = [path] if path else [DEFAULT_CONFIG_PATH, DEFAULT_CONFIG_EXAMPLE_PATH]
    for candidate in candidates:
        if candidate and candidate.exists():
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                return payload, candidate
    return {}, None


def text(value: Any) -> str:
    if value is None:
        return ""
    result = str(value).replace("\r", "").replace("\n", " ").strip()
    return "" if result.lower() in {"nan", "nat", "none", "null"} else result


def normalize_header(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", text(value)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", raw).strip()


def normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_header(value))


def _unique_headers(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: dict[str, int] = {}
    for index, value in enumerate(values, start=1):
        header = text(value) or f"columna_{index}"
        count = seen.get(normalized_key(header), 0) + 1
        seen[normalized_key(header)] = count
        result.append(header if count == 1 else f"{header}_{count}")
    return result


def _header_score(row: list[Any]) -> int:
    aliases = {normalized_key(item) for item in HEADER_HINT_KEYS}
    values = {normalized_key(item) for item in row if text(item)}
    return len(values & aliases)


def matrix_to_rows(matrix: list[list[Any]]) -> tuple[list[str], list[dict[str, str]]]:
    nonempty = [row for row in matrix if any(text(value) for value in row)]
    if not nonempty:
        return [], []
    search_limit = min(20, len(nonempty))
    header_index = max(range(search_limit), key=lambda index: _header_score(nonempty[index]))
    if _header_score(nonempty[header_index]) < 2:
        header_index = 0
    headers = _unique_headers(nonempty[header_index])
    rows: list[dict[str, str]] = []
    for raw_row in nonempty[header_index + 1:]:
        values = list(raw_row) + [""] * max(0, len(headers) - len(raw_row))
        row = {header: text(values[index]) for index, header in enumerate(headers)}
        if any(row.values()):
            rows.append(row)
    return headers, rows


def _read_text(path: Path) -> str:
    content = path.read_bytes()
    encodings = ("utf-16", "utf-8-sig", "cp1252", "latin-1") if content.startswith((b"\xff\xfe", b"\xfe\xff")) else ("utf-8-sig", "cp1252", "latin-1")
    for encoding in encodings:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _detect_delimiter(content: str) -> str:
    sample = content[:10000]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        counts = {delimiter: sample.count(delimiter) for delimiter in (";", ",", "\t", "|")}
        return max(counts, key=counts.get) if max(counts.values()) else ";"


def read_csv_matrix(path: Path) -> list[list[str]]:
    content = _read_text(path)
    delimiter = _detect_delimiter(content)
    return [row for row in csv.reader(content.splitlines(), delimiter=delimiter)]


def _xlsx_column_index(reference: str) -> int:
    letters = re.match(r"[A-Za-z]+", reference or "")
    if not letters:
        return 0
    value = 0
    for character in letters.group(0).upper():
        value = value * 26 + ord(character) - ord("A") + 1
    return value - 1


def read_xlsx_matrix(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        shared: list[str] = []
        shared_name = "xl/sharedStrings.xml"
        if shared_name in names:
            root = ElementTree.fromstring(archive.read(shared_name))
            for item in root.iter():
                if item.tag.rsplit("}", 1)[-1] == "si":
                    shared.append("".join(node.text or "" for node in item.iter() if node.tag.rsplit("}", 1)[-1] == "t"))
        sheet_name = next((name for name in sorted(names) if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")), None)
        if not sheet_name:
            return []
        root = ElementTree.fromstring(archive.read(sheet_name))
        matrix: list[list[str]] = []
        for row_node in root.iter():
            if row_node.tag.rsplit("}", 1)[-1] != "row":
                continue
            values: dict[int, str] = {}
            for cell in row_node:
                if cell.tag.rsplit("}", 1)[-1] != "c":
                    continue
                index = _xlsx_column_index(cell.attrib.get("r", ""))
                cell_type = cell.attrib.get("t", "")
                value_node = next((node for node in cell if node.tag.rsplit("}", 1)[-1] == "v"), None)
                inline_node = next((node for node in cell.iter() if node.tag.rsplit("}", 1)[-1] == "t"), None)
                value = inline_node.text if cell_type == "inlineStr" and inline_node is not None else value_node.text if value_node is not None else ""
                if cell_type == "s" and value is not None:
                    try:
                        value = shared[int(value)]
                    except (ValueError, IndexError):
                        pass
                values[index] = text(value)
            if values:
                width = max(values) + 1
                matrix.append([values.get(index, "") for index in range(width)])
        return matrix


def read_json_matrix(path: Path) -> list[list[Any]]:
    payload = json.loads(_read_text(path))
    if isinstance(payload, dict):
        for key in ("data", "rows", "items", "results", "datos", "series"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if isinstance(payload, list) and payload and all(isinstance(item, dict) for item in payload):
        headers: list[str] = []
        for item in payload:
            for key in item:
                if key not in headers:
                    headers.append(str(key))
        return [headers] + [[item.get(header, "") for header in headers] for item in payload]
    if isinstance(payload, list) and all(isinstance(item, list) for item in payload):
        return payload
    if isinstance(payload, dict):
        return [[key, value] for key, value in payload.items()]
    return []


def read_tabular_file(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".txt", ".tsv"}:
        matrix = read_csv_matrix(path)
    elif suffix in {".html", ".htm"}:
        tables = read_html_tables(path)
        matrix = tables[0] if tables else []
    elif suffix == ".xlsx":
        matrix = read_xlsx_matrix(path)
    elif suffix == ".json":
        matrix = read_json_matrix(path)
    elif suffix == ".xls":
        try:
            import pandas as pd  # type: ignore
        except ImportError as exc:
            raise ValueError(".xls requiere pandas/xlrd; convierta el archivo a .xlsx o .csv para la prueba controlada") from exc
        frame = pd.read_excel(path)
        return matrix_to_rows([list(frame.columns), *frame.fillna("").astype(str).values.tolist()])
    else:
        raise ValueError(f"extensión no soportada: {path.suffix or '(sin extensión)'}")
    return matrix_to_rows(matrix)


def find_column(headers: list[str], field: str) -> str:
    candidates = {normalized_key(item) for item in HEADER_ALIASES.get(field, [field])}
    for header in headers:
        if normalized_key(header) in candidates:
            return header
    for header in headers:
        header_key = normalized_key(header)
        if any(candidate and (candidate in header_key or header_key in candidate) for candidate in candidates):
            return header
    return ""


def row_value(row: dict[str, str], headers: list[str], field: str) -> str:
    column = find_column(headers, field)
    return text(row.get(column, "")) if column else ""


def parse_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raw = text(value).replace("$", "")
    raw = re.sub(r"(?i)\b(ars|usd|pesos?|dolares?|dólares?)\b", "", raw)
    raw = re.sub(r"[^0-9,.-]", "", raw).strip()
    if not raw or raw in {"-", ".", ","}:
        return None
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
    elif "," in raw:
        parts = raw.split(",")
        raw = "".join(parts) if len(parts) > 1 and len(parts[-1]) == 3 else raw.replace(",", ".")
    elif "." in raw:
        parts = raw.split(".")
        raw = "".join(parts) if len(parts) > 1 and len(parts[-1]) == 3 else raw
    try:
        return float(raw)
    except ValueError:
        return None


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = text(value)
    if not raw:
        return None
    numeric = parse_number(raw)
    if numeric is not None and re.fullmatch(r"\d+(?:\.0+)?", raw) and 20000 < numeric < 80000:
        try:
            return date(1899, 12, 30) + timedelta(days=int(numeric))
        except ValueError:
            pass
    raw = raw.replace("T", " ").split(" ", 1)[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y", "%Y-%m", "%Y/%m", "%m/%Y", "%Y%m"):
        try:
            parsed = datetime.strptime(raw[:10], fmt).date()
            return parsed.replace(day=1) if fmt in {"%Y-%m", "%Y/%m", "%m/%Y", "%Y%m"} else parsed
        except ValueError:
            continue
    match = re.fullmatch(r"([A-Za-zÁÉÍÓÚáéíóúñÑ]+)[ -]+(\d{4})", raw)
    if match:
        month = MONTH_NAMES.get(normalize_header(match.group(1)))
        if month:
            return date(int(match.group(2)), month, 1)
    match = re.fullmatch(r"(\d{4})[ -]+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)", raw)
    if match:
        month = MONTH_NAMES.get(normalize_header(match.group(2)))
        if month:
            return date(int(match.group(1)), month, 1)
    return None


def parse_period(row: dict[str, str], headers: list[str]) -> date | None:
    parsed = parse_date(row_value(row, headers, "fecha"))
    if parsed:
        return parsed
    parsed = parse_date(row_value(row, headers, "periodo"))
    if parsed:
        return parsed.replace(day=1)
    year = parse_number(row_value(row, headers, "año"))
    month_raw = row_value(row, headers, "mes")
    month = parse_number(month_raw)
    if month is None:
        month = MONTH_NAMES.get(normalize_header(month_raw))
    if year is not None and month is not None and 1 <= int(month) <= 12:
        try:
            return date(int(year), int(month), 1)
        except ValueError:
            return None
    return None


def format_number(value: float | int | None) -> str:
    if value is None:
        return ""
    return f"{float(value):.6f}".rstrip("0").rstrip(".") or "0"


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows({field: text(row.get(field, "")) for field in fields} for row in rows)
