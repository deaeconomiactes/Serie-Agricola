#!/usr/bin/env python3
"""Integra descargas manuales de BCR sin mezclar commodities con horticultura."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "commodities_bcr" / "raw"
PROCESSED_DIR = ROOT / "data" / "commodities_bcr" / "processed"
CATALOG_PATH = ROOT / "data" / "commodities_bcr" / "catalogo_commodities_bcr.csv"
OUTPUT_PATH = PROCESSED_DIR / "COMMODITIES_BCR_INTEGRADO.csv"
OUTPUT_COLUMNS = [
    "fecha", "año", "mes", "commodity", "commodity_original", "fuente", "mercado",
    "tipo_precio", "moneda", "unidad", "precio", "frecuencia", "condicion_comercial",
    "contrato", "vencimiento", "fuente_url", "fecha_actualizacion", "fecha_descarga",
    "archivo_origen", "fuente_descarga", "fecha_integracion", "observaciones",
]
EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".html"}
NON_REAL_MARKERS = ("plantilla", "simul", "prueba", "test")
DEFAULT_SOURCE = "Bolsa de Comercio de Rosario / Cámara Arbitral de Cereales"
DEFAULT_MARKET = "Rosario"
DEFAULT_PRICE_TYPE = "Precio de pizarra"
DEFAULT_CURRENCY = "ARS"
DEFAULT_UNIT = "$/Tn"
DEFAULT_CONDITION = "Mercadería disponible / referencia de pizarra BCR"
HEADER_KEYS = {
    "fecha", "fechamercado", "fechapizarra", "fechacotizacion", "dia", "producto", "grano", "commodity", "especie",
    "precio", "preciopizarra", "pizarra", "preciocamara", "cotizacion", "valor", "moneda", "unidad",
}


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
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_argentine_number(value: Any) -> float | None:
    """Convierte números argentinos, incluyendo 250.000,50 y $ 250.000."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raw = text(value).replace("$", "").replace("ARS", "").replace("USD", "").strip()
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


parse_number = parse_argentine_number


def read_catalog() -> dict[str, str]:
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


def normalize_commodity(value: Any, filename: str, aliases: dict[str, str]) -> tuple[str, str, str]:
    original = text(value)
    if original and key(original) in aliases:
        return aliases[key(original)], original, ""
    if original:
        return original, original, "commodity no catalogado; se conserva para revisión"
    filename_key = key(filename)
    for alias, canonical in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if alias and alias in filename_key:
            return canonical, canonical, "commodity inferido desde el nombre del archivo"
    return "No identificado", "", "commodity no identificado; revisar archivo"


def value_for(row: dict[str, Any], *names: str) -> Any:
    normalized = {key(name): value for name, value in row.items()}
    for name in names:
        if key(name) in normalized:
            return normalized[key(name)]
    return ""


def read_csv(path: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    raw = path.read_bytes()
    content = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            content = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if content is None:
        raise ValueError(f"no se pudo decodificar {path.name}")
    try:
        dialect = csv.Sniffer().sniff(content[:4096], delimiters=";,\t|")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    reader = csv.DictReader(content.splitlines(), dialect=dialect)
    columns = [text(column) for column in (reader.fieldnames or [])]
    return [dict(row) for row in reader], ["CSV"], columns


def rows_from_matrix(values: list[tuple[Any, ...]]) -> tuple[list[dict[str, Any]], list[str]]:
    nonempty = [index for index, row in enumerate(values[:30]) if row and any(text(cell) for cell in row)]
    if not nonempty:
        return [], []
    header_index = max(nonempty, key=lambda index: sum(key(cell) in HEADER_KEYS for cell in values[index]))
    headers = [text(cell) or f"columna_{index + 1}" for index, cell in enumerate(values[header_index])]
    rows = []
    for values_row in values[header_index + 1:]:
        if not values_row or not any(text(cell) for cell in values_row):
            continue
        rows.append({headers[index]: values_row[index] if index < len(values_row) else "" for index in range(len(headers))})
    return rows, headers


def read_excel(path: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    if path.suffix.lower() == ".xls":
        try:
            import pandas as pd
            frames = pd.read_excel(path, sheet_name=None, header=None)
            result: list[dict[str, Any]] = []
            sheets: list[str] = []
            columns: list[str] = []
            for sheet_name, frame in frames.items():
                matrix = [tuple(row) for row in frame.where(frame.notna(), "").itertuples(index=False, name=None)]
                sheet_rows, sheet_columns = rows_from_matrix(matrix)
                if sheet_rows:
                    result.extend(sheet_rows)
                    sheets.append(str(sheet_name))
                    columns.extend(column for column in sheet_columns if column not in columns)
            return result, sheets or ["XLS"], columns
        except ImportError as exc:
            raise RuntimeError("para leer XLS instale pandas y xlrd, o convierta el archivo a XLSX/CSV") from exc
        except Exception as exc:
            raise RuntimeError(f"no se pudo leer XLS: {exc.__class__.__name__}; pruebe convertirlo a XLSX/CSV") from exc
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("para leer XLSX instale openpyxl o convierta el archivo a CSV") from exc
    workbook = load_workbook(path, read_only=True, data_only=True)
    result: list[dict[str, Any]] = []
    sheets: list[str] = []
    columns: list[str] = []
    for sheet in workbook.worksheets:
        sheet_rows, sheet_columns = rows_from_matrix([tuple(row) for row in sheet.values])
        if sheet_rows:
            result.extend(sheet_rows)
            sheets.append(sheet.title)
            columns.extend(column for column in sheet_columns if column not in columns)
    return result, sheets or [sheet.title for sheet in workbook.worksheets], columns


def extract_json_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records: list[dict[str, Any]] = []
        for item in payload:
            records.extend(extract_json_records(item))
        return records
    if isinstance(payload, dict):
        for name in ("data", "results", "records", "items", "rows"):
            if name in payload:
                nested = extract_json_records(payload[name])
                if nested:
                    return nested
        return [payload]
    return []


def read_json(path: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = extract_json_records(payload)
    return rows, ["JSON"], [text(column) for column in (list(rows[0].keys()) if rows else [])]


def read_html(path: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Lee sólo tablas HTML claras; una página sin tablas queda como diagnóstico."""
    try:
        import pandas as pd
        tables = pd.read_html(path)
    except ImportError as exc:
        raise RuntimeError("para leer tablas HTML instale pandas o convierta el archivo a XLSX/CSV") from exc
    except ValueError:
        return [], ["HTML"], []
    rows: list[dict[str, Any]] = []
    columns: list[str] = []
    for frame in tables:
        frame = frame.where(frame.notna(), "")
        table_columns = [text(column) for column in frame.columns]
        table_rows = [{table_columns[index]: row[index] for index in range(len(table_columns))} for row in frame.itertuples(index=False, name=None)]
        rows.extend(table_rows)
        columns.extend(column for column in table_columns if column not in columns)
    return rows, [f"tabla_{index + 1}" for index in range(len(tables))] or ["HTML"], columns


def read_source(path: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    if path.suffix.lower() == ".csv":
        return read_csv(path)
    if path.suffix.lower() == ".json":
        return read_json(path)
    if path.suffix.lower() == ".html":
        return read_html(path)
    return read_excel(path)


def detect_frequency(filename: str, dates: list[date]) -> str:
    filename_key = key(filename)
    if "mensual" in filename_key or "monthly" in filename_key:
        return "Mensual"
    if "anual" in filename_key or "annual" in filename_key:
        return "Anual"
    unique_dates = sorted(set(dates))
    if len(unique_dates) >= 2:
        gaps = [(later - earlier).days for earlier, later in zip(unique_dates, unique_dates[1:])]
        if gaps and max(gaps) <= 3:
            return "Diaria"
    return "Sin determinar"


def source_download(path: Path) -> str:
    name = path.name.lower()
    if path.name.upper().startswith("BCR_API_") or "_api_" in name:
        return "API"
    if "public" in name or path.suffix.lower() == ".html":
        return "public-web"
    return "manual"


def process_file(path: Path, aliases: dict[str, str]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    source_rows, sheets, columns = read_source(path)
    parsed_dates = [parse_date(value_for(row, "Fecha", "Fecha Mercado", "Fecha de mercado", "Fecha Pizarra", "Fecha Cotización", "Fecha Cotizacion", "Día", "Dia")) for row in source_rows]
    valid_dates = [item for item in parsed_dates if item]
    detected_frequency = detect_frequency(path.name, valid_dates)
    rows: list[dict[str, str]] = []
    for index, source in enumerate(source_rows):
        raw_commodity = value_for(source, "Producto", "Grano", "Commodity", "Especie")
        commodity, original, commodity_note = normalize_commodity(raw_commodity, path.name, aliases)
        raw_price = value_for(source, "Precio", "Precio Pizarra", "Pizarra", "Precio Cámara", "Precio Camara", "Cotización", "Cotizacion", "Valor")
        parsed_price = parse_argentine_number(raw_price)
        market_date = parsed_dates[index]
        if not market_date and parsed_price is None and not raw_commodity:
            continue
        observation = text(value_for(source, "Observación", "Observaciones", "Nota", "Notas"))
        if commodity_note:
            observation = "; ".join(part for part in (observation, commodity_note) if part)
        rows.append({
            "fecha": market_date.isoformat() if market_date else "",
            "año": str(market_date.year) if market_date else "",
            "mes": str(market_date.month) if market_date else "",
            "commodity": commodity,
            "commodity_original": original,
            "fuente": text(value_for(source, "Fuente", "Source")) or DEFAULT_SOURCE,
            "mercado": text(value_for(source, "Mercado", "Plaza", "Market")) or DEFAULT_MARKET,
            "tipo_precio": text(value_for(source, "Tipo de precio", "Tipo Precio", "Tipo", "Price Type")) or DEFAULT_PRICE_TYPE,
            "moneda": text(value_for(source, "Moneda", "Currency")) or DEFAULT_CURRENCY,
            "unidad": text(value_for(source, "Unidad", "Unit")) or DEFAULT_UNIT,
            "precio": "" if parsed_price is None else f"{parsed_price:g}",
            "frecuencia": text(value_for(source, "Frecuencia", "Frequency")) or detected_frequency,
            "condicion_comercial": text(value_for(source, "Condición comercial", "Condicion comercial", "Condición", "Condicion", "Condition")) or DEFAULT_CONDITION,
            "contrato": text(value_for(source, "Contrato", "Contract")),
            "vencimiento": text(value_for(source, "Vencimiento", "Expiry", "Expiration")),
            "fuente_url": text(value_for(source, "Fuente URL", "URL", "Source URL")),
            "fecha_actualizacion": text(value_for(source, "Fecha actualización", "Fecha actualizacion", "Updated At")),
            "fecha_descarga": text(value_for(source, "Fecha descarga", "Download Date")) or date.today().isoformat(),
            "archivo_origen": path.name,
            "fuente_descarga": source_download(path),
            "fecha_integracion": date.today().isoformat(),
            "observaciones": observation,
        })
    diagnostics = {
        "sheets": sheets,
        "columns": columns,
        "read": len(source_rows),
        "integrated": len(rows),
        "dates": valid_dates,
        "prices": [parse_argentine_number(row["precio"]) for row in rows if row["precio"]],
        "currencies": sorted({row["moneda"] for row in rows if row["moneda"]}),
        "units": sorted({row["unidad"] for row in rows if row["unidad"]}),
        "commodities": sorted({row["commodity"] for row in rows}),
        "download_source": source_download(path),
    }
    return rows, diagnostics


def is_non_real(path: Path) -> bool:
    filename = key(path.name)
    return any(marker in filename for marker in NON_REAL_MARKERS)


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


def print_diagnostics(path: Path, diagnostics: dict[str, Any]) -> None:
    prices = [price for price in diagnostics["prices"] if price is not None]
    print(f"Archivo procesado: {path.name}")
    print(f"  Hojas detectadas: {', '.join(diagnostics['sheets'])}")
    print(f"  Columnas detectadas: {', '.join(diagnostics['columns']) or '(ninguna)'}")
    print(f"  Commodity detectado: {', '.join(diagnostics['commodities']) or 'no identificado'}")
    print(f"  Fuente de descarga: {diagnostics['download_source']}")
    print(f"  Filas leídas: {diagnostics['read']}; filas integradas: {diagnostics['integrated']}")
    print(f"  Precio mínimo: {min(prices):g}" if prices else "  Precio mínimo: sin precio válido")
    print(f"  Precio máximo: {max(prices):g}" if prices else "  Precio máximo: sin precio válido")
    print(f"  Fecha mínima: {min(diagnostics['dates']).isoformat()}" if diagnostics["dates"] else "  Fecha mínima: sin fecha válida")
    print(f"  Fecha máxima: {max(diagnostics['dates']).isoformat()}" if diagnostics["dates"] else "  Fecha máxima: sin fecha válida")
    print(f"  Moneda detectada: {', '.join(diagnostics['currencies']) or DEFAULT_CURRENCY + ' (por defecto)'}")
    print(f"  Unidad detectada: {', '.join(diagnostics['units']) or DEFAULT_UNIT + ' (por defecto)'}")


def main() -> int:
    aliases = read_catalog()
    candidates = candidate_files()
    files = [path for path in candidates if not is_non_real(path)]
    non_real = [path for path in candidates if is_non_real(path)]
    if non_real:
        print("Se omiten archivos marcados como plantilla/prueba/simulación: " + ", ".join(path.name for path in non_real))
    if not files:
        remove_output()
        print("No se encontraron archivos reales de BCR en data/commodities_bcr/raw/. Descargue un Excel/CSV de Precios de Pizarra/Cámara y vuelva a ejecutar la integración.")
        if non_real:
            print("Los datos disponibles son de prueba o plantilla. No usar para análisis real.")
        print("No hay datos integrados ni se generan reportes vacíos.")
        return 0

    all_rows: list[dict[str, str]] = []
    errors = 0
    for path in files:
        try:
            rows, diagnostics = process_file(path, aliases)
            print_diagnostics(path, diagnostics)
            if not diagnostics["columns"]:
                print(f"ERROR en {path.name}: no se detectaron columnas. Sugerencia: use encabezados Fecha, Producto/Grano, Precio, Moneda y Unidad.")
                errors += 1
            all_rows.extend(rows)
        except Exception as exc:
            errors += 1
            print(f"ERROR en {path.name}: {exc}")
            print("  Columnas detectadas: no disponibles")
            print("  Sugerencia: descargue nuevamente el archivo de BCR o conviértalo a XLSX/CSV manteniendo los encabezados.")
    if not all_rows:
        remove_output()
        print("No se integraron filas válidas de archivos reales. No se generan reportes vacíos.")
        return 1 if errors else 0
    write_output(all_rows)
    print(f"Integración finalizada: {len(all_rows)} registros en {OUTPUT_PATH}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
