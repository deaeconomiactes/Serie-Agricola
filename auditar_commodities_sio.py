#!/usr/bin/env python3
"""Audita calidad, cobertura y actualidad de datos integrados de SIO Granos."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from contextlib import nullcontext
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median


csv.field_size_limit(2**31 - 1)


ROOT = Path(__file__).resolve().parent
PROCESSED_PATH = ROOT / "data" / "commodities_sio" / "processed" / "COMMODITIES_SIO_INTEGRADO.csv"
LATEST_SNAPSHOT_PATH = ROOT / "data" / "commodities_sio" / "processed" / "COMMODITIES_SIO_LATEST_SNAPSHOT.csv"
HISTORIC_SNAPSHOTS_PATH = ROOT / "data" / "commodities_sio" / "processed" / "COMMODITIES_SIO_HISTORICO_SNAPSHOTS.csv"
LIGHT_HISTORY_PATH = ROOT / "data" / "commodities_sio" / "dashboard" / "COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv"
PAGINATED_PROCESSED_PATH = ROOT / "data" / "commodities_sio" / "processed" / "COMMODITIES_SIO_MUESTRA_PAGINADA.csv"
MANUAL_EXPORT_PROCESSED_PATH = ROOT / "data" / "commodities_sio" / "processed" / "COMMODITIES_SIO_EXPORTACION_MANUAL.csv"
MANUAL_EXPORT_SAMPLE_PATH = ROOT / "data" / "commodities_sio" / "processed" / "COMMODITIES_SIO_EXPORTACION_MANUAL_SAMPLE.csv"
RAW_DIR = ROOT / "data" / "commodities_sio" / "raw"
REPORT_DIR = ROOT / "data" / "commodities_sio" / "reports"
MANUAL_EXPORT_REPORT_PATH = REPORT_DIR / "REPORTE_EXPORTACION_MANUAL_SIO.md"
MANUAL_EXPORT_SUMMARY_PATH = REPORT_DIR / "RESUMEN_EXPORTACION_MANUAL_SIO.csv"
MANUAL_EXPORT_ZERO_PATH = REPORT_DIR / "RESUMEN_PRECIOS_CERO_SIO.csv"
MANUAL_EXPORT_COMMODITY_CURRENCY_PATH = REPORT_DIR / "RESUMEN_COMMODITY_MONEDA_SIO.csv"
ZERO_CASES_PATH = REPORT_DIR / "CASOS_PRECIOS_CERO_SIO.csv"
ZERO_REPORT_PATH = REPORT_DIR / "REPORTE_PRECIOS_CERO_SIO.md"
ANALYTIC_PATH = ROOT / "data" / "commodities_sio" / "processed" / "COMMODITIES_SIO_ANALITICO_PRECIOS.csv"
ANALYTIC_SAMPLE_PATH = ROOT / "data" / "commodities_sio" / "processed" / "COMMODITIES_SIO_ANALITICO_PRECIOS_SAMPLE.csv"
ANALYTIC_SUMMARY_PATH = REPORT_DIR / "RESUMEN_ANALITICO_PRECIOS_SIO.csv"
ANALYTIC_COMMODITY_CURRENCY_PATH = REPORT_DIR / "RESUMEN_ANALITICO_COMMODITY_MONEDA_SIO.csv"
ANALYTIC_SERIES_PATH = REPORT_DIR / "RESUMEN_ANALITICO_SERIES_SIO.csv"
ANALYTIC_PROCEDENCIA_PATH = REPORT_DIR / "RESUMEN_ANALITICO_PROCEDENCIA_SIO.csv"
ANALYTIC_DELIVERY_PATH = REPORT_DIR / "RESUMEN_ANALITICO_LUGAR_ENTREGA_SIO.csv"
ANALYTIC_REPORT_PATH = REPORT_DIR / "REPORTE_BASE_ANALITICA_PRECIOS_SIO.md"
PAGINATED_REPORT_PATH = REPORT_DIR / "REPORTE_MUESTRA_PAGINADA_SIO.md"
PAGINATION_REPORT_PATH = REPORT_DIR / "REPORTE_PAGINACION_SIO.md"
DAILY_UPDATE_REPORT_PATH = REPORT_DIR / "REPORTE_ACTUALIZACION_DIARIA_SIO.md"
REPORTS = {
    "report": REPORT_DIR / "REPORTE_AUDITORIA_COMMODITIES_SIO.md",
    "coverage": REPORT_DIR / "RESUMEN_COBERTURA_COMMODITIES_SIO.csv",
    "commodities": REPORT_DIR / "RESUMEN_COMMODITIES_SIO.csv",
    "series": REPORT_DIR / "RESUMEN_SERIES_COMMODITIES_SIO.csv",
    "problems": REPORT_DIR / "CASOS_PROBLEMATICOS_COMMODITIES_SIO.csv",
    "actuality": REPORT_DIR / "RESUMEN_ACTUALIDAD_COMMODITIES_SIO.csv",
}


def snapshot_identity(row: dict[str, str]) -> tuple[str, ...]:
    operation_id = value(row, "id_operacion_sio")
    if operation_id:
        return ("id", operation_id)
    return (
        "fallback",
        value(row, "fecha"),
        value(row, "commodity"),
        value(row, "precio_original_texto"),
        value(row, "volumen"),
        value(row, "procedencia"),
        value(row, "lugar_entrega"),
        value(row, "condicion_comercial"),
    )


def snapshot_capture_value(row: dict[str, str]) -> str:
    return value(row, "fecha_descarga_snapshot")


def snapshot_raw_files() -> list[Path]:
    if not RAW_DIR.exists():
        return []
    return sorted(RAW_DIR.glob("SIO_latest_GetOperaciones_*.json"))


def write_daily_update_report() -> None:
    latest_rows = read_rows(LATEST_SNAPSHOT_PATH)
    history_path = HISTORIC_SNAPSHOTS_PATH if HISTORIC_SNAPSHOTS_PATH.exists() else LIGHT_HISTORY_PATH
    history_rows = read_rows(history_path)
    raw_files = snapshot_raw_files()
    latest_capture = max((snapshot_capture_value(row) for row in latest_rows if snapshot_capture_value(row)), default="")
    if not latest_capture and raw_files:
        match = re.search(r"_(\d{8})_(\d{6})\.json$", raw_files[-1].name, flags=re.I)
        if match:
            try:
                latest_capture = datetime.strptime(f"{match.group(1)}{match.group(2)}", "%Y%m%d%H%M%S").isoformat(timespec="seconds")
            except ValueError:
                latest_capture = ""
    previous_rows = [row for row in history_rows if snapshot_capture_value(row) and snapshot_capture_value(row) < latest_capture]
    latest_keys = {snapshot_identity(row) for row in latest_rows}
    previous_keys = {snapshot_identity(row) for row in previous_rows}
    new_count = len(latest_keys - previous_keys) if previous_rows else len(latest_keys)
    duplicate_count = len(latest_keys & previous_keys) if previous_rows else 0
    dates = [parsed for parsed in (parse_date(value(row, "fecha")) for row in history_rows) if parsed]
    currencies = sorted({value(row, "moneda") for row in latest_rows if value(row, "moneda") and value(row, "moneda") != "Sin especificar"})
    commodities = sorted({value(row, "commodity") for row in latest_rows if value(row, "commodity") and value(row, "commodity") != "Sin especificar"})
    positive_prices = sum(1 for row in latest_rows if (parse_price(value(row, "precio")) or 0) > 0)
    zero_prices = sum(1 for row in latest_rows if parse_price(value(row, "precio")) == 0)
    dashboard_ready = sum(1 for row in latest_rows if parse_price(value(row, "precio")) is not None and parse_price(value(row, "precio")) > 0 and parse_date(value(row, "fecha")) and value(row, "commodity") not in {"", "Sin especificar"} and value(row, "moneda") not in {"", "Sin especificar"} and value(row, "unidad") not in {"", "Sin especificar"})
    source_file = latest_rows[0].get("archivo_origen", "") if latest_rows else (raw_files[-1].name if raw_files else "")
    lines = [
        "# Reporte de actualización diaria SIO", "", "## Objetivo", "",
        "Controlar la captura incremental de snapshots de últimas operaciones SIO. Esta actualización no representa un histórico completo.", "",
        "## Última corrida", "",
        f"- Fecha/hora de captura: {latest_capture or 'sin captura registrada'}.",
        f"- Archivo raw usado: `{source_file or 'no disponible'}`.",
        f"- Histórico persistente usado: `{history_path.relative_to(ROOT).as_posix()}`.",
        f"- Histórico liviano versionable: `{LIGHT_HISTORY_PATH.relative_to(ROOT).as_posix()}`.",
        f"- Operaciones latest válidas: {len(latest_rows)}.",
        f"- Operaciones nuevas respecto de capturas anteriores: {new_count}.",
        f"- Duplicados omitidos respecto de capturas anteriores: {duplicate_count}.",
        f"- Filas acumuladas: {len(history_rows)}.",
        f"- Fecha mínima de operaciones acumuladas: {min(dates).isoformat() if dates else 'sin fecha válida'}.",
        f"- Fecha máxima de operaciones acumuladas: {max(dates).isoformat() if dates else 'sin fecha válida'}.",
        f"- Monedas latest: {', '.join(currencies) or 'sin especificar'}.",
        f"- Commodities latest: {', '.join(commodities) or 'sin especificar'}.",
        f"- Precios válidos positivos latest: {positive_prices}.",
        f"- Precios cero latest: {zero_prices}.",
        f"- Filas aptas para dashboard por fecha, commodity, moneda, unidad y precio positivo: {dashboard_ready}/{len(latest_rows)}.",
        "- Estado: apto para regenerar agregados livianos sólo dentro de las series con metadatos homogéneos.", "",
        "## Limitaciones", "",
        "- El snapshot contiene sólo las últimas operaciones devueltas por `GetOperaciones`; no es histórico completo.",
        "- La cobertura depende de la frecuencia de ejecución.",
        "- Si el proceso no corre un día, puede perder operaciones que ya no estén presentes en el snapshot siguiente.",
        "- No se pagina ni se prueban variantes del endpoint.",
        "- SIO no reemplaza BCR ni el histórico local mensual de precios internos.",
        "- Los precios cero se conservan para trazabilidad, pero no son válidos para series, promedios, rankings ni semáforos.", "",
        "## Recomendación", "",
        "- Ejecutar como mínimo una vez por día durante el piloto.",
        "- Si se busca mayor cobertura intradiaria, ejecutar cada 3 o 6 horas.",
        "- Mantener monitoreo de duplicados, cambios de estructura, moneda, unidad y fecha.",
        "- Conservar los raw localmente y versionar sólo scripts, reportes y agregados livianos.", "",
    ]
    DAILY_UPDATE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DAILY_UPDATE_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


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


def read_rows(path: Path = PROCESSED_PATH) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
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


def actuality_for_rows(rows: list[dict[str, str]], source_file: str, today: date) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    commodities = sorted({value(row, "commodity") or "Sin especificar" for row in rows})
    for commodity in commodities:
        dates = [item for item in (parse_date(value(row, "fecha")) for row in rows if (value(row, "commodity") or "Sin especificar") == commodity) if item]
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
        result.append({"fuente_archivo": source_file, "commodity": commodity, "fecha_max": max_date.isoformat() if max_date else "", "dias_desde_ultimo_dato": str(age) if max_date else "", "registros_ultimos_7_dias": str(count_7), "registros_ultimos_30_dias": str(count_30), "estado_actualidad": status})
    return result


def export_summary(stats: dict[str, object]) -> str:
    if not stats.get("rows"):
        return "## Exportación manual\n\nNo existe una exportación manual procesada para auditar.\n"
    rows = int(stats["rows"])
    dates = stats["dates"]
    currencies = stats["currencies"]
    units = stats["units"]
    commodities = stats["commodities"]
    return "\n".join([
        "## Exportación manual", "", "La exportación manual es una tercera salida separada y no reemplaza `COMMODITIES_SIO_INTEGRADO.csv` ni la muestra paginada.",
        f"- Filas: {rows}.", f"- Rango de fechas: {min(dates).isoformat() if dates else 'sin fecha válida'} a {max(dates).isoformat() if dates else 'sin fecha válida'}.",
        f"- Monedas: {', '.join(currencies) or 'sin especificar'}; unidades: {', '.join(units) or 'sin especificar'}.",
        f"- Productos: {', '.join(commodities)}.", f"- Duplicados por ID: {stats['duplicate_ids']}.",
        f"- Aptitud piloto: {stats['pilot_count']}/{rows}; aptitud dashboard: {stats['dashboard_count']}/{rows}.",
        "- Diferencia frente a GetOperaciones: proviene de un archivo descargado manualmente; requiere validar columnas, moneda, unidad, cobertura y licencia antes de cualquier automatización o publicación.", "",
    ])


def write_manual_export_report(stats: dict[str, object]) -> None:
    if not stats.get("rows"):
        return
    columns = [str(item) for item in stats.get("source_columns", [])]
    mapped = [
        (["FECHA OPERACION", "FECHA CONCERTACION"], "fecha", "fecha de operación/concertación observada", "alta", "se conserva la fecha normalizada"),
        (["PRODUCTO"], "commodity", "producto de la exportación", "alta", "se normaliza contra el catálogo SIO"),
        (["PRECIO/TN MONTO"], "precio", "precio original", "alta", "se conserva precio_original_texto"),
        (["PRECIO/TN MONEDA"], "moneda", "campo monetario explícito", "alta", "no se infiere por contexto"),
        (["CANT. (TN)"], "volumen", "cantidad explícita en toneladas", "alta", "se conserva volumen_unidad=TN"),
        (["PROCEDENCIA PCIA", "PROCEDENCIA LOCALID."], "procedencia", "procedencia de la operación", "alta", "se combinan los campos de procedencia disponibles"),
        (["LUGAR ENTREGA"], "lugar_entrega", "lugar de entrega", "alta", "se conserva como lugar_entrega"),
        (["CONDICION PAGO"], "condicion_pago", "condición de pago", "alta", "se conserva si tiene dato"),
    ]
    mapping_rows: list[str] = []
    used: set[str] = set()
    for originals, destination, evidence, confidence, notes in mapped:
        matches = [column for column in columns if any(re.sub(r"[^a-z0-9]", "", column.lower()) == re.sub(r"[^a-z0-9]", "", original.lower()) for original in originals)]
        original_display = " / ".join(matches) if matches else " / ".join(originals)
        if matches: used.update(matches)
        mapping_rows.append(f"| {original_display} | {destination} | {evidence} | {confidence} | {notes} |")
    unused = [column for column in columns if column not in used]
    valid_prices = int(stats["valid_prices"])
    rows = int(stats["rows"])
    currency_explicit = bool(stats["currencies"])
    unit_explicit = bool(stats["units"])
    decision = "A. Exportación manual apta como fuente piloto." if rows and valid_prices / rows >= 0.95 and currency_explicit and unit_explicit and not stats["zero_prices"] else "B. Exportación manual parcialmente apta; requiere ajustes."
    source_name = str(stats.get("source_name", "SIO_exportar_operaciones_*.csv/.xls/.xlsx"))
    lines = [
        "# Reporte de exportación manual SIO", "", "## Objetivo", "", "Validar si el archivo descargado desde Exportar Operaciones permite construir una base tabular más completa que el endpoint GetOperaciones.", "", "## Archivo procesado", "", f"- Nombre: `{source_name}`.", "- Tipo: exportación manual tabular.", f"- Filas: {rows}.", f"- Columnas: {len(columns)}.", f"- Fecha de integración: {date.today().isoformat()}.", "", "## Columnas originales detectadas", "", *[f"- `{column}`" for column in columns], "", "## Mapeo aplicado", "", "| Columna original | Campo destino | Evidencia | Confianza | Observaciones |", "| --- | --- | --- | --- | --- |", *mapping_rows, "", "## Resultado de integración", "", f"- Filas generadas: {rows}.", "- Columnas generadas: esquema normalizado estándar de SIO.", f"- Campos faltantes: {', '.join(field for field, count in [('precio', valid_prices), ('moneda', len(stats['currencies'])), ('unidad', len(stats['units']))] if count == 0) or 'ninguno de los campos principales'}.", f"- Campos originales no utilizados o conservados sólo como evidencia: {', '.join(unused) or 'ninguno'}.", "- Advertencia: la salida normalizada conserva los campos analíticos definidos; las columnas originales no mapeadas quedan registradas en este reporte y no se descartan silenciosamente como evidencia.", "", "## Resultado de auditoría", "", f"- Commodities: {', '.join(stats['commodities']) or 'ninguno'}.", f"- Fechas: {min(stats['dates']).isoformat() if stats['dates'] else 'sin fecha'} a {max(stats['dates']).isoformat() if stats['dates'] else 'sin fecha'}.", f"- Monedas: {', '.join(stats['currencies']) or 'sin especificar'}; unidades: {', '.join(stats['units']) or 'sin especificar'}.", f"- Precios válidos: {valid_prices}; faltantes: {stats['missing_prices']}; cero: {stats['zero_prices']}; negativos: {stats['negative_prices']}.", f"- Volumen con dato: {stats['volume_count']}; procedencia: {stats['procedencia_count']}; lugar de entrega: {stats['delivery_count']}; condición de pago: {stats['payment_count']}.", f"- Duplicados por ID: {stats['duplicate_ids']}.", f"- Aptitud piloto: {stats['pilot_count']}/{rows}; aptitud dashboard: {stats['dashboard_count']}/{rows}.", "", "## Comparación con endpoint GetOperaciones", "", "- La exportación manual debe compararse por cantidad de filas, columnas y cobertura, no sólo por una respuesta puntual del endpoint.", f"- Trae más filas que la muestra piloto de GetOperaciones de 15 filas: {'sí' if rows > 15 else 'no'}.", f"- Trae moneda explícita: {'sí' if currency_explicit else 'no'}; unidad explícita: {'sí' if unit_explicit else 'no'}.", "- La exportación manual no valida `pCurrentPage`; evita el problema operativo de la paginación del endpoint sólo como descarga manual.", "", "## Decisión metodológica", "", decision, "", "## Recomendación próxima", "", "Mantener un flujo documentado de descarga manual recurrente si se confirma la procedencia, licencia, cobertura y estabilidad del archivo. Definir periodicidad, conservar raw fuera de Git y versionar sólo processed/reportes controlados. No integrar al dashboard todavía.", ""]
    MANUAL_EXPORT_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def manual_export_stats(path: Path) -> dict[str, object]:
    stats: dict[str, object] = {"rows": 0, "columns": [], "dates": [], "currencies": set(), "units": set(), "commodities": set(), "duplicate_ids": 0, "pilot_count": 0, "dashboard_count": 0, "valid_prices": 0, "missing_prices": 0, "zero_prices": 0, "negative_prices": 0, "volume_count": 0, "procedencia_count": 0, "delivery_count": 0, "payment_count": 0}
    ids: Counter[str] = Counter()
    commodity_dates: dict[str, list[date]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        stats["columns"] = list(reader.fieldnames or [])
        for row in reader:
            stats["rows"] = int(stats["rows"]) + 1
            parsed_date = parse_date(value(row, "fecha"))
            if parsed_date:
                stats["dates"].append(parsed_date)
                commodity_dates.setdefault(value(row, "commodity") or "Sin especificar", []).append(parsed_date)
            commodity = value(row, "commodity") or "Sin especificar"
            stats["commodities"].add(commodity)
            currency = value(row, "moneda")
            unit = value(row, "unidad")
            if currency and currency != "Sin especificar": stats["currencies"].add(currency)
            if unit and unit != "Sin especificar": stats["units"].add(unit)
            price = parse_price(value(row, "precio"))
            if price is None: stats["missing_prices"] += 1
            else:
                stats["valid_prices"] += 1
                stats["zero_prices"] += int(price == 0)
                stats["negative_prices"] += int(price < 0)
            stats["volume_count"] += int(parse_price(value(row, "volumen")) is not None)
            stats["procedencia_count"] += int(bool(value(row, "procedencia")))
            stats["delivery_count"] += int(bool(value(row, "lugar_entrega")))
            stats["payment_count"] += int(bool(value(row, "condicion_pago")))
            operation_id = value(row, "id_operacion_sio")
            if operation_id: ids[operation_id] += 1
            stats["pilot_count"] += int(value(row, "apto_piloto").lower() in {"sí", "si"})
            stats["dashboard_count"] += int(value(row, "apto_dashboard").lower() == "si")
    stats["dates"] = sorted(stats["dates"])
    stats["currencies"] = sorted(stats["currencies"])
    stats["units"] = sorted(stats["units"])
    stats["commodities"] = sorted(stats["commodities"])
    stats["duplicate_ids"] = sum(count - 1 for count in ids.values() if count > 1)
    stats["commodity_dates"] = commodity_dates
    raw_candidates = sorted((ROOT / "data" / "commodities_sio" / "raw").glob("SIO_exportar_operaciones_*.csv"))
    if raw_candidates:
        raw_path = raw_candidates[-1]
        prefix = raw_path.read_bytes()[:4]
        encoding = "utf-16-le" if len(prefix) >= 2 and prefix[1] == 0 else "utf-16-be" if len(prefix) >= 2 and prefix[0] == 0 else "utf-8-sig"
        with raw_path.open("r", encoding=encoding, errors="replace", newline="") as raw_handle:
            stats["source_name"] = raw_path.name
            stats["source_columns"] = [column for column in csv.reader(raw_handle, delimiter=";").__next__() if column.strip()]
    else:
        stats["source_name"] = "SIO_exportar_operaciones_*.xlsx/.xls/.csv"
        stats["source_columns"] = []
    return stats


ZERO_CASE_FIELDS = [
    "fecha", "commodity", "operacion", "tipo_precio", "moneda", "unidad", "precio", "precio_original_texto",
    "campo_precio_original", "volumen", "volumen_unidad", "procedencia", "lugar_entrega", "condicion_comercial",
    "precio_cero_tipo", "observaciones", "archivo_origen",
]


def classify_zero_row(row: dict[str, str]) -> str:
    existing = value(row, "precio_cero_tipo")
    if existing:
        return existing
    raw = value(row, "precio_original_texto")
    normalized = re.sub(r"[^a-z0-9]", "", raw.lower())
    operation = re.sub(r"[^a-z0-9]", "", value(row, "operacion").lower())
    if not raw:
        return "campo_vacio_parseado_cero"
    if normalized in {"sc", "sincotizacion", "sinprecio", "afijar", "fijar"} or any(token in normalized for token in ("sincot", "sinprecio", "afijar")):
        return "texto_sin_precio"
    if any(token in operation for token in ("anulacion", "rectificacion")) and normalized in {"0", "00", "000"}:
        return "operacion_sin_precio"
    if re.sub(r"[^0-9]", "", raw) and set(re.sub(r"[^0-9]", "", raw)) == {"0"}:
        return "cero_explicito"
    return "parsing_fallido" if raw else "no_determinado"


def write_zero_audit(path: Path) -> dict[str, object]:
    metrics: dict[str, object] = {"total": 0, "positive": 0, "zero": 0, "missing": 0, "zero_pct": 0.0, "types": Counter(), "dimensions": {}, "originals": Counter()}
    dimension_names = ["commodity", "moneda", "tipo_precio", "operacion", "condicion_pago", "procedencia", "lugar_entrega", "año", "mes", "archivo_origen"]
    dimensions = {name: Counter() for name in dimension_names}
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("r", encoding="utf-8-sig", newline="") as handle, ZERO_CASES_PATH.open("w", encoding="utf-8-sig", newline="") as cases_handle:
        reader = csv.DictReader(handle, delimiter=";")
        writer = csv.DictWriter(cases_handle, fieldnames=ZERO_CASE_FIELDS, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            metrics["total"] += 1
            parsed_price = parse_price(value(row, "precio"))
            if parsed_price is None:
                metrics["missing"] += 1
                continue
            if parsed_price > 0:
                metrics["positive"] += 1
                continue
            if parsed_price != 0:
                continue
            metrics["zero"] += 1
            zero_type = classify_zero_row(row)
            metrics["types"][zero_type] += 1
            raw_original = value(row, "precio_original_texto")
            if not raw_original:
                metrics["originals"]["precio_original_texto vacío"] += 1
            elif re.sub(r"[^0-9]", "", raw_original) and set(re.sub(r"[^0-9]", "", raw_original)) == {"0"}:
                metrics["originals"]["precio_original_texto dice cero"] += 1
            elif zero_type == "texto_sin_precio":
                metrics["originals"]["texto sin precio"] += 1
            else:
                metrics["originals"]["otro valor original"] += 1
            parsed_date = parse_date(value(row, "fecha"))
            row["precio_cero_tipo"] = zero_type
            for name in dimension_names:
                if name == "año":
                    label = str(parsed_date.year) if parsed_date else "Sin fecha"
                elif name == "mes":
                    label = parsed_date.strftime("%Y-%m") if parsed_date else "Sin fecha"
                elif name == "condicion_pago":
                    label = value(row, "condicion_pago") or "Sin especificar"
                else:
                    label = value(row, name) or "Sin especificar"
                dimensions[name][label] += 1
            writer.writerow({field: row.get(field, "") for field in ZERO_CASE_FIELDS})
    metrics["zero_pct"] = (metrics["zero"] / metrics["total"] * 100) if metrics["total"] else 0.0
    metrics["dimensions"] = dimensions
    write_zero_report(metrics)
    return metrics


def markdown_counter(title: str, counter: Counter[str]) -> list[str]:
    lines = [f"### {title}", "", "| Valor | Registros |", "| --- | ---: |"]
    lines.extend(f"| {name.replace('|', '/')} | {count} |" for name, count in counter.most_common())
    return lines + [""]


def write_zero_report(metrics: dict[str, object]) -> None:
    total = int(metrics["total"])
    zero = int(metrics["zero"])
    positive = int(metrics["positive"])
    missing = int(metrics["missing"])
    zero_pct = float(metrics["zero_pct"])
    decision = "Conservar los registros en la base completa, pero excluir precio=0 de toda serie, promedio, ranking y semáforo. No imputar ni reemplazar el valor original."
    lines = [
        "# Reporte de precios cero SIO", "", "## Objetivo", "", "Auditar precios cero en la exportación manual SIO antes de usar la base para análisis o dashboard.", "", "## Resumen ejecutivo", "", f"- Filas totales: {total}.", f"- Precios positivos: {positive}.", f"- Precios cero: {zero} ({zero_pct:.2f}%).", f"- Precios faltantes: {missing}.", f"- Decisión metodológica: {decision}", "", "## Distribución de precios cero", "",
    ]
    for name, counter in metrics["dimensions"].items():
        lines.extend(markdown_counter(name, counter))
    lines.extend(markdown_counter("precio_cero_tipo", metrics["types"]))
    """
    lines.extend(["## Origen probable de los ceros", "", f"- `precio_original_texto`: {', '.join(f'{name}={count}' for name, count in metrics['originals'].most_common()) or 'sin evidencia'}.", "- La clasificación se basa en el valor original y en el campo operación; no afirma que un cero sea económicamente válido sin documentación adicional.", "- Los ceros actuales observados en esta exportación están respaldados por texto original numérico `0`/`0,00`; los casos de texto sin precio, vacío o parsing fallido quedan contemplados para futuras exportaciones.", "", "## Regla propuesta", "", "- Conservar registros y valor original para trazabilidad.", "- Excluir `precio=0` de promedios, evolución, rankings y semáforos.", "- Mantenerlos visibles sólo en auditoría/calidad.", "- No imputar precio ni convertir cero en missing sin conservar el valor original.", "- Usar `precio_valido_para_serie=sí` como filtro analítico.", "", "## Impacto en dashboard", "", "No debe graficarse precio cero como precio de mercado. Los indicadores deben usar sólo `precio_valido_para_serie=sí` y mostrar una nota metodológica si SIO se integra en el futuro.", "", "## Casos problemáticos", "", "Se generó `data/commodities_sio/reports/CASOS_PRECIOS_CERO_SIO.csv` con todos los registros con precio cero y su clasificación.", ""]
    """
    original_summary = ", ".join("{}={}".format(name, count) for name, count in metrics["originals"].most_common()) or "sin evidencia"
    lines.extend([
        "## Origen probable de los ceros", "", f"- `precio_original_texto`: {original_summary}.",
        "- La clasificación se basa en el valor original y en el campo operación; no afirma que un cero sea económicamente válido sin documentación adicional.",
        "- Los ceros actuales observados están respaldados por texto original numérico `0`/`0,00`; las categorías de texto sin precio, vacío o parsing fallido quedan contempladas para futuras exportaciones.",
        "", "## Regla propuesta", "", "- Conservar registros y valor original para trazabilidad.",
        "- Excluir `precio=0` de promedios, evolución, rankings y semáforos.", "- Mantenerlos visibles sólo en auditoría/calidad.",
        "- No imputar precio ni convertir cero en missing sin conservar el valor original.", "- Usar `precio_valido_para_serie=sí` como filtro analítico.",
        "", "## Impacto en dashboard", "", "No debe graficarse precio cero como precio de mercado. Los indicadores deben usar sólo `precio_valido_para_serie=sí` y mostrar una nota metodológica si SIO se integra en el futuro.",
        "", "## Casos problemáticos", "", "Se generó `data/commodities_sio/reports/CASOS_PRECIOS_CERO_SIO.csv` con todos los registros con precio cero y su clasificación.", "",
    ])
    ZERO_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


ANALYTIC_SAMPLE_LIMIT = 1000
ANALYTIC_VERSIONABLE_LIMIT_BYTES = 100 * 1024 * 1024


def is_yes(value_text: str) -> bool:
    return value_text.strip().lower() in {"sí", "si", "true", "1"}


def analytical_eligibility(row: dict[str, str]) -> tuple[bool, list[str], float | None, date | None]:
    parsed_price = parse_price(value(row, "precio"))
    parsed_date = parse_date(value(row, "fecha"))
    reasons: list[str] = []
    if not is_yes(value(row, "precio_valido_para_serie")):
        reasons.append("precio_valido_para_serie_no")
    if parsed_price is None:
        reasons.append("precio_faltante_o_invalido")
    elif parsed_price <= 0:
        reasons.append("precio_no_positivo")
    if is_yes(value(row, "precio_cero_flag")) or parsed_price == 0:
        reasons.append("precio_cero")
    if parsed_date is None:
        reasons.append("fecha_invalida_o_faltante")
    if not value(row, "commodity") or value(row, "commodity") == "Sin especificar":
        reasons.append("commodity_vacio_o_sin_especificar")
    currency = value(row, "moneda")
    currency_explicit = is_yes(value(row, "moneda_explicitamente_informada"))
    if not currency_explicit or not currency or currency == "Sin especificar":
        reasons.append("moneda_no_explicita")
    if not value(row, "unidad") or value(row, "unidad") == "Sin especificar":
        reasons.append("unidad_no_explicita")
    if not value(row, "fuente"):
        reasons.append("fuente_vacia")
    return not reasons, reasons, parsed_price, parsed_date


def analytic_group(store: dict[tuple[str, ...], dict[str, object]], key_value: tuple[str, ...], row: dict[str, str], parsed_price: float, parsed_date: date) -> None:
    item = store.setdefault(key_value, {"filas": 0, "precios": [], "fechas": set(), "volumen_total": 0.0})
    item["filas"] += 1
    item["precios"].append(parsed_price)
    item["fechas"].add(parsed_date)
    volume = parse_price(value(row, "volumen"))
    if volume is not None:
        item["volumen_total"] += volume


def format_stat(number: float | None) -> str:
    if number is None:
        return ""
    return f"{number:.6f}".rstrip("0").rstrip(".") or "0"


def group_rows(store: dict[tuple[str, ...], dict[str, object]], names: list[str], include_volume: bool = False, series: bool = False) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for key_value, item in sorted(store.items()):
        prices = item["precios"]
        dates = sorted(item["fechas"])
        row = {name: str(part) for name, part in zip(names, key_value)}
        row.update({
            "filas": str(item["filas"]),
            "fecha_min": dates[0].isoformat() if dates else "",
            "fecha_max": dates[-1].isoformat() if dates else "",
        })
        if series:
            row["dias_con_datos"] = str(len(dates))
            row["aptitud_serie"] = "Apta" if len(dates) >= 2 else "Insuficiente cobertura temporal"
        else:
            row.update({
                "precio_min": format_stat(min(prices) if prices else None),
                "precio_promedio": format_stat(sum(prices) / len(prices) if prices else None),
                "precio_mediana": format_stat(float(median(prices)) if prices else None),
                "precio_max": format_stat(max(prices) if prices else None),
            })
            if include_volume:
                row["volumen_total"] = format_stat(float(item["volumen_total"]))
        result.append(row)
    return result


def write_analytic_report(metrics: dict[str, object]) -> None:
    total = int(metrics["filas_base_completa"])
    analytic = int(metrics["filas_analiticas"])
    excluded = int(metrics["filas_excluidas"])
    usable_pct = float(metrics["porcentaje_usable"])
    full_path = Path(str(metrics["analytic_path"]))
    sample_path = Path(str(metrics["sample_path"]))
    size_bytes = full_path.stat().st_size if full_path.exists() else 0
    size_mb = size_bytes / (1024 * 1024) if size_bytes else 0
    versioning = "no; el archivo supera 100 MB y queda ignorado por Git" if size_bytes > ANALYTIC_VERSIONABLE_LIMIT_BYTES else "posible, sujeto a revisión de tamaño"
    source_kind = "exportación manual completa" if metrics["source_is_complete"] else "base analítica disponible localmente"
    date_min = metrics["fecha_min"] or "sin fecha válida"
    date_max = metrics["fecha_max"] or "sin fecha válida"
    currencies = ", ".join(metrics["monedas"]) or "ninguna"
    units = ", ".join(metrics["unidades"]) or "ninguna"
    commodities = ", ".join(metrics["commodities"]) or "ninguno"
    series_rows = metrics["series_rows"][:20]
    lines = [
        "# Reporte de base analítica de precios SIO", "",
        "## Objetivo", "",
        "Construir una base de precios apta para análisis, separada de la base completa de operaciones. Los registros excluidos permanecen en la base completa y no se imputan.", "",
        "## Fuente", "",
        f"- Archivo completo usado: `{metrics['source_label']}`.",
        f"- Origen: SIO Granos / Secretaría de Agricultura.",
        f"- Filas de la base completa procesada: {total}.",
        f"- Fecha de integración/auditoría: {date.today().isoformat()}.",
        f"- Archivo analítico generado: `{full_path.as_posix()}` ({size_mb:.2f} MB).",
        f"- Versionado: {versioning}.",
        f"- Muestra liviana: `{sample_path.as_posix()}`; máximo {ANALYTIC_SAMPLE_LIMIT} filas.", "",
        "## Regla de inclusión", "",
        "Se incluye una fila sólo si cumple simultáneamente:",
        "- `precio_valido_para_serie=sí`.",
        "- `precio > 0`.",
        "- fecha válida.",
        "- commodity informado y no `Sin especificar`.",
        "- moneda explícita (`moneda_explicitamente_informada=sí`).",
        "- unidad explícita.",
        "- fuente no vacía.", "",
        "## Regla de exclusión", "",
        "Se excluyen de la base analítica los precios cero, faltantes o no positivos; registros con moneda o unidad sin especificar; fechas inválidas; commodities vacíos; fuentes vacías; y cualquier fila marcada como no válida para serie. La base completa conserva todos esos registros para trazabilidad.", "",
        "## Resultados", "",
        f"- Filas analíticas: {analytic}.",
        f"- Filas excluidas: {excluded}.",
        f"- Porcentaje usable: {usable_pct:.2f}%.",
        f"- Precios cero excluidos: {metrics['precios_cero_excluidos']}.",
        f"- Commodities: {commodities}.",
        f"- Monedas: {currencies}.",
        f"- Unidades: {units}.",
        f"- Rango de fechas: {date_min} a {date_max}.",
        f"- Precios positivos válidos: {metrics['precios_positivos']}.",
        "- Principales series detectadas:",
    ]
    lines.extend(f"  - {item['commodity']} / {item['moneda']} / {item['unidad']} / {item['tipo_precio']} / condición {item['condicion_comercial']}: {item['filas']} filas, {item['dias_con_datos']} días." for item in series_rows)
    if not series_rows:
        lines.append("  - No se detectaron series.")
    lines.extend([
        "", "## Comparabilidad", "",
        "- ARS y USD no deben mezclarse en una misma serie.",
        "- Las series deben separarse por commodity, moneda, unidad, tipo_precio y condición comercial.",
        "- No se deben comparar directamente operaciones con distinta condición comercial.",
        "- Esta base no equivale a precio de pizarra BCR.", "",
        "## Aptitud para dashboard", "",
        "- Apta para exploración analítica: sí, con filtros de moneda, unidad, commodity y tipo de precio.",
        "- Apta para dashboard piloto: parcial; requiere validar actualización, frecuencia, interpretación y selección de series.",
        "- Apta para dashboard productivo: no, hasta validar actualización automática e interpretación metodológica.", "",
        "## Recomendación próxima", "",
        "Si la base analítica queda consistente, preparar un dataset mensual/diario agregado por commodity-moneda-unidad; definir reglas de visualización separando ARS/USD; no mostrar precios cero; y no integrar todavía al dashboard hasta validar actualización automática y metodología.", "",
        "## Exclusiones por motivo", "",
        "| Motivo | Registros |", "| --- | ---: |",
    ])
    lines.extend(f"| {name} | {count} |" for name, count in metrics["exclusion_reasons"].most_common())
    ANALYTIC_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_analytic_base(source_path: Path, output_path: Path | None = ANALYTIC_PATH) -> dict[str, object]:
    """Filtra precios aptos sin cargar la exportación completa en memoria."""

    if not source_path.exists():
        return {"available": False, "source_label": source_path.as_posix()}
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rows: list[dict[str, str]] = []
    fallback_rows: list[dict[str, str]] = []
    sample_keys: set[tuple[str, ...]] = set()
    sample_dimensions = {field: set() for field in ("commodity", "moneda", "año", "mes", "procedencia", "lugar_entrega", "tipo_precio")}
    commodity_currency: dict[tuple[str, ...], dict[str, object]] = {}
    series: dict[tuple[str, ...], dict[str, object]] = {}
    procedencia: dict[tuple[str, ...], dict[str, object]] = {}
    delivery: dict[tuple[str, ...], dict[str, object]] = {}
    exclusion_reasons: Counter[str] = Counter()
    total = analytic = positive = zero_excluded = 0
    dates: list[date] = []
    currencies: set[str] = set()
    units: set[str] = set()
    commodities: set[str] = set()
    fieldnames: list[str] = []

    def add_sample(row: dict[str, str]) -> None:
        if len(sample_rows) >= ANALYTIC_SAMPLE_LIMIT:
            return
        row_key = (value(row, "id_operacion_sio"), value(row, "fecha"), value(row, "commodity"), value(row, "precio"), value(row, "moneda"), value(row, "volumen"))
        if row_key in sample_keys:
            return
        dimensions = {
            field: value(row, field) or "Sin especificar"
            for field in sample_dimensions
        }
        new_dimension = any(dimensions[field] not in sample_dimensions[field] for field in sample_dimensions)
        if len(sample_rows) < 100 or new_dimension:
            sample_keys.add(row_key)
            sample_rows.append(dict(row))
            for field, dimension_value in dimensions.items():
                sample_dimensions[field].add(dimension_value)

    output_context = output_path.open("w", encoding="utf-8-sig", newline="") if output_path else nullcontext(None)
    with source_path.open("r", encoding="utf-8-sig", newline="") as source_handle, output_context as output_handle:
        reader = csv.DictReader(source_handle, delimiter=";")
        fieldnames = list(reader.fieldnames or [])
        writer = csv.DictWriter(output_handle, fieldnames=fieldnames, delimiter=";", extrasaction="ignore") if output_handle else None
        if writer:
            writer.writeheader()
        for row in reader:
            total += 1
            eligible, reasons, parsed_price, parsed_date = analytical_eligibility(row)
            if not eligible:
                exclusion_reasons.update(reasons)
                if parsed_price == 0 or is_yes(value(row, "precio_cero_flag")):
                    zero_excluded += 1
                continue
            analytic += 1
            positive += 1
            if len(fallback_rows) < ANALYTIC_SAMPLE_LIMIT:
                fallback_rows.append(dict(row))
            add_sample(row)
            if writer:
                writer.writerow(row)
            assert parsed_price is not None and parsed_date is not None
            dates.append(parsed_date)
            commodity = value(row, "commodity")
            currency = value(row, "moneda")
            unit = value(row, "unidad")
            price_type = value(row, "tipo_precio") or "Sin especificar"
            commercial = value(row, "condicion_comercial") or "Sin especificar"
            origin = value(row, "procedencia") or "Sin especificar"
            place = value(row, "lugar_entrega") or "Sin especificar"
            commodities.add(commodity)
            currencies.add(currency)
            units.add(unit)
            analytic_group(commodity_currency, (commodity, currency, unit), row, parsed_price, parsed_date)
            analytic_group(series, (commodity, currency, unit, price_type, commercial), row, parsed_price, parsed_date)
            analytic_group(procedencia, (commodity, currency, origin), row, parsed_price, parsed_date)
            analytic_group(delivery, (commodity, currency, place), row, parsed_price, parsed_date)

    for row in fallback_rows:
        if len(sample_rows) >= ANALYTIC_SAMPLE_LIMIT:
            break
        add_sample(row)
    write_csv(ANALYTIC_SAMPLE_PATH, fieldnames, sample_rows)
    commodity_currency_rows = group_rows(commodity_currency, ["commodity", "moneda", "unidad"])
    series_rows = group_rows(series, ["commodity", "moneda", "unidad", "tipo_precio", "condicion_comercial"], series=True)
    procedencia_rows = group_rows(procedencia, ["commodity", "moneda", "procedencia"], include_volume=True)
    delivery_rows = group_rows(delivery, ["commodity", "moneda", "lugar_entrega"], include_volume=True)
    summary = {
        "filas_base_completa": str(total),
        "filas_analiticas": str(analytic),
        "filas_excluidas": str(total - analytic),
        "porcentaje_usable": format_stat((analytic / total * 100) if total else 0),
        "precios_cero_excluidos": str(zero_excluded),
        "monedas_detectadas": "|".join(sorted(currencies)),
        "unidades_detectadas": "|".join(sorted(units)),
        "fecha_min": min(dates).isoformat() if dates else "",
        "fecha_max": max(dates).isoformat() if dates else "",
        "commodities_detectados": "|".join(sorted(commodities)),
    }
    write_csv(ANALYTIC_SUMMARY_PATH, list(summary.keys()), [summary])
    write_csv(ANALYTIC_COMMODITY_CURRENCY_PATH, ["commodity", "moneda", "unidad", "filas", "precio_min", "precio_promedio", "precio_mediana", "precio_max", "fecha_min", "fecha_max"], commodity_currency_rows)
    write_csv(ANALYTIC_SERIES_PATH, ["commodity", "moneda", "unidad", "tipo_precio", "condicion_comercial", "filas", "fecha_min", "fecha_max", "dias_con_datos", "aptitud_serie"], series_rows)
    write_csv(ANALYTIC_PROCEDENCIA_PATH, ["commodity", "moneda", "procedencia", "filas", "precio_min", "precio_promedio", "precio_mediana", "precio_max", "fecha_min", "fecha_max", "volumen_total"], procedencia_rows)
    write_csv(ANALYTIC_DELIVERY_PATH, ["commodity", "moneda", "lugar_entrega", "filas", "precio_min", "precio_promedio", "precio_mediana", "precio_max", "fecha_min", "fecha_max", "volumen_total"], delivery_rows)
    metrics: dict[str, object] = {
        "available": True, "source_label": source_path.as_posix(), "source_is_complete": source_path == MANUAL_EXPORT_PROCESSED_PATH,
        "analytic_path": ANALYTIC_PATH.as_posix(), "sample_path": ANALYTIC_SAMPLE_PATH.as_posix(), "filas_base_completa": total,
        "filas_analiticas": analytic, "filas_excluidas": total - analytic, "porcentaje_usable": analytic / total * 100 if total else 0,
        "precios_cero_excluidos": zero_excluded, "precios_positivos": positive, "monedas": sorted(currencies), "unidades": sorted(units),
        "commodities": sorted(commodities), "fecha_min": min(dates).isoformat() if dates else "", "fecha_max": max(dates).isoformat() if dates else "",
        "exclusion_reasons": exclusion_reasons, "series_rows": series_rows,
    }
    write_analytic_report(metrics)
    return metrics


def write_manual_lightweight_outputs(path: Path) -> None:
    """Genera sólo artefactos pequeños; el CSV completo nunca se copia al repositorio."""

    sample_candidates: list[dict[str, str]] = []
    priority_candidates: list[dict[str, str]] = []
    zero_candidates: list[dict[str, str]] = []
    priority_keys: set[tuple[str, str]] = set()
    zero_keys: set[tuple[str, str]] = set()
    commodity_stats: dict[str, dict[str, object]] = {}
    zero_stats: dict[tuple[str, str], dict[str, object]] = {}
    currency_stats: dict[tuple[str, str], dict[str, object]] = {}

    def add_stat(store: dict, key_value: tuple[str, ...], row: dict[str, str], include_zero: bool = True) -> None:
        commodity = value(row, "commodity") or "Sin especificar"
        currency = value(row, "moneda") or "Sin especificar"
        unit = value(row, "unidad") or "Sin especificar"
        parsed_date = parse_date(value(row, "fecha"))
        price = parse_price(value(row, "precio"))
        item = store.setdefault(key_value, {"filas": 0, "precios_validos": 0, "precios_cero": 0, "monedas": set(), "unidades": set(), "fecha_min": None, "fecha_max": None})
        item["filas"] += 1
        if price is not None:
            item["precios_validos"] += 1
            item["precios_cero"] += int(price == 0) if include_zero else 0
        if currency != "Sin especificar": item["monedas"].add(currency)
        if unit != "Sin especificar": item["unidades"].add(unit)
        if parsed_date:
            item["fecha_min"] = min(parsed_date, item["fecha_min"]) if item["fecha_min"] else parsed_date
            item["fecha_max"] = max(parsed_date, item["fecha_max"]) if item["fecha_max"] else parsed_date

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            commodity = value(row, "commodity") or "Sin especificar"
            currency = value(row, "moneda") or "Sin especificar"
            price = parse_price(value(row, "precio"))
            valid = bool(commodity and price is not None)
            if valid and len(sample_candidates) < 1000:
                sample_candidates.append(dict(row))
            priority_key = (commodity, currency)
            if valid and priority_key not in priority_keys:
                priority_keys.add(priority_key)
                priority_candidates.append(dict(row))
            if valid and price == 0 and priority_key not in zero_keys:
                zero_keys.add(priority_key)
                zero_candidates.append(dict(row))
            add_stat(commodity_stats, (commodity,), row)
            if price == 0:
                add_stat(zero_stats, (commodity, currency), row, include_zero=True)
            add_stat(currency_stats, (commodity, currency), row, include_zero=True)

    selected: list[dict[str, str]] = []
    seen_sample: set[tuple[str, ...]] = set()
    for row in priority_candidates + zero_candidates + sample_candidates:
        sample_key = (value(row, "id_operacion_sio"), value(row, "fecha"), value(row, "commodity"), value(row, "precio"), value(row, "moneda"), value(row, "volumen"))
        if sample_key in seen_sample:
            continue
        seen_sample.add(sample_key)
        selected.append(row)
        if len(selected) >= 1000:
            break
    write_csv(MANUAL_EXPORT_SAMPLE_PATH, fieldnames, selected)

    def summary_rows(store: dict[tuple[str, ...], dict[str, object]], names: list[str]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for key_value, item in sorted(store.items()):
            row = {name: str(value) for name, value in zip(names, key_value)}
            row.update({"filas": str(item["filas"]), "precios_validos": str(item["precios_validos"]), "precios_cero": str(item["precios_cero"]), "monedas": "|".join(sorted(item["monedas"])), "unidades": "|".join(sorted(item["unidades"])), "fecha_min": item["fecha_min"].isoformat() if item["fecha_min"] else "", "fecha_max": item["fecha_max"].isoformat() if item["fecha_max"] else ""})
            rows.append(row)
        return rows

    fields = ["commodity", "filas", "precios_validos", "precios_cero", "monedas", "unidades", "fecha_min", "fecha_max"]
    write_csv(MANUAL_EXPORT_SUMMARY_PATH, fields, summary_rows(commodity_stats, ["commodity"]))
    zero_fields = ["commodity", "moneda", "filas", "precios_validos", "precios_cero", "monedas", "unidades", "fecha_min", "fecha_max"]
    write_csv(MANUAL_EXPORT_ZERO_PATH, zero_fields, summary_rows(zero_stats, ["commodity", "moneda"]))
    currency_fields = ["commodity", "moneda", "filas", "precios_validos", "precios_cero", "monedas", "unidades", "fecha_min", "fecha_max"]
    write_csv(MANUAL_EXPORT_COMMODITY_CURRENCY_PATH, currency_fields, summary_rows(currency_stats, ["commodity", "moneda"]))


def audited_files_section(primary_rows: list[dict[str, str]], technical_rows: list[dict[str, str]], manual_rows: list[dict[str, str]]) -> tuple[str, str, str]:
    primary_status = "parcial_piloto" if primary_rows and all(value(row, "apto_dashboard") == "parcial_piloto" for row in primary_rows) else "no"
    technical_state = sorted({value(row, "estado_paginacion") for row in technical_rows if value(row, "estado_paginacion")})
    technical_aptitude = "no" if "duplicada" in technical_state else "parcial_piloto" if technical_rows else "no disponible"
    files_section = "\n".join([
        "## Archivos auditados", "", "| Archivo | Tipo | Filas | Finalidad | Aptitud |", "| --- | --- | ---: | --- | --- |",
        f"| `data/commodities_sio/processed/COMMODITIES_SIO_INTEGRADO.csv` | integración piloto principal | {len(primary_rows)} | referencia piloto base | {primary_status} |",
        f"| `data/commodities_sio/processed/COMMODITIES_SIO_MUESTRA_PAGINADA.csv` | muestra técnica de paginación | {len(technical_rows)} | diagnóstico de request, páginas y duplicados | {technical_aptitude} |" if technical_rows else "| `data/commodities_sio/processed/COMMODITIES_SIO_MUESTRA_PAGINADA.csv` | muestra técnica de paginación | 0 | no disponible | no disponible |",
        f"| `data/commodities_sio/processed/COMMODITIES_SIO_EXPORTACION_MANUAL.csv` | exportación manual | {manual_rows.get('rows', 0)} | archivo descargado localmente | {'parcial_piloto' if manual_rows.get('rows') else 'no disponible'} |" if manual_rows.get('rows') else "| `data/commodities_sio/processed/COMMODITIES_SIO_EXPORTACION_MANUAL.csv` | exportación manual | 0 | no disponible | no disponible |",
        "",
    ])
    if technical_rows:
        technical_section = "\n".join([
            "## Muestra paginada técnica", "", f"La muestra contiene {len(technical_rows)} fila(s) y es evidencia técnica separada: no reemplaza `COMMODITIES_SIO_INTEGRADO.csv`.", f"Estado de paginación registrado: {', '.join(technical_state) or 'sin dato'}.", "No es apta para dashboard cuando `estado_paginacion=duplicada`; se conserva para diagnosticar duplicados y paginación.", "",
        ])
    else:
        technical_section = "\n".join(["## Muestra paginada técnica", "", "No existe una muestra técnica procesada para auditar.", ""])
    return files_section, technical_section, export_summary(manual_rows)


def pilot_eligible(row: dict[str, str]) -> bool:
    return bool(parse_date(value(row, "fecha")) and value(row, "commodity") and parse_price(value(row, "precio")) is not None and parse_price(value(row, "precio")) > 0 and value(row, "fuente") and value(row, "campo_precio_original") and value(row, "campo_precio_original") != "Sin especificar" and value(row, "unidad") and value(row, "unidad") != "Sin especificar")


def dashboard_status(row: dict[str, str], currency_values: list[str], unit_values: list[str]) -> str:
    if value(row, "precio_valido_para_serie") == "no" or parse_price(value(row, "precio")) in {None, 0}:
        return "no"
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
    observed_files = sorted(RAW_DIR.glob("SIO_GetOperaciones_observed_pCurrentPage_*.json"))
    preferred_files = sorted(RAW_DIR.glob("SIO_test_pagination_page_*.json"))
    fallback_files = sorted(RAW_DIR.glob("SIO_GetOperaciones_page_*.json"))
    candidates = observed_files or preferred_files or fallback_files
    latest_by_page: dict[str, Path] = {}
    for path in candidates:
        page_match = re.search(r"(?:page[_-]|observed_pcurrentpage[_-])(\d+)", path.stem, flags=re.I)
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
        page_match = re.search(r"(?:page[_-]|observed_pcurrentpage[_-])(\d+)", path.stem, flags=re.I)
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
    report_paths = [path for path in (PAGINATED_REPORT_PATH, PAGINATION_REPORT_PATH) if path.exists()]
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
    snapshot_rows = read_rows(HISTORIC_SNAPSHOTS_PATH) or read_rows(LIGHT_HISTORY_PATH)
    technical_rows = read_rows(PAGINATED_PROCESSED_PATH)
    write_daily_update_report()
    manual_export_stats_value = manual_export_stats(MANUAL_EXPORT_PROCESSED_PATH) if MANUAL_EXPORT_PROCESSED_PATH.exists() else {"rows": 0, "columns": [], "dates": [], "currencies": [], "units": [], "commodities": []}
    if manual_export_stats_value.get("rows"):
        write_manual_lightweight_outputs(MANUAL_EXPORT_PROCESSED_PATH)
        zero_metrics = write_zero_audit(MANUAL_EXPORT_PROCESSED_PATH)
        analytic_metrics = build_analytic_base(MANUAL_EXPORT_PROCESSED_PATH)
    elif ANALYTIC_PATH.exists():
        zero_metrics = {"total": 0, "positive": 0, "zero": 0, "missing": 0, "zero_pct": 0.0, "types": Counter(), "dimensions": {}, "originals": Counter()}
        analytic_metrics = build_analytic_base(ANALYTIC_PATH, output_path=None)
    elif ANALYTIC_SAMPLE_PATH.exists():
        zero_metrics = {"total": 0, "positive": 0, "zero": 0, "missing": 0, "zero_pct": 0.0, "types": Counter(), "dimensions": {}, "originals": Counter()}
        analytic_metrics = build_analytic_base(ANALYTIC_SAMPLE_PATH, output_path=None)
    else:
        zero_metrics = {"total": 0, "positive": 0, "zero": 0, "missing": 0, "zero_pct": 0.0, "types": Counter(), "dimensions": {}, "originals": Counter()}
        analytic_metrics = {"available": False}
    if not rows and not technical_rows and not snapshot_rows and not manual_export_stats_value.get("rows") and not analytic_metrics.get("available"):
        return no_data()
    if not rows:
        if snapshot_rows:
            print("No hay integración piloto principal; se auditará el histórico de snapshots disponible.")
            rows = snapshot_rows
        else:
            print("No hay integración piloto principal; se auditará la salida técnica o manual disponible.")
            rows = technical_rows
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
    technical_actuality = actuality_for_rows(technical_rows, "muestra_paginada", today) if technical_rows else []
    manual_export_actuality = [{"fuente_archivo": "exportacion_manual", "commodity": commodity, "fecha_max": max(dates).isoformat() if dates else "", "dias_desde_ultimo_dato": str((today - max(dates)).days) if dates else "", "registros_ultimos_7_dias": str(sum(1 for item in dates if today - timedelta(days=6) <= item <= today)), "registros_ultimos_30_dias": str(sum(1 for item in dates if today - timedelta(days=29) <= item <= today)), "estado_actualidad": "Actualizado" if dates and (today - max(dates)).days <= 7 else "Reciente" if dates and (today - max(dates)).days <= 30 else "Desactualizado" if dates else "Sin fecha"} for commodity, dates in manual_export_stats_value.get("commodity_dates", {}).items()]
    primary_actuality = [dict(item, fuente_archivo="integrado_principal") for item in actuality]
    actuality_export = primary_actuality + technical_actuality + manual_export_actuality
    write_csv(REPORTS["actuality"], ["fuente_archivo", "commodity", "fecha_max", "dias_desde_ultimo_dato", "registros_ultimos_7_dias", "registros_ultimos_30_dias", "estado_actualidad"], actuality_export)

    max_date = max(all_dates) if all_dates else None
    min_date = min(all_dates) if all_dates else None
    age = (today - max_date).days if max_date else None
    positive_prices = sum(1 for item in all_prices if item > 0)
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
    files_section, technical_section, manual_export_section = audited_files_section(rows, technical_rows, manual_export_stats_value)
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
        f"- Muestra piloto de una sola página GetOperaciones: {'sí' if pilot_rows else 'no'}; filas piloto: {pilot_rows or 'sin marca piloto'}.", f"- Filas totales: {len(rows)}.", f"- Columnas mapeadas con dato: {', '.join(mapped_columns) or 'ninguna'}.", f"- Columnas faltantes/no separadas: {', '.join(missing_columns) or 'ninguna'}.", f"- Commodities detectados: {', '.join(commodities)}.", f"- Años disponibles: {', '.join(str(item) for item in years) if years else 'ninguno'}.", f"- Meses disponibles: {', '.join(months) if months else 'ninguno'}.", f"- Rango de fechas: {min_date.isoformat() if min_date else 'sin fecha válida'} a {max_date.isoformat() if max_date else 'sin fecha válida'}.", f"- Fecha máxima: {max_date.isoformat() if max_date else 'sin fecha válida'}; días desde último dato: {age if max_date else 'sin fecha válida'}.", f"- Precios válidos: {len(all_prices)}; faltantes: {missing_price}; cero: {zero_price}; negativos: {negative_price}.", f"- Precios válidos para serie (positivos): {positive_prices}/{len(rows)}.", f"- Monedas especificadas: {coverage_count(rows, 'moneda')}/{len(rows)}; sin especificar: {len(rows) - coverage_count(rows, 'moneda')}.", f"- Unidades de precio especificadas: {coverage_count(rows, 'unidad')}/{len(rows)}; sin especificar: {len(rows) - coverage_count(rows, 'unidad')}.", f"- Unidades de volumen especificadas: {volume_unit_count}/{len(rows)}; sin especificar: {len(rows) - volume_unit_count}.", f"- Campos originales de precio: {', '.join(price_field_values) or 'ninguno'}; campos originales de volumen: {', '.join(volume_field_values) or 'ninguno'}.", f"- Precio unitario con dato: {price_unit_count}; precio total con dato: {price_total_count}; inconsistencias detectadas: {inconsistent_price}.", f"- Volumen con dato numérico: {volume_valid}; procedencia con dato: {coverage_count(rows, 'procedencia')}; lugar de entrega (zona) con dato: {coverage_count(rows, 'zona')}; condición de pago con dato: {coverage_count(rows, 'condicion_pago')}.", f"- apto_piloto: {'sí' if pilot_eligible_count == len(rows) else 'no'} ({pilot_eligible_count}/{len(rows)} filas).", f"- apto_dashboard: {'sí' if dashboard_eligible_count == len(rows) else 'no'} ({dashboard_eligible_count}/{len(rows)} filas).", f"- Series utilizables para dashboard analítico futuro: {usable_count} de {len(series)}.", "",
    ]
    if warnings:
        lines.extend(["## Advertencias", "", *[f"- {warning}" for warning in warnings], ""])
    lines.extend([files_section, technical_section, manual_export_section])
    if zero_metrics["total"]:
        lines.extend(["## Precios cero y aptitud analítica", "", f"La exportación manual contiene {zero_metrics['zero']} precio(s) cero sobre {zero_metrics['total']} fila(s) ({zero_metrics['zero_pct']:.2f}%). Los ceros se conservan para trazabilidad, pero sólo las filas con `precio_valido_para_serie=sí` pueden alimentar series, promedios, rankings o semáforos.", f"Clasificación principal: {', '.join(f'{name}={count}' for name, count in zero_metrics['types'].most_common())}.", "La base no se considera plenamente apta para indicadores de precio hasta aplicar este filtro y revisar los casos cero.", ""])
    if analytic_metrics.get("available"):
        lines.extend([
            "## Base analítica de precios", "",
            f"- Filas de la base completa evaluadas: {analytic_metrics['filas_base_completa']}.",
            f"- Filas analíticas: {analytic_metrics['filas_analiticas']}.",
            f"- Filas excluidas: {analytic_metrics['filas_excluidas']} ({100 - float(analytic_metrics['porcentaje_usable']):.2f}%).",
            f"- Porcentaje usable: {float(analytic_metrics['porcentaje_usable']):.2f}%.",
            f"- Precios positivos válidos: {analytic_metrics['precios_positivos']}; precios cero excluidos: {analytic_metrics['precios_cero_excluidos']}.",
            f"- Monedas: {', '.join(analytic_metrics['monedas']) or 'ninguna'}; unidades: {', '.join(analytic_metrics['unidades']) or 'ninguna'}.",
            f"- Commodities: {', '.join(analytic_metrics['commodities']) or 'ninguno'}.",
            f"- Rango de fechas: {analytic_metrics['fecha_min'] or 'sin fecha'} a {analytic_metrics['fecha_max'] or 'sin fecha'}.",
            "- Aptitud: apta para exploración analítica; parcial para un dashboard piloto; no apta para producción hasta validar actualización automática y metodología.",
            "- ARS y USD se mantienen separados en los resúmenes y no se comparan conjuntamente.", "",
        ])
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
    write_manual_export_report(manual_export_stats_value)
    write_daily_update_report()
    if technical_rows:
        update_paginated_audit_report(technical_rows)
    print(f"Auditoría SIO finalizada: {len(rows)} filas, {len(commodities)} commodity(s).")
    print(f"Fecha máxima: {max_date.isoformat() if max_date else 'sin fecha válida'}; precios válidos: {len(all_prices)}; faltantes: {missing_price}.")
    for path in REPORTS.values():
        print(f"Reporte: {path}")
    print(f"Reporte de actualización diaria: {DAILY_UPDATE_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
