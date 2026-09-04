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
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
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
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";", extrasaction="ignore")
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


def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def display_values(rows: list[dict[str, str]], field: str) -> list[str]:
    return sorted({value(row, field) for row in rows if value(row, field) and value(row, field) != "Sin especificar"})


def coverage_count(rows: list[dict[str, str]], field: str) -> int:
    return sum(1 for row in rows if value(row, field) and value(row, field) != "Sin especificar")


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(item).replace("|", "/") for item in row) + " |" for row in rows)
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
        commodity = value(row, "commodity") or "Sin especificar"
        parsed_date = parse_date(value(row, "fecha"))
        parsed_price = parse_price(value(row, "precio"))
        if parsed_date:
            all_dates.append(parsed_date)
            dates_by[commodity].append(parsed_date)
        else:
            invalid_date += 1
            problems.append({"fila": str(row_number), "tipo": "fecha inválida o faltante", "commodity": commodity, "fecha": value(row, "fecha"), "precio": value(row, "precio"), "detalle": "Revisar fecha de declaración/concertación/entrega y su formato."})
        if parsed_price is None:
            missing_price += 1
            problems.append({"fila": str(row_number), "tipo": "precio inválido o faltante", "commodity": commodity, "fecha": value(row, "fecha"), "precio": value(row, "precio"), "detalle": "Revisar Precio, Precio/Monto, Monto, Precio hecho, Cotización o Valor."})
        else:
            all_prices.append(parsed_price)
            prices_by[commodity].append(parsed_price)
            if parsed_price == 0:
                zero_price += 1
                problems.append({"fila": str(row_number), "tipo": "precio cero", "commodity": commodity, "fecha": value(row, "fecha"), "precio": value(row, "precio"), "detalle": "No se considera una observación normal de mercado."})
            if parsed_price < 0:
                negative_price += 1
                problems.append({"fila": str(row_number), "tipo": "precio negativo", "commodity": commodity, "fecha": value(row, "fecha"), "precio": value(row, "precio"), "detalle": "Revisar signo y parsing de la respuesta SIO."})
        for field, label in (("moneda", "moneda faltante"), ("unidad", "unidad faltante"), ("tipo_precio", "tipo de precio faltante")):
            if not value(row, field) or value(row, field) == "Sin especificar":
                problems.append({"fila": str(row_number), "tipo": label, "commodity": commodity, "fecha": value(row, "fecha"), "precio": value(row, "precio"), "detalle": f"Completar {field} antes de usar la serie analíticamente."})
        duplicates[(value(row, "fecha"), commodity, value(row, "tipo_precio"), value(row, "moneda"), value(row, "unidad"), value(row, "mercado"))] += 1

    for duplicate_key, count in duplicates.items():
        if count > 1:
            problems.append({"fila": "", "tipo": "posible duplicado", "commodity": duplicate_key[1], "fecha": duplicate_key[0], "precio": "", "detalle": f"La clave fecha/commodity/tipo/moneda/unidad/mercado aparece {count} veces."})

    commodities = sorted({value(row, "commodity") or "Sin especificar" for row in rows})
    years = sorted({item.year for item in all_dates})
    months = sorted({item.strftime("%Y-%m") for item in all_dates})
    actuality: list[dict[str, str]] = []
    summary: list[dict[str, str]] = []
    series: list[dict[str, str]] = []
    coverage: list[dict[str, str]] = []
    for item in all_dates:
        coverage.append({"nivel": "mes", "commodity": "", "año": str(item.year), "mes": item.strftime("%Y-%m"), "registros": "1"})
    for commodity in commodities:
        subset = [row for row in rows if (value(row, "commodity") or "Sin especificar") == commodity]
        dates = dates_by[commodity]
        prices = prices_by[commodity]
        min_date = min(dates) if dates else None
        max_date = max(dates) if dates else None
        age = (today - max_date).days if max_date else None
        count_7 = sum(1 for item in dates if today - timedelta(days=6) <= item <= today)
        count_30 = sum(1 for item in dates if today - timedelta(days=29) <= item <= today)
        if not max_date:
            status = "Sin fecha"
        elif age is not None and age < 0:
            status = "Fecha futura"
        elif age is not None and age <= 7:
            status = "Actualizado"
        elif age is not None and age <= 30:
            status = "Reciente"
        else:
            status = "Desactualizado"
        currencies = display_values(subset, "moneda")
        units = display_values(subset, "unidad")
        types = display_values(subset, "tipo_precio")
        frequencies = display_values(subset, "frecuencia")
        quality = "Alta" if len(prices) >= 5 and len(dates) >= 5 and len(currencies) == 1 and len(units) == 1 else "Media" if len(prices) >= 2 and len(dates) >= 2 else "Baja"
        usable = "Sí" if len(prices) >= 2 and len(dates) >= 2 and len(currencies) == 1 and len(units) == 1 and len(types) == 1 and status not in {"Fecha futura", "Sin fecha"} else "No"
        actuality.append({"commodity": commodity, "fecha_max": max_date.isoformat() if max_date else "", "dias_desde_ultimo_dato": str(age) if max_date else "", "registros_ultimos_7_dias": str(count_7), "registros_ultimos_30_dias": str(count_30), "estado_actualidad": status})
        summary.append({"commodity": commodity, "filas_totales": str(len(subset)), "años": "|".join(str(item.year) for item in sorted(set(dates))), "meses": "|".join(sorted({item.strftime('%Y-%m') for item in dates})), "fecha_min": min_date.isoformat() if min_date else "", "fecha_max": max_date.isoformat() if max_date else "", "precios_validos": str(len(prices)), "precios_faltantes": str(sum(1 for row in subset if parse_price(value(row, "precio")) is None)), "precios_cero": str(sum(1 for item in prices if item == 0)), "precios_negativos": str(sum(1 for item in prices if item < 0)), "moneda": "|".join(currencies), "unidad": "|".join(units), "tipo_precio": "|".join(types), "volumen_con_dato": str(coverage_count(subset, "volumen")), "procedencia_con_dato": str(coverage_count(subset, "procedencia")), "precio_puesto_en_con_dato": str(coverage_count(subset, "precio_puesto_en")), "operacion_con_dato": str(coverage_count(subset, "operacion")), "condicion_pago_con_dato": str(coverage_count(subset, "condicion_pago"))})
        series.append({"commodity": commodity, "moneda": "|".join(currencies), "unidad": "|".join(units), "tipo_precio": "|".join(types), "frecuencia": "|".join(frequencies) or "Sin especificar", "registros": str(len(subset)), "fechas_validas": str(len(dates)), "precios_validos": str(len(prices)), "calidad_serie": quality, "aptitud_dashboard_analitico": usable, "motivo": "" if usable == "Sí" else "Se requieren fechas, precios y metadatos homogéneos; la serie debe validarse antes de publicar."})
        for year in sorted({item.year for item in dates}):
            coverage.append({"nivel": "commodity_año", "commodity": commodity, "año": str(year), "mes": "", "registros": str(sum(1 for item in dates if item.year == year))})
        coverage.append({"nivel": "commodity", "commodity": commodity, "año": "", "mes": "", "registros": str(len(dates))})
        coverage.append({"nivel": "commodity_ultimos_30_dias", "commodity": commodity, "año": "", "mes": "", "registros": str(count_30)})

    coverage_fields = ["nivel", "commodity", "año", "mes", "registros"]
    write_csv(REPORTS["coverage"], coverage_fields, coverage)
    write_csv(REPORTS["commodities"], list(summary[0].keys()), summary)
    write_csv(REPORTS["series"], list(series[0].keys()), series)
    write_csv(REPORTS["problems"], ["fila", "tipo", "commodity", "fecha", "precio", "detalle"], problems)
    write_csv(REPORTS["actuality"], list(actuality[0].keys()), actuality)

    max_date = max(all_dates) if all_dates else None
    min_date = min(all_dates) if all_dates else None
    age = (today - max_date).days if max_date else None
    usable_count = sum(1 for item in series if item["aptitud_dashboard_analitico"] == "Sí")
    updated = [item["commodity"] for item in actuality if item["estado_actualidad"] == "Actualizado"]
    recent = [item["commodity"] for item in actuality if item["estado_actualidad"] in {"Actualizado", "Reciente"}]
    no_recent = [item["commodity"] for item in actuality if item["estado_actualidad"] not in {"Actualizado", "Reciente"}]
    warnings: list[str] = []
    if missing_price:
        warnings.append(f"{missing_price} fila(s) sin precio válido.")
    if invalid_date:
        warnings.append(f"{invalid_date} fila(s) sin fecha válida.")
    if zero_price or negative_price:
        warnings.append(f"Precios cero: {zero_price}; precios negativos: {negative_price}.")
    currency_values = display_values(rows, "moneda")
    unit_values = display_values(rows, "unidad")
    type_values = display_values(rows, "tipo_precio")
    volume_valid = sum(1 for row in rows if parse_price(value(row, "volumen")) is not None)
    pilot_fields = ["fecha", "operacion", "tipo_precio", "commodity", "volumen", "procedencia", "precio", "zona", "condicion_pago"]
    mapped_columns = [field for field in pilot_fields if coverage_count(rows, field)]
    missing_columns = [field for field in ["moneda", "unidad", "volumen_unidad", "precio_puesto_en", "frecuencia"] if not coverage_count(rows, field)]
    pilot_rows = sum(1 for row in rows if "integración piloto una página GetOperaciones" in value(row, "observaciones"))
    lines = [
        "# Reporte de auditoría de commodities SIO", "", f"Fecha de auditoría: {today.isoformat()}", "", "## Resumen", "",
        f"- Muestra piloto de una sola página GetOperaciones: {'sí' if pilot_rows else 'no'}; filas piloto: {pilot_rows or 'sin marca piloto'}.", f"- Filas totales: {len(rows)}.", f"- Columnas mapeadas con dato: {', '.join(mapped_columns) or 'ninguna'}.", f"- Columnas faltantes/no separadas: {', '.join(missing_columns) or 'ninguna'}.", f"- Commodities detectados: {', '.join(commodities)}.", f"- Años disponibles: {', '.join(str(item) for item in years) if years else 'ninguno'}.", f"- Meses disponibles: {', '.join(months) if months else 'ninguno'}.", f"- Rango de fechas: {min_date.isoformat() if min_date else 'sin fecha válida'} a {max_date.isoformat() if max_date else 'sin fecha válida'}.", f"- Fecha máxima: {max_date.isoformat() if max_date else 'sin fecha válida'}; días desde último dato: {age if max_date else 'sin fecha válida'}.", f"- Precios válidos: {len(all_prices)}; faltantes: {missing_price}; cero: {zero_price}; negativos: {negative_price}.", f"- Monedas: {', '.join(currency_values) or 'ninguna'}; unidades: {', '.join(unit_values) or 'ninguna'}; tipos de precio: {', '.join(type_values) or 'ninguno'}.", f"- Volumen con dato numérico: {volume_valid}; procedencia con dato: {coverage_count(rows, 'procedencia')}; lugar de entrega (zona) con dato: {coverage_count(rows, 'zona')}; condición de pago con dato: {coverage_count(rows, 'condicion_pago')}.", f"- Series utilizables para dashboard analítico futuro: {usable_count} de {len(series)}.", "",
    ]
    if warnings:
        lines.extend(["## Advertencias", "", *[f"- {warning}" for warning in warnings], ""])
    lines.extend([
        "## Actualidad de la información", "", f"Fecha máxima disponible: {max_date.isoformat() if max_date else 'sin fecha válida'}.", f"Días desde el último dato: {age if age is not None else 'sin fecha válida'}.", f"Commodities actualizados (últimos 7 días): {', '.join(updated) if updated else 'ninguno'}.", f"Commodities recientes o actualizados (últimos 30 días): {', '.join(recent) if recent else 'ninguno'}.", f"Commodities sin dato reciente: {', '.join(no_recent) if no_recent else 'ninguno'}.", f"Cobertura últimos 7 días: {sum(int(item['registros_ultimos_7_dias']) for item in actuality)} registro(s). Cobertura últimos 30 días: {sum(int(item['registros_ultimos_30_dias']) for item in actuality)} registro(s).", "", markdown_table(["Commodity", "Fecha máxima", "Días", "Últimos 7 días", "Últimos 30 días", "Estado"], [[item["commodity"], item["fecha_max"] or "—", item["dias_desde_ultimo_dato"] or "—", item["registros_ultimos_7_dias"], item["registros_ultimos_30_dias"], item["estado_actualidad"]] for item in actuality]), "",
        "## Recomendación de automatización", "", "SIO Granos debe mantenerse como exploración separada hasta validar la procedencia, la definición del precio, los permisos de uso, la estabilidad de la consulta pública y la homogeneidad de moneda, unidad, frecuencia y tipo de precio.", "Si hay datos recientes y la consulta/exportación pública es estable, conviene automatizar con ventanas de hasta 180 días y auditoría previa. Si no hay exportación estable, mantener la descarga manual en raw/ y conservar la respuesta original.", "No publicar en el dashboard ni mezclar con BCR o frutas/hortalizas antes de esa validación.", "", "## Series y aptitud analítica", "", markdown_table(["Commodity", "Moneda", "Unidad", "Tipo", "Frecuencia", "Calidad", "Aptitud"], [[item["commodity"], item["moneda"], item["unidad"], item["tipo_precio"], item["frecuencia"], item["calidad_serie"], item["aptitud_dashboard_analitico"]] for item in series]), "", f"Casos problemáticos: {len(problems)}. Ver CASOS_PROBLEMATICOS_COMMODITIES_SIO.csv.", "", "## Próximos pasos", "", "Validar una respuesta real de SIO y revisar especialmente fecha, condición de pago, operación, volumen, procedencia, precio puesto en, unidad, moneda y permisos. No inventar datos ni usar fuentes alternativas como equivalentes de SIO/BCR sin evidencia.",
    ])
    REPORTS["report"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Auditoría SIO finalizada: {len(rows)} filas, {len(commodities)} commodity(s).")
    print(f"Fecha máxima: {max_date.isoformat() if max_date else 'sin fecha válida'}; precios válidos: {len(all_prices)}; faltantes: {missing_price}.")
    for path in REPORTS.values():
        print(f"Reporte: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
