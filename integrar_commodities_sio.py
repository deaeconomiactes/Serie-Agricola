#!/usr/bin/env python3
"""Integra respuestas reales de SIO Granos, separadas del pipeline BCR."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "commodities_sio" / "raw"
PROCESSED_DIR = ROOT / "data" / "commodities_sio" / "processed"
CATALOG_PATH = ROOT / "data" / "commodities_sio" / "catalogo_productos_sio.csv"
MAPPING_LOCAL_PATH = ROOT / "data" / "commodities_sio" / "mapeo_getoperaciones_sio.local.json"
MAPPING_EXAMPLE_PATH = ROOT / "data" / "commodities_sio" / "mapeo_getoperaciones_sio.example.json"
OUTPUT_PATH = PROCESSED_DIR / "COMMODITIES_SIO_INTEGRADO.csv"
PAGINATED_REPORT_PATH = ROOT / "data" / "commodities_sio" / "reports" / "REPORTE_MUESTRA_PAGINADA_SIO.md"
OUTPUT_COLUMNS = [
    "fecha", "año", "mes", "commodity", "fuente", "mercado", "tipo_precio",
    "precio_tipo_original", "precio_unidad", "precio_total", "campo_precio_original", "valor_precio_original", "precio_original_texto", "moneda", "moneda_explicitamente_informada", "moneda_inferida", "campo_moneda_original", "valor_moneda_original", "unidad", "precio", "volumen", "volumen_unidad", "campo_volumen_original", "procedencia",
    "provincia", "localidad", "zona", "lugar_entrega", "precio_puesto_en", "operacion",
    "condicion_pago", "condicion_comercial", "frecuencia", "archivo_origen",
    "fecha_integracion", "observaciones", "apto_piloto", "apto_dashboard", "pagina_origen", "id_operacion_sio", "muestra_tipo", "muestra_paginas",
]
EXTENSIONS = {".json", ".csv", ".xlsx", ".xls", ".html", ".htm"}
NON_REAL_MARKERS = ("plantilla", "simul", "prueba", "ejemplo", "sample")
DEFAULT_SOURCE = "SIO Granos / Secretaría de Agricultura"
HEADER_KEYS = {
    "fecha", "fechadeclaracion", "fechaconcertacion", "fechadeentrega", "producto",
    "grano", "commodity", "especie", "precio", "preciomonto", "preciotn", "monto",
    "cotizacion", "valor", "moneda", "unidad", "volumen", "cantidad", "cantidadtn",
    "tn", "procedencia", "provincia", "localidad", "zona", "operacion",
}


def key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", normalized.lower())


def text(value: Any) -> str:
    if value is None:
        return ""
    result = str(value).replace("\r", "").strip()
    return "" if result.lower() in {"nan", "nat", "none"} else result


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = text(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raw = text(value).replace("$", "").replace("ARS", "").replace("USD", "")
    raw = re.sub(r"[^0-9,.-]", "", raw)
    if not raw or raw in {"-", ".", ","}:
        return None
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", "") if raw.count(",") > 1 else raw.replace(",", ".")
    elif "." in raw:
        parts = raw.split(".")
        if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
            raw = "".join(parts)
    try:
        return float(raw)
    except ValueError:
        return None


def extract_explicit_currency(value: Any) -> tuple[str, str, str]:
    """Normaliza sólo símbolos/textos monetarios presentes en el valor original."""

    raw = text(value)
    if re.search(r"U\s*\$\s*S|US\s*\$|\bUSD\b", raw, flags=re.I):
        return "USD", "sí", "no"
    if "$" in raw:
        return "ARS", "sí", "no"
    return "Sin especificar", "no", "no"


def normalize_explicit_currency_field(value: Any) -> str:
    raw = text(value)
    if not raw:
        return ""
    currency, explicit, _ = extract_explicit_currency(raw)
    if explicit == "sí":
        return currency
    if re.fullmatch(r"USD|US DOLLARS?|DOLARES?|DÓLARES?", raw, flags=re.I):
        return "USD"
    if re.fullmatch(r"ARS|PESOS?|PESOS? ARGENTINOS?", raw, flags=re.I):
        return "ARS"
    return raw


def read_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    if not CATALOG_PATH.exists():
        return aliases
    with CATALOG_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            canonical = text(row.get("commodity"))
            for alias in [canonical] + text(row.get("aliases")).split("|"):
                if alias:
                    aliases[key(alias)] = canonical
    return aliases


def load_positional_mapping() -> tuple[dict[int, dict[str, Any]] | None, str]:
    """Carga sólo un mapeo explícitamente validado y respaldado por evidencia."""

    selected = next((path for path in (MAPPING_LOCAL_PATH, MAPPING_EXAMPLE_PATH) if path.exists()), None)
    if selected is None:
        return None, "mapeo posicional SIO pendiente de validación; no existe archivo de mapeo"
    try:
        document = json.loads(selected.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"mapeo posicional SIO pendiente de validación; archivo inválido ({exc.__class__.__name__})"
    if not isinstance(document, dict) or document.get("mapping_status") != "validado":
        return None, "mapeo posicional SIO pendiente de validación"
    evidence = document.get("evidence", [])
    evidence_items = [evidence] if isinstance(evidence, str) else evidence if isinstance(evidence, list) else []
    documented_evidence = any((ROOT / item).exists() if not Path(item).is_absolute() else Path(item).exists() for item in evidence_items if isinstance(item, str) and item.strip())
    raw_mapping = document.get("row_mapping")
    if not documented_evidence or not isinstance(raw_mapping, dict):
        return None, "mapeo posicional SIO pendiente de validación; falta evidencia documentada"
    mapping: dict[int, dict[str, Any]] = {}
    for position, field in raw_mapping.items():
        try:
            position_number = int(position)
        except (TypeError, ValueError):
            continue
        if position_number < 0:
            continue
        if isinstance(field, str) and field.strip():
            mapping[position_number] = {"target_field": field.strip()}
        elif isinstance(field, dict) and isinstance(field.get("target_field"), str) and field["target_field"].strip():
            mapping[position_number] = dict(field)
    if not mapping or not any(key(spec.get("target_field")) in {"fecha", "producto", "commodity", "precio"} for spec in mapping.values()):
        return None, "mapeo posicional SIO pendiente de validación; faltan campos mínimos"
    return mapping, f"mapeo posicional validado desde {selected.name}"


def map_positional_row(source: dict[str, Any], mapping: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    raw_row = next((value for name, value in source.items() if key(name) == "row"), None)
    if not isinstance(raw_row, (list, tuple)):
        return None
    mapped: dict[str, Any] = {}
    for position, specification in mapping.items():
        if position < len(raw_row):
            field = specification["target_field"].strip()
            mapped[field] = raw_row[position]
            source_label = text(specification.get("source_label"))
            if source_label:
                mapped[f"__source_label_{field}"] = source_label
            unit_field = text(specification.get("unit_field"))
            unit_value = text(specification.get("unit_value_if_label_matches"))
            if unit_field and unit_value and source_label:
                mapped[f"__unit_value_{unit_field}"] = unit_value
    return mapped or None


def normalize_commodity(value: Any, filename: str, aliases: dict[str, str]) -> tuple[str, str]:
    original = text(value)
    if original and key(original) in aliases:
        return aliases[key(original)], ""
    if original:
        return original, "commodity no catalogado; se conserva para revisión"
    filename_key = key(filename)
    for alias, canonical in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if alias and alias in filename_key:
            return canonical, "commodity inferido desde el nombre del archivo"
    return "Sin especificar", "commodity no identificado; revisar respuesta"


def value_for(row: dict[str, Any], *names: str) -> Any:
    normalized = {key(name): value for name, value in row.items()}
    for name in names:
        if key(name) in normalized:
            return normalized[key(name)]
    return ""


def value_with_field(row: dict[str, Any], *names: str) -> tuple[Any, str]:
    normalized = {key(name): (value, str(name)) for name, value in row.items()}
    for name in names:
        if key(name) in normalized:
            return normalized[key(name)]
    return "", ""


def explicit_unit_from_label(label: str, unit_value: str = "") -> str:
    if unit_value:
        return unit_value
    normalized = key(label)
    if "preciotn" in normalized or ("preciopor" in normalized and "tn" in normalized) or ("preciopor" in normalized and "tonelada" in normalized) or "$/tn" in label.lower():
        return "TN"
    return ""


def extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        result: list[dict[str, Any]] = []
        for item in payload:
            result.extend(extract_records(item))
        return result
    if isinstance(payload, dict):
        containers = {"data", "results", "records", "items", "rows", "operaciones", "d"}
        for name, value in payload.items():
            if str(name).lower() in containers:
                nested = extract_records(value)
                if nested:
                    return nested
        return [payload]
    return []


def read_matrix(values: list[tuple[Any, ...]]) -> tuple[list[dict[str, Any]], list[str]]:
    nonempty = [index for index, row in enumerate(values[:30]) if row and any(text(cell) for cell in row)]
    if not nonempty:
        return [], []
    header_index = max(nonempty, key=lambda index: sum(key(cell) in HEADER_KEYS for cell in values[index]))
    headers = [text(cell) or f"columna_{index + 1}" for index, cell in enumerate(values[header_index])]
    rows: list[dict[str, Any]] = []
    for values_row in values[header_index + 1:]:
        if values_row and any(text(cell) for cell in values_row):
            rows.append({headers[index]: values_row[index] if index < len(values_row) else "" for index in range(len(headers))})
    return rows, headers


class HTMLTableParser(HTMLParser):
    """Extrae tablas HTML simples sin interpretar formularios ni JavaScript."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[tuple[Any, ...]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table" and self._table is None:
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"th", "td"} and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append([tuple(row) for row in self._table])
            self._table = None


def read_file(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        content = path.read_text(encoding="utf-8-sig", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(content[:4096], delimiters=";,\t|")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.DictReader(content.splitlines(), dialect=dialect)
        return [dict(row) for row in reader], [text(column) for column in (reader.fieldnames or [])]
    if suffix == ".json":
        return extract_records(json.loads(path.read_text(encoding="utf-8-sig"))), []
    if suffix in {".html", ".htm"}:
        try:
            import pandas as pd
            frames = pd.read_html(path)
        except ImportError as exc:
            parser = HTMLTableParser()
            parser.feed(path.read_text(encoding="utf-8", errors="replace"))
            rows: list[dict[str, Any]] = []
            columns: list[str] = []
            for table in parser.tables:
                if not any(key(cell) in HEADER_KEYS for row in table[:5] for cell in row):
                    continue
                table_rows, table_columns = read_matrix(table)
                rows.extend(table_rows)
                columns.extend(column for column in table_columns if column not in columns)
            return rows, columns
        rows: list[dict[str, Any]] = []
        columns: list[str] = []
        for frame in frames:
            frame = frame.fillna("")
            table_rows, table_columns = read_matrix([tuple(frame.columns)] + [tuple(row) for row in frame.itertuples(index=False, name=None)])
            rows.extend(table_rows)
            columns.extend(column for column in table_columns if column not in columns)
        return rows, columns
    try:
        import pandas as pd
    except ImportError:
        pd = None
    if suffix == ".xls":
        if pd is None:
            raise RuntimeError("para leer XLS instale pandas y xlrd, o convierta a XLSX/CSV")
        frames = pd.read_excel(path, sheet_name=None, header=None)
        rows: list[dict[str, Any]] = []
        columns: list[str] = []
        for frame in frames.values():
            table_rows, table_columns = read_matrix([tuple(row) for row in frame.fillna("").itertuples(index=False, name=None)])
            rows.extend(table_rows)
            columns.extend(column for column in table_columns if column not in columns)
        return rows, columns
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("para leer XLSX instale openpyxl o convierta a CSV") from exc
    workbook = load_workbook(path, read_only=True, data_only=True)
    rows: list[dict[str, Any]] = []
    columns: list[str] = []
    for sheet in workbook.worksheets:
        table_rows, table_columns = read_matrix([tuple(row) for row in sheet.values])
        rows.extend(table_rows)
        columns.extend(column for column in table_columns if column not in columns)
    return rows, columns


def first_text(source: dict[str, Any], *names: str) -> str:
    return text(value_for(source, *names))


def process_file(path: Path, aliases: dict[str, str], positional_mapping: dict[int, dict[str, Any]] | None, sample_pages: int) -> tuple[list[dict[str, str]], dict[str, Any]]:
    source_rows, columns = read_file(path)
    rows: list[dict[str, str]] = []
    dates: list[date] = []
    prices: list[float] = []
    commodities: set[str] = set()
    positional_skipped = 0
    positional_applied = 0
    page_match = re.search(r"page[_-](\d+)", path.stem, flags=re.I)
    page_origin = page_match.group(1) if page_match else ""
    sample_type = "paginacion_controlada" if page_match else "piloto_una_pagina"
    for source in source_rows:
        used_positional = False
        source_id = first_text(source, "ID", "id_operacion_sio")
        has_positional_row = any(key(name) == "row" for name in source)
        if has_positional_row:
            if positional_mapping is None:
                positional_skipped += 1
                continue
            mapped_source = map_positional_row(source, positional_mapping)
            if mapped_source is None:
                positional_skipped += 1
                continue
            source = mapped_source
            if source_id:
                source["id_operacion_sio"] = source_id
            positional_applied += 1
            used_positional = True
        market_date = parse_date(value_for(source, "Fecha Declaración", "Fecha Declaracion", "Fecha de Concertación", "Fecha de Concertacion", "Fecha de Entrega", "Fecha Concertación", "Fecha Concertacion", "Fecha"))
        raw_commodity = value_for(source, "Producto", "Grano", "Especie", "Commodity")
        commodity, commodity_note = normalize_commodity(raw_commodity, path.name, aliases)
        raw_price, detected_price_field = value_with_field(source, "Precio/TN Monto", "Precio/Monto", "Precio/TN", "Precio TN", "Precio unitario", "Precio", "Monto", "Precio hecho", "Precio Hecho", "Cotización", "Cotizacion", "Valor")
        price = parse_number(raw_price)
        if not market_date and price is None and not raw_commodity:
            continue
        if market_date:
            dates.append(market_date)
        if price is not None:
            prices.append(price)
        price_original = text(raw_price)
        price_label = text(source.get("__source_label_precio")) or detected_price_field
        price_type_original = first_text(source, "precio_tipo_original", "Precio tipo original", "Precio")
        raw_currency, detected_currency_field = value_with_field(source, "Moneda", "Currency", "Código moneda", "Codigo moneda")
        moneda, moneda_explicitamente_informada, moneda_inferida = extract_explicit_currency(price_original)
        currency_original = price_original if moneda_explicitamente_informada == "sí" else text(raw_currency)
        currency_label = price_label if moneda_explicitamente_informada == "sí" else detected_currency_field
        if moneda_explicitamente_informada != "sí" and text(raw_currency):
            moneda = normalize_explicit_currency_field(raw_currency)
            moneda_explicitamente_informada = "sí"
        source_unit = first_text(source, "Unidad", "Unit")
        explicit_price_unit = explicit_unit_from_label(price_label, text(source.get("__unit_value_unidad")))
        unidad = source_unit or explicit_price_unit
        precio_unidad = price if explicit_price_unit and price is not None else None
        raw_total, detected_total_field = value_with_field(source, "Precio total", "Monto total", "Total")
        precio_total = parse_number(raw_total)
        tipo = first_text(source, "tipo_precio", "Tipo de precio", "Tipo Precio", "Price Type", "Tipo") or price_type_original
        volumen, detected_volume_field = value_with_field(source, "Cantidad (TN)", "Cantidad TN", "Volumen TN", "Toneladas", "Volumen", "Cantidad", "TN")
        volume_label = text(source.get("__source_label_volumen")) or detected_volume_field
        volumen_unidad = first_text(source, "volumen_unidad", "Unidad de volumen", "Unidad volumen", "Volume Unit") or text(source.get("__unit_value_volumen_unidad"))
        if not volumen_unidad and key(volume_label) in {"cantidadtn", "cantidadtns", "volumentn", "toneladas", "tn"}:
            volumen_unidad = "TN"
        row_missing: list[str] = []
        if moneda_explicitamente_informada == "sí":
            row_missing.append(f"moneda extraída explícitamente del campo precio original: {moneda}" if currency_label == price_label else f"moneda informada explícitamente en campo original: {moneda}")
        else:
            moneda = "Sin especificar"
            row_missing.append("moneda no informada explícitamente en endpoint GetOperaciones; no se infiere del valor original")
        if not unidad:
            unidad = "Sin especificar"
            row_missing.append("falta unidad")
        if not tipo:
            tipo = "Sin especificar"
            row_missing.append("falta tipo_precio")
        if not market_date:
            row_missing.append("falta fecha válida")
        if price is None:
            row_missing.append("falta precio válido")
        operation = first_text(source, "Operación", "Operacion", "operacion")
        payment = first_text(source, "condicion_pago", "Condición de Pago", "Condicion de Pago", "Pago")
        commercial = first_text(source, "Condición comercial", "Condicion comercial", "Condición", "Condicion", "Entrega")
        observation = first_text(source, "Observación", "Observaciones", "Nota", "Notas")
        pilot_note = "integración piloto una página GetOperaciones" if used_positional else ""
        notes = "; ".join(dict.fromkeys([part for part in [observation, commodity_note, pilot_note] + row_missing if part]))
        source_name = first_text(source, "Fuente", "Source") or DEFAULT_SOURCE
        delivery_place = first_text(source, "Zona", "Lugar de entrega", "lugar_entrega")
        pilot_status = "sí" if market_date and commodity != "Sin especificar" and price is not None and source_name and price_label and price_label != "Sin especificar" and explicit_price_unit else "no"
        dashboard_status = "parcial_piloto" if pilot_status == "sí" and moneda_explicitamente_informada == "sí" and explicit_price_unit and used_positional else "no"
        commodities.add(commodity)
        rows.append({
            "fecha": market_date.isoformat() if market_date else "",
            "año": str(market_date.year) if market_date else "",
            "mes": str(market_date.month) if market_date else "",
            "commodity": commodity,
            "fuente": source_name,
            "mercado": first_text(source, "Mercado", "Market"),
            "tipo_precio": tipo,
            "precio_tipo_original": price_type_original,
            "precio_unidad": "" if precio_unidad is None else f"{precio_unidad:g}",
            "precio_total": "" if precio_total is None else f"{precio_total:g}",
            "campo_precio_original": price_label or "Sin especificar",
            "valor_precio_original": price_original,
            "precio_original_texto": price_original,
            "moneda": moneda,
            "moneda_explicitamente_informada": moneda_explicitamente_informada,
            "moneda_inferida": moneda_inferida,
            "campo_moneda_original": currency_label or "Sin especificar",
            "valor_moneda_original": currency_original,
            "unidad": unidad,
            "precio": "" if price is None else f"{price:g}",
            "volumen": volumen,
            "volumen_unidad": volumen_unidad,
            "campo_volumen_original": volume_label or "Sin especificar",
            "procedencia": first_text(source, "Procedencia"),
            "provincia": first_text(source, "Provincia", "Pcia"),
            "localidad": first_text(source, "Localidad"),
            "zona": delivery_place,
            "lugar_entrega": delivery_place,
            "precio_puesto_en": first_text(source, "Precio puesto en", "Destino", "Puerto"),
            "operacion": operation,
            "condicion_pago": payment,
            "condicion_comercial": commercial,
            "frecuencia": first_text(source, "Frecuencia", "Frequency"),
            "archivo_origen": path.name,
            "fecha_integracion": date.today().isoformat(),
            "observaciones": notes,
            "apto_piloto": pilot_status,
            "apto_dashboard": dashboard_status,
            "pagina_origen": page_origin,
            "id_operacion_sio": source_id or first_text(source, "id_operacion_sio", "ID"),
            "muestra_tipo": sample_type,
            "muestra_paginas": str(sample_pages),
        })
    return rows, {"read": len(source_rows), "integrated": len(rows), "positional_skipped": positional_skipped, "positional_applied": positional_applied, "columns": columns, "commodities": sorted(commodities), "dates": dates, "prices": prices}


def real_files() -> list[Path]:
    if not RAW_DIR.exists():
        return []
    return sorted(path for path in RAW_DIR.iterdir() if path.is_file() and path.suffix.lower() in EXTENSIONS and not any(marker in path.stem.lower() for marker in NON_REAL_MARKERS))


def row_signature(row: dict[str, str]) -> tuple[str, ...]:
    excluded = {"archivo_origen", "fecha_integracion", "observaciones", "pagina_origen", "muestra_paginas", "muestra_tipo"}
    return tuple(str(row.get(column, "")) for column in OUTPUT_COLUMNS if column not in excluded)


def deduplicate_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    kept: list[dict[str, str]] = []
    duplicates: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    seen_by_id: dict[str, dict[str, str]] = {}
    seen_by_key: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        operation_id = text(row.get("id_operacion_sio"))
        key_value = (text(row.get("fecha")), text(row.get("commodity")), text(row.get("precio")), text(row.get("moneda")), text(row.get("unidad")), text(row.get("volumen")), text(row.get("procedencia")), text(row.get("lugar_entrega")), text(row.get("tipo_precio")))
        previous = seen_by_id.get(operation_id) if operation_id else seen_by_key.get(key_value)
        if previous is None:
            kept.append(row)
            if operation_id:
                seen_by_id[operation_id] = row
            else:
                seen_by_key[key_value] = row
            continue
        if row_signature(previous) == row_signature(row):
            duplicates.append({"id_operacion_sio": operation_id, "archivo_origen": row.get("archivo_origen", ""), "pagina_origen": row.get("pagina_origen", ""), "motivo": "duplicado exacto; se conserva la primera aparición"})
        else:
            conflicts.append({"id_operacion_sio": operation_id, "archivo_origen": row.get("archivo_origen", ""), "pagina_origen": row.get("pagina_origen", ""), "motivo": "mismo ID/claves pero contenido diferente; se conservan ambas filas para revisión"})
            kept.append(row)
    return kept, duplicates, conflicts


def update_paginated_report(files: list[Path], diagnostics: list[dict[str, Any]], rows: list[dict[str, str]], duplicates: list[dict[str, str]], conflicts: list[dict[str, str]], page_count: int) -> None:
    if not PAGINATED_REPORT_PATH.exists():
        return
    report = PAGINATED_REPORT_PATH.read_text(encoding="utf-8")
    total_read = sum(int(item.get("read", 0)) for item in diagnostics)
    columns = [column for column in OUTPUT_COLUMNS if any(row.get(column) for row in rows)]
    integration_section = "\n".join([
        "## Resultado de integración", "", f"- Filas leídas antes de deduplicar: {total_read}.", f"- Archivos procesados: {len(files)}.", f"- Páginas procesadas: {page_count}.", f"- Duplicados exactos eliminados: {len(duplicates)}.", f"- Conflictos conservados para revisión: {len(conflicts)}.", f"- Filas finales: {len(rows)}.", f"- Columnas principales: {', '.join(columns)}.", "",
    ])
    report = re.sub(r"## Resultado de integración\n.*?(?=\n## Resultado de auditoría)", integration_section.rstrip(), report, flags=re.S)
    PAGINATED_REPORT_PATH.write_text(report, encoding="utf-8")


def remove_output() -> None:
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()


def write_output(rows: list[dict[str, str]]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    files = real_files()
    if not files:
        remove_output()
        print("No hay archivos reales de SIO Granos en data/commodities_sio/raw/.")
        print("No hay datos integrados ni se generan reportes vacíos.")
        return 0
    aliases = read_aliases()
    positional_mapping, mapping_status = load_positional_mapping()
    print(f"Mapeo posicional: {mapping_status}")
    page_files = [path for path in files if re.search(r"page[_-]\d+", path.stem, flags=re.I)]
    page_numbers = {int(match.group(1)) for path in page_files if (match := re.search(r"page[_-](\d+)", path.stem, flags=re.I))}
    sample_pages = len(page_numbers) or 1
    all_rows: list[dict[str, str]] = []
    diagnostics_by_file: list[dict[str, Any]] = []
    errors = 0
    for path in files:
        try:
            rows, diagnostics = process_file(path, aliases, positional_mapping, sample_pages)
            all_rows.extend(rows)
            diagnostics_by_file.append(diagnostics)
            print(f"Archivo procesado: {path.name}")
            print(f"  Columnas detectadas: {', '.join(diagnostics['columns']) or '(JSON/estructura anidada)'}")
            print(f"  Commodities detectados: {', '.join(diagnostics['commodities']) or 'sin identificar'}")
            print(f"  Filas leídas: {diagnostics['read']}; filas integradas: {diagnostics['integrated']}")
            if diagnostics["positional_skipped"]:
                print(f"  Filas Row posicionales omitidas: {diagnostics['positional_skipped']}")
            if diagnostics["positional_applied"]:
                print(f"  Filas Row con mapeo validado aplicado: {diagnostics['positional_applied']}")
            print(f"  Precio mínimo: {min(diagnostics['prices']):g}" if diagnostics["prices"] else "  Precio mínimo: sin precio válido")
            print(f"  Precio máximo: {max(diagnostics['prices']):g}" if diagnostics["prices"] else "  Precio máximo: sin precio válido")
            print(f"  Fecha mínima: {min(diagnostics['dates']).isoformat()}" if diagnostics["dates"] else "  Fecha mínima: sin fecha válida")
            print(f"  Fecha máxima: {max(diagnostics['dates']).isoformat()}" if diagnostics["dates"] else "  Fecha máxima: sin fecha válida")
            if path.suffix.lower() == ".json" and diagnostics["read"] and not diagnostics["integrated"]:
                print("  Respuesta SIO no mapeable automáticamente: revisar el esquema de filas y no integrar por posición sin validación.")
        except Exception as exc:
            errors += 1
            print(f"ERROR en {path.name}: {exc}")
            print("  Sugerencia: revisar encabezados o conservar la respuesta original para ajustar el mapeo.")
    if not all_rows:
        remove_output()
        print("No se integraron filas válidas de SIO Granos. No se generan reportes vacíos.")
        return 0
    integrated_rows, duplicates, conflicts = deduplicate_rows(all_rows)
    write_output(integrated_rows)
    update_paginated_report(files, diagnostics_by_file, integrated_rows, duplicates, conflicts, sample_pages)
    print(f"Duplicados exactos eliminados: {len(duplicates)}; conflictos conservados: {len(conflicts)}")
    print(f"Integración SIO finalizada: {len(integrated_rows)} filas en {OUTPUT_PATH}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
