#!/usr/bin/env python3
"""Integra archivos locales mensuales sin consultar fuentes externas."""

from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean, median

from local_mensual_common import (
    DEFAULT_PROCESSED_DIR,
    DEFAULT_RAW_DIR,
    INTEGRATED_FIELDS,
    find_column,
    format_number,
    parse_date,
    parse_number,
    parse_period,
    read_tabular_file,
    row_value,
    text,
    write_csv,
)


RAW_EXTENSIONS = {".csv", ".txt", ".tsv", ".xlsx", ".xls", ".json"}
KNOWN_COMMODITIES = {
    "soja": "Soja", "soya": "Soja", "maiz": "Maíz", "corn": "Maíz",
    "trigo": "Trigo", "wheat": "Trigo", "girasol": "Girasol", "sunflower": "Girasol",
    "sorgo": "Sorgo", "sorghum": "Sorgo", "cebada": "Cebada", "barley": "Cebada",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Integra commodities locales mensuales desde raw/")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--output", default=str(DEFAULT_PROCESSED_DIR / "COMMODITIES_LOCAL_MENSUAL_INTEGRADO.csv"))
    parser.add_argument("--source-name", default=os.getenv("LOCAL_MENSUAL_SOURCE_NAME", ""))
    parser.add_argument("--market", default=os.getenv("LOCAL_MENSUAL_MARKET", ""))
    parser.add_argument("--tipo-precio", default=os.getenv("LOCAL_MENSUAL_TIPO_PRECIO", ""))
    parser.add_argument("--currency", default=os.getenv("LOCAL_MENSUAL_CURRENCY", ""))
    parser.add_argument("--unit", default=os.getenv("LOCAL_MENSUAL_UNIT", ""))
    parser.add_argument("--input-frequency", choices=("auto", "mensual", "diaria"), default=os.getenv("LOCAL_MENSUAL_INPUT_FREQUENCY", "auto"))
    parser.add_argument("--aggregate-method", choices=("median", "mean"), default=os.getenv("LOCAL_MENSUAL_AGGREGATE_METHOD", "median"))
    return parser.parse_args()


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text(value).lower().translate(str.maketrans("áéíóúñ", "aeioun")))


def normalize_commodity(value: str) -> tuple[str, str]:
    original = text(value)
    canonical = KNOWN_COMMODITIES.get(normalized(original))
    if canonical:
        return canonical, "" if canonical == original else f"commodity normalizado desde '{original}'"
    return original, "commodity no catalogado; se conserva para revisión" if original else "commodity no informado"


def source_value(row: dict[str, str], headers: list[str], field: str, fallback: str) -> str:
    return row_value(row, headers, field) or text(fallback)


def output_row(row: dict[str, str], headers: list[str], path: Path, args: argparse.Namespace, parsed_date, price: float | None, observations: str = "") -> dict[str, str]:
    commodity, commodity_note = normalize_commodity(row_value(row, headers, "commodity"))
    notes = [item for item in (row_value(row, headers, "observaciones"), commodity_note, observations) if item]
    frequency = row_value(row, headers, "frecuencia") or ("mensual" if args.input_frequency == "auto" else args.input_frequency)
    if frequency.lower() not in {"diaria", "diario", "daily"}:
        frequency = "mensual"
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
        "commodity": commodity,
        "fuente": source_value(row, headers, "fuente", args.source_name),
        "mercado": source_value(row, headers, "mercado", args.market),
        "tipo_precio": source_value(row, headers, "tipo_precio", args.tipo_precio),
        "moneda": source_value(row, headers, "moneda", args.currency),
        "unidad": source_value(row, headers, "unidad", args.unit),
        "precio": format_number(price),
        "frecuencia": "mensual",
        "archivo_origen": path.name,
        "fecha_integracion": date.today().isoformat(),
        "observaciones": "; ".join(notes),
    }


def choose_frequency(row: dict[str, str], headers: list[str], args: argparse.Namespace) -> str:
    if args.input_frequency in {"mensual", "diaria"}:
        return args.input_frequency
    value = row_value(row, headers, "frecuencia").lower()
    return "diaria" if value in {"diaria", "diario", "daily", "daily series"} else "mensual"


def integrate_file(path: Path, args: argparse.Namespace) -> tuple[list[dict[str, str]], int, str]:
    headers, rows = read_tabular_file(path)
    if not headers:
        return [], 0, "sin encabezados"
    direct_rows: list[dict[str, str]] = []
    daily_groups: dict[tuple[str, ...], list[tuple[float, dict[str, str], object]]] = defaultdict(list)
    for row in rows:
        parsed_date = parse_period(row, headers)
        price_column = find_column(headers, "precio")
        price = parse_number(row.get(price_column, "")) if price_column else None
        frequency = choose_frequency(row, headers, args)
        if frequency == "diaria" and parsed_date and price is not None:
            commodity, commodity_note = normalize_commodity(row_value(row, headers, "commodity"))
            key = (
                parsed_date.strftime("%Y-%m"), commodity,
                source_value(row, headers, "fuente", args.source_name),
                source_value(row, headers, "mercado", args.market),
                source_value(row, headers, "tipo_precio", args.tipo_precio),
                source_value(row, headers, "moneda", args.currency),
                source_value(row, headers, "unidad", args.unit),
            )
            daily_groups[key].append((price, row, parsed_date))
            continue
        notes = ""
        if frequency == "diaria":
            notes = "registro diario no agregado por fecha o precio inválido"
        if price is None and price_column:
            notes = "; ".join(item for item in (notes, "precio no numérico o faltante") if item)
        direct_rows.append(output_row(row, headers, path, args, parsed_date, price, notes))

    for key, values in daily_groups.items():
        period, commodity, source, market, price_type, currency, unit = key
        prices = [item[0] for item in values]
        first_row = values[0][1]
        first_date = values[0][2].replace(day=1)
        aggregate = median(prices) if args.aggregate_method == "median" else mean(prices)
        canonical, commodity_note = normalize_commodity(commodity)
        notes = [f"agregado desde datos diarios: {args.aggregate_method}", f"registros diarios={len(prices)}"]
        if commodity_note:
            notes.append(commodity_note)
        direct_rows.append({
            "fecha": first_date.isoformat(), "año": str(first_date.year), "mes": str(first_date.month), "periodo_ym": period,
            "commodity": canonical, "fuente": source, "mercado": market, "tipo_precio": price_type,
            "moneda": currency, "unidad": unit, "precio": format_number(aggregate), "frecuencia": "mensual",
            "archivo_origen": path.name, "fecha_integracion": date.today().isoformat(), "observaciones": "; ".join(notes),
        })
    return direct_rows, len(rows), ""


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
    raw_dir = Path(args.raw_dir)
    output = Path(args.output)
    raw_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in raw_dir.iterdir() if path.is_file() and path.suffix.lower() in RAW_EXTENSIONS)
    all_rows: list[dict[str, str]] = []
    total_read = 0
    skipped: list[str] = []
    for path in files:
        try:
            rows, read_count, note = integrate_file(path, args)
        except Exception as exc:
            skipped.append(f"{path.name}: {exc.__class__.__name__}: {exc}")
            continue
        all_rows.extend(rows)
        total_read += read_count
        if note:
            skipped.append(f"{path.name}: {note}")
    all_rows.sort(key=lambda row: (row.get("periodo_ym", ""), row.get("commodity", ""), row.get("fuente", ""), row.get("moneda", ""), row.get("tipo_precio", "")))
    all_rows, duplicates = deduplicate(all_rows)
    write_csv(output, INTEGRATED_FIELDS, all_rows)
    print(f"Archivos encontrados: {len(files)}")
    print(f"Filas leídas: {total_read}; filas integradas: {len(all_rows)}; duplicados exactos omitidos: {duplicates}")
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
