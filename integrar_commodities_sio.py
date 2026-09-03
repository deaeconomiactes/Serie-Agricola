#!/usr/bin/env python3
"""Integra respuestas SIO Granos manteniendo una capa separada de BCR."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "commodities_sio" / "raw"
PROCESSED_DIR = ROOT / "data" / "commodities_sio" / "processed"
CATALOG_PATH = ROOT / "data" / "commodities_sio" / "catalogo_productos_sio.csv"
OUTPUT_PATH = PROCESSED_DIR / "COMMODITIES_SIO_INTEGRADO.csv"
OUTPUT_COLUMNS = [
    "fecha", "año", "mes", "commodity", "fuente", "mercado", "tipo_precio", "moneda", "unidad", "precio", "volumen", "zona", "provincia", "condicion_comercial", "archivo_origen", "fecha_integracion", "observaciones",
]
EXTENSIONS = {".json", ".csv", ".xlsx", ".xls"}
NON_REAL_MARKERS = ("plantilla", "simul", "prueba", "test")
DEFAULT_SOURCE = "SIO Granos / Secretaría de Agricultura"
HEADER_KEYS = {"fecha", "fechaconcertacion", "fechaentrega", "producto", "grano", "commodity", "especie", "precio", "preciotn", "cotizacion", "valor", "moneda", "unidad", "volumen", "cantidad", "zona", "provincia"}


def key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", normalized.lower())


def text(value: Any) -> str:
    if value is None:
        return ""
    result = str(value).strip()
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


def extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        result: list[dict[str, Any]] = []
        for item in payload:
            result.extend(extract_records(item))
        return result
    if isinstance(payload, dict):
        for name in ("data", "results", "records", "items", "rows", "operaciones"):
            if name in payload:
                nested = extract_records(payload[name])
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
    rows = []
    for values_row in values[header_index + 1:]:
        if values_row and any(text(cell) for cell in values_row):
            rows.append({headers[index]: values_row[index] if index < len(values_row) else "" for index in range(len(headers))})
    return rows, headers


def read_file(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if path.suffix.lower() == ".csv":
        content = path.read_text(encoding="utf-8-sig", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(content[:4096], delimiters=";,\t|")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.DictReader(content.splitlines(), dialect=dialect)
        return [dict(row) for row in reader], [text(column) for column in (reader.fieldnames or [])]
    if path.suffix.lower() == ".json":
        return (extract_records(json.loads(path.read_text(encoding="utf-8-sig"))), [])
    if path.suffix.lower() == ".xls":
        try:
            import pandas as pd
            frames = pd.read_excel(path, sheet_name=None, header=None)
            rows: list[dict[str, Any]] = []
            columns: list[str] = []
            for frame in frames.values():
                sheet_rows, sheet_columns = read_matrix([tuple(row) for row in frame.where(frame.notna(), "").itertuples(index=False, name=None)])
                rows.extend(sheet_rows)
                columns.extend(column for column in sheet_columns if column not in columns)
            return rows, columns
        except ImportError as exc:
            raise RuntimeError("para leer XLS instale pandas y xlrd, o convierta a XLSX/CSV") from exc
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("para leer XLSX instale openpyxl o convierta a CSV") from exc
    workbook = load_workbook(path, read_only=True, data_only=True)
    rows: list[dict[str, Any]] = []
    columns: list[str] = []
    for sheet in workbook.worksheets:
        sheet_rows, sheet_columns = read_matrix([tuple(row) for row in sheet.values])
        rows.extend(sheet_rows)
        columns.extend(column for column in sheet_columns if column not in columns)
    return rows, columns


def process_file(path: Path, aliases: dict[str, str]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    source_rows, columns = read_file(path)
    rows: list[dict[str, str]] = []
    missing_fields: set[str] = set()
    dates: list[date] = []
    prices: list[float] = []
    for source in source_rows:
        market_date = parse_date(value_for(source, "Fecha", "Fecha Concertación", "Fecha Concertacion", "Fecha de mercado", "Fecha Entrega"))
        raw_commodity = value_for(source, "Producto", "Grano", "Commodity", "Especie")
        commodity, commodity_note = normalize_commodity(raw_commodity, path.name, aliases)
        raw_price = value_for(source, "Precio", "Precio/TN", "Precio TN", "Precio Hecho", "Cotización", "Cotizacion", "Valor")
        price = parse_number(raw_price)
        if not market_date and price is None and not raw_commodity:
            continue
        if market_date:
            dates.append(market_date)
        if price is not None:
            prices.append(price)
        moneda = text(value_for(source, "Moneda", "Currency"))
        unidad = text(value_for(source, "Unidad", "Unit"))
        tipo = text(value_for(source, "Operación", "Operacion", "Tipo de precio", "Tipo Precio", "Tipo", "Price Type"))
        row_missing: list[str] = []
        if not moneda:
            moneda = "Sin especificar"
            missing_fields.add("moneda")
            row_missing.append("falta moneda")
        if not unidad:
            unidad = "Sin especificar"
            missing_fields.add("unidad")
            row_missing.append("falta unidad")
        if not tipo:
            tipo = "Sin especificar"
            missing_fields.add("tipo_precio")
            row_missing.append("falta tipo_precio")
        observation = text(value_for(source, "Observación", "Observaciones", "Nota", "Notas"))
        observation = "; ".join(dict.fromkeys([part for part in [observation, commodity_note] + row_missing if part]))
        rows.append({
            "fecha": market_date.isoformat() if market_date else "",
            "año": str(market_date.year) if market_date else "",
            "mes": str(market_date.month) if market_date else "",
            "commodity": commodity,
            "fuente": text(value_for(source, "Fuente", "Source")) or DEFAULT_SOURCE,
            "mercado": text(value_for(source, "Mercado", "Market")),
            "tipo_precio": tipo,
            "moneda": moneda,
            "unidad": unidad,
            "precio": "" if price is None else f"{price:g}",
            "volumen": text(value_for(source, "Volumen", "Cantidad", "Toneladas", "Cantidad TN", "Volumen TN")),
            "zona": text(value_for(source, "Zona", "Localidad", "Lugar de entrega")),
            "provincia": text(value_for(source, "Provincia", "Pcia")),
            "condicion_comercial": text(value_for(source, "Condición comercial", "Condicion comercial", "Condición", "Condicion", "Pago", "Entrega")),
            "archivo_origen": path.name,
            "fecha_integracion": date.today().isoformat(),
            "observaciones": observation,
        })
    return rows, {"columns": columns, "read": len(source_rows), "integrated": len(rows), "dates": dates, "prices": prices, "commodities": sorted({row["commodity"] for row in rows})}


def is_non_real(path: Path) -> bool:
    return any(marker in key(path.name) for marker in NON_REAL_MARKERS)


def candidate_files() -> list[Path]:
    if not RAW_DIR.exists():
        return []
    return sorted(path for path in RAW_DIR.iterdir() if path.is_file() and path.suffix.lower() in EXTENSIONS and not path.name.startswith("~$"))


def remove_output() -> None:
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()


def write_output(rows: Iterable[dict[str, str]]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    candidates = candidate_files()
    files = [path for path in candidates if not is_non_real(path)]
    non_real = [path for path in candidates if is_non_real(path)]
    if non_real:
        print("Se omiten archivos de prueba/plantilla: " + ", ".join(path.name for path in non_real))
    if not files:
        remove_output()
        print("No hay archivos reales de SIO Granos en data/commodities_sio/raw/.")
        print("No hay datos integrados ni se generan reportes vacíos.")
        return 0
    aliases = read_aliases()
    all_rows: list[dict[str, str]] = []
    errors = 0
    for path in files:
        try:
            rows, diagnostics = process_file(path, aliases)
            all_rows.extend(rows)
            print(f"Archivo procesado: {path.name}")
            print(f"  Columnas detectadas: {', '.join(diagnostics['columns']) or '(JSON/estructura anidada)'}")
            print(f"  Commodity detectado: {', '.join(diagnostics['commodities']) or 'sin identificar'}")
            print(f"  Filas leídas: {diagnostics['read']}; filas integradas: {diagnostics['integrated']}")
            print(f"  Precio mínimo: {min(diagnostics['prices']):g}" if diagnostics["prices"] else "  Precio mínimo: sin precio válido")
            print(f"  Precio máximo: {max(diagnostics['prices']):g}" if diagnostics["prices"] else "  Precio máximo: sin precio válido")
            print(f"  Fecha mínima: {min(diagnostics['dates']).isoformat()}" if diagnostics["dates"] else "  Fecha mínima: sin fecha válida")
            print(f"  Fecha máxima: {max(diagnostics['dates']).isoformat()}" if diagnostics["dates"] else "  Fecha máxima: sin fecha válida")
        except Exception as exc:
            errors += 1
            print(f"ERROR en {path.name}: {exc}")
            print("  Sugerencia: revisar encabezados o conservar la respuesta JSON original para ajustar el mapeo.")
    if not all_rows:
        remove_output()
        print("No se integraron filas válidas de SIO Granos. No se generan reportes vacíos.")
        return 0
    write_output(all_rows)
    print(f"Integración SIO finalizada: {len(all_rows)} filas en {OUTPUT_PATH}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
