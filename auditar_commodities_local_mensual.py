#!/usr/bin/env python3
"""Audita cobertura, validez y comparabilidad de la fuente local mensual."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

from local_mensual_common import (
    DEFAULT_PROCESSED_DIR,
    DEFAULT_REPORT_DIR,
    INTEGRATED_FIELDS,
    format_number,
    parse_date,
    parse_number,
    text,
    write_csv,
)


REPORT_PATH = DEFAULT_REPORT_DIR / "REPORTE_AUDITORIA_COMMODITIES_LOCAL_MENSUAL.md"
COVERAGE_PATH = DEFAULT_REPORT_DIR / "RESUMEN_COBERTURA_COMMODITIES_LOCAL_MENSUAL.csv"
COVERAGE_FIELDS = ["fuente", "commodity", "periodo_ym", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia", "registros", "precio_min", "precio_max"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audita el integrado local mensual")
    parser.add_argument("--input", default=str(DEFAULT_PROCESSED_DIR / "COMMODITIES_LOCAL_MENSUAL_INTEGRADO.csv"))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def values(rows: list[dict[str, str]], field: str) -> list[str]:
    return sorted({text(row.get(field)) for row in rows if text(row.get(field))})


def render_list(items: list[str]) -> str:
    return ", ".join(f"`{item}`" for item in items) if items else "sin datos"


def audit(rows: list[dict[str, str]], input_path: Path) -> tuple[str, list[dict[str, str]]]:
    dates = [parsed for row in rows if (parsed := parse_date(text(row.get("fecha"))))]
    invalid_dates = sum(parse_date(text(row.get("fecha"))) is None for row in rows)
    missing_commodity = sum(not text(row.get("commodity")) for row in rows)
    missing_source = sum(not text(row.get("fuente")) for row in rows)
    missing_currency = sum(not text(row.get("moneda")) for row in rows)
    missing_unit = sum(not text(row.get("unidad")) for row in rows)
    missing_type = sum(not text(row.get("tipo_precio")) for row in rows)
    prices = [parse_number(text(row.get("precio"))) for row in rows]
    invalid_prices = sum(price is None for price in prices)
    zero_prices = sum(price == 0 for price in prices if price is not None)
    negative_prices = sum(price < 0 for price in prices if price is not None)
    future_dates = sum(parsed > date.today() for parsed in dates)
    comparison_fields = [field for field in INTEGRATED_FIELDS if field not in {"fecha_integracion", "observaciones"}]
    duplicate_keys: set[tuple[str, ...]] = set()
    duplicate_exact = 0
    for row in rows:
        key = tuple(text(row.get(field)) for field in comparison_fields)
        if key in duplicate_keys:
            duplicate_exact += 1
        duplicate_keys.add(key)

    coverage: dict[tuple[str, ...], list[float]] = defaultdict(list)
    for row, price in zip(rows, prices):
        key = tuple(text(row.get(field)) for field in ("fuente", "commodity", "periodo_ym", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia"))
        if key[1] and key[2]:
            if price is not None and price > 0:
                coverage[key].append(price)
            else:
                coverage.setdefault(key, [])
    coverage_rows: list[dict[str, str]] = []
    for key, price_values in sorted(coverage.items()):
        source, commodity, period, market, price_type, currency, unit, frequency = key
        coverage_rows.append({
            "fuente": source, "commodity": commodity, "periodo_ym": period, "mercado": market,
            "tipo_precio": price_type, "moneda": currency, "unidad": unit, "frecuencia": frequency,
            "registros": str(len(price_values)), "precio_min": format_number(min(price_values) if price_values else None),
            "precio_max": format_number(max(price_values) if price_values else None),
        })

    mixes: dict[tuple[str, ...], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        key = (text(row.get("fuente")), text(row.get("commodity")), text(row.get("periodo_ym")))
        for field in ("moneda", "unidad", "frecuencia", "tipo_precio"):
            value = text(row.get(field))
            if value:
                mixes[key][field].add(value)
    mixed_groups = [key for key, dimensions in mixes.items() if any(len(values_set) > 1 for values_set in dimensions.values())]
    sources = values(rows, "fuente")
    commodities = values(rows, "commodity")
    currencies = values(rows, "moneda")
    units = values(rows, "unidad")
    frequencies = values(rows, "frecuencia")
    types = values(rows, "tipo_precio")
    min_date = min(dates).isoformat() if dates else "sin fecha"
    max_date = max(dates).isoformat() if dates else "sin fecha"
    dashboard_eligible = sum(
        parse_date(text(row.get("fecha"))) is not None
        and text(row.get("commodity"))
        and text(row.get("fuente"))
        and text(row.get("moneda"))
        and text(row.get("unidad"))
        and parse_number(text(row.get("precio"))) is not None
        and parse_number(text(row.get("precio"))) > 0
        for row in rows
    )
    status = "sin datos" if not rows else "requiere revisión" if any((invalid_dates, missing_commodity, missing_source, missing_currency, missing_unit, invalid_prices, zero_prices, negative_prices, mixed_groups)) else "apta para prueba controlada"
    report = f"""# Reporte de auditoría — commodities locales mensuales

Fecha de auditoría: {date.today().isoformat()}

## Dataset y grano

- Archivo auditado: `{input_path.as_posix()}`.
- Grano esperado: una observación mensual por commodity, fuente, mercado, tipo de precio, moneda y unidad; si se agregan datos diarios, la regla debe quedar en `observaciones`.
- Filas integradas: **{len(rows)}**.
- Filas elegibles para dashboard: **{dashboard_eligible}**.
- Estado general: **{status}**.

## Cobertura

- Fecha mínima: **{min_date}**.
- Fecha máxima: **{max_date}**.
- Años: {render_list(values(rows, 'año'))}.
- Períodos mensuales: {render_list(values(rows, 'periodo_ym'))}.
- Fuentes: {render_list(sources)}.
- Commodities: {render_list(commodities)}.
- Monedas: {render_list(currencies)}.
- Unidades: {render_list(units)}.
- Frecuencias: {render_list(frequencies)}.
- Tipos de precio: {render_list(types)}.

## Controles de calidad

- Fechas inválidas o faltantes: **{invalid_dates}**; fechas futuras: **{future_dates}**.
- Commodity faltante: **{missing_commodity}**; fuente faltante: **{missing_source}**.
- Moneda faltante: **{missing_currency}**; unidad faltante: **{missing_unit}**; tipo de precio faltante: **{missing_type}**.
- Precio faltante/no numérico: **{invalid_prices}**; precio cero: **{zero_prices}**; precio negativo: **{negative_prices}**.
- Duplicados exactos según clave normalizada: **{duplicate_exact}**.
- Grupos con más de una moneda, unidad, frecuencia o tipo de precio: **{len(mixed_groups)}**.

Los ceros, negativos y precios sin moneda o unidad explícita se conservan para trazabilidad en el integrado, pero no deben alimentar las salidas dashboard-ready. Las mezclas detectadas deben resolverse por filtro o por una dimensión explícita; no se agregan silenciosamente.

## Salidas

- `RESUMEN_COBERTURA_COMMODITIES_LOCAL_MENSUAL.csv`: cobertura por fuente, commodity, período y dimensiones metodológicas.
- Las salidas dashboard-ready deben ser compactas y mantenerse separadas de SIO, BCR y World Bank.

## Recomendación

"""
    if not rows:
        report += "No hay archivos integrados. Coloque una fuente local documentada en `raw/`, ejecute la integración y vuelva a auditar. No se inventan datos ni se habilita una serie visual vacía como si tuviera cobertura.\n"
    elif dashboard_eligible == 0:
        report += "No hay filas elegibles para dashboard. Corregir o documentar fuente, fecha, moneda, unidad y precio antes de publicar.\n"
    else:
        report += "La fuente puede pasar a una prueba controlada si se verifican procedencia, cobertura, licencia, continuidad mensual y ausencia de mezclas incompatibles.\n"
    return report, coverage_rows


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(input_path)
    report, coverage_rows = audit(rows, input_path)
    write_csv(report_dir / COVERAGE_PATH.name, COVERAGE_FIELDS, coverage_rows)
    (report_dir / REPORT_PATH.name).write_text(report, encoding="utf-8")
    print(f"Auditoría local mensual finalizada: {len(rows)} fila(s).")
    print(f"Reporte: {(report_dir / REPORT_PATH.name).resolve()}")
    print(f"Cobertura: {(report_dir / COVERAGE_PATH.name).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
