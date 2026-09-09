#!/usr/bin/env python3
"""Audita cobertura, validez, continuidad y comparabilidad del integrado local."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

from local_mensual_common import DEFAULT_PROCESSED_DIR, DEFAULT_REPORT_DIR, INTEGRATED_FIELDS, format_number, parse_date, parse_number, text, write_csv


REPORT_NAME = "REPORTE_AUDITORIA_LOCAL_MENSUAL.md"
SUMMARY_NAME = "RESUMEN_LOCAL_MENSUAL.csv"
SERIES_NAME = "RESUMEN_LOCAL_MENSUAL_SERIES.csv"
LEGACY_REPORT_NAME = "REPORTE_AUDITORIA_COMMODITIES_LOCAL_MENSUAL.md"
LEGACY_COVERAGE_NAME = "RESUMEN_COBERTURA_COMMODITIES_LOCAL_MENSUAL.csv"
SUMMARY_FIELDS = ["metrica", "valor", "detalle"]
SERIES_FIELDS = [
    "commodity", "fuente", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia", "filas",
    "fecha_min", "fecha_max", "meses_observados", "meses_esperados", "meses_faltantes", "precios_validos",
    "precios_faltantes", "precios_cero", "precios_negativos", "aptitud_dashboard",
]
LEGACY_COVERAGE_FIELDS = [
    "fuente", "commodity", "periodo_ym", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia",
    "registros", "precio_min", "precio_max",
]


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


def unique_values(rows: list[dict[str, str]], field: str) -> list[str]:
    return sorted({text(row.get(field)) for row in rows if text(row.get(field))})


def render_list(items: list[str]) -> str:
    return ", ".join(f"`{item}`" for item in items) if items else "sin datos"


def month_index(parsed: date) -> int:
    return parsed.year * 12 + parsed.month


def series_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(text(row.get(field)) for field in ("commodity", "fuente", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia"))


def series_aptitude(item: dict[str, object]) -> str:
    if not item["filas"]:
        return "sin datos"
    if any(not item[field] for field in ("commodity", "fuente", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia")):
        return "requiere revisión"
    if item["precios_validos"] == 0:
        return "no apta"
    if item["precios_faltantes"] or item["precios_cero"] or item["precios_negativos"]:
        return "requiere revisión"
    if item["meses_faltantes"]:
        return "apta con brechas"
    return "apta para dashboard histórico"


def build_series_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[series_key(row)].append(row)
    output: list[dict[str, str]] = []
    for key, group in sorted(grouped.items()):
        dates = [parsed for row in group if (parsed := parse_date(text(row.get("fecha"))))]
        periods = {month_index(parsed) for parsed in dates}
        expected = set(range(min(periods), max(periods) + 1)) if periods else set()
        prices = [parse_number(text(row.get("precio"))) for row in group]
        valid = [price for price in prices if price is not None]
        missing = sum(price is None for price in prices)
        zero = sum(price == 0 for price in valid)
        negative = sum(price < 0 for price in valid)
        item: dict[str, object] = {
            "commodity": key[0], "fuente": key[1], "mercado": key[2], "tipo_precio": key[3], "moneda": key[4], "unidad": key[5], "frecuencia": key[6],
            "filas": len(group), "fecha_min": min(dates).isoformat() if dates else "", "fecha_max": max(dates).isoformat() if dates else "",
            "meses_observados": len(periods), "meses_esperados": len(expected), "meses_faltantes": len(expected - periods), "precios_validos": len(valid),
            "precios_faltantes": missing, "precios_cero": zero, "precios_negativos": negative,
        }
        output.append({field: str(item.get(field, "")) for field in SERIES_FIELDS[:-1]} | {"aptitud_dashboard": series_aptitude(item)})
    return output


def build_monthly_coverage(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, ...], list[float]] = defaultdict(list)
    for row in rows:
        price = parse_number(text(row.get("precio")))
        key = tuple(text(row.get(field)) for field in ("fuente", "commodity", "periodo_ym", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia"))
        if key[1] and key[2] and price is not None and price > 0:
            grouped[key].append(price)
    output: list[dict[str, str]] = []
    for key, prices in sorted(grouped.items()):
        output.append({
            "fuente": key[0], "commodity": key[1], "periodo_ym": key[2], "mercado": key[3], "tipo_precio": key[4],
            "moneda": key[5], "unidad": key[6], "frecuencia": key[7], "registros": str(len(prices)),
            "precio_min": format_number(min(prices)), "precio_max": format_number(max(prices)),
        })
    return output


def audit(rows: list[dict[str, str]], input_path: Path) -> tuple[str, list[dict[str, str]], list[dict[str, str]]]:
    parsed_dates = [parsed for row in rows if (parsed := parse_date(text(row.get("fecha"))))]
    prices = [parse_number(text(row.get("precio"))) for row in rows]
    valid_prices = [price for price in prices if price is not None]
    missing_prices = sum(price is None for price in prices)
    zero_prices = sum(price == 0 for price in valid_prices)
    negative_prices = sum(price < 0 for price in valid_prices)
    invalid_dates = len(rows) - len(parsed_dates)
    future_dates = sum(parsed > date.today() for parsed in parsed_dates)
    required_missing = {
        field: sum(not text(row.get(field)) for row in rows)
        for field in ("commodity", "fuente", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia")
    }
    duplicate_fields = [field for field in INTEGRATED_FIELDS if field not in {"fecha_integracion", "observaciones"}]
    seen: set[tuple[str, ...]] = set()
    duplicates = 0
    for row in rows:
        key = tuple(text(row.get(field)) for field in duplicate_fields)
        if key in seen:
            duplicates += 1
        seen.add(key)
    series_rows = build_series_rows(rows)
    coverage_rows = build_monthly_coverage(rows)
    eligible = sum(
        parse_date(text(row.get("fecha"))) is not None
        and all(text(row.get(field)) for field in ("commodity", "fuente", "moneda", "unidad"))
        and (parse_number(text(row.get("precio"))) or 0) > 0
        for row in rows
    )
    missing_months = sum(int(row["meses_faltantes"]) for row in series_rows)
    if not rows:
        status = "sin datos"
    elif not eligible:
        status = "no apta"
    elif invalid_dates or any(required_missing.values()) or zero_prices or negative_prices or duplicates:
        status = "requiere revisión"
    elif missing_months:
        status = "apta con brechas"
    else:
        status = "apta para dashboard histórico"
    report = f"""# Reporte de auditoría — histórico local mensual de commodities

Fecha de auditoría: {date.today().isoformat()}

## Dataset y grano

- Archivo auditado: `{input_path.as_posix()}`.
- Grano esperado: una observación por commodity, fuente, plaza/mercado, tipo de precio, moneda, unidad y mes.
- Filas integradas: **{len(rows)}**.
- Precios numéricos: **{len(valid_prices)}**; filas elegibles para dashboard: **{eligible}**.
- Estado general: **{status}**.

## Cobertura

- Fecha mínima: **{min(parsed_dates).isoformat() if parsed_dates else 'sin fecha'}**.
- Fecha máxima: **{max(parsed_dates).isoformat() if parsed_dates else 'sin fecha'}**.
- Años: {render_list(unique_values(rows, 'año'))}.
- Meses/períodos: **{len({text(row.get('periodo_ym')) for row in rows if text(row.get('periodo_ym'))})}**.
- Commodities: {render_list(unique_values(rows, 'commodity'))}.
- Fuentes: {render_list(unique_values(rows, 'fuente'))}.
- Mercados/plazas: {render_list(unique_values(rows, 'mercado'))}.
- Monedas: {render_list(unique_values(rows, 'moneda'))}.
- Unidades: {render_list(unique_values(rows, 'unidad'))}.
- Tipos de precio: {render_list(unique_values(rows, 'tipo_precio'))}.

## Controles de calidad

- Fechas faltantes o inválidas: **{invalid_dates}**; fechas futuras: **{future_dates}**.
- Precios faltantes/no numéricos: **{missing_prices}**; precios cero: **{zero_prices}**; precios negativos: **{negative_prices}**.
- Duplicados exactos según dimensiones del integrado: **{duplicates}**.
- Meses faltantes dentro del rango de cada serie: **{missing_months}**.
- Campos requeridos faltantes: {', '.join(f'`{field}`={count}' for field, count in required_missing.items())}.

Los precios cero, negativos, sin fecha o sin dimensiones metodológicas no alimentan el dashboard-ready. Las plazas se mantienen separadas dentro de `mercado`; no se combinan silenciosamente con SIO, FOB, FAS ni World Bank.

## Aptitud para dashboard histórico

La aptitud se calcula por serie en `RESUMEN_LOCAL_MENSUAL_SERIES.csv`. Una serie sin precio positivo no es apta; una serie con huecos se marca **apta con brechas** y requiere una lectura explícita de cobertura antes de usar variaciones o comparaciones interanuales.

## Archivos generados

- `RESUMEN_LOCAL_MENSUAL.csv`: indicadores generales de filas, cobertura, validez, dimensiones y continuidad.
- `RESUMEN_LOCAL_MENSUAL_SERIES.csv`: auditoría por serie metodológicamente homogénea.
- `RESUMEN_COBERTURA_COMMODITIES_LOCAL_MENSUAL.csv`: compatibilidad con el reporte anterior, por período y plaza.

## Recomendación

"""
    if not rows:
        report += "No hay datos integrados. Ejecute el descargador con `--allow-web` sobre URLs configuradas, o coloque una descarga autorizada en `raw/`; luego integre y vuelva a auditar.\n"
    elif status in {"no apta", "requiere revisión"}:
        report += "No publicar todavía. Revisar la procedencia, unidad/moneda explícitas, celdas faltantes, duplicados y continuidad por commodity/plaza.\n"
    elif status == "apta con brechas":
        report += "La fuente es utilizable para una prueba histórica con brechas visibles; no interpolar meses faltantes ni presentar continuidad donde no exista.\n"
    else:
        report += "La fuente es apta para una prueba controlada de dashboard histórico, manteniendo cada dimensión y su nota metodológica.\n"
    return report, series_rows, coverage_rows


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(input_path)
    report, series_rows, coverage_rows = audit(rows, input_path)
    summary_rows = [
        {"metrica": "filas", "valor": str(len(rows)), "detalle": "filas leídas del integrado"},
        {"metrica": "commodities", "valor": str(len(unique_values(rows, "commodity"))), "detalle": "commodities con valor informado"},
        {"metrica": "fecha_min", "valor": min((text(row.get("fecha")) for row in rows if parse_date(text(row.get("fecha")))), default=""), "detalle": "fecha mínima válida"},
        {"metrica": "fecha_max", "valor": max((text(row.get("fecha")) for row in rows if parse_date(text(row.get("fecha")))), default=""), "detalle": "fecha máxima válida"},
        {"metrica": "años", "valor": "|".join(unique_values(rows, "año")), "detalle": "años presentes"},
        {"metrica": "meses", "valor": str(len({text(row.get("periodo_ym")) for row in rows if text(row.get("periodo_ym"))})), "detalle": "períodos mensuales distintos"},
        {"metrica": "precios_validos", "valor": str(sum(parse_number(text(row.get("precio"))) is not None for row in rows)), "detalle": "valores numéricos, incluidos cero/negativos"},
        {"metrica": "precios_faltantes", "valor": str(sum(parse_number(text(row.get("precio"))) is None for row in rows)), "detalle": "filas integradas sin precio; celdas S/C o vacías del HTML se excluyen antes"},
        {"metrica": "precios_cero", "valor": str(sum(parse_number(text(row.get("precio"))) == 0 for row in rows)), "detalle": "no alimentan dashboard-ready"},
        {"metrica": "precios_negativos", "valor": str(sum((parse_number(text(row.get("precio"))) or 0) < 0 for row in rows)), "detalle": "no alimentan dashboard-ready"},
        {"metrica": "fuentes", "valor": "|".join(unique_values(rows, "fuente")), "detalle": "fuentes sin mezclar"},
        {"metrica": "monedas", "valor": "|".join(unique_values(rows, "moneda")), "detalle": "monedas conservadas por separado"},
        {"metrica": "unidades", "valor": "|".join(unique_values(rows, "unidad")), "detalle": "unidades conservadas por separado"},
        {"metrica": "continuidad_mensual", "valor": str(sum(int(row["meses_faltantes"]) for row in series_rows)), "detalle": "meses faltantes dentro del rango por serie"},
        {"metrica": "aptitud_dashboard", "valor": "|".join(sorted({row["aptitud_dashboard"] for row in series_rows})), "detalle": "resultado por serie"},
    ]
    write_csv(report_dir / SUMMARY_NAME, SUMMARY_FIELDS, summary_rows)
    write_csv(report_dir / SERIES_NAME, SERIES_FIELDS, series_rows)
    write_csv(report_dir / LEGACY_COVERAGE_NAME, LEGACY_COVERAGE_FIELDS, coverage_rows)
    (report_dir / REPORT_NAME).write_text(report, encoding="utf-8")
    (report_dir / LEGACY_REPORT_NAME).write_text(report, encoding="utf-8")
    print(f"Auditoría local mensual finalizada: {len(rows)} fila(s); estado: {next(row['valor'] for row in summary_rows if row['metrica'] == 'aptitud_dashboard') or ('sin datos' if not rows else 'ver reporte')}")
    print(f"Reporte: {(report_dir / REPORT_NAME).resolve()}")
    print(f"Resumen: {(report_dir / SUMMARY_NAME).resolve()}")
    print(f"Series: {(report_dir / SERIES_NAME).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
