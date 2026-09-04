#!/usr/bin/env python3
"""Audita calidad, cobertura y actualidad de datos integrados de SIO Granos."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROCESSED_PATH = ROOT / "data" / "commodities_sio" / "processed" / "COMMODITIES_SIO_INTEGRADO.csv"
RAW_DIR = ROOT / "data" / "commodities_sio" / "raw"
REPORT_DIR = ROOT / "data" / "commodities_sio" / "reports"
PAGINATED_REPORT_PATH = REPORT_DIR / "REPORTE_MUESTRA_PAGINADA_SIO.md"
PAGINATION_REPORT_PATH = REPORT_DIR / "REPORTE_PAGINACION_SIO.md"
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


def pilot_eligible(row: dict[str, str]) -> bool:
    return bool(parse_date(value(row, "fecha")) and value(row, "commodity") and parse_price(value(row, "precio")) is not None and value(row, "fuente") and value(row, "campo_precio_original") and value(row, "campo_precio_original") != "Sin especificar" and value(row, "unidad") and value(row, "unidad") != "Sin especificar")


def dashboard_status(row: dict[str, str], currency_values: list[str], unit_values: list[str]) -> str:
    explicit_currency = value(row, "moneda_explicitamente_informada").lower() in {"sí", "si", "true"} and value(row, "moneda") != "Sin especificar"
    explicit_unit = value(row, "unidad") != "Sin especificar" and bool(value(row, "unidad"))
    pilot_page = "integración piloto una página GetOperaciones" in value(row, "observaciones")
    if pilot_eligible(row) and explicit_currency and not currency_was_inferred(row) and explicit_unit and pilot_page:
        return "parcial_piloto"
    return "no"


def dashboard_eligible(row: dict[str, str], currency_values: list[str], unit_values: list[str]) -> bool:
    return dashboard_status(row, currency_values, unit_values) != "no"


def currency_was_inferred(row: dict[str, str]) -> bool:
    return bool(re.search(r"moneda\s+(?:inferida|asumida)|currency\s+(?:inferred|assumed)", value(row, "observaciones"), flags=re.I))


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(item).replace("|", "/") for item in row) + " |" for row in rows)
    return "\n".join(lines)


def format_counts(counts: Counter[str]) -> str:
    return ", ".join(f"{name or 'sin dato'}={count}" for name, count in sorted(counts.items())) or "sin dato"


def read_page_items(path: Path) -> list[dict[str, object]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    if isinstance(payload, dict) and isinstance(payload.get("d"), dict):
        payload = payload["d"]
    if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
        return []
    return [item for item in payload["Items"] if isinstance(item, dict)]


def pagination_metrics() -> dict[str, object]:
    preferred_files = sorted(RAW_DIR.glob("SIO_test_pagination_page_*.json"))
    fallback_files = sorted(RAW_DIR.glob("SIO_GetOperaciones_page_*.json"))
    candidates = preferred_files or fallback_files
    latest_by_page: dict[str, Path] = {}
    for path in candidates:
        page_match = re.search(r"page[_-](\d+)", path.stem, flags=re.I)
        page_key = page_match.group(1) if page_match else path.name
        if page_key not in latest_by_page or path.name > latest_by_page[page_key].name:
            latest_by_page[page_key] = path
    page_files = [latest_by_page[key] for key in sorted(latest_by_page, key=lambda item: int(item) if item.isdigit() else item)]
    page_groups: dict[str, list[str]] = {}
    raw_items: list[dict[str, object]] = []
    for path in page_files:
        items = read_page_items(path)
        if not items:
            continue
        signatures = [json.dumps({"ID": item.get("ID"), "Row": item.get("Row")}, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for item in items]
        page_match = re.search(r"page[_-](\d+)", path.stem, flags=re.I)
        page_key = page_match.group(1) if page_match else path.name
        page_groups[page_key] = signatures
        raw_items.extend(items)
    all_signatures = [json.dumps({"ID": item.get("ID"), "Row": item.get("Row")}, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for item in raw_items]
    ids = [str(item.get("ID")) for item in raw_items if item.get("ID") is not None]
    duplicate_ids = sum(count - 1 for count in Counter(ids).values() if count > 1)
    unique_rows = len(set(all_signatures))
    duplicate_exact = max(len(all_signatures) - unique_rows, 0)
    first = next(iter(page_groups.values()), [])
    if len(page_groups) == 0:
        status = "no_probada"
    elif len(page_groups) >= 2 and first and all(signatures == first for signatures in page_groups.values()):
        status = "duplicada"
    elif len(page_groups) >= 2:
        status = "validada" if duplicate_exact == 0 else "parcial"
    else:
        status = "parcial"
    return {"pages": len(page_groups), "raw_rows": len(all_signatures), "unique_rows": unique_rows, "duplicate_ids": duplicate_ids, "duplicate_exact": duplicate_exact, "duplication_pct": (duplicate_exact / len(all_signatures) * 100) if all_signatures else 0, "status": status}


def update_paginated_audit_report(rows: list[dict[str, str]]) -> None:
    report_paths = [path for path in (REPORTS["report"], PAGINATED_REPORT_PATH, PAGINATION_REPORT_PATH) if path.exists()]
    if not report_paths:
        return
    pages = sorted({value(row, "pagina_origen") for row in rows if value(row, "pagina_origen")}, key=lambda item: int(item))
    sample_page_count = max((int(value(row, "muestra_paginas")) for row in rows if value(row, "muestra_paginas").isdigit()), default=len(pages))
    records_by_page = Counter(value(row, "pagina_origen") for row in rows if value(row, "pagina_origen"))
    ids = [value(row, "id_operacion_sio") for row in rows if value(row, "id_operacion_sio")]
    duplicate_ids = sum(count - 1 for count in Counter(ids).values() if count > 1)
    composite_keys = [(value(row, "fecha"), value(row, "commodity"), value(row, "precio"), value(row, "moneda"), value(row, "unidad"), value(row, "volumen"), value(row, "lugar_entrega"), value(row, "tipo_precio")) for row in rows if not value(row, "id_operacion_sio")]
    duplicate_composites = sum(count - 1 for count in Counter(composite_keys).values() if count > 1)
    currencies = display_values(rows, "moneda")
    units = display_values(rows, "unidad")
    prices_by_currency = Counter(value(row, "moneda") for row in rows if parse_price(value(row, "precio")) is not None and value(row, "moneda") != "Sin especificar")
    pilot_statuses = Counter(value(row, "apto_piloto") for row in rows)
    dashboard_statuses = Counter(value(row, "apto_dashboard") for row in rows)
    dates = [parse_date(value(row, "fecha")) for row in rows]
    dates = [item for item in dates if item]
    metrics = pagination_metrics()
    pagination_section = "\n".join(["## Paginación y duplicados", "", f"- Páginas procesadas: {metrics['pages']}.", f"- Filas brutas: {metrics['raw_rows']}.", f"- Filas únicas por ID/Row: {metrics['unique_rows']}.", f"- Duplicados por ID: {metrics['duplicate_ids']}.", f"- Duplicados exactos por Row: {metrics['duplicate_exact']}.", f"- Porcentaje de duplicación: {metrics['duplication_pct']:.1f}%.", f"- estado_paginacion: `{metrics['status']}`.", "- Si las páginas repiten contenido, no se habilita `apto_dashboard=si`; el estado se mantiene en `parcial_piloto` o `no`.", ""])
    result_section = "\n".join([
        "## Resultado de auditoría", "", f"- Commodities: {', '.join(sorted({value(row, 'commodity') for row in rows if value(row, 'commodity')})) or 'ninguno'}.", f"- Rango de fechas: {min(dates).isoformat() if dates else 'sin fecha válida'} a {max(dates).isoformat() if dates else 'sin fecha válida'}.", f"- Monedas: {', '.join(currencies) or 'ninguna'}; mezcla ARS/USD: {'sí' if {'ARS', 'USD'}.issubset(set(currencies)) else 'no'}.", f"- Unidades: {', '.join(units) or 'ninguna'}.", f"- Precios válidos por moneda: {', '.join(f'{name}={count}' for name, count in sorted(prices_by_currency.items())) or 'ninguno'}.", f"- Volumen válido: {sum(1 for row in rows if parse_price(value(row, 'volumen')) is not None)}/{len(rows)}.", f"- Procedencias con dato: {coverage_count(rows, 'procedencia')}; lugares de entrega con dato: {coverage_count(rows, 'lugar_entrega')}; condiciones de pago con dato: {coverage_count(rows, 'condicion_pago')}.", f"- Páginas solicitadas/procesadas: {sample_page_count}; páginas con filas finales: {', '.join(pages) or 'no identificadas'}; registros finales por página: {', '.join(f'{page}={records_by_page[page]}' for page in pages) or 'no identificados'}.", f"- Duplicados por id_operacion_sio en CSV final: {duplicate_ids}; duplicados compuestos sin ID: {duplicate_composites}.", f"- apto_piloto: {format_counts(pilot_statuses)}.", f"- apto_dashboard: {format_counts(dashboard_statuses)}.", "- Comparabilidad conjunta ARS/USD: no; deben mantenerse series separadas por moneda.", "",
    ])
    for report_path in report_paths:
        report = report_path.read_text(encoding="utf-8")
        report = re.sub(r"## Resultado de auditoría\n.*?(?=\n## Riesgos)", result_section.rstrip(), report, flags=re.S)
        if "## Paginación y duplicados" in report:
            report = re.sub(r"## Paginación y duplicados\n.*?(?=\n## |\Z)", pagination_section.rstrip() + "\n", report, flags=re.S)
        else:
            insertion = "\n" + pagination_section + "\n"
            report = report.replace("\n## Actualidad de la información", insertion + "\n## Actualidad de la información", 1)
        report_path.write_text(report, encoding="utf-8")


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
    missing_price = zero_price = negative_price = invalid_date = inconsistent_price = 0
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
        price_unit_value = parse_price(value(row, "precio_unidad"))
        price_total_value = parse_price(value(row, "precio_total"))
        volume_value = parse_price(value(row, "volumen"))
        if parsed_price is not None and price_unit_value is not None and abs(parsed_price - price_unit_value) > 0.000001:
            inconsistent_price += 1
            problems.append({"fila": str(row_number), "tipo": "precio y precio_unidad inconsistentes", "commodity": commodity, "fecha": value(row, "fecha"), "precio": value(row, "precio"), "detalle": "Comparar precio seleccionado con precio_unidad antes de usar la serie."})
        if price_total_value is not None and price_unit_value is not None and volume_value is not None and abs(price_total_value - price_unit_value * volume_value) > max(1, abs(price_total_value) * 0.01):
            inconsistent_price += 1
            problems.append({"fila": str(row_number), "tipo": "precio total inconsistente", "commodity": commodity, "fecha": value(row, "fecha"), "precio": value(row, "precio"), "detalle": "precio_total no coincide aproximadamente con precio_unidad por volumen."})
        for field, label in (("moneda", "moneda faltante"), ("unidad", "unidad de precio faltante"), ("volumen_unidad", "unidad de volumen faltante"), ("tipo_precio", "tipo de precio faltante"), ("campo_precio_original", "campo de precio original faltante"), ("campo_volumen_original", "campo de volumen original faltante")):
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
    all_currency_values = display_values(rows, "moneda")
    all_unit_values = display_values(rows, "unidad")
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
        dashboard_statuses = [dashboard_status(row, all_currency_values, all_unit_values) for row in subset]
        dashboard_status_value = "si" if dashboard_statuses and all(item == "si" for item in dashboard_statuses) else "parcial_piloto" if dashboard_statuses and all(item == "parcial_piloto" for item in dashboard_statuses) else "no"
        usable = "Sí" if len(prices) >= 2 and len(dates) >= 2 and len(currencies) == 1 and len(units) == 1 and len(types) == 1 and status not in {"Fecha futura", "Sin fecha"} and dashboard_status_value == "si" else "No"
        actuality.append({"commodity": commodity, "fecha_max": max_date.isoformat() if max_date else "", "dias_desde_ultimo_dato": str(age) if max_date else "", "registros_ultimos_7_dias": str(count_7), "registros_ultimos_30_dias": str(count_30), "estado_actualidad": status})
        pilot_count = sum(1 for row in subset if pilot_eligible(row))
        dashboard_count = sum(1 for row in subset if dashboard_eligible(row, all_currency_values, all_unit_values))
        summary.append({"commodity": commodity, "filas_totales": str(len(subset)), "años": "|".join(str(item.year) for item in sorted(set(dates))), "meses": "|".join(sorted({item.strftime('%Y-%m') for item in dates})), "fecha_min": min_date.isoformat() if min_date else "", "fecha_max": max_date.isoformat() if max_date else "", "precios_validos": str(len(prices)), "precios_faltantes": str(sum(1 for row in subset if parse_price(value(row, "precio")) is None)), "precios_cero": str(sum(1 for item in prices if item == 0)), "precios_negativos": str(sum(1 for item in prices if item < 0)), "moneda": "|".join(currencies), "unidad": "|".join(units), "tipo_precio": "|".join(types), "precio_unidad_con_dato": str(coverage_count(subset, "precio_unidad")), "precio_total_con_dato": str(coverage_count(subset, "precio_total")), "campo_precio_original": "|".join(display_values(subset, "campo_precio_original")), "campo_volumen_original": "|".join(display_values(subset, "campo_volumen_original")), "volumen_con_dato": str(coverage_count(subset, "volumen")), "volumen_unidad_con_dato": str(coverage_count(subset, "volumen_unidad")), "procedencia_con_dato": str(coverage_count(subset, "procedencia")), "precio_puesto_en_con_dato": str(coverage_count(subset, "precio_puesto_en")), "operacion_con_dato": str(coverage_count(subset, "operacion")), "condicion_pago_con_dato": str(coverage_count(subset, "condicion_pago")), "apto_piloto": "Sí" if pilot_count == len(subset) else "No", "apto_dashboard": dashboard_status_value})
        series.append({"commodity": commodity, "moneda": "|".join(currencies), "unidad": "|".join(units), "tipo_precio": "|".join(types), "frecuencia": "|".join(frequencies) or "Sin especificar", "registros": str(len(subset)), "fechas_validas": str(len(dates)), "precios_validos": str(len(prices)), "precio_unidad_con_dato": str(coverage_count(subset, "precio_unidad")), "precio_total_con_dato": str(coverage_count(subset, "precio_total")), "campo_precio_original": "|".join(display_values(subset, "campo_precio_original")), "campo_volumen_original": "|".join(display_values(subset, "campo_volumen_original")), "apto_piloto": "Sí" if pilot_count == len(subset) else "No", "apto_dashboard": dashboard_status_value, "calidad_serie": quality, "aptitud_dashboard_analitico": usable, "motivo": "" if usable == "Sí" else "Se requieren validación de cobertura histórica/paginación y moneda/unidad homogéneas antes de publicar."})
        for year in sorted({item.year for item in dates}):
            coverage.append({"nivel": "commodity_año", "commodity": commodity, "año": str(year), "mes": "", "registros": str(sum(1 for item in dates if item.year == year))})
        coverage.append({"nivel": "commodity", "commodity": commodity, "año": "", "mes": "", "registros": str(len(dates))})
        coverage.append({"nivel": "commodity_ultimos_30_dias", "commodity": commodity, "año": "", "mes": "", "registros": str(count_30)})

    split_series: list[dict[str, str]] = []
    for commodity in commodities:
        commodity_rows = [row for row in rows if (value(row, "commodity") or "Sin especificar") == commodity]
        currency_groups = sorted({value(row, "moneda") or "Sin especificar" for row in commodity_rows})
        for currency in currency_groups:
            subset = [row for row in commodity_rows if (value(row, "moneda") or "Sin especificar") == currency]
            dates = [parsed for parsed in (parse_date(value(row, "fecha")) for row in subset) if parsed]
            prices = [parsed for parsed in (parse_price(value(row, "precio")) for row in subset) if parsed is not None]
            units = display_values(subset, "unidad")
            types = display_values(subset, "tipo_precio")
            frequencies = display_values(subset, "frecuencia")
            statuses = [dashboard_status(row, all_currency_values, all_unit_values) for row in subset]
            status_value = "si" if statuses and all(item == "si" for item in statuses) else "parcial_piloto" if statuses and all(item == "parcial_piloto" for item in statuses) else "no"
            quality = "Alta" if len(prices) >= 5 and len(dates) >= 5 and len(units) == 1 else "Media" if len(prices) >= 2 and len(dates) >= 2 else "Baja"
            usable = "Sí" if len(prices) >= 2 and len(dates) >= 2 and len(units) == 1 and len(types) == 1 and status_value == "si" else "No"
            split_series.append({"commodity": commodity, "moneda": currency if currency != "Sin especificar" else "", "unidad": "|".join(units), "tipo_precio": "|".join(types), "frecuencia": "|".join(frequencies) or "Sin especificar", "registros": str(len(subset)), "fechas_validas": str(len(dates)), "precios_validos": str(len(prices)), "precio_unidad_con_dato": str(coverage_count(subset, "precio_unidad")), "precio_total_con_dato": str(coverage_count(subset, "precio_total")), "campo_precio_original": "|".join(display_values(subset, "campo_precio_original")), "campo_volumen_original": "|".join(display_values(subset, "campo_volumen_original")), "apto_piloto": "Sí" if all(value(row, "apto_piloto").lower() in {"sí", "si"} for row in subset) else "No", "apto_dashboard": status_value, "calidad_serie": quality, "aptitud_dashboard_analitico": usable, "motivo": "" if usable == "Sí" else "Serie separada por moneda; requiere mayor cobertura y validación antes de publicar."})
    series = split_series

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
    missing_columns = [field for field in ["moneda", "precio_total", "precio_puesto_en", "frecuencia"] if not coverage_count(rows, field)]
    pilot_rows = sum(1 for row in rows if "integración piloto una página GetOperaciones" in value(row, "observaciones"))
    pilot_eligible_count = sum(1 for row in rows if pilot_eligible(row))
    dashboard_eligible_count = sum(1 for row in rows if dashboard_eligible(row, currency_values, unit_values))
    price_unit_count = coverage_count(rows, "precio_unidad")
    price_total_count = coverage_count(rows, "precio_total")
    volume_unit_count = coverage_count(rows, "volumen_unidad")
    price_field_values = display_values(rows, "campo_precio_original")
    volume_field_values = display_values(rows, "campo_volumen_original")
    currency_explicit_count = sum(1 for row in rows if value(row, "moneda_explicitamente_informada").lower() in {"sí", "si", "true"} and value(row, "moneda") != "Sin especificar")
    currency_inferred_count = sum(1 for row in rows if currency_was_inferred(row))
    currency_unspecified_count = len(rows) - currency_explicit_count - currency_inferred_count
    currency_counts = Counter(value(row, "moneda") for row in rows if value(row, "moneda") and value(row, "moneda") != "Sin especificar")
    valid_prices_by_currency = Counter(value(row, "moneda") for row in rows if parse_price(value(row, "precio")) is not None and value(row, "moneda") != "Sin especificar")
    currency_valid_pct = (currency_explicit_count / len(rows) * 100) if rows else 0
    dashboard_status_values = [dashboard_status(row, currency_values, unit_values) for row in rows]
    dashboard_status_counts = Counter(dashboard_status_values)
    dashboard_full_count = dashboard_status_counts.get("si", 0)
    dashboard_partial_count = dashboard_status_counts.get("parcial_piloto", 0)
    dashboard_no_count = dashboard_status_counts.get("no", 0)
    dashboard_eligible_count = dashboard_full_count
    currency_audit_lines = [
        f"- Moneda explícitamente informada: {'sí' if currency_explicit_count else 'no'} ({currency_explicit_count}/{len(rows)}).",
        f"- Moneda inferida: {'sí' if currency_inferred_count else 'no'} ({currency_inferred_count}/{len(rows)}).",
        f"- Moneda sin especificar: {'sí' if currency_unspecified_count else 'no'} ({currency_unspecified_count}/{len(rows)}).",
        f"- Porcentaje de filas con moneda válida/explícita: {currency_valid_pct:.1f}%.",
        f"- Conteo por moneda explícita: {', '.join(f'{name}={count}' for name, count in sorted(currency_counts.items())) or 'ninguna'}.",
        f"- Precios válidos por moneda: {', '.join(f'{name}={count}' for name, count in sorted(valid_prices_by_currency.items())) or 'ninguno'}.",
        f"- Estado apto_dashboard: si={dashboard_full_count}, parcial_piloto={dashboard_partial_count}, no={dashboard_no_count}.",
    ]
    lines = [
        "# Reporte de auditoría de commodities SIO", "", f"Fecha de auditoría: {today.isoformat()}", "", "## Resumen", "",
        *currency_audit_lines,
        f"- Muestra piloto de una sola página GetOperaciones: {'sí' if pilot_rows else 'no'}; filas piloto: {pilot_rows or 'sin marca piloto'}.", f"- Filas totales: {len(rows)}.", f"- Columnas mapeadas con dato: {', '.join(mapped_columns) or 'ninguna'}.", f"- Columnas faltantes/no separadas: {', '.join(missing_columns) or 'ninguna'}.", f"- Commodities detectados: {', '.join(commodities)}.", f"- Años disponibles: {', '.join(str(item) for item in years) if years else 'ninguno'}.", f"- Meses disponibles: {', '.join(months) if months else 'ninguno'}.", f"- Rango de fechas: {min_date.isoformat() if min_date else 'sin fecha válida'} a {max_date.isoformat() if max_date else 'sin fecha válida'}.", f"- Fecha máxima: {max_date.isoformat() if max_date else 'sin fecha válida'}; días desde último dato: {age if max_date else 'sin fecha válida'}.", f"- Precios válidos: {len(all_prices)}; faltantes: {missing_price}; cero: {zero_price}; negativos: {negative_price}.", f"- Monedas especificadas: {coverage_count(rows, 'moneda')}/{len(rows)}; sin especificar: {len(rows) - coverage_count(rows, 'moneda')}.", f"- Unidades de precio especificadas: {coverage_count(rows, 'unidad')}/{len(rows)}; sin especificar: {len(rows) - coverage_count(rows, 'unidad')}.", f"- Unidades de volumen especificadas: {volume_unit_count}/{len(rows)}; sin especificar: {len(rows) - volume_unit_count}.", f"- Campos originales de precio: {', '.join(price_field_values) or 'ninguno'}; campos originales de volumen: {', '.join(volume_field_values) or 'ninguno'}.", f"- Precio unitario con dato: {price_unit_count}; precio total con dato: {price_total_count}; inconsistencias detectadas: {inconsistent_price}.", f"- Volumen con dato numérico: {volume_valid}; procedencia con dato: {coverage_count(rows, 'procedencia')}; lugar de entrega (zona) con dato: {coverage_count(rows, 'zona')}; condición de pago con dato: {coverage_count(rows, 'condicion_pago')}.", f"- apto_piloto: {'sí' if pilot_eligible_count == len(rows) else 'no'} ({pilot_eligible_count}/{len(rows)} filas).", f"- apto_dashboard: {'sí' if dashboard_eligible_count == len(rows) else 'no'} ({dashboard_eligible_count}/{len(rows)} filas).", f"- Series utilizables para dashboard analítico futuro: {usable_count} de {len(series)}.", "",
    ]
    if warnings:
        lines.extend(["## Advertencias", "", *[f"- {warning}" for warning in warnings], ""])
    lines.extend(["## Moneda y comparabilidad", "", f"Moneda explícitamente informada: {'sí' if currency_explicit_count else 'no'} ({currency_explicit_count}/{len(rows)} filas). Moneda inferida: {'sí' if currency_inferred_count else 'no'} ({currency_inferred_count}/{len(rows)} filas). Moneda sin especificar: {'sí' if currency_unspecified_count else 'no'} ({currency_unspecified_count}/{len(rows)} filas).", f"Comparabilidad monetaria: {'sí' if currency_explicit_count and len(currency_counts) == 1 and not currency_inferred_count and not currency_unspecified_count else 'no'}.", "Los valores no deben compararse ni usarse para variaciones monetarias mientras la moneda permanezca embebida o no informada explícitamente. La auditoría conserva `moneda=Sin especificar` y no habilita `apto_dashboard`.", ""])
    lines.extend([
        "## Actualidad de la información", "", f"Fecha máxima disponible: {max_date.isoformat() if max_date else 'sin fecha válida'}.", f"Días desde el último dato: {age if age is not None else 'sin fecha válida'}.", f"Commodities actualizados (últimos 7 días): {', '.join(updated) if updated else 'ninguno'}.", f"Commodities recientes o actualizados (últimos 30 días): {', '.join(recent) if recent else 'ninguno'}.", f"Commodities sin dato reciente: {', '.join(no_recent) if no_recent else 'ninguno'}.", f"Cobertura últimos 7 días: {sum(int(item['registros_ultimos_7_dias']) for item in actuality)} registro(s). Cobertura últimos 30 días: {sum(int(item['registros_ultimos_30_dias']) for item in actuality)} registro(s).", "", markdown_table(["Commodity", "Fecha máxima", "Días", "Últimos 7 días", "Últimos 30 días", "Estado"], [[item["commodity"], item["fecha_max"] or "—", item["dias_desde_ultimo_dato"] or "—", item["registros_ultimos_7_dias"], item["registros_ultimos_30_dias"], item["estado_actualidad"]] for item in actuality]), "",
        "## Recomendación de automatización", "", "SIO Granos debe mantenerse como exploración separada hasta validar la procedencia, la definición del precio, los permisos de uso, la estabilidad de la consulta pública y la homogeneidad de moneda, unidad, frecuencia y tipo de precio.", "Si hay datos recientes y la consulta/exportación pública es estable, conviene automatizar con ventanas de hasta 180 días y auditoría previa. Si no hay exportación estable, mantener la descarga manual en raw/ y conservar la respuesta original.", "No publicar en el dashboard ni mezclar con BCR o frutas/hortalizas antes de esa validación.", "", "## Series y aptitud analítica", "", markdown_table(["Commodity", "Moneda", "Unidad", "Tipo", "Frecuencia", "Apto piloto", "Apto dashboard", "Calidad", "Aptitud analítica"], [[item["commodity"], item["moneda"], item["unidad"], item["tipo_precio"], item["frecuencia"], item["apto_piloto"], item["apto_dashboard"], item["calidad_serie"], item["aptitud_dashboard_analitico"]] for item in series]), "", f"Casos problemáticos: {len(problems)}. Ver CASOS_PROBLEMATICOS_COMMODITIES_SIO.csv.", "", "## Próximos pasos", "", "Validar una respuesta real de SIO y revisar especialmente fecha, condición de pago, operación, volumen, procedencia, precio puesto en, unidad, moneda y permisos. No inventar datos ni usar fuentes alternativas como equivalentes de SIO/BCR sin evidencia.",
    ])
    report_text = "\n".join(lines) + "\n"
    dashboard_summary = f"- apto_dashboard pleno: {'sí' if dashboard_full_count == len(rows) else 'no'} ({dashboard_full_count}/{len(rows)} filas); estado piloto: {'parcial_piloto' if dashboard_partial_count else 'no'} ({dashboard_partial_count}/{len(rows)} filas)."
    report_text = re.sub(r"- apto_dashboard: [^\n]*", dashboard_summary, report_text, count=1)
    report_text = report_text.replace("Los valores no deben compararse ni usarse para variaciones monetarias mientras la moneda permanezca embebida o no informada explícitamente. La auditoría conserva `moneda=Sin especificar` y no habilita `apto_dashboard`.", "Los precios sólo deben compararse dentro de una misma moneda; en esta muestra hay ARS y USD explícitos, por lo que no corresponde calcular variaciones monetarias conjuntas. El estado queda como `parcial_piloto` y no como `si` pleno.")
    embedded_section = "## Moneda embebida en campo de precio\n\n`Row[10]` contiene el campo original de precio. El símbolo monetario se extrae sólo si aparece explícitamente: `U$S`/`US$`/`USD` se normaliza a `USD`, y `$` sin esos marcadores se normaliza a `ARS`. No se infiere moneda por contexto y se conserva `precio_original_texto`."
    report_text = report_text.replace("## Moneda y comparabilidad", embedded_section + "\n\n## Moneda y comparabilidad", 1)
    REPORTS["report"].write_text(report_text, encoding="utf-8")
    update_paginated_audit_report(rows)
    print(f"Auditoría SIO finalizada: {len(rows)} filas, {len(commodities)} commodity(s).")
    print(f"Fecha máxima: {max_date.isoformat() if max_date else 'sin fecha válida'}; precios válidos: {len(all_prices)}; faltantes: {missing_price}.")
    for path in REPORTS.values():
        print(f"Reporte: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
