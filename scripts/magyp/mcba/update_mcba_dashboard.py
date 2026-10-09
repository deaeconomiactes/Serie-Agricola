"""Una captura controlada → publicación incremental; nunca descarta historia ya publicada."""
from __future__ import annotations
import argparse
import csv
import io
import json
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import (PipelineError, atomic_write, csv_bytes,
    publish_bundle, sha256, utc_now)
from scripts.magyp.mcba.acquisition import browser_fetch
from scripts.magyp.mcba.fetch_mcba import capture
from scripts.magyp.mcba.normalize_mcba import run as normalize_run
from scripts.magyp.mcba.build_analytical_mcba import run as analytical_run
from scripts.magyp.mcba.build_dashboard_mcba import run as dashboard_run

DAILY = "MCBA_MAGYP_DAILY.csv"
DIMENSIONS = ("source", "market_normalized", "type", "product_normalized", "variety_normalized",
    "origin_normalized", "package_normalized", "quality", "size", "grade", "currency", "price_unit",
    "record_kind", "observation_level")
REQUIRED = set(DIMENSIONS) | {"date", "price", "observation_id", "raw_sha256", "capture_id",
    "product_raw", "variety_raw", "origin_raw", "package_raw", "kg_raw", "volume",
    "capture_timestamp", "source_url", "data_source", "source_status", "last_update"}


def read_bundle(folder):
    """Valida todos los hashes del conjunto; ningún CSV sin marcador se acepta como fallback."""
    try:
        marker = json.loads((folder / "_SUCCESS.json").read_text(encoding="utf-8"))
        for name, digest in marker["files"].items():
            if Path(name).name != name or sha256((folder / name).read_bytes()) != digest:
                raise PipelineError("Bundle previo inconsistente")
        payload = (folder / DAILY).read_text(encoding="utf-8")
        rows = list(csv.DictReader(io.StringIO(payload)))
        validate_daily(rows)
        if marker["record_count"] != len(rows):
            raise PipelineError("Conteo del bundle inconsistente")
        return rows
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise PipelineError("Bundle ausente o incompleto") from error


def validate_daily(rows):
    if not rows:
        raise PipelineError("Salida diaria vacía")
    ids = set()
    for r in rows:
        try:
            day = date.fromisoformat(r["date"])
            stamp = datetime.fromisoformat(r["capture_timestamp"].replace("Z", "+00:00"))
            price = float(r["price"])
            if (not REQUIRED.issubset(r) or day.isoformat() != r["date"] or
                not 0 < price < float("inf") or r["currency"] != "ARS" or r["price_unit"] != "kg" or
                not r["product_normalized"] or r["observation_level"] not in {"detail", "species_summary"} or
                not r["capture_id"] or stamp.utcoffset().total_seconds() != 0 or
                r["source_url"] != "https://ssma.magyp.gob.ar/frutas.precios.aspx" or
                len(r["raw_sha256"]) != 64 or any(c not in "0123456789abcdef" for c in r["raw_sha256"]) or
                r["volume"] not in ("", None) or r["observation_id"] in ids or
                r["data_source"] != "MAGYP" or r["source_status"] != "MAGYP" or
                (r["observation_level"] == "detail" and r["variety_normalized"] == "PROM.ESP.")):
                raise ValueError()
            ids.add(r["observation_id"])
        except (KeyError, ValueError, TypeError, AttributeError) as error:
            raise PipelineError("Contrato diario inválido") from error


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


def update(day, raw_root, published, allow_web=False, timeout=40, max_requests=80):
    date.fromisoformat(day)
    if not allow_web:
        raise PipelineError("Adquisición requiere --allow-web")
    # A single run is isolated. Revisions are merged by whole observation date, never by product.
    if list((raw_root / "raw/mcba").glob("*/manifest.json")):
        raise PipelineError("Usar un directorio de captura vacío para esta actualización")
    try:
        result = browser_fetch(day, day, timeout, max_requests, "chromium")
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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--date", required=True)
    p.add_argument("--data-root", type=Path, required=True, help="Carpeta aislada fuera de Git")
    p.add_argument("--published-dir", type=Path, default=ROOT / "data/magyp/dashboard/mcba")
    p.add_argument("--allow-web", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.dry_run:
        date.fromisoformat(a.date)
        print("[FETCH] DRY-RUN: sin requests ni escrituras")
        return
    try:
        update(a.date, a.data_root, a.published_dir, a.allow_web)
    except Exception as error:
        print("[PUBLISH] ERROR " + (str(error) if isinstance(error, PipelineError) else type(error).__name__) +
              "; última salida válida conservada", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
