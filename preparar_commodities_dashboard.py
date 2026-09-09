#!/usr/bin/env python3
"""Prepara agregados livianos de SIO Granos para el dashboard visual."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median


csv.field_size_limit(2**31 - 1)

ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "commodities_sio" / "processed"
DASHBOARD_DIR = ROOT / "data" / "commodities_sio" / "dashboard"
REPORT_DIR = ROOT / "data" / "commodities_sio" / "reports"
ANALYTIC_PATH = PROCESSED_DIR / "COMMODITIES_SIO_ANALITICO_PRECIOS.csv"
ANALYTIC_SAMPLE_PATH = PROCESSED_DIR / "COMMODITIES_SIO_ANALITICO_PRECIOS_SAMPLE.csv"
SNAPSHOT_HISTORY_PATH = PROCESSED_DIR / "COMMODITIES_SIO_HISTORICO_SNAPSHOTS.csv"
LATEST_SNAPSHOT_PATH = PROCESSED_DIR / "COMMODITIES_SIO_LATEST_SNAPSHOT.csv"
LIGHT_SNAPSHOT_HISTORY_PATH = DASHBOARD_DIR / "COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv"
REPORT_PATH = REPORT_DIR / "REPORTE_DASHBOARD_COMMODITIES_SIO.md"
SOURCE_NAME = "SIO Granos / Secretaría de Agricultura"

OUTPUTS = {
    "diario": DASHBOARD_DIR / "COMMODITIES_SIO_DASHBOARD_DIARIO.csv",
    "mensual": DASHBOARD_DIR / "COMMODITIES_SIO_DASHBOARD_MENSUAL.csv",
    "ultimos": DASHBOARD_DIR / "COMMODITIES_SIO_DASHBOARD_ULTIMOS.csv",
    "resumen": DASHBOARD_DIR / "COMMODITIES_SIO_DASHBOARD_RESUMEN.csv",
    "semaforo": DASHBOARD_DIR / "COMMODITIES_SIO_DASHBOARD_SEMAFORO.csv",
}


def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def parse_date(raw_value: str) -> date | None:
    raw = (raw_value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_number(raw_value: str) -> float | None:
    source = (raw_value or "").strip()
    scientific = re.fullmatch(r"[-+]?\d+(?:\.\d+)?[eE][-+]?\d+", source)
    if scientific:
        try:
            return float(scientific.group(0))
        except ValueError:
            return None
    raw = source.replace("$", "").replace("ARS", "").replace("USD", "")
    raw = re.sub(r"[^0-9,.-]", "", raw)
    if not raw or raw in {"-", ".", ","}:
        return None
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", "") if raw.count(",") > 1 else raw.replace(",", ".")
    # En los datos SIO el punto funciona como separador decimal. No asumir
    # separador de miles: esa ambigüedad ya queda resuelta por la fuente y,
    # si coexiste coma y punto, por la rama anterior.
    try:
        return float(raw)
    except ValueError:
        return None


def is_yes(raw_value: str) -> bool:
    return (raw_value or "").strip().lower() in {"sí", "si", "true", "1"}


def valid_analytic_row(row: dict[str, str]) -> tuple[bool, float | None, date | None]:
    price = parse_number(value(row, "precio"))
    parsed_date = parse_date(value(row, "fecha"))
    currency = value(row, "moneda")
    unit = value(row, "unidad")
    currency_is_explicit = is_yes(value(row, "moneda_explicitamente_informada")) or (
        "moneda_explicitamente_informada" not in row and currency not in {"", "Sin especificar"}
    )
    eligible = all([
        is_yes(value(row, "precio_valido_para_serie")),
        price is not None and price > 0,
        not is_yes(value(row, "precio_cero_flag")),
        parsed_date is not None,
        bool(value(row, "commodity")) and value(row, "commodity") != "Sin especificar",
        currency_is_explicit,
        bool(currency) and currency != "Sin especificar",
        bool(unit) and unit != "Sin especificar",
        bool(value(row, "fuente")),
    ])
    return eligible, price, parsed_date


def new_group() -> dict[str, object]:
    return {"operations": 0, "prices": [], "volume_total": 0.0, "weighted_sum": 0.0, "volume_valid": False, "procedencias": set(), "lugares": set(), "dates": set()}


def add_group(store: dict[tuple[str, ...], dict[str, object]], key: tuple[str, ...], row: dict[str, str], price: float, parsed_date: date) -> None:
    item = store.setdefault(key, new_group())
    item["operations"] += 1
    item["prices"].append(price)
    item["dates"].add(parsed_date)
    volume = parse_number(value(row, "volumen"))
    if volume is not None and volume >= 0:
        item["volume_valid"] = True
        item["volume_total"] += volume
        item["weighted_sum"] += price * volume
    procedencia = value(row, "procedencia")
    lugar = value(row, "lugar_entrega")
    if procedencia and procedencia != "Sin especificar":
        item["procedencias"].add(procedencia)
    if lugar and lugar != "Sin especificar":
        item["lugares"].add(lugar)


def format_number(number: float | int | None) -> str:
    if number is None:
        return ""
    return f"{float(number):.6f}".rstrip("0").rstrip(".") or "0"


def stats(item: dict[str, object]) -> dict[str, str]:
    prices = item["prices"]
    volume_total = float(item["volume_total"])
    return {
        "operaciones": str(item["operations"]),
        "precio_promedio": format_number(sum(prices) / len(prices) if prices else None),
        "precio_mediana": format_number(float(median(prices)) if prices else None),
        "precio_min": format_number(min(prices) if prices else None),
        "precio_max": format_number(max(prices) if prices else None),
        "volumen_total": format_number(volume_total if item["volume_valid"] else None),
        "precio_ponderado_volumen": format_number(float(item["weighted_sum"]) / volume_total if item["volume_valid"] and volume_total > 0 else None),
    }


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def latest_snapshot_capture() -> str:
    if not LATEST_SNAPSHOT_PATH.exists():
        return ""
    try:
        with LATEST_SNAPSHOT_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            captures = [value(row, "fecha_descarga_snapshot") for row in csv.DictReader(handle, delimiter=";")]
    except OSError:
        return ""
    return max((item for item in captures if item), default="")


def state_for_variation(variation: float | None) -> str:
    if variation is None:
        return "Sin dato"
    if abs(variation) > 50:
        return "Revisar"
    if variation < -5:
        return "Baja"
    if variation <= 5:
        return "Estable"
    if variation <= 20:
        return "Suba moderada"
    return "Suba fuerte"


def variation(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous <= 0:
        return None
    result = (current / previous - 1) * 100
    return result if result == result and abs(result) != float("inf") else None


def build_dashboard(source_path: Path) -> dict[str, object]:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    daily: dict[tuple[str, ...], dict[str, object]] = {}
    daily_base: dict[tuple[str, ...], dict[str, object]] = {}
    monthly: dict[tuple[str, ...], dict[str, object]] = {}
    total_rows = 0
    valid_rows = 0
    currencies: set[str] = set()
    units: set[str] = set()
    commodities: set[str] = set()
    dates: list[date] = []
    capture_timestamps: list[str] = []
    dashboard_update_dates: list[str] = []

    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            total_rows += 1
            capture = value(row, "fecha_descarga_snapshot")
            if capture:
                capture_timestamps.append(capture)
            dashboard_update = value(row, "fecha_actualizacion_dashboard")
            if dashboard_update:
                dashboard_update_dates.append(dashboard_update)
            eligible, price, parsed_date = valid_analytic_row(row)
            if not eligible or price is None or parsed_date is None:
                continue
            valid_rows += 1
            commodity = value(row, "commodity")
            currency = value(row, "moneda")
            unit = value(row, "unidad")
            price_type = value(row, "tipo_precio") or "Sin especificar"
            condition = value(row, "condicion_comercial") or "Sin especificar"
            source = value(row, "fuente") or SOURCE_NAME
            date_key = parsed_date.isoformat()
            base = (commodity, currency, unit, price_type)
            daily_key = (date_key, str(parsed_date.year), str(parsed_date.month), commodity, currency, unit, price_type, condition, source)
            monthly_key = (str(parsed_date.year), str(parsed_date.month), date_key[:7], commodity, currency, unit, price_type, source)
            daily_base_key = base + (date_key,)
            add_group(daily, daily_key, row, price, parsed_date)
            add_group(daily_base, daily_base_key, row, price, parsed_date)
            add_group(monthly, monthly_key, row, price, parsed_date)
            currencies.add(currency)
            units.add(unit)
            commodities.add(commodity)
            dates.append(parsed_date)

    daily_fields = ["fecha", "año", "mes", "commodity", "moneda", "unidad", "tipo_precio", "condicion_comercial", "fuente", "operaciones", "precio_promedio", "precio_mediana", "precio_min", "precio_max", "volumen_total", "precio_ponderado_volumen", "procedencias", "lugares_entrega"]
    daily_rows: list[dict[str, str]] = []
    for key, item in sorted(daily.items()):
        day, year, month, commodity, currency, unit, price_type, condition, source = key
        row = {"fecha": day, "año": year, "mes": month, "commodity": commodity, "moneda": currency, "unidad": unit, "tipo_precio": price_type, "condicion_comercial": condition, "fuente": source}
        row.update(stats(item))
        row["procedencias"] = "|".join(sorted(item["procedencias"]))
        row["lugares_entrega"] = "|".join(sorted(item["lugares"]))
        daily_rows.append(row)
    write_csv(OUTPUTS["diario"], daily_fields, daily_rows)

    monthly_fields = ["año", "mes", "periodo_ym", "commodity", "moneda", "unidad", "tipo_precio", "fuente", "operaciones", "precio_promedio", "precio_mediana", "precio_min", "precio_max", "volumen_total", "precio_ponderado_volumen", "dias_con_datos", "variacion_mensual_pct", "variacion_interanual_pct"]
    monthly_rows: list[dict[str, str]] = []
    monthly_by_series: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for key, item in sorted(monthly.items()):
        year, month, period, commodity, currency, unit, price_type, source = key
        row = {"año": year, "mes": month, "periodo_ym": period, "commodity": commodity, "moneda": currency, "unidad": unit, "tipo_precio": price_type, "fuente": source}
        row.update(stats(item))
        row["dias_con_datos"] = str(len(item["dates"]))
        monthly_rows.append(row)
        monthly_by_series[(commodity, currency, unit, price_type)].append(row)
    for series_rows in monthly_by_series.values():
        series_rows.sort(key=lambda row: row["periodo_ym"])
        by_period = {row["periodo_ym"]: row for row in series_rows}
        for index, row in enumerate(series_rows):
            current = parse_number(row["precio_mediana"])
            previous = parse_number(series_rows[index - 1]["precio_mediana"]) if index else None
            row["variacion_mensual_pct"] = format_number(variation(current, previous))
            year = int(row["año"])
            month = int(row["mes"])
            yoy_row = by_period.get(f"{year - 1:04d}-{month:02d}")
            row["variacion_interanual_pct"] = format_number(variation(current, parse_number(yoy_row["precio_mediana"]) if yoy_row else None))
    monthly_rows.sort(key=lambda row: (row["periodo_ym"], row["commodity"], row["moneda"], row["unidad"], row["tipo_precio"]))
    write_csv(OUTPUTS["mensual"], monthly_fields, monthly_rows)

    latest_fields = ["commodity", "moneda", "unidad", "tipo_precio", "fecha_ultima", "precio_mediana_ultimo_dia", "precio_promedio_ultimo_dia", "operaciones_ultimo_dia", "volumen_ultimo_dia", "variacion_7d_pct", "variacion_30d_pct", "estado"]
    latest_rows: list[dict[str, str]] = []
    latest_by_series: dict[tuple[str, ...], list[tuple[date, dict[str, object]]]] = defaultdict(list)
    for key, item in daily_base.items():
        commodity, currency, unit, price_type, date_key = key
        latest_by_series[(commodity, currency, unit, price_type)].append((date.fromisoformat(date_key), item))
    for series_key, values in sorted(latest_by_series.items()):
        values.sort(key=lambda pair: pair[0])
        latest_date, latest_item = values[-1]
        daily_values = {item_date: parse_number(stats(item)["precio_mediana"]) for item_date, item in values}

        def reference(days_back: int) -> float | None:
            target = latest_date - timedelta(days=days_back)
            candidates = [item_date for item_date in daily_values if item_date <= target]
            return daily_values[max(candidates)] if candidates else None

        latest_stats = stats(latest_item)
        var_7 = variation(parse_number(latest_stats["precio_mediana"]), reference(7))
        var_30 = variation(parse_number(latest_stats["precio_mediana"]), reference(30))
        latest_rows.append({
            "commodity": series_key[0], "moneda": series_key[1], "unidad": series_key[2], "tipo_precio": series_key[3], "fecha_ultima": latest_date.isoformat(),
            "precio_mediana_ultimo_dia": latest_stats["precio_mediana"], "precio_promedio_ultimo_dia": latest_stats["precio_promedio"], "operaciones_ultimo_dia": latest_stats["operaciones"], "volumen_ultimo_dia": latest_stats["volumen_total"],
            "variacion_7d_pct": format_number(var_7), "variacion_30d_pct": format_number(var_30), "estado": state_for_variation(var_30 if var_30 is not None else var_7),
        })
    write_csv(OUTPUTS["ultimos"], latest_fields, latest_rows)

    semaphore_fields = ["commodity", "moneda", "unidad", "tipo_precio", "año", "mes", "periodo_ym", "precio_mediana", "variacion_mensual_pct", "estado"]
    semaphore_rows = [{field: row.get(field, "") for field in semaphore_fields} for row in monthly_rows]
    for row in semaphore_rows:
        row["estado"] = state_for_variation(parse_number(row["variacion_mensual_pct"]))
    write_csv(OUTPUTS["semaforo"], semaphore_fields, semaphore_rows)

    latest_capture = max(capture_timestamps) if capture_timestamps else ""
    latest_capture = max(filter(None, [latest_capture, latest_snapshot_capture()]), default="")
    dashboard_update = max(dashboard_update_dates) if dashboard_update_dates else date.today().isoformat()
    snapshot_history = source_path in {SNAPSHOT_HISTORY_PATH, LIGHT_SNAPSHOT_HISTORY_PATH}
    summary_fields = ["fecha_actualizacion", "fecha_actualizacion_dashboard", "fecha_ultima_captura_sio", "fecha_ultima_operacion_sio", "fecha_min_operacion_sio", "fecha_max_operacion_sio", "fecha_min", "fecha_max", "filas_analiticas", "commodities", "monedas", "unidades", "operaciones", "fuente", "modo", "nota_metodologica_corta"]
    summary_row = {
        "fecha_actualizacion": date.today().isoformat(), "fecha_actualizacion_dashboard": dashboard_update, "fecha_ultima_captura_sio": latest_capture, "fecha_ultima_operacion_sio": max(dates).isoformat() if dates else "", "fecha_min_operacion_sio": min(dates).isoformat() if dates else "", "fecha_max_operacion_sio": max(dates).isoformat() if dates else "", "fecha_min": min(dates).isoformat() if dates else "", "fecha_max": max(dates).isoformat() if dates else "", "filas_analiticas": str(valid_rows),
        "commodities": "|".join(sorted(commodities)), "monedas": "|".join(sorted(currencies)), "unidades": "|".join(sorted(units)), "operaciones": str(valid_rows), "fuente": SOURCE_NAME,
        "modo": "histórico_snapshots" if snapshot_history else "muestra" if source_path == ANALYTIC_SAMPLE_PATH else "base_analitica_completa",
        "nota_metodologica_corta": "Sólo precios positivos, moneda/unidad explícitas y precio_valido_para_serie=sí; ARS y USD se mantienen separados. Fuente SIO Granos; no equivale a BCR. Actualización por snapshots de últimas operaciones SIO. No equivale a histórico completo." if snapshot_history else "Sólo precios positivos, moneda/unidad explícitas y precio_valido_para_serie=sí; ARS y USD se mantienen separados. Fuente SIO Granos; no equivale a BCR.",
    }
    write_csv(OUTPUTS["resumen"], summary_fields, [summary_row])

    rows_by_output = {name: sum(1 for _ in path.open("r", encoding="utf-8-sig")) - 1 for name, path in OUTPUTS.items()}
    metrics = {
        "source_path": source_path, "source_is_sample": source_path == ANALYTIC_SAMPLE_PATH, "source_is_snapshot_history": snapshot_history, "latest_capture": latest_capture, "dashboard_update": dashboard_update, "latest_operation": max(dates).isoformat() if dates else "", "min_operation": min(dates).isoformat() if dates else "", "max_operation": max(dates).isoformat() if dates else "", "source_rows": total_rows, "valid_rows": valid_rows,
        "dates": dates, "commodities": sorted(commodities), "currencies": sorted(currencies), "units": sorted(units), "rows_by_output": rows_by_output,
    }
    write_dashboard_report(metrics)
    return metrics


def write_dashboard_report(metrics: dict[str, object]) -> None:
    source_path = Path(metrics["source_path"])
    source_note = "Se usó la muestra analítica; los resultados son sólo ilustrativos y no sustituyen la base completa." if metrics["source_is_sample"] else "Se usó el histórico acumulado de snapshots SIO; el dashboard sólo recibe agregados livianos." if metrics["source_is_snapshot_history"] else "Se usó la base analítica completa local; el dashboard sólo recibe agregados livianos."
    lines = [
        "# Reporte de dashboard de commodities SIO", "", "## Fuente y criterio", "",
        f"- Fuente de preparación: `{source_path.as_posix()}`.", f"- {source_note}", f"- Filas leídas: {metrics['source_rows']}; filas analíticas válidas utilizadas: {metrics['valid_rows']}.",
        f"- Rango temporal: {min(metrics['dates']).isoformat() if metrics['dates'] else 'sin fecha'} a {max(metrics['dates']).isoformat() if metrics['dates'] else 'sin fecha'}.", f"- Actualización del dashboard: {metrics['dashboard_update'] or 'no disponible'}.", f"- Última captura SIO: {metrics['latest_capture'] or 'no disponible'}.", f"- Última operación informada: {metrics['latest_operation'] or 'no disponible'}.", f"- Rango de operaciones: {metrics['min_operation'] or 'sin fecha'} — {metrics['max_operation'] or 'sin fecha'}.",
        f"- Commodities: {', '.join(metrics['commodities']) or 'ninguno'}.", f"- Monedas: {', '.join(metrics['currencies']) or 'ninguna'}; unidades: {', '.join(metrics['units']) or 'ninguna'}.",
        "- Regla: sólo `precio_valido_para_serie=sí`, precio positivo, fecha válida, commodity, fuente, moneda explícita y unidad explícita. Los precios cero quedan fuera.",
        "- Las series se separan por commodity, moneda, unidad y tipo_precio; ARS y USD no se agregan conjuntamente.", "",
        "## Archivos generados", "", "| Archivo | Filas | Tamaño (MB) | Uso |", "| --- | ---: | ---: | --- |",
    ]
    descriptions = {"diario": "evolución diaria y volumen", "mensual": "series mensuales y variaciones", "ultimos": "último dato por serie", "resumen": "indicadores de fuente y cobertura", "semaforo": "variaciones mensuales por serie"}
    for name, path in OUTPUTS.items():
        size_mb = path.stat().st_size / (1024 * 1024)
        lines.append(f"| `{path.as_posix()}` | {metrics['rows_by_output'][name]} | {size_mb:.3f} | {descriptions[name]} |")
    lines.extend([
        "", "## Filtros y visualizaciones", "", "- Filtros: commodity, moneda, unidad, tipo de precio y frecuencia diaria/mensual.",
        "- KPIs: última actualización, commodities, operaciones analíticas, moneda seleccionada y mediana del último dato.",
        "- Gráficos: evolución de mediana, ranking reciente, volumen por commodity y semáforo mensual.",
        "- La mediana es la métrica principal de visualización; el promedio y el ponderado por volumen quedan como contexto.", "",
        "## Limitaciones y aptitud", "", "- La fuente corresponde a operaciones informadas SIO y no equivale a precio de pizarra BCR, futuros ni precios mayoristas frutihortícolas.",
        "- Los agregados no corrigen la limitación de paginación de GetOperaciones ni garantizan actualización automática. Cuando la fuente es el histórico de snapshots, cada corrida incorpora sólo las últimas operaciones observadas y no equivale a histórico completo.",
        "- La aptitud es exploratoria y parcial para piloto; no productiva hasta validar actualización, frecuencia, procedencia, permisos e interpretación.",
        "- Los estados `Baja`, `Estable`, `Suba moderada`, `Suba fuerte`, `Revisar` y `Sin dato` describen variación de precios; no representan escasez ni desabastecimiento.",
        "- La base completa no se carga en el navegador ni se versiona cuando supera el tamaño razonable para Git.", "",
    ])
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if LIGHT_SNAPSHOT_HISTORY_PATH.exists():
        source_path = LIGHT_SNAPSHOT_HISTORY_PATH
    elif SNAPSHOT_HISTORY_PATH.exists():
        source_path = SNAPSHOT_HISTORY_PATH
    elif ANALYTIC_PATH.exists():
        source_path = ANALYTIC_PATH
    elif ANALYTIC_SAMPLE_PATH.exists():
        source_path = ANALYTIC_SAMPLE_PATH
        print("ADVERTENCIA: no existe la base analítica completa; se usa sólo la muestra como fallback.")
    else:
        print("No existe la base analítica SIO ni su muestra. Ejecute auditar_commodities_sio.py primero.")
        return 1
    metrics = build_dashboard(source_path)
    print(f"Fuente utilizada: {source_path}")
    print(f"Filas analíticas utilizadas: {metrics['valid_rows']}")
    for name, path in OUTPUTS.items():
        print(f"Dashboard {name}: {path} ({metrics['rows_by_output'][name]} filas, {path.stat().st_size} bytes)")
    print(f"Reporte: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
