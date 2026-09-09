#!/usr/bin/env python3
"""Construye agregados mensuales livianos para el dashboard local."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from statistics import mean, median

from local_mensual_common import DEFAULT_DASHBOARD_DIR, DEFAULT_PROCESSED_DIR, format_number, parse_date, parse_number, text, write_csv


INPUT_PATH = DEFAULT_PROCESSED_DIR / "COMMODITIES_LOCAL_MENSUAL_INTEGRADO.csv"
MONTHLY_FIELDS = [
    "año", "mes", "periodo_ym", "commodity", "fuente", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia",
    "operaciones", "precio_promedio", "precio_mediana", "precio_min", "precio_max", "variacion_mensual_pct", "variacion_interanual_pct",
]
LATEST_FIELDS = [
    "commodity", "fuente", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia", "periodo_ultimo",
    "precio_mediana_ultimo_periodo", "precio_promedio_ultimo_periodo", "operaciones_ultimo_periodo", "variacion_mensual_pct", "variacion_interanual_pct", "estado",
]
SUMMARY_FIELDS = [
    "fecha_actualizacion", "fecha_min", "fecha_max", "filas_integradas", "filas_dashboard", "fuentes", "mercados", "commodities", "monedas", "unidades", "tipos_precio", "frecuencia", "modo", "nota_metodologica_corta",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepara dashboard-ready de commodities locales mensuales")
    parser.add_argument("--input", default=str(INPUT_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_DASHBOARD_DIR))
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def variation(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous <= 0:
        return None
    return (current / previous - 1) * 100


def state_for(value: float | None) -> str:
    if value is None:
        return "Sin dato"
    if abs(value) > 50:
        return "Revisar"
    if value < -5:
        return "Baja"
    if value <= 5:
        return "Estable"
    if value <= 20:
        return "Suba moderada"
    return "Suba fuerte"


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    rows = read_rows(input_path)
    groups: dict[tuple[str, ...], list[float]] = defaultdict(list)
    all_dates: list[date] = []
    dashboard_source_rows = 0
    for row in rows:
        parsed = parse_date(text(row.get("fecha")))
        price = parse_number(text(row.get("precio")))
        required = all(text(row.get(field)) for field in ("commodity", "fuente", "moneda", "unidad"))
        if not parsed or not required or price is None or price <= 0:
            continue
        period = parsed.strftime("%Y-%m")
        key = (
            period, text(row.get("commodity")), text(row.get("fuente")), text(row.get("mercado")), text(row.get("tipo_precio")) or "Sin especificar",
            text(row.get("moneda")), text(row.get("unidad")), "mensual",
        )
        groups[key].append(price)
        all_dates.append(parsed)
        dashboard_source_rows += 1

    monthly_rows: list[dict[str, str]] = []
    series_rows: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for key, prices in sorted(groups.items()):
        period, commodity, source, market, price_type, currency, unit, frequency = key
        year, month = period.split("-")
        row = {
            "año": year, "mes": month, "periodo_ym": period, "commodity": commodity, "fuente": source, "mercado": market,
            "tipo_precio": price_type, "moneda": currency, "unidad": unit, "frecuencia": frequency,
            "operaciones": str(len(prices)), "precio_promedio": format_number(mean(prices)), "precio_mediana": format_number(median(prices)),
            "precio_min": format_number(min(prices)), "precio_max": format_number(max(prices)), "variacion_mensual_pct": "", "variacion_interanual_pct": "",
        }
        monthly_rows.append(row)
        series_rows[(commodity, source, market, price_type, currency, unit, frequency)].append(row)

    for series in series_rows.values():
        series.sort(key=lambda row: row["periodo_ym"])
        by_period = {row["periodo_ym"]: row for row in series}
        for index, row in enumerate(series):
            current = parse_number(row["precio_mediana"])
            previous = parse_number(series[index - 1]["precio_mediana"]) if index else None
            previous_year = by_period.get(f"{int(row['año']) - 1:04d}-{int(row['mes']):02d}")
            row["variacion_mensual_pct"] = format_number(variation(current, previous))
            row["variacion_interanual_pct"] = format_number(variation(current, parse_number(previous_year["precio_mediana"]) if previous_year else None))
    monthly_rows.sort(key=lambda row: (row["periodo_ym"], row["commodity"], row["fuente"], row["moneda"], row["tipo_precio"]))

    latest_rows: list[dict[str, str]] = []
    for series in series_rows.values():
        latest = series[-1]
        latest_rows.append({
            "commodity": latest["commodity"], "fuente": latest["fuente"], "mercado": latest["mercado"], "tipo_precio": latest["tipo_precio"],
            "moneda": latest["moneda"], "unidad": latest["unidad"], "frecuencia": latest["frecuencia"], "periodo_ultimo": latest["periodo_ym"],
            "precio_mediana_ultimo_periodo": latest["precio_mediana"], "precio_promedio_ultimo_periodo": latest["precio_promedio"], "operaciones_ultimo_periodo": latest["operaciones"],
            "variacion_mensual_pct": latest["variacion_mensual_pct"], "variacion_interanual_pct": latest["variacion_interanual_pct"], "estado": state_for(parse_number(latest["variacion_mensual_pct"])),
        })
    latest_rows.sort(key=lambda row: (row["commodity"], row["fuente"], row["moneda"], row["tipo_precio"]))

    semaforo_rows = [{**row, "estado": state_for(parse_number(row["variacion_mensual_pct"]))} for row in monthly_rows]
    values = lambda field: sorted({text(row.get(field)) for row in monthly_rows if text(row.get(field))})
    summary = {
        "fecha_actualizacion": date.today().isoformat(), "fecha_min": min(all_dates).isoformat() if all_dates else "", "fecha_max": max(all_dates).isoformat() if all_dates else "",
        "filas_integradas": str(len(rows)), "filas_dashboard": str(dashboard_source_rows), "fuentes": "|".join(values("fuente")), "mercados": "|".join(values("mercado")),
        "commodities": "|".join(values("commodity")), "monedas": "|".join(values("moneda")), "unidades": "|".join(values("unidad")), "tipos_precio": "|".join(values("tipo_precio")),
        "frecuencia": "mensual", "modo": "base_local_mensual" if monthly_rows else "sin_datos",
        "nota_metodologica_corta": "Agregados mensuales locales; sólo precios positivos con fuente, moneda y unidad informadas. No mezclar con SIO, BCR ni World Bank.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "COMMODITIES_LOCAL_MENSUAL_DASHBOARD_MENSUAL.csv", MONTHLY_FIELDS, monthly_rows)
    write_csv(output_dir / "COMMODITIES_LOCAL_MENSUAL_DASHBOARD_ULTIMOS.csv", LATEST_FIELDS, latest_rows)
    write_csv(output_dir / "COMMODITIES_LOCAL_MENSUAL_DASHBOARD_SEMAFORO.csv", [*MONTHLY_FIELDS, "estado"], semaforo_rows)
    write_csv(output_dir / "COMMODITIES_LOCAL_MENSUAL_DASHBOARD_RESUMEN.csv", SUMMARY_FIELDS, [summary])
    print(f"Filas integradas: {len(rows)}; filas dashboard-ready: {dashboard_source_rows}")
    print(f"Salida dashboard: {output_dir.resolve()}")
    if not rows:
        print("No hay datos locales mensuales; se generaron encabezados y resumen sin datos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
