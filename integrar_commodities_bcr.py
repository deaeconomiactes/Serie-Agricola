"""Integra descargas manuales de precios de pizarra BCR/Cámara Arbitral.

El script no realiza scraping ni llamadas de red. Lee archivos CSV, XLSX o XLS
desde ``data/commodities_bcr/raw/`` o desde la carpeta indicada como argumento
y genera una base independiente en ``data/commodities_bcr/processed/``.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = PROJECT_DIR / "data" / "commodities_bcr" / "raw"
OUTPUT_PATH = PROJECT_DIR / "data" / "commodities_bcr" / "processed" / "COMMODITIES_BCR_INTEGRADO.csv"
TEMPLATE_PATH = DEFAULT_INPUT_DIR / "PLANTILLA_COMMODITIES_BCR.csv"
CATALOG_PATH = PROJECT_DIR / "data" / "commodities_bcr" / "catalogo_commodities_bcr.csv"

OUTPUT_COLUMNS = [
    "fecha", "año", "mes", "commodity", "fuente", "mercado", "tipo_precio",
    "moneda", "unidad", "precio", "frecuencia", "condicion_comercial",
    "archivo_origen", "fecha_integracion", "observaciones",
]
TABULAR_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}
DATE_COLUMNS = ("fecha", "date", "fecha mercado", "fecha de mercado", "fecha pizarra", "día", "dia")
COMMODITY_COLUMNS = ("producto", "grano", "especie", "commodity", "producto/grano")
PRICE_COLUMNS = ("precio", "precio pizarra", "pizarra", "valor", "cotizacion", "cotización", "precio camara", "precio cámara", "cámara", "camara")
UNIT_COLUMNS = ("unidad", "unit", "unidad precio", "unidad de precio")
CURRENCY_COLUMNS = ("moneda", "currency", "divisa")
NOTE_COLUMNS = ("observacion", "observaciones", "observación", "observaciones", "nota", "notas")
CONDITION_COLUMNS = ("condicion comercial", "condición comercial", "condicion", "condición", "entrega", "pago")
MARKET_COLUMNS = ("mercado", "plaza", "puerto")
PRICE_TYPE_COLUMNS = ("tipo precio", "tipo de precio", "tipo")
ID_COLUMNS = ("id grano", "idgrano", "bcr id grano", "bcr_id_grano")
IGNORED_FILENAMES = {"desktop.ini", "plantilla_commodities_bcr.csv"}
PRICE_EXCLUDED_KEYS = ("ano", "anio", "mes", "cantidad", "volumen", "observacion", "nota")
MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def normalize_text(value: Any) -> str:
    """Normaliza espacios y errores frecuentes de codificación sin perder acentos."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).replace("\xa0", " ").strip()
    for bad, good in (("Ã¡", "á"), ("Ã©", "é"), ("Ã­", "í"), ("Ã³", "ó"),
                      ("Ãº", "ú"), ("Ã±", "ñ"), ("Â°", "°")):
        text = text.replace(bad, good)
    return re.sub(r"\s+", " ", text)


def _key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", normalize_text(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def load_commodity_catalog(path: Path = CATALOG_PATH) -> tuple[dict[str, str], set[str], dict[str, str]]:
    """Carga aliases del catálogo sin hacer obligatorio su uso."""
    if not path.exists():
        return {}, set(), {}
    try:
        catalog = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    except (OSError, UnicodeError, pd.errors.ParserError):
        return {}, set(), {}
    aliases: dict[str, str] = {}
    canonical: set[str] = set()
    ids: dict[str, str] = {}
    for _, row in catalog.iterrows():
        product = normalize_text(row.get("commodity", ""))
        if not product:
            continue
        canonical.add(_key(product))
        aliases[_key(product)] = product
        bcr_id = normalize_text(row.get("bcr_id_grano", ""))
        if bcr_id:
            ids[_key(bcr_id)] = product
        for alias in re.split(r"[|,;/]", normalize_text(row.get("aliases", ""))):
            if _key(alias):
                aliases[_key(alias)] = product
    return aliases, canonical, ids


def normalize_commodity(value: Any, catalog: dict[str, str] | None = None) -> str:
    text = normalize_text(value)
    key = _key(text)
    if not key or key in {"nan", "none", "null", "n/a", "na", "total", "totales"}:
        return ""
    if catalog is None:
        catalog, _, _ = load_commodity_catalog()
    if key in catalog:
        return catalog[key]
    if "trigocandeal" in key:
        return "Trigo Candeal"
    if "trigopan" in key or key.startswith("trigo"):
        return "Trigo"
    if key.startswith("soja"):
        return "Soja"
    if key.startswith("maiz") or key.startswith("maiz"):
        return "Maíz"
    if key.startswith("girasol"):
        return "Girasol"
    if key.startswith("sorgo"):
        return "Sorgo"
    if key.startswith("cebada"):
        return "Cebada"
    return text


def commodity_from_filename(filename: str, catalog: dict[str, str] | None = None) -> str:
    """Detecta el commodity en el nombre cuando falta la columna de producto."""
    key = _key(Path(filename).stem)
    if catalog is None:
        catalog, _, _ = load_commodity_catalog()
    for alias in sorted(catalog, key=len, reverse=True):
        if alias and alias in key:
            return catalog[alias]
    for token, commodity in (("girasol", "Girasol"), ("soja", "Soja"), ("maiz", "Maíz"),
                             ("trigo", "Trigo"), ("sorgo", "Sorgo"), ("cebada", "Cebada")):
        if token in key:
            return commodity
    return ""


def normalize_price_type(value: Any) -> str:
    text = normalize_text(value)
    key = _key(text)
    if not key:
        return ""
    if "fob" in key:
        return "FOB"
    if "fas" in key:
        return "FAS"
    if "futur" in key or "forward" in key:
        return "Futuro"
    if "disponible" in key or key in {"spot", "contado"}:
        return "Precio disponible"
    if "ajuste" in key or "cierre" in key:
        return "Cierre/Ajuste"
    if "pizarra" in key or "camara" in key:
        return "Precio de pizarra"
    return text


def normalize_currency(value: Any) -> str:
    text = normalize_text(value)
    key = _key(text)
    if not key:
        return ""
    if key in {"ars", "peso", "pesos", "pesosargentinos", "$", "arsmonto"} or "peso" in key:
        return "ARS"
    if key in {"usd", "us", "dolar", "dolares", "dollar", "dollars", "u$s", "us$"} or "dolar" in key:
        return "USD"
    return text.upper()


def normalize_unit(value: Any) -> str:
    text = normalize_text(value)
    key = _key(text)
    if not key:
        return ""
    if "tonelada" in key or key in {"tn", "t", "ton", "tons", "mt", "usdtn", "arstn"}:
        return "$/Tn"
    if "kilogram" in key or key in {"kg", "usdkg", "arskg"}:
        return "$/Kg"
    return text


def parse_argentine_number(value: Any) -> float | None:
    """Convierte números argentinos y conserva ceros y negativos para auditoría."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if not pd.isna(value) else None
    text = normalize_text(value).replace("$", "").replace(" ", "")
    if not text or text.lower() in {"nan", "nat", "none", "null", "n/a", "na", "-", "–", "s/c", "s/d"}:
        return None
    text = re.sub(r"[^0-9,.-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None
    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text:
        parts = text.split(",")
        text = "".join(parts[:-1]) + "." + parts[-1] if len(parts[-1]) <= 2 else "".join(parts)
    elif "." in text:
        left, right = text.rsplit(".", 1)
        text = left.replace(".", "") + ("." + right if len(right) <= 2 else right)
    try:
        return float(text)
    except ValueError:
        return None


def parse_date(value: Any) -> str:
    """Devuelve una fecha ISO válida, sin fabricar días para períodos agregados."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, (int, float)) and not pd.isna(value) and 1 <= float(value) <= 100000:
        try:
            return (datetime(1899, 12, 30) + timedelta(days=float(value))).strftime("%Y-%m-%d")
        except (OverflowError, ValueError):
            return ""
    text = normalize_text(value).split(" ", 1)[0]
    if not text or _key(text) in {"nan", "nat", "none", "null"}:
        return ""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    return parsed.strftime("%Y-%m-%d") if not pd.isna(parsed) else ""


def _filename_date(filename: str) -> str:
    name = Path(filename).stem
    for pattern in (r"(?<!\d)(\d{4})[-_](\d{2})[-_](\d{2})(?!\d)",
                    r"(?<!\d)(\d{2})[-_](\d{2})[-_](\d{4})(?!\d)",
                    r"(?<!\d)(\d{8})(?!\d)", r"(?<!\d)(\d{6})(?!\d)"):
        match = re.search(pattern, name)
        if not match:
            continue
        raw = match.group(1)
        if len(raw) == 8:
            for candidate in (raw, f"{raw[4:]}-{raw[2:4]}-{raw[:2]}", f"{raw[:2]}-{raw[2:4]}-{raw[4:]}"):
                parsed = parse_date(candidate)
                if parsed:
                    return parsed
        elif len(raw) == 6:
            parsed = parse_date(f"{raw[:2]}-{raw[2:4]}-{raw[4:]}")
            if parsed:
                return parsed
        else:
            parsed = parse_date(raw)
            if parsed:
                return parsed
    return ""


def _filename_year_month(filename: str) -> tuple[str, str]:
    """Extrae año/mes sólo cuando el nombre los identifica sin inventar un día."""
    stem = Path(filename).stem
    key = _key(stem)
    year_match = re.search(r"(?<!\d)(20\d{2})(?!\d)", key)
    year = year_match.group(1) if year_match else ""
    for month_name, month_number in MONTHS.items():
        if month_name in key:
            return year, f"{month_number:02d}"
    for match in re.finditer(r"(?<!\d)(0?[1-9]|1[0-2])[-_](20\d{2})(?!\d)", stem):
        return match.group(2), f"{int(match.group(1)):02d}"
    for match in re.finditer(r"(?<!\d)(20\d{2})[-_](0?[1-9]|1[0-2])(?!\d)", stem):
        return match.group(1), f"{int(match.group(2)):02d}"
    return year, ""


def infer_frequency_from_filename_or_data(df: pd.DataFrame, filename: str) -> str:
    """Determina frecuencia sin convertir una fuente mensual/anual en diaria."""
    dates = pd.to_datetime(df.get("_fecha", pd.Series(dtype=object)), errors="coerce", format="%Y-%m-%d").dropna()
    if dates.empty:
        return "Sin determinar"
    key = _key(Path(filename).stem)
    if "anual" in key or "annual" in key or "yearly" in key:
        return "Anual"
    if "mensual" in key or "monthly" in key or "mes" in key:
        return "Mensual"
    if "diaria" in key or "daily" in key:
        return "Diaria"
    unique = dates.dt.normalize().drop_duplicates().sort_values()
    if len(unique) >= 2:
        gaps = unique.diff().dropna().dt.days
        if (gaps >= 300).all():
            return "Anual"
        if (gaps >= 25).all() and (gaps <= 45).all():
            return "Mensual"
        return "Diaria"
    return "Sin determinar"


def _find_column(columns: list[Any], candidates: tuple[str, ...]) -> str | None:
    wanted = {_key(item) for item in candidates}
    normalized = {str(column): _key(column) for column in columns}
    for column, key in normalized.items():
        if key in wanted:
            return column
    for column, key in normalized.items():
        if any(candidate and (key.startswith(candidate) or candidate.startswith(key)) for candidate in wanted):
            return column
    return None


def _find_price_column(columns: list[Any]) -> str | None:
    """Encuentra una columna de precio sin confundir dimensiones o notas."""
    candidate_keys = {_key(candidate) for candidate in PRICE_COLUMNS}
    for column in columns:
        key = _key(column)
        if any(excluded in key for excluded in PRICE_EXCLUDED_KEYS):
            continue
        if key in candidate_keys:
            return str(column)
    for column in columns:
        key = _key(column)
        if any(excluded in key for excluded in PRICE_EXCLUDED_KEYS):
            continue
        if any(candidate in key for candidate in candidate_keys if len(candidate) >= 5):
            return str(column)
    return None


def _read_csv(path: Path) -> list[tuple[str, pd.DataFrame]]:
    sample = path.read_bytes()[:8192]
    text = ""
    detected_encoding = "latin-1"
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = sample.decode(encoding)
            detected_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    if not text:
        raise ValueError("no se pudo detectar la codificación")
    try:
        delimiter = csv.Sniffer().sniff(text, delimiters=";,\t,").delimiter
    except csv.Error:
        delimiter = ";"
    return [("", pd.read_csv(path, sep=delimiter, header=None, dtype=object, encoding=detected_encoding))]


def _json_records(payload: Any) -> list[dict[str, Any]]:
    """Extrae registros de listas, data/results y envoltorios con metadata."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "results", "records", "items"):
        if key in payload:
            records = _json_records(payload[key])
            if records:
                return records
    if any(isinstance(value, (str, int, float, bool)) or value is None for value in payload.values()):
        return [payload]
    return []


def _read_json(path: Path) -> list[tuple[str, pd.DataFrame]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    records = _json_records(payload)
    return [("", pd.DataFrame(records, dtype=object))] if records else []


def _headered(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.dropna(axis=0, how="all").dropna(axis=1, how="all").reset_index(drop=True)
    if frame.empty:
        return pd.DataFrame()
    candidate_rows = []
    for index, row in frame.head(30).iterrows():
        keys = {_key(value) for value in row.tolist() if normalize_text(value)}
        score = sum(any(_key(candidate) in keys for candidate in candidates) for candidates in (DATE_COLUMNS, COMMODITY_COLUMNS, PRICE_COLUMNS))
        candidate_rows.append((score, index))
    score, header_index = max(candidate_rows, default=(0, 0))
    if score < 2:
        return pd.DataFrame()
    headers = []
    for position, value in enumerate(frame.iloc[header_index].tolist()):
        header = normalize_text(value) or f"columna_{position + 1}"
        if header in headers:
            header = f"{header}_{position + 1}"
        headers.append(header)
    result = frame.iloc[header_index + 1:].copy()
    result.columns = headers
    return result.dropna(axis=0, how="all").reset_index(drop=True)


def read_tables(path: Path) -> list[tuple[str, pd.DataFrame]]:
    if path.suffix.lower() == ".json":
        return _read_json(path)
    if path.suffix.lower() == ".csv":
        frames = _read_csv(path)
    else:
        frames = [(str(sheet), frame) for sheet, frame in pd.read_excel(path, sheet_name=None, header=None, dtype=object).items()]
    tables = []
    for sheet, frame in frames:
        table = _headered(frame)
        if not table.empty:
            tables.append((sheet, table))
    return tables


def _value(row: pd.Series, candidates: tuple[str, ...]) -> Any:
    column = _find_column(list(row.index), candidates)
    return row[column] if column is not None else ""


def _row_observations(row: pd.Series, used: set[str]) -> str:
    parts = []
    for column, value in row.items():
        text = normalize_text(value)
        if str(column) not in used and text and _key(text) not in {"nan", "none", "null"}:
            parts.append(f"{normalize_text(column)}={text}")
    return "; ".join(parts)


def _default_condition() -> str:
    return "Mercadería disponible / referencia de pizarra BCR"


def create_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "fecha;commodity;precio;moneda;unidad;tipo_precio;observaciones\n"
        "# Ejemplo: completar con una descarga BCR real; esta fila se ignora\n",
        encoding="utf-8-sig",
    )


def integrate_file(path: Path, integration_date: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    catalog, canonical_commodities, catalog_ids = load_commodity_catalog()
    for sheet_name, frame in read_tables(path):
        date_column = _find_column(list(frame.columns), DATE_COLUMNS)
        commodity_column = _find_column(list(frame.columns), COMMODITY_COLUMNS)
        id_column = _find_column(list(frame.columns), ID_COLUMNS)
        price_column = _find_price_column(list(frame.columns))
        filename_commodity = commodity_from_filename(path.name, catalog)
        id_commodity = ""
        if id_column:
            for raw_id in frame[id_column].tolist():
                id_commodity = catalog_ids.get(_key(raw_id), "")
                if id_commodity:
                    break
        if not price_column or (not commodity_column and not filename_commodity and not id_commodity):
            continue
        frame = frame.copy()
        frame["_fecha"] = frame[date_column].map(parse_date) if date_column else ""
        frequency = infer_frequency_from_filename_or_data(frame, f"{path.name} {sheet_name}")
        fallback_year, fallback_month = _filename_year_month(path.name)
        explicit_unit_column = _find_column(list(frame.columns), UNIT_COLUMNS)
        explicit_currency_column = _find_column(list(frame.columns), CURRENCY_COLUMNS)
        explicit_note_column = _find_column(list(frame.columns), NOTE_COLUMNS)
        explicit_condition_column = _find_column(list(frame.columns), CONDITION_COLUMNS)
        explicit_market_column = _find_column(list(frame.columns), MARKET_COLUMNS)
        explicit_price_type_column = _find_column(list(frame.columns), PRICE_TYPE_COLUMNS)
        for _, row in frame.iterrows():
            raw_commodity = row.get(commodity_column, "") if commodity_column else ""
            commodity = normalize_commodity(raw_commodity, catalog) if commodity_column else ""
            commodity = commodity or (catalog_ids.get(_key(row.get(id_column, "")), "") if id_column else "") or filename_commodity
            if not commodity:
                continue
            date_value = row.get("_fecha", "")
            if not date_value:
                date_value = _filename_date(path.name)
            year_value = date_value[:4] if date_value else fallback_year
            month_value = date_value[5:7] if date_value else fallback_month
            raw_price = row.get(price_column, "")
            price = parse_argentine_number(raw_price)
            raw_unit = row.get(explicit_unit_column, "") if explicit_unit_column else ""
            explicit_unit = normalize_unit(raw_unit)
            explicit_currency = normalize_currency(row.get(explicit_currency_column, "")) if explicit_currency_column else ""
            if not explicit_currency:
                currency_hint = _key(f"{normalize_text(raw_unit)} {price_column}")
                if "usd" in currency_hint or "dolar" in currency_hint or "dollar" in currency_hint:
                    explicit_currency = "USD"
            unit = explicit_unit or "$/Tn"
            currency = explicit_currency or "ARS"
            notes = []
            if canonical_commodities and _key(commodity) not in canonical_commodities:
                notes.append("commodity no catalogado; se conserva para revisión")
            if not explicit_unit:
                notes.append("unidad por defecto BCR: $/Tn; validar contra la fuente")
            if not explicit_currency:
                notes.append("moneda por defecto BCR: ARS; validar contra la fuente")
            note_value = normalize_text(row.get(explicit_note_column, "")) if explicit_note_column else ""
            if note_value:
                notes.append(note_value)
            condition = normalize_text(row.get(explicit_condition_column, "")) if explicit_condition_column else ""
            market = normalize_text(row.get(explicit_market_column, "")) if explicit_market_column else ""
            price_type = normalize_price_type(row.get(explicit_price_type_column, "")) if explicit_price_type_column else ""
            if not price_type:
                price_type = normalize_price_type(f"{price_column} {path.name}") or "Precio de pizarra"
            used = {str(column) for column in (date_column, commodity_column, price_column, explicit_unit_column, explicit_currency_column, explicit_note_column, explicit_condition_column, explicit_market_column, explicit_price_type_column) if column}
            extras = _row_observations(row, used | {"_fecha"})
            if extras:
                notes.append(extras)
            if not date_value:
                notes.append("fecha faltante: no se pudo inferir del archivo")
            if price_type in {"FOB", "FAS", "Futuro", "Cierre/Ajuste", "Precio disponible"}:
                notes.append(f"tipo de referencia detectado: {price_type}; no tratar como precio de pizarra")
            if price is None:
                notes.append("precio faltante o no numérico")
            output.append({
                "fecha": date_value, "año": year_value, "mes": month_value,
                "commodity": commodity, "fuente": "Bolsa de Comercio de Rosario / Cámara Arbitral de Cereales",
                "mercado": market or "Rosario", "tipo_precio": price_type or "Precio de pizarra", "moneda": currency, "unidad": unit,
                "precio": "" if price is None else price, "frecuencia": frequency,
                "condicion_comercial": condition or _default_condition(), "archivo_origen": path.name,
                "fecha_integracion": integration_date, "observaciones": " | ".join(notes),
            })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", nargs="?", type=Path, default=DEFAULT_INPUT_DIR, help="Carpeta con descargas BCR CSV/XLSX/XLS")
    args = parser.parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in input_dir.glob("*") if path.is_file() and path.suffix.lower() in TABULAR_EXTENSIONS and not path.name.startswith("~$") and path.name.lower() not in IGNORED_FILENAMES and path.stat().st_size > 0)
    print(f"Carpeta de entrada: {input_dir}")
    print(f"Archivos encontrados: {len(files)}")
    if not files:
        if input_dir == DEFAULT_INPUT_DIR:
            create_template(TEMPLATE_PATH)
            print("No se encontraron archivos BCR en data/commodities_bcr/raw/. Descargue archivos manualmente y vuelva a ejecutar.")
            print(f"Plantilla generada: {TEMPLATE_PATH}")
        else:
            print(f"No se encontraron archivos BCR en {input_dir}. Descargue archivos manualmente y vuelva a ejecutar.")
    rows: list[dict[str, Any]] = []
    processed, errors = [], []
    integration_date = date.today().isoformat()
    for path in files:
        try:
            file_rows = integrate_file(path, integration_date)
            rows.extend(file_rows)
            processed.append(f"{path.name} ({len(file_rows)} filas)")
        except Exception as exc:  # reportar un archivo defectuoso sin perder los demás
            errors.append(f"{path.name}: {exc}")
    pd.DataFrame(rows, columns=OUTPUT_COLUMNS).to_csv(OUTPUT_PATH, sep=";", index=False, encoding="utf-8-sig")
    dates = sorted(row["fecha"] for row in rows if row["fecha"])
    commodities = sorted({row["commodity"] for row in rows if row["commodity"]})
    print("Archivos procesados:")
    for item in processed:
        print(f"- {item}")
    print("Archivos con error:")
    for item in errors:
        print(f"- {item}")
    print(f"Filas integradas: {len(rows)}")
    print(f"Commodities detectados: {', '.join(commodities) or 'ninguno'}")
    print(f"Rango de fechas: {dates[0] if dates else 'n/d'} a {dates[-1] if dates else 'n/d'}")
    print(f"Archivo generado: {OUTPUT_PATH}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
