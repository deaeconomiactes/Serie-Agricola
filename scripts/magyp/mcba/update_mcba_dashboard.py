"""Una captura controlada → publicación incremental; nunca descarta historia ya publicada."""
from __future__ import annotations
import argparse
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import (PipelineError, atomic_write, csv_bytes,
    publish_bundle, utc_now)
from scripts.magyp.mcba.acquisition import browser_fetch
from scripts.magyp.mcba.fetch_mcba import capture
from scripts.magyp.mcba.normalize_mcba import run as normalize_run
from scripts.magyp.mcba.build_analytical_mcba import run as analytical_run
from scripts.magyp.mcba.build_dashboard_mcba import run as dashboard_run

# Reexportados para conservar el contrato de los consumidores existentes.
from scripts.magyp.mcba.published_bundle import DAILY, DIMENSIONS, REQUIRED, read_bundle, validate_daily


def merge_daily(previous, delta):
    validate_daily(delta)
    if previous:
        validate_daily(previous)
        if set(previous[0]) != set(delta[0]):
            raise PipelineError("Cambio de schema: requiere migración explícita")
    replacement = {r["date"] for r in delta}
    for day in replacement:
        before = [r["capture_timestamp"] for r in previous if r["date"] == day]
        after = {r["capture_id"] for r in delta if r["date"] == day}
        if len(after) != 1 or (before and min(r["capture_timestamp"] for r in delta if r["date"] == day) < max(before)):
            raise PipelineError("Revisión fuera de orden o fecha con capturas mezcladas")
    merged = [r for r in previous if r["date"] not in replacement] + delta
    merged.sort(key=lambda r: (r["date"], str(tuple(r[k] for k in DIMENSIONS)), r["observation_id"]))
    validate_daily(merged)
    return merged


def outputs_for(rows):
    validate_daily(rows)
    details = [r for r in rows if r["observation_level"] == "detail"]
    if not details:
        raise PipelineError("Sin detalle comercial")
    latest = {}
    flags = Counter()
    for r in rows:
        key = tuple(r[k] for k in DIMENSIONS)
        if key not in latest or (r["date"], r["capture_timestamp"], r["observation_id"]) > (
                latest[key]["date"], latest[key]["capture_timestamp"], latest[key]["observation_id"]):
            latest[key] = r
        value = r.get("quality_flags", "[]")
        flags.update(json.loads(value) if isinstance(value, str) else value)
    dates = sorted({r["date"] for r in rows})
    stamp = max(r["capture_timestamp"] for r in rows)
    summary = [{"source": "mcba", "rows_analytical": len(rows), "valid_rows": len(rows),
        "date_min": dates[0], "date_max": dates[-1], "observed_days": len(dates),
        "detail_rows": len(details), "summary_rows": len(rows) - len(details), "quality_flags": dict(flags),
        "source_url": rows[0]["source_url"], "updated_at": stamp, "data_source": "MAGYP",
        "source_status": "MAGYP", "last_update": stamp, "monthly_official_status": "not_operational",
        "dashboard_schema_version": "mcba-dashboard-v3"}]
    datasets = {"DAILY": rows, "DETAIL": details, "LATEST": list(latest.values()), "SUMMARY": summary}
    return {f"MCBA_MAGYP_{name}.csv": csv_bytes(values, list(values[0])) for name, values in datasets.items()}


def publish_incremental(staging, target):
    delta = read_bundle(staging)
    # A partially missing prior bundle fails closed, rather than starting an empty history.
    previous = read_bundle(target) if target.exists() and any(target.glob("MCBA_MAGYP_*.csv")) else []
    rows = merge_daily(previous, delta)
    result = publish_bundle(target, outputs_for(rows), len(rows))
    print(f"[PUBLISH] {len(rows)} registros; historia preservada; {len(delta)} observaciones de captura")
    return result


def update(day, raw_root, published, allow_web=False, timeout=60, max_requests=80, browser_channel="auto"):
    date.fromisoformat(day)
    if not allow_web:
        raise PipelineError("Adquisición requiere --allow-web")
    # A single run is isolated. Revisions are merged by whole observation date, never by product.
    if list((raw_root / "raw/mcba").glob("*/manifest.json")):
        raise PipelineError("Usar un directorio de captura vacío para esta actualización")
    try:
        result = browser_fetch(day, day, timeout, max_requests, browser_channel)
        capture(result.payload, day, raw_root, "browser_automation", result.http_status, result.content_type,
            date_to=day, request_method=result.request_method, request_count=result.diagnostics["request_count"],
            acquisition_classification=result.classification)
        normalize_run(raw_root)
        analytical_run(raw_root)
        dashboard_run(raw_root)
        publish_incremental(raw_root / "dashboard/mcba", published)
        status = {"source_status": "MAGYP", "attempted_at": utc_now(), "requested_date": day}
        atomic_write(published / "MCBA_MAGYP_UPDATE_STATUS.json", (json.dumps(status) + "\n").encode())
    except Exception as error:
        diagnostic = {"source": "mcba", "requested_date": day, "attempted_at": utc_now(),
            "result": "failed", "error_class": type(error).__name__,
            "diagnostics": getattr(error, "diagnostics", {})}
        atomic_write(raw_root / "reports/MCBA_INTEGRATION_ATTEMPT.json",
                     (json.dumps(diagnostic, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        if (published / "_SUCCESS.json").exists():
            status = {"source_status": "MAGYP_LAST_VALID", "attempted_at": utc_now(), "requested_date": day}
            atomic_write(published / "MCBA_MAGYP_UPDATE_STATUS.json", (json.dumps(status) + "\n").encode())
        raise


def run_productive(day, raw_root, published, allow_web=False, browser_channel="auto"):
    """Availability is an operational outcome; integrity failures remain fatal."""
    previous = []
    outcome = "PIPELINE_ERROR"
    error = None
    try:
        date.fromisoformat(day)
        if (published / "_SUCCESS.json").exists() or any(published.glob("MCBA_MAGYP_*.csv")):
            previous = read_bundle(published)
        if any(r["date"] == day for r in previous):
            outcome = "NO_OP_ALREADY_CURRENT"
        else:
            try:
                update(day, raw_root, published, allow_web, browser_channel=browser_channel)
                outcome = "UPDATED"
            except Exception as exc:
                diag = getattr(exc, "diagnostics", {})
                kind = diag.get("error_type")
                stage = diag.get("acquisition_stage")
                if kind == "NO_PUBLICATION":
                    outcome = "NO_PUBLICATION"
                elif stage != "validate_xlsx" and kind in {
                    "TIMEOUT", "CONNECTION", "HTTP_5XX", "HTTP_401", "HTTP_403", "HTTP_404",
                    "HTTP_429", "NAVIGATION_NO_RESPONSE"}:
                    outcome = "SOURCE_UNAVAILABLE"
                else:
                    raise
    except Exception as exc:
        error = exc
    rows = read_bundle(published) if outcome == "UPDATED" else previous
    state = {"result": outcome, "source": "MAGyP",
        "source_url": "https://ssma.magyp.gob.ar/frutas.precios.aspx",
        "source_status": "MAGYP" if outcome == "UPDATED" else "MAGYP_LAST_VALID",
        "requested_date": day, "attempted_at": utc_now(),
        "last_observation_date": max((r["date"] for r in rows), default=None),
        "last_successful_update": max((r["capture_timestamp"] for r in rows), default=None)}
    atomic_write(raw_root / "reports/MCBA_RUN_STATUS.json",
                 (json.dumps(state, indent=2) + "\n").encode())
    if outcome == "UPDATED":
        atomic_write(published / "MCBA_MAGYP_UPDATE_STATUS.json",
                     (json.dumps(state, indent=2) + "\n").encode())
    print(f"[PUBLISH] {outcome}; última observación={state['last_observation_date']}; "
          f"última actualización exitosa={state['last_successful_update']}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(f"result={outcome}\n")
    if error is not None:
        raise error
    return state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--date", required=True)
    p.add_argument("--data-root", type=Path, required=True, help="Carpeta aislada fuera de Git")
    p.add_argument("--published-dir", type=Path, default=ROOT / "data/magyp/dashboard/mcba")
    p.add_argument("--allow-web", action="store_true")
    p.add_argument("--browser-channel", choices=("auto", "msedge", "chromium"), default="auto")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.dry_run:
        date.fromisoformat(a.date)
        print("[FETCH] DRY-RUN: sin requests ni escrituras")
        return
    try:
        run_productive(a.date, a.data_root, a.published_dir, a.allow_web, browser_channel=a.browser_channel)
    except Exception as error:
        print("[PUBLISH] ERROR " + (str(error) if isinstance(error, PipelineError) else type(error).__name__) +
              "; última salida válida conservada", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
