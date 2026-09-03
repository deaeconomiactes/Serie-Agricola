#!/usr/bin/env python3
"""Audita cobertura, calidad básica y actualidad del CSV BCR integrado."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "commodities_bcr" / "raw"
PROCESSED_PATH = ROOT / "data" / "commodities_bcr" / "processed" / "COMMODITIES_BCR_INTEGRADO.csv"
REPORT_DIR = ROOT / "data" / "commodities_bcr" / "reports"
ACTUALITY_PATH = REPORT_DIR / "RESUMEN_ACTUALIDAD_COMMODITIES_BCR.csv"
REPORT_PATH = REPORT_DIR / "REPORTE_AUDITORIA_COMMODITIES_BCR.md"


def parse_date(value: str) -> date | None:
    raw = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            pass
    return None


def read_rows() -> list[dict[str, str]]:
    if not PROCESSED_PATH.exists():
        return []
    with PROCESSED_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def real_raw_files() -> list[Path]:
    if not RAW_DIR.exists():
        return []
    ignored = {"PLANTILLA_COMMODITIES_BCR.csv", "desktop.ini"}
    return sorted(path for path in RAW_DIR.iterdir() if path.is_file() and path.suffix.lower() in {".csv", ".xlsx", ".xls", ".json"} and path.name not in ignored and not path.name.startswith("~$"))


def print_no_data() -> int:
    files = real_raw_files()
    all_candidate_files = list(RAW_DIR.iterdir()) if RAW_DIR.exists() else []
    if any(path.is_file() and re.search(r"plantilla|simulad|prueba|test", path.name, re.IGNORECASE) for path in all_candidate_files):
        print("Los datos disponibles son de prueba o plantilla. No usar para análisis real.")
    print("No hay datos integrados para auditar.")
    if files:
        print(f"Hay {len(files)} archivo(s) en raw/, pero no produjeron registros válidos: revise formato y columnas.")
    else:
        print("No hay archivos reales en data/commodities_bcr/raw/.")
    print("Próximos pasos: descargue archivos reales de Pizarra/Cámara para soja, maíz, trigo, girasol y sorgo; ejecute integrar_commodities_bcr.py y luego vuelva a auditar.")
    print("No se generan reportes vacíos que parezcan información válida.")
    return 0


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    result = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    result.extend("| " + " | ".join(str(value).replace("|", "/") for value in row) + " |" for row in rows)
    return "\n".join(result)


def main() -> int:
    rows = read_rows()
    if not rows:
        return print_no_data()

    today = date.today()
    dates_by_commodity: dict[str, list[date]] = defaultdict(list)
    invalid_dates = 0
    missing_prices = 0
    simulated = False
    for row in rows:
        commodity = row.get("commodity", "").strip() or "Sin identificar"
        parsed = parse_date(row.get("fecha", ""))
        if parsed:
            dates_by_commodity[commodity].append(parsed)
        else:
            invalid_dates += 1
        if not (row.get("precio") or "").strip():
            missing_prices += 1
        origin = (row.get("archivo_origen", "") + " " + row.get("observaciones", "")).lower()
        if re.search(r"plantilla|simulad|prueba|test", origin):
            simulated = True

    commodities = sorted(set(dates_by_commodity) | {row.get("commodity", "Sin identificar").strip() or "Sin identificar" for row in rows})
    actuality_rows: list[dict[str, str]] = []
    for commodity in commodities:
        commodity_dates = dates_by_commodity.get(commodity, [])
        max_date = max(commodity_dates) if commodity_dates else None
        days_old = (today - max_date).days if max_date else ""
        count_7 = sum(1 for item in commodity_dates if today - timedelta(days=6) <= item <= today)
        count_30 = sum(1 for item in commodity_dates if today - timedelta(days=29) <= item <= today)
        if not max_date:
            status = "Sin fecha"
        elif days_old <= 7:
            status = "Actualizado"
        elif days_old <= 30:
            status = "Reciente"
        else:
            status = "Desactualizado"
        actuality_rows.append({
            "commodity": commodity,
            "fecha_max": max_date.isoformat() if max_date else "",
            "dias_desde_ultimo_dato": str(days_old) if max_date else "",
            "registros_ultimos_7_dias": str(count_7),
            "registros_ultimos_30_dias": str(count_30),
            "estado_actualidad": status,
        })

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with ACTUALITY_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["commodity", "fecha_max", "dias_desde_ultimo_dato", "registros_ultimos_7_dias", "registros_ultimos_30_dias", "estado_actualidad"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(actuality_rows)

    recent = [row for row in actuality_rows if row["estado_actualidad"] in {"Actualizado", "Reciente"}]
    updated = [row["commodity"] for row in actuality_rows if row["estado_actualidad"] == "Actualizado"]
    stale = [row["commodity"] for row in actuality_rows if row["estado_actualidad"] in {"Desactualizado", "Sin fecha"}]
    total_7 = sum(int(row["registros_ultimos_7_dias"]) for row in actuality_rows)
    total_30 = sum(int(row["registros_ultimos_30_dias"]) for row in actuality_rows)
    warnings = []
    if simulated:
        warnings.append("Los datos disponibles son de prueba o plantilla. No usar para análisis real.")
    if invalid_dates:
        warnings.append(f"{invalid_dates} registro(s) no tiene(n) fecha válida.")
    if missing_prices:
        warnings.append(f"{missing_prices} registro(s) no tiene(n) precio numérico.")

    md = [
        "# Reporte de auditoría de commodities BCR",
        "",
        f"Fecha de auditoría: {today.isoformat()}",
        "",
        "## Resumen",
        "",
        f"- Registros integrados: {len(rows)}.",
        f"- Commodities con observaciones: {len(commodities)}.",
        f"- Cobertura de últimos 7 días: {total_7} registro(s); commodities con actividad reciente: {sum(1 for row in actuality_rows if int(row['registros_ultimos_7_dias']) > 0)} de {len(commodities)}.",
        f"- Cobertura de últimos 30 días: {total_30} registro(s); commodities con actividad: {sum(1 for row in actuality_rows if int(row['registros_ultimos_30_dias']) > 0)} de {len(commodities)}.",
        "",
    ]
    if warnings:
        md.extend(["## Advertencias", "", *[f"- {warning}" for warning in warnings], ""])
    md.extend([
        "## Actualidad de la información",
        "",
        f"Commodities actualizados (últimos 7 días): {', '.join(updated) if updated else 'ninguno'}.",
        f"Commodities recientes o actualizados: {', '.join(row['commodity'] for row in recent) if recent else 'ninguno'}.",
        f"Commodities desactualizados o sin fecha: {', '.join(stale) if stale else 'ninguno'}.",
        "",
        markdown_table(
            ["Commodity", "Fecha máxima", "Días desde último dato", "Últimos 7 días", "Últimos 30 días", "Estado"],
            [[row["commodity"], row["fecha_max"] or "—", row["dias_desde_ultimo_dato"] or "—", row["registros_ultimos_7_dias"], row["registros_ultimos_30_dias"], row["estado_actualidad"]] for row in actuality_rows],
        ),
        "",
        "El detalle estructurado se encuentra en `RESUMEN_ACTUALIDAD_COMMODITIES_BCR.csv`.",
        "",
        "## Recomendación de automatización",
        "",
        "- Automatizar por API sólo si BCR/GIX confirma un endpoint estable, autorización, autenticación y condiciones de uso compatibles.",
        "- Mantener descarga manual si no hay endpoint o credenciales autorizadas; la fuente y el tipo de precio deben seguir siendo pizarra/Cámara.",
        "- No publicar en el dashboard hasta validar unidad, moneda, frecuencia, cobertura y fecha máxima por commodity.",
        "- Próximo paso: ampliar la muestra con descargas reales de los últimos 30 días o 3 meses y volver a ejecutar integración y auditoría.",
        "",
        "## Limitaciones",
        "",
        "La auditoría mide actualidad respecto de la fecha de ejecución y no determina por sí sola si una observación representa una operación, una estimación o una conversión. Esa revisión requiere conservar y consultar la metodología de BCR/Cámara Arbitral.",
    ])
    REPORT_PATH.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Auditoría finalizada: {len(rows)} registros, {len(commodities)} commodities.")
    print(f"Resumen de actualidad: {ACTUALITY_PATH}")
    print(f"Reporte: {REPORT_PATH}")
    if simulated:
        print("Los datos disponibles son de prueba o plantilla. No usar para análisis real.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
