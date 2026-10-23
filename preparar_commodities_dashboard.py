#!/usr/bin/env python3
"""CLI compatible para publicar estadísticas transaccionales SIO validadas."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PROCESSED_DIR = ROOT / "data" / "commodities_sio" / "processed"

DASHBOARD_DIR = ROOT / "data" / "commodities_sio" / "dashboard"

REPORT_DIR = ROOT / "data" / "commodities_sio" / "reports"

ANALYTIC_PATH = PROCESSED_DIR / "COMMODITIES_SIO_ANALITICO_PRECIOS.csv"

SNAPSHOT_HISTORY_PATH = PROCESSED_DIR / "COMMODITIES_SIO_HISTORICO_SNAPSHOTS.csv"

LATEST_SNAPSHOT_PATH = PROCESSED_DIR / "COMMODITIES_SIO_LATEST_SNAPSHOT.csv"

LIGHT_SNAPSHOT_HISTORY_PATH = DASHBOARD_DIR / "COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv"

REPORT_PATH = REPORT_DIR / "REPORTE_DASHBOARD_COMMODITIES_SIO.md"

OUTPUTS = {
    "diario": DASHBOARD_DIR / "COMMODITIES_SIO_DASHBOARD_DIARIO.csv",
    "mensual": DASHBOARD_DIR / "COMMODITIES_SIO_DASHBOARD_MENSUAL.csv",
    "ultimos": DASHBOARD_DIR / "COMMODITIES_SIO_DASHBOARD_ULTIMOS.csv",
    "resumen": DASHBOARD_DIR / "COMMODITIES_SIO_DASHBOARD_RESUMEN.csv",
    "semaforo": DASHBOARD_DIR / "COMMODITIES_SIO_DASHBOARD_SEMAFORO.csv",
}



def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def latest_snapshot_capture() -> str:
    if not LATEST_SNAPSHOT_PATH.exists():
        return ""
    try:
        with LATEST_SNAPSHOT_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            captures = [value(row, "fecha_descarga_snapshot") for row in csv.DictReader(handle, delimiter=";")]
    except OSError:
        return ""
    return max((item for item in captures if item), default="")


def build_dashboard(source_path: Path) -> dict[str, object]:
    from scripts.sio.grain import build
    return build(source_path, OUTPUTS, REPORT_PATH, latest_snapshot_capture())



def main() -> int:
    source_path = next((p for p in (LIGHT_SNAPSHOT_HISTORY_PATH, SNAPSHOT_HISTORY_PATH, ANALYTIC_PATH) if p.exists()), None)
    if source_path is None:
        print("[VALIDATE] Sin histórico de eventos SIO; última salida válida conservada. No se publican muestras automáticamente.")
        return 1
    try:
        metrics = build_dashboard(source_path)
    except (ValueError, OSError) as error:
        print(f"[VALIDATE] SIO: {error}; última salida válida conservada")
        return 1
    print(f"[VALIDATE] {metrics['valid_rows']} eventos; {metrics['series']} series por dimensiones informadas")
    for name, path in OUTPUTS.items():
        print(f"[PUBLISH] {name}: {metrics['rows_by_output'][name]} filas, {path.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
