#!/usr/bin/env python3
"""Normaliza descargas BCR sin mezclar este dominio con frutas/hortalizas."""

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
    "fecha", "commodity", "commodity_original", "fuente", "mercado", "tipo_precio",
    "moneda", "unidad", "precio", "frecuencia", "condicion_comercial", "contrato",
    "vencimiento", "fuente_url", "fecha_actualizacion", "fecha_descarga", "archivo_origen",
    "observaciones",
]
EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}
IGNORED_NAMES = {"PLANTILLA_COMMODITIES_BCR.csv", "desktop.ini"}


def key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


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
            pass
    return None


def parse_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raw = text(value).replace("$", "").replace("ARS", "").replace("USD", "").strip()
    if not raw:
        return None
    raw = re.sub(r"[^0-9,.-]", "", raw)
    if not raw:
        return None
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def read_catalog() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    alias_map: dict[str, str] = {}
    rows: dict[str, dict[str, str]] = {}
    if not CATALOG_PATH.exists():
        return alias_map, rows
    with CATALOG_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            canonical = text(row.get("commodity"))
            if not canonical:
                continue
            rows[key(canonical)] = row
            for alias in [canonical] + text(row.get("aliases")).split("|"):
                if alias.strip():
                    alias_map[key(alias)] = canonical
    return alias_map, rows


def normalize_commodity(value: Any, filename: str, alias_map: dict[str, str]) -> tuple[str, str, str]:
    original = text(value)
    if original and key(original) in alias_map:
        return alias_map[key(original)], original, ""
    if original:
        return original, original, "commodity no catalogado; conservar para revisión"
    filename_key = key(filename)
    for alias, canonical in sorted(alias_map.items(), key=lambda item: len(item[0]), reverse=True):
        if alias and alias in filename_key:
            return canonical, original or canonical, "commodity inferido desde el nombre del archivo"
    return "No identificado", original, "commodity no identificado; revisar archivo"


def read_csv(path: Path) -> list[dict[str, Any]]:
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
    sample = content[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    return [dict(row) for row in csv.DictReader(content.splitlines(), dialect=dialect)]


def read_json(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for name in ("data", "results", "records", "items", "rows"):
            if isinstance(payload.get(name), list):
                return [row for row in payload[name] if isinstance(row, dict)]
        return [payload]
    return []


def read_excel(path: Path) -> list[dict[str, Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("para leer XLSX/XLS instale openpyxl o convierta el archivo a CSV") from exc
    workbook = load_workbook(path, read_only=True, data_only=True)
    rows: list[dict[str, Any]] = []
    for sheet in workbook.worksheets:
        values = list(sheet.values)
        if not values:
            continue
        header_index = next((i for i, row in enumerate(values[:10]) if row and any(text(cell) for cell in row)), None)
        if header_index is None:
            continue
        headers = [text(cell) or f"columna_{i + 1}" for i, cell in enumerate(values[header_index])]
        for values_row in values[header_index + 1:]:
            if not values_row or not any(text(cell) for cell in values_row):
                continue
            rows.append({headers[i]: values_row[i] if i < len(values_row) else "" for i in range(len(headers))})
    return rows


def read_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        return read_csv(path)
    if path.suffix.lower() == ".json":
        return read_json(path)
    return read_excel(path)


def value_for(row: dict[str, Any], *names: str) -> Any:
    normalized = {key(name): value for name, value in row.items()}
    for name in names:
        if key(name) in normalized:
            return normalized[key(name)]
    return ""


def frequency(filename: str, dates: list[date]) -> str:
    name = key(filename)
    if "mensual" in name or "monthly" in name:
        return "Mensual"
    if "anual" in name or "annual" in name:
        return "Anual"
    if len(dates) >= 2:
        gaps = sorted((later - earlier).days for earlier, later in zip(sorted(set(dates)), sorted(set(dates))[1:]))
        if gaps and sum(gaps) / len(gaps) <= 3:
            return "Diaria"
    return "Sin determinar"


def process_file(path: Path, alias_map: dict[str, str]) -> tuple[list[dict[str, str]], bool]:
    source_rows = read_rows(path)
    if not source_rows:
        return [], False
    parsed_dates = [parse_date(value_for(row, "fecha", "date", "fecha mercado", "fecha cotizacion", "fecha de mercado")) for row in source_rows]
    valid_dates = [item for item in parsed_dates if item]
    rows: list[dict[str, str]] = []
    for index, source in enumerate(source_rows):
        commodity_value = value_for(source, "commodity", "producto", "grano", "cereal", "especie")
        commodity, original, commodity_note = normalize_commodity(commodity_value, path.name, alias_map)
        observation = text(value_for(source, "observaciones", "observacion", "notas", "notes"))
        if commodity_note:
            observation = "; ".join(part for part in (observation, commodity_note) if part)
        market_date = parsed_dates[index]
        price = parse_number(value_for(source, "precio", "price", "valor", "cotizacion", "cotización", "precio pizarra"))
        if not market_date and price is None and not commodity_value:
            continue
        rows.append({
            "fecha": market_date.isoformat() if market_date else "",
            "commodity": commodity,
            "commodity_original": original,
            "fuente": text(value_for(source, "fuente", "source")) or "BCR/Cámara Arbitral",
            "mercado": text(value_for(source, "mercado", "market", "plaza")),
            "tipo_precio": text(value_for(source, "tipo_precio", "tipo de precio", "tipo", "price type")) or "Pizarra/Cámara (verificar)",
            "moneda": text(value_for(source, "moneda", "currency")),
            "unidad": text(value_for(source, "unidad", "unit")),
            "precio": "" if price is None else f"{price:g}",
            "frecuencia": text(value_for(source, "frecuencia", "frequency")) or frequency(path.name, valid_dates),
            "condicion_comercial": text(value_for(source, "condicion_comercial", "condición comercial", "condicion", "condition")),
            "contrato": text(value_for(source, "contrato", "contract")),
            "vencimiento": text(value_for(source, "vencimiento", "expiry", "expiration")),
            "fuente_url": text(value_for(source, "fuente_url", "url", "source url")),
            "fecha_actualizacion": text(value_for(source, "fecha_actualizacion", "fecha actualización", "updated_at")),
            "fecha_descarga": text(value_for(source, "fecha_descarga", "download_date")) or date.today().isoformat(),
            "archivo_origen": path.name,
            "observaciones": observation,
        })
    return rows, True


def raw_files() -> list[Path]:
    if not RAW_DIR.exists():
        return []
    return sorted(path for path in RAW_DIR.iterdir() if path.is_file() and path.suffix.lower() in EXTENSIONS and path.name not in IGNORED_NAMES and not path.name.startswith("~$"))


def write_output(rows: Iterable[dict[str, str]]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    alias_map, _ = read_catalog()
    files = raw_files()
    if not files:
        write_output([])
        template_files = []
        if RAW_DIR.exists():
            template_files = [path for path in RAW_DIR.iterdir() if path.is_file() and any(token in key(path.name) for token in ("plantilla", "simul", "prueba", "test"))]
        if template_files:
            print("Los datos disponibles son de prueba o plantilla. No usar para análisis real.")
        print("No hay archivos reales BCR en data/commodities_bcr/raw/.")
        print("No hay datos integrados. Se creó sólo el encabezado del CSV procesado; no hay reportes para publicar.")
        print("Próximo paso: descargue archivos manuales de Pizarra/Cámara para soja, maíz, trigo, girasol y sorgo, o configure una API autorizada.")
        return 0

    all_rows: list[dict[str, str]] = []
    simulated = False
    for path in files:
        lowered = key(path.name)
        if any(token in lowered for token in ("plantilla", "simul", "prueba", "test")):
            simulated = True
        try:
            rows, had_source = process_file(path, alias_map)
            all_rows.extend(rows)
            print(f"{path.name}: {len(rows)} registro(s) normalizado(s)")
            if not had_source:
                print(f"  Aviso: {path.name} no contiene filas reconocibles.")
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            print(f"ERROR en {path.name}: {exc}")
            return 1
    write_output(all_rows)
    if simulated:
        print("Los datos disponibles son de prueba o plantilla. No usar para análisis real.")
    if not all_rows:
        print("No hay datos integrados válidos. No se generarán reportes vacíos.")
        return 0
    print(f"Integración finalizada: {len(all_rows)} registros en {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
