#!/usr/bin/env python3
"""Integra HTML/CSV/XLSX de precios internos locales mensuales.

La publicación HTML de Secretaría contiene bloques anchos por commodity y
plaza. El integrador los convierte a formato largo, conserva la plaza dentro
de ``mercado`` y omite celdas vacías o ``S/C`` sin inventar precios.
"""

from __future__ import annotations

import argparse
import os
import re
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any

from local_mensual_common import (
    DEFAULT_PROCESSED_DIR,
    DEFAULT_RAW_DIR,
    INTEGRATED_FIELDS,
    find_column,
    format_number,
    load_source_config,
    parse_date,
    parse_number,
    parse_period,
    read_html_tables,
    read_html_text,
    read_tabular_file,
    row_value,
    text,
    write_csv,
)


RAW_EXTENSIONS = {".csv", ".txt", ".tsv", ".xlsx", ".xls", ".json", ".html", ".htm"}
KNOWN_COMMODITIES = {
    "soja": "Soja", "soya": "Soja", "maiz": "Maíz", "corn": "Maíz",
    "trigo": "Trigo", "wheat": "Trigo", "girasol": "Girasol", "sunflower": "Girasol",
    "sorgo": "Sorgo", "sorghum": "Sorgo", "cebada": "Cebada", "barley": "Cebada",
    "cebadaforrajera": "Cebada forrajera", "barleyfeed": "Cebada forrajera",
}
MISSING_VALUES = {"", "sc", "s/c", "sd", "s/d", "n/d", "na", "n/a", "no disponible", "-"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Integra precios internos locales mensuales desde raw/")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--output", default=str(DEFAULT_PROCESSED_DIR / "COMMODITIES_LOCAL_MENSUAL_INTEGRADO.csv"))
    parser.add_argument("--config", default="", help="configuración JSON alternativa")
    parser.add_argument("--source-name", default=os.getenv("LOCAL_MENSUAL_SOURCE_NAME", ""))
    parser.add_argument("--market", default=os.getenv("LOCAL_MENSUAL_MARKET", ""))
    parser.add_argument("--tipo-precio", default=os.getenv("LOCAL_MENSUAL_TIPO_PRECIO", ""))
    parser.add_argument("--currency", default=os.getenv("LOCAL_MENSUAL_CURRENCY", ""))
    parser.add_argument("--unit", default=os.getenv("LOCAL_MENSUAL_UNIT", ""))
    parser.add_argument("--input-frequency", choices=("auto", "mensual", "diaria"), default=os.getenv("LOCAL_MENSUAL_INPUT_FREQUENCY", "auto"))
    parser.add_argument("--aggregate-method", choices=("median", "mean"), default=os.getenv("LOCAL_MENSUAL_AGGREGATE_METHOD", "median"))
    return parser.parse_args()


def normalized(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", text(value)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "", raw)


def normalize_commodity(value: str) -> tuple[str, str]:
    original = text(value)
    canonical = KNOWN_COMMODITIES.get(normalized(original))
    if canonical:
        return canonical, "" if normalized(original) == normalized(canonical) else f"commodity normalizado desde '{original}'"
    return original, "commodity no catalogado; se conserva para revisión" if original else "commodity no informado"


def config_text(config: dict[str, Any], key: str) -> str:
    return text(config.get(key, ""))


def metadata(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, str]:
    return {
        "fuente": text(args.source_name) or config_text(config, "nombre_fuente"),
        "mercado": text(args.market) or config_text(config, "mercado"),
        "tipo_precio": text(args.tipo_precio) or config_text(config, "tipo_precio"),
        "moneda": text(args.currency) or config_text(config, "moneda"),
        "unidad": text(args.unit) or config_text(config, "unidad"),
        "frecuencia": config_text(config, "frecuencia") or "Mensual",
    }


def source_value(row: dict[str, str], headers: list[str], field: str, fallback: str) -> str:
    return row_value(row, headers, field) or text(fallback)


def build_row(
    *, commodity: str, parsed_date: date | None, price: float, path: Path, metadata_values: dict[str, str],
    market: str = "", observations: str = "", frequency: str = "mensual",
) -> dict[str, str]:
    canonical, commodity_note = normalize_commodity(commodity)
    notes = [item for item in (commodity_note, observations) if item]
    if parsed_date:
        parsed_date = parsed_date.replace(day=1)
        date_value = parsed_date.isoformat()
        period = parsed_date.strftime("%Y-%m")
    else:
        date_value = ""
        period = ""
    return {
        "fecha": date_value,
        "año": str(parsed_date.year) if parsed_date else "",
        "mes": str(parsed_date.month) if parsed_date else "",
        "periodo_ym": period,
        "commodity": canonical,
        "fuente": metadata_values["fuente"],
        "mercado": market or metadata_values["mercado"],
        "tipo_precio": metadata_values["tipo_precio"],
        "moneda": metadata_values["moneda"],
        "unidad": metadata_values["unidad"],
        "precio": format_number(price),
        "frecuencia": "mensual" if frequency.lower() not in {"diaria", "diario", "daily"} else "mensual",
        "archivo_origen": path.name,
        "fecha_integracion": date.today().isoformat(),
        "observaciones": "; ".join(notes),
    }


def choose_frequency(row: dict[str, str], headers: list[str], args: argparse.Namespace) -> str:
    if args.input_frequency in {"mensual", "diaria"}:
        return args.input_frequency
    value = row_value(row, headers, "frecuencia").lower()
    return "diaria" if value in {"diaria", "diario", "daily", "daily series"} else "mensual"


def html_metadata_is_explicit(document: str) -> bool:
    value = normalized(document)
    compact = re.sub(r"\s+", "", document.lower())
    pesos_por_tonelada = "pesosargentinos" in value and ("porton" in value or "portoneladas" in value or "pton" in value)
    pesos_por_tonelada_simbolo = any(token in compact for token in ("$/tn", "$/ton"))
    return pesos_por_tonelada or pesos_por_tonelada_simbolo


def year_from_row(row: list[str]) -> int | None:
    for value in row[:3]:
        match = re.search(r"\b((?:19|20)\d{2})\b", text(value))
        if match:
            return int(match.group(1))
    return None


def month_from_value(value: str) -> int | None:
    aliases = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
        "noviembre": 11, "diciembre": 12,
    }
    return aliases.get(normalized(value))


def is_header_row(row: list[str]) -> bool:
    first = normalized(row[0] if row else "")
    if "ano" not in first or "mes" not in first:
        return False
    return any(normalized(value) in KNOWN_COMMODITIES for value in row[1:])


def integrate_html_table(matrix: list[list[str]], path: Path, metadata_values: dict[str, str], explicit_metadata: bool) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    pending_commodities: list[str] | None = None
    schema: list[tuple[str, str]] = []
    current_year: int | None = None
    for raw_row in matrix:
        row = [text(value) for value in raw_row]
        if not any(row):
            continue
        if is_header_row(row):
            pending_commodities = [normalize_commodity(value)[0] if normalized(value) in KNOWN_COMMODITIES else "" for value in row[1:]]
            schema = []
            continue
        if pending_commodities is not None:
            locations = row[1:]
            schema = [(commodity, text(locations[index]) if index < len(locations) else "") for index, commodity in enumerate(pending_commodities) if commodity]
            pending_commodities = None
            continue
        row_year = year_from_row(row)
        if row_year:
            current_year = row_year
            continue
        month = month_from_value(row[0] if row else "")
        if not schema or not current_year or not month:
            continue
        parsed_date = date(current_year, month, 1)
        for offset, (commodity, location) in enumerate(schema, start=1):
            raw_price = row[offset] if offset < len(row) else ""
            if normalized(raw_price) in MISSING_VALUES:
                continue
            price = parse_number(raw_price)
            if price is None:
                continue
            market = metadata_values["mercado"]
            if location:
                market = f"{market} — {location}" if market else location
            notes = [f"plaza/puerto: {location}" if location else "", "tabla HTML de precios internos"]
            if not explicit_metadata:
                notes.append("moneda/unidad no completadas: la página no declaró pesos argentinos por tonelada")
            rows.append(build_row(
                commodity=commodity, parsed_date=parsed_date, price=price, path=path,
                metadata_values=metadata_values, market=market, observations="; ".join(item for item in notes if item),
            ))
    return rows


def integrate_html_file(path: Path, args: argparse.Namespace, config: dict[str, Any]) -> tuple[list[dict[str, str]], int, str]:
    tables = read_html_tables(path)
    if not tables:
        return [], 0, "HTML sin tablas"
    explicit = html_metadata_is_explicit(read_html_text(path))
    values = metadata(args, config)
    if not explicit:
        values["moneda"] = ""
        values["unidad"] = ""
    rows: list[dict[str, str]] = []
    for table in tables:
        rows.extend(integrate_html_table(table, path, values, explicit))
    return rows, sum(len(table) for table in tables), "" if rows else "no se detectó una tabla mensual compatible"


def integrate_tabular_file(path: Path, args: argparse.Namespace, config: dict[str, Any]) -> tuple[list[dict[str, str]], int, str]:
    headers, source_rows = read_tabular_file(path)
    if not headers:
        return [], 0, "sin encabezados"
    values = metadata(args, config)
    direct_rows: list[dict[str, str]] = []
    daily_groups: dict[tuple[str, ...], list[tuple[float, date]]] = defaultdict(list)
    price_column = find_column(headers, "precio")
    for row in source_rows:
        parsed_date = parse_period(row, headers)
        price = parse_number(row.get(price_column, "")) if price_column else None
        if price is None:
            continue
        frequency = choose_frequency(row, headers, args)
        commodity = row_value(row, headers, "commodity")
        if not commodity:
            continue
        row_values = {
            "fuente": source_value(row, headers, "fuente", values["fuente"]),
            "mercado": source_value(row, headers, "mercado", values["mercado"]),
            "tipo_precio": source_value(row, headers, "tipo_precio", values["tipo_precio"]),
            "moneda": source_value(row, headers, "moneda", values["moneda"]),
            "unidad": source_value(row, headers, "unidad", values["unidad"]),
        }
        if frequency == "diaria" and parsed_date:
            canonical, _ = normalize_commodity(commodity)
            key = (canonical, row_values["fuente"], row_values["mercado"], row_values["tipo_precio"], row_values["moneda"], row_values["unidad"], parsed_date.strftime("%Y-%m"))
            daily_groups[key].append((price, parsed_date))
        elif parsed_date:
            direct_rows.append(build_row(commodity=commodity, parsed_date=parsed_date, price=price, path=path, metadata_values=row_values, market=row_values["mercado"], observations="tabla estructurada"))
    for key, values_for_period in daily_groups.items():
        commodity, source, market, price_type, currency, unit, period = key
        prices = [item[0] for item in values_for_period]
        parsed_date = parse_date(period)
        metadata_values = {"fuente": source, "mercado": market, "tipo_precio": price_type, "moneda": currency, "unidad": unit}
        aggregate = median(prices) if args.aggregate_method == "median" else mean(prices)
        direct_rows.append(build_row(commodity=commodity, parsed_date=parsed_date, price=aggregate, path=path, metadata_values=metadata_values, market=market, observations=f"agregado desde datos diarios: {args.aggregate_method}; registros diarios={len(prices)}"))
    return direct_rows, len(source_rows), ""


def integrate_file(path: Path, args: argparse.Namespace, config: dict[str, Any]) -> tuple[list[dict[str, str]], int, str]:
    return integrate_html_file(path, args, config) if path.suffix.lower() in {".html", ".htm"} else integrate_tabular_file(path, args, config)


def deduplicate(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    comparison_fields = [field for field in INTEGRATED_FIELDS if field not in {"fecha_integracion", "observaciones"}]
    duplicates = 0
    for row in rows:
        key = tuple(text(row.get(field, "")) for field in comparison_fields)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        result.append(row)
    return result, duplicates


def main() -> int:
    args = parse_args()
    config_path = Path(args.config) if args.config else None
    config, loaded_path = load_source_config(config_path)
    raw_dir = Path(args.raw_dir)
    output = Path(args.output)
    raw_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in raw_dir.iterdir() if path.is_file() and path.suffix.lower() in RAW_EXTENSIONS)
    all_rows: list[dict[str, str]] = []
    total_read = 0
    skipped: list[str] = []
    for path in files:
        try:
            rows, read_count, note = integrate_file(path, args, config)
        except Exception as exc:
            skipped.append(f"{path.name}: {exc.__class__.__name__}: {exc}")
            continue
        all_rows.extend(rows)
        total_read += read_count
        if note:
            skipped.append(f"{path.name}: {note}")
    all_rows.sort(key=lambda row: (row.get("periodo_ym", ""), row.get("commodity", ""), row.get("fuente", ""), row.get("mercado", ""), row.get("moneda", "")))
    all_rows, duplicates = deduplicate(all_rows)
    write_csv(output, INTEGRATED_FIELDS, all_rows)
    print(f"Configuración: {loaded_path.resolve() if loaded_path else 'no encontrada'}")
    print(f"Archivos encontrados: {len(files)}")
    print(f"Filas de tablas leídas: {total_read}; filas integradas: {len(all_rows)}; duplicados exactos omitidos: {duplicates}")
    print(f"Salida: {output.resolve()}")
    if skipped:
        print("Archivos observados:")
        for item in skipped:
            print(f"- {item}")
    if not files:
        print("No hay archivos locales en raw/. Se generó sólo el encabezado, sin inventar datos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
