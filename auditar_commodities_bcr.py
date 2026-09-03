#!/usr/bin/env python3
"""Audita cobertura, validez, comparabilidad y actualidad del dataset BCR."""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "commodities_bcr" / "raw"
PROCESSED_PATH = ROOT / "data" / "commodities_bcr" / "processed" / "COMMODITIES_BCR_INTEGRADO.csv"
REPORT_DIR = ROOT / "data" / "commodities_bcr" / "reports"
REPORT_FILES = {
    "report": REPORT_DIR / "REPORTE_AUDITORIA_COMMODITIES_BCR.md",
    "coverage": REPORT_DIR / "RESUMEN_COBERTURA_COMMODITIES_BCR.csv",
    "commodities": REPORT_DIR / "RESUMEN_COMMODITIES_BCR.csv",
    "series": REPORT_DIR / "RESUMEN_SERIES_COMMODITIES_BCR.csv",
    "problems": REPORT_DIR / "CASOS_PROBLEMATICOS_COMMODITIES_BCR.csv",
    "actuality": REPORT_DIR / "RESUMEN_ACTUALIDAD_COMMODITIES_BCR.csv",
}
NON_REAL_MARKERS = re.compile(r"plantilla|simulad|prueba|test", re.IGNORECASE)


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


def raw_candidates() -> list[Path]:
    if not RAW_DIR.exists():
        return []
    return sorted(path for path in RAW_DIR.iterdir() if path.is_file() and path.suffix.lower() in {".csv", ".xlsx", ".xls"} and not path.name.startswith("~$"))


def remove_reports() -> None:
    for path in REPORT_FILES.values():
        if path.exists():
            path.unlink()


def no_data_diagnostic() -> int:
    remove_reports()
    candidates = raw_candidates()
    non_real = [path for path in candidates if NON_REAL_MARKERS.search(path.name)]
    print("No se encontraron archivos reales de BCR en data/commodities_bcr/raw/. Descargue un Excel/CSV de Precios de Pizarra/Cámara y vuelva a ejecutar la integración.")
    if non_real:
        print("Los datos disponibles son de prueba o plantilla. No usar para análisis real.")
    print("No hay datos integrados para auditar y no se generan reportes vacíos que parezcan válidos.")
    print("Próximos pasos: coloque BCR_pizarra_maiz_ultimos_30_dias.xlsx o equivalente en raw/, ejecute integrar_commodities_bcr.py y vuelva a ejecutar esta auditoría.")
    return 0


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(value).replace("|", "/") for value in row) + " |" for row in rows)
    return "\n".join(lines)


def main() -> int:
    rows = read_rows()
    if not rows:
        return no_data_diagnostic()

    today = date.today()
    dates_by_commodity: dict[str, list[date]] = defaultdict(list)
    prices_by_commodity: dict[str, list[float]] = defaultdict(list)
    all_dates: list[date] = []
    all_prices: list[float] = []
    problems: list[dict[str, str]] = []
    key_counts: Counter[tuple[str, ...]] = Counter()
    simulated = False
    missing_price = zero_price = negative_price = invalid_date = 0

    for row_number, row in enumerate(rows, start=2):
        commodity = (row.get("commodity") or "Sin identificar").strip() or "Sin identificar"
        parsed_date = parse_date(row.get("fecha", ""))
        parsed_price = parse_price(row.get("precio", ""))
        if parsed_date:
            all_dates.append(parsed_date)
            dates_by_commodity[commodity].append(parsed_date)
        else:
            invalid_date += 1
            problems.append({"fila": str(row_number), "tipo": "fecha inválida o faltante", "commodity": commodity, "fecha": row.get("fecha", ""), "precio": row.get("precio", ""), "detalle": "Use fecha de mercado con formato YYYY-MM-DD o DD/MM/YYYY."})
        if parsed_price is None:
            missing_price += 1
            problems.append({"fila": str(row_number), "tipo": "precio inválido o faltante", "commodity": commodity, "fecha": row.get("fecha", ""), "precio": row.get("precio", ""), "detalle": "No se detectó una columna/valor de precio válido; revisar encabezado Precio/Pizarra/Cotización/Valor."})
        else:
            all_prices.append(parsed_price)
            prices_by_commodity[commodity].append(parsed_price)
            if parsed_price == 0:
                zero_price += 1
                problems.append({"fila": str(row_number), "tipo": "precio cero", "commodity": commodity, "fecha": row.get("fecha", ""), "precio": row.get("precio", ""), "detalle": "Un precio cero no se considera válido para análisis de mercado."})
            if parsed_price < 0:
                negative_price += 1
                problems.append({"fila": str(row_number), "tipo": "precio negativo", "commodity": commodity, "fecha": row.get("fecha", ""), "precio": row.get("precio", ""), "detalle": "Revisar signo y formato de la descarga."})
        if NON_REAL_MARKERS.search(row.get("archivo_origen", "") + " " + row.get("observaciones", "")):
            simulated = True
        key_counts[(row.get("fecha", ""), commodity, row.get("tipo_precio", ""), row.get("moneda", ""), row.get("unidad", ""), row.get("mercado", ""))] += 1

    for duplicate_key, count in key_counts.items():
        if count > 1:
            problems.append({"fila": "", "tipo": "posible duplicado", "commodity": duplicate_key[1], "fecha": duplicate_key[0], "precio": "", "detalle": f"La clave fecha/commodity/tipo/moneda/unidad/mercado aparece {count} veces."})

    commodities = sorted({(row.get("commodity") or "Sin identificar").strip() or "Sin identificar" for row in rows})
    actuality_rows: list[dict[str, str]] = []
    commodity_rows: list[dict[str, str]] = []
    series_rows: list[dict[str, str]] = []
    for commodity in commodities:
        subset = [row for row in rows if ((row.get("commodity") or "Sin identificar").strip() or "Sin identificar") == commodity]
        dates = dates_by_commodity[commodity]
        prices = prices_by_commodity[commodity]
        max_date = max(dates) if dates else None
        min_date = min(dates) if dates else None
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
        units = sorted({(row.get("unidad") or "").strip() for row in subset if (row.get("unidad") or "").strip()})
        currencies = sorted({(row.get("moneda") or "").strip() for row in subset if (row.get("moneda") or "").strip()})
        frequencies = sorted({(row.get("frecuencia") or "Sin determinar").strip() or "Sin determinar" for row in subset})
        quality = "Alta" if len(prices) >= 5 and len(dates) >= 5 and len(units) <= 1 and len(currencies) <= 1 else "Media" if len(prices) >= 2 and len(dates) >= 2 else "Baja"
        usable = "Sí" if len(prices) >= 2 and len(dates) >= 2 and len(units) == 1 and len(currencies) == 1 and status != "Fecha futura" else "No"
        actuality_rows.append({"commodity": commodity, "fecha_max": max_date.isoformat() if max_date else "", "dias_desde_ultimo_dato": str(age) if max_date else "", "registros_ultimos_7_dias": str(count_7), "registros_ultimos_30_dias": str(count_30), "estado_actualidad": status})
        commodity_rows.append({"commodity": commodity, "filas_totales": str(len(subset)), "fecha_min": min_date.isoformat() if min_date else "", "fecha_max": max_date.isoformat() if max_date else "", "precios_validos": str(len(prices)), "precios_faltantes": str(sum(1 for row in subset if parse_price(row.get("precio", "")) is None)), "precios_cero": str(sum(1 for price in prices if price == 0)), "precios_negativos": str(sum(1 for price in prices if price < 0)), "precio_min": f"{min(prices):g}" if prices else "", "precio_max": f"{max(prices):g}" if prices else "", "unidad": "|".join(units), "moneda": "|".join(currencies), "frecuencia": "|".join(frequencies)})
        series_rows.append({"commodity": commodity, "unidad": "|".join(units), "moneda": "|".join(currencies), "frecuencia_detectada": "|".join(frequencies), "calidad_serie": quality, "sirve_visualizacion_analitica": usable, "motivo": "" if usable == "Sí" else "Se requieren al menos dos precios y fechas válidas, con unidad y moneda homogéneas."})

    max_date = max(all_dates) if all_dates else None
    min_date = min(all_dates) if all_dates else None
    age = (today - max_date).days if max_date else ""
    coverage_7 = sum(1 for item in all_dates if today - timedelta(days=6) <= item <= today)
    coverage_30 = sum(1 for item in all_dates if today - timedelta(days=29) <= item <= today)
    write_csv(REPORT_FILES["coverage"], ["metrica", "valor", "observacion"], [
        {"metrica": "filas_totales", "valor": str(len(rows)), "observacion": "Filas provenientes de archivos reales no marcados como plantilla/prueba."},
        {"metrica": "commodity_detectado", "valor": "|".join(commodities), "observacion": "Normalizado por catálogo o conservado para revisión."},
        {"metrica": "fecha_minima", "valor": min_date.isoformat() if min_date else "", "observacion": "Fecha de mercado válida."},
        {"metrica": "fecha_maxima", "valor": max_date.isoformat() if max_date else "", "observacion": "Fecha de mercado válida."},
        {"metrica": "dias_desde_ultimo_dato", "valor": str(age) if max_date else "", "observacion": "Calculado respecto de la fecha de auditoría."},
        {"metrica": "precios_validos", "valor": str(len(all_prices)), "observacion": "Valores numéricos luego de parsing argentino."},
        {"metrica": "precios_faltantes", "valor": str(missing_price), "observacion": "Sin valor numérico válido."},
        {"metrica": "precios_cero", "valor": str(zero_price), "observacion": "Caso problemático."},
        {"metrica": "precios_negativos", "valor": str(negative_price), "observacion": "Caso problemático."},
        {"metrica": "cobertura_ultimos_7_dias", "valor": str(coverage_7), "observacion": "Cantidad de registros con fecha en la ventana."},
        {"metrica": "cobertura_ultimos_30_dias", "valor": str(coverage_30), "observacion": "Cantidad de registros con fecha en la ventana."},
    ])
    write_csv(REPORT_FILES["commodities"], list(commodity_rows[0].keys()), commodity_rows)
    write_csv(REPORT_FILES["series"], list(series_rows[0].keys()), series_rows)
    write_csv(REPORT_FILES["problems"], ["fila", "tipo", "commodity", "fecha", "precio", "detalle"], problems)
    write_csv(REPORT_FILES["actuality"], list(actuality_rows[0].keys()), actuality_rows)

    updated = [row["commodity"] for row in actuality_rows if row["estado_actualidad"] == "Actualizado"]
    recent = [row["commodity"] for row in actuality_rows if row["estado_actualidad"] in {"Actualizado", "Reciente"}]
    stale = [row["commodity"] for row in actuality_rows if row["estado_actualidad"] in {"Desactualizado", "Sin fecha", "Fecha futura"}]
    warnings = []
    if simulated:
        warnings.append("Los datos disponibles son de prueba o plantilla. No usar para análisis real.")
    if missing_price:
        warnings.append(f"{missing_price} fila(s) no tiene(n) precio válido; revisar las columnas detectadas por el integrador.")
    if invalid_date:
        warnings.append(f"{invalid_date} fila(s) no tiene(n) fecha válida; la actualidad no puede calcularse para ellas.")
    if zero_price or negative_price:
        warnings.append(f"Hay {zero_price} precio(s) cero y {negative_price} negativo(s); no sirven como observaciones normales de mercado.")
    usable_count = sum(1 for row in series_rows if row["sirve_visualizacion_analitica"] == "Sí")
    report_lines = [
        "# Reporte de auditoría de commodities BCR", "", f"Fecha de auditoría: {today.isoformat()}", "",
        "## Resumen", "", f"- Filas totales: {len(rows)}.", f"- Commodities detectados: {', '.join(commodities)}.", f"- Fecha mínima: {min_date.isoformat() if min_date else 'sin fecha válida'}.", f"- Fecha máxima: {max_date.isoformat() if max_date else 'sin fecha válida'}.", f"- Días desde último dato: {age if max_date else 'sin fecha válida'}.", f"- Precios válidos: {len(all_prices)}; faltantes: {missing_price}; cero: {zero_price}; negativos: {negative_price}.", f"- Series aptas para futura visualización analítica: {usable_count} de {len(series_rows)}.", "",
    ]
    if warnings:
        report_lines.extend(["## Advertencias", "", *[f"- {warning}" for warning in warnings], ""])
    report_lines.extend([
        "## Actualidad de la información", "", f"Commodities actualizados: {', '.join(updated) if updated else 'ninguno'}.", f"Commodities recientes o actualizados: {', '.join(recent) if recent else 'ninguno'}.", f"Commodities sin dato reciente, desactualizados o con fecha futura: {', '.join(stale) if stale else 'ninguno'}.", f"Cobertura de últimos 7 días: {coverage_7} registro(s). Cobertura de últimos 30 días: {coverage_30} registro(s).", "", markdown_table(["Commodity", "Fecha máxima", "Días", "Últimos 7 días", "Últimos 30 días", "Estado"], [[row["commodity"], row["fecha_max"] or "—", row["dias_desde_ultimo_dato"] or "—", row["registros_ultimos_7_dias"], row["registros_ultimos_30_dias"], row["estado_actualidad"]] for row in actuality_rows]), "",
        "## Calidad y utilidad analítica", "", "La aptitud visual se determina por cantidad de precios/fechas válidas y homogeneidad de moneda y unidad; no reemplaza la validación metodológica de BCR.", "", markdown_table(["Commodity", "Calidad", "Visualización analítica", "Motivo"], [[row["commodity"], row["calidad_serie"], row["sirve_visualizacion_analitica"], row["motivo"]] for row in series_rows]), "", f"Casos problemáticos detectados: {len(problems)}. Ver `CASOS_PROBLEMATICOS_COMMODITIES_BCR.csv`.", "",
        "## Recomendación de automatización", "", "Mantener descarga manual mientras no exista una API BCR/GIX confirmada, autorizada y estable. No hacer scraping ni llamadas automáticas; si se habilita una API en el futuro, mantener credenciales fuera del repositorio y ejecutar la descarga desde un proceso local/backend.", "", "## Próximos pasos", "", "1. Revisar el archivo real, su fuente, tipo de precio, unidad, moneda y condiciones de uso.", "2. Confirmar que la serie sea Precio de Pizarra / Precio Cámara y que la fecha máxima sea suficientemente actual.", "3. Corregir casos problemáticos y repetir integración/auditoría antes de decidir cualquier módulo visual.",
    ])
    REPORT_FILES["report"].write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"Auditoría finalizada: {len(rows)} filas, {len(commodities)} commodity(s).")
    print(f"Precios válidos: {len(all_prices)}; faltantes: {missing_price}; cero: {zero_price}; negativos: {negative_price}.")
    print(f"Fecha mínima: {min_date.isoformat() if min_date else 'sin fecha válida'}; fecha máxima: {max_date.isoformat() if max_date else 'sin fecha válida'}.")
    print(f"Series aptas para visualización analítica futura: {usable_count} de {len(series_rows)}.")
    if warnings:
        for warning in warnings:
            print(f"ADVERTENCIA: {warning}")
    for path in REPORT_FILES.values():
        print(f"Reporte: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
