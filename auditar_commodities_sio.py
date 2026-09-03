#!/usr/bin/env python3
"""Audita calidad, cobertura y actualidad de datos integrados de SIO Granos."""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROCESSED_PATH = ROOT / "data" / "commodities_sio" / "processed" / "COMMODITIES_SIO_INTEGRADO.csv"
REPORT_DIR = ROOT / "data" / "commodities_sio" / "reports"
REPORTS = {
    "report": REPORT_DIR / "REPORTE_AUDITORIA_COMMODITIES_SIO.md",
    "coverage": REPORT_DIR / "RESUMEN_COBERTURA_COMMODITIES_SIO.csv",
    "commodities": REPORT_DIR / "RESUMEN_COMMODITIES_SIO.csv",
    "series": REPORT_DIR / "RESUMEN_SERIES_COMMODITIES_SIO.csv",
    "problems": REPORT_DIR / "CASOS_PROBLEMATICOS_COMMODITIES_SIO.csv",
    "actuality": REPORT_DIR / "RESUMEN_ACTUALIDAD_COMMODITIES_SIO.csv",
}
def parse_date(value: str) -> date | None:
    raw = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_price(value: str) -> float | None:
    raw = (value or "").strip().replace("$", "").replace("ARS", "").replace("USD", "")
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


def read_rows() -> list[dict[str, str]]:
    if not PROCESSED_PATH.exists():
        return []
    with PROCESSED_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def remove_reports() -> None:
    for path in REPORTS.values():
        if path.exists():
            path.unlink()


def no_data() -> int:
    remove_reports()
    print("No hay datos integrados de SIO Granos para auditar.")
    print("Coloque respuestas reales en data/commodities_sio/raw/, ejecute integrar_commodities_sio.py y vuelva a ejecutar esta auditoría.")
    print("No se generan reportes vacíos.")
    return 0


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(value).replace("|", "/") for value in row) + " |" for row in rows)
    return "\n".join(lines)


def main() -> int:
    rows = read_rows()
    if not rows:
        return no_data()
    today = date.today()
    dates_by: dict[str, list[date]] = defaultdict(list)
    prices_by: dict[str, list[float]] = defaultdict(list)
    all_dates: list[date] = []
    all_prices: list[float] = []
    problems: list[dict[str, str]] = []
    duplicates: Counter[tuple[str, ...]] = Counter()
    missing_price = zero_price = negative_price = invalid_date = 0
    for row_number, row in enumerate(rows, start=2):
        commodity = (row.get("commodity") or "Sin especificar").strip() or "Sin especificar"
        parsed_date = parse_date(row.get("fecha", ""))
        parsed_price = parse_price(row.get("precio", ""))
        if parsed_date:
            all_dates.append(parsed_date)
            dates_by[commodity].append(parsed_date)
        else:
            invalid_date += 1
            problems.append({"fila": str(row_number), "tipo": "fecha inválida o faltante", "commodity": commodity, "fecha": row.get("fecha", ""), "precio": row.get("precio", ""), "detalle": "Revisar fecha de concertación/mercado y su formato."})
        if parsed_price is None:
            missing_price += 1
            problems.append({"fila": str(row_number), "tipo": "precio inválido o faltante", "commodity": commodity, "fecha": row.get("fecha", ""), "precio": row.get("precio", ""), "detalle": "Revisar la columna Precio, Precio Hecho, Cotización o Valor."})
        else:
            all_prices.append(parsed_price)
            prices_by[commodity].append(parsed_price)
            if parsed_price == 0:
                zero_price += 1
                problems.append({"fila": str(row_number), "tipo": "precio cero", "commodity": commodity, "fecha": row.get("fecha", ""), "precio": row.get("precio", ""), "detalle": "No se considera una observación normal de mercado."})
            if parsed_price < 0:
                negative_price += 1
                problems.append({"fila": str(row_number), "tipo": "precio negativo", "commodity": commodity, "fecha": row.get("fecha", ""), "precio": row.get("precio", ""), "detalle": "Revisar signo y parsing de la respuesta SIO."})
        duplicates[(row.get("fecha", ""), commodity, row.get("tipo_precio", ""), row.get("moneda", ""), row.get("unidad", ""), row.get("mercado", ""))] += 1

    for duplicate_key, count in duplicates.items():
        if count > 1:
            problems.append({"fila": "", "tipo": "posible duplicado", "commodity": duplicate_key[1], "fecha": duplicate_key[0], "precio": "", "detalle": f"La clave fecha/commodity/tipo/moneda/unidad/mercado aparece {count} veces."})

    commodities = sorted({(row.get("commodity") or "Sin especificar").strip() or "Sin especificar" for row in rows})
    years = sorted({item.year for item in all_dates})
    months = sorted({item.strftime("%Y-%m") for item in all_dates})
    actuality: list[dict[str, str]] = []
    summary: list[dict[str, str]] = []
    series: list[dict[str, str]] = []
    coverage: list[dict[str, str]] = []
    for item in all_dates:
        coverage.append({"nivel": "mes", "commodity": "", "año": str(item.year), "mes": item.strftime("%Y-%m"), "registros": "1"})
    for commodity in commodities:
        subset = [row for row in rows if ((row.get("commodity") or "Sin especificar").strip() or "Sin especificar") == commodity]
        dates = dates_by[commodity]
        prices = prices_by[commodity]
        min_date = min(dates) if dates else None
        max_date = max(dates) if dates else None
        age = (today - max_date).days if max_date else ""
        count_7 = sum(1 for item in dates if today - timedelta(days=6) <= item <= today)
        count_30 = sum(1 for item in dates if today - timedelta(days=29) <= item <= today)
        if not max_date:
            status = "Sin fecha"
        elif age < 0:
            status = "Fecha futura"
        elif age <= 7:
            status = "Actualizado"
        elif age <= 30:
            status = "Reciente"
        else:
            status = "Desactualizado"
        currencies = sorted({(row.get("moneda") or "").strip() for row in subset if (row.get("moneda") or "").strip()})
        units = sorted({(row.get("unidad") or "").strip() for row in subset if (row.get("unidad") or "").strip()})
        types = sorted({(row.get("tipo_precio") or "").strip() for row in subset if (row.get("tipo_precio") or "").strip()})
        quality = "Alta" if len(prices) >= 5 and len(dates) >= 5 and len(currencies) <= 1 and len(units) <= 1 else "Media" if len(prices) >= 2 and len(dates) >= 2 else "Baja"
        usable = "Sí" if len(prices) >= 2 and len(dates) >= 2 and len(currencies) == 1 and len(units) == 1 and status != "Fecha futura" else "No"
        actuality.append({"commodity": commodity, "fecha_max": max_date.isoformat() if max_date else "", "dias_desde_ultimo_dato": str(age) if max_date else "", "registros_ultimos_7_dias": str(count_7), "registros_ultimos_30_dias": str(count_30), "estado_actualidad": status})
        summary.append({"commodity": commodity, "filas_totales": str(len(subset)), "años": "|".join(str(item.year) for item in sorted(set(dates))), "meses": "|".join(sorted({item.strftime('%Y-%m') for item in dates})), "fecha_min": min_date.isoformat() if min_date else "", "fecha_max": max_date.isoformat() if max_date else "", "precios_validos": str(len(prices)), "precios_faltantes": str(sum(1 for row in subset if parse_price(row.get("precio", "")) is None)), "precios_cero": str(sum(1 for item in prices if item == 0)), "precios_negativos": str(sum(1 for item in prices if item < 0)), "moneda": "|".join(currencies), "unidad": "|".join(units), "tipo_precio": "|".join(types)})
        series.append({"commodity": commodity, "moneda": "|".join(currencies), "unidad": "|".join(units), "tipo_precio": "|".join(types), "frecuencia": "|".join(sorted({row.get('frecuencia', '') or 'Sin especificar' for row in subset})), "calidad_serie": quality, "aptitud_dashboard_analitico": usable, "motivo": "" if usable == "Sí" else "Se requieren precios y fechas válidas, con moneda y unidad homogéneas."})
        for year in sorted({item.year for item in dates}):
            coverage.append({"nivel": "commodity_año", "commodity": commodity, "año": str(year), "mes": "", "registros": str(sum(1 for item in dates if item.year == year))})
    for commodity in commodities:
        coverage.append({"nivel": "commodity", "commodity": commodity, "año": "", "mes": "", "registros": str(len(dates_by[commodity]))})
    coverage_fields = ["nivel", "commodity", "año", "mes", "registros"]
    write_csv(REPORTS["coverage"], coverage_fields, coverage)
    write_csv(REPORTS["commodities"], list(summary[0].keys()), summary)
    write_csv(REPORTS["series"], list(series[0].keys()), series)
    write_csv(REPORTS["problems"], ["fila", "tipo", "commodity", "fecha", "precio", "detalle"], problems)
    write_csv(REPORTS["actuality"], list(actuality[0].keys()), actuality)

    max_date = max(all_dates) if all_dates else None
    min_date = min(all_dates) if all_dates else None
    age = (today - max_date).days if max_date else ""
    usable_count = sum(1 for row in series if row["aptitud_dashboard_analitico"] == "Sí")
    updated = [row["commodity"] for row in actuality if row["estado_actualidad"] == "Actualizado"]
    recent = [row["commodity"] for row in actuality if row["estado_actualidad"] in {"Actualizado", "Reciente"}]
    warnings = []
    if missing_price:
        warnings.append(f"{missing_price} fila(s) sin precio válido.")
    if invalid_date:
        warnings.append(f"{invalid_date} fila(s) sin fecha válida.")
    if zero_price or negative_price:
        warnings.append(f"Precios cero: {zero_price}; precios negativos: {negative_price}.")
    lines = ["# Reporte de auditoría de commodities SIO", "", f"Fecha de auditoría: {today.isoformat()}", "", "## Resumen", "", f"- Filas totales: {len(rows)}.", f"- Commodities detectados: {', '.join(commodities)}.", f"- Años disponibles: {', '.join(str(item) for item in years) if years else 'ninguno'}.", f"- Meses disponibles: {', '.join(months) if months else 'ninguno'}.", f"- Rango de fechas: {min_date.isoformat() if min_date else 'sin fecha válida'} a {max_date.isoformat() if max_date else 'sin fecha válida'}.", f"- Fecha máxima: {max_date.isoformat() if max_date else 'sin fecha válida'}; días desde último dato: {age if max_date else 'sin fecha válida'}.", f"- Precios válidos: {len(all_prices)}; faltantes: {missing_price}; cero: {zero_price}; negativos: {negative_price}.", f"- Monedas detectadas: {', '.join(sorted({row.get('moneda', '') for row in rows if row.get('moneda', '')})) or 'ninguna'}.", f"- Unidades detectadas: {', '.join(sorted({row.get('unidad', '') for row in rows if row.get('unidad', '')})) or 'ninguna'}.", f"- Tipos de precio detectados: {', '.join(sorted({row.get('tipo_precio', '') for row in rows if row.get('tipo_precio', '')})) or 'ninguno'}.", f"- Series utilizables para dashboard analítico futuro: {usable_count} de {len(series)}.", ""]
    if warnings:
        lines.extend(["## Advertencias", "", *[f"- {warning}" for warning in warnings], ""])
    lines.extend(["## Actualidad", "", f"Commodities actualizados: {', '.join(updated) if updated else 'ninguno'}.", f"Commodities recientes o actualizados: {', '.join(recent) if recent else 'ninguno'}.", f"Cobertura de últimos 7 días: {sum(int(row['registros_ultimos_7_dias']) for row in actuality)} registro(s). Cobertura de últimos 30 días: {sum(int(row['registros_ultimos_30_dias']) for row in actuality)} registro(s).", "", markdown_table(["Commodity", "Fecha máxima", "Días", "Últimos 7 días", "Últimos 30 días", "Estado"], [[row["commodity"], row["fecha_max"] or "—", row["dias_desde_ultimo_dato"] or "—", row["registros_ultimos_7_dias"], row["registros_ultimos_30_dias"], row["estado_actualidad"]] for row in actuality]), "", "## Series y aptitud analítica", "", markdown_table(["Commodity", "Moneda", "Unidad", "Tipo", "Calidad", "Aptitud"], [[row["commodity"], row["moneda"], row["unidad"], row["tipo_precio"], row["calidad_serie"], row["aptitud_dashboard_analitico"]] for row in series]), "", f"Casos problemáticos: {len(problems)}. Ver CASOS_PROBLEMATICOS_COMMODITIES_SIO.csv.", "", "## Próximos pasos", "", "Validar la respuesta real de SIO, especialmente definición de precio, fecha de concertación, condición comercial, unidad, moneda, cobertura y permisos. No publicar ni mezclar con BCR o frutas/hortalizas sin una revisión metodológica."])
    REPORTS["report"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Auditoría SIO finalizada: {len(rows)} filas, {len(commodities)} commodity(s).")
    print(f"Fecha máxima: {max_date.isoformat() if max_date else 'sin fecha válida'}; precios válidos: {len(all_prices)}; faltantes: {missing_price}.")
    for path in REPORTS.values():
        print(f"Reporte: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
