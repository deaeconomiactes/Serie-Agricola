"""Reportes offline de cobertura, etiquetas, resumen de especie y diferencias de producto."""
import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import json
from pathlib import Path
from statistics import mean
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import atomic_write, csv_bytes, load_raw, read_jsonl
from scripts.magyp.mcba.model import parse_export, iso_date, number
from scripts.magyp.mcba.labels import normalized_label, normalization_rule, load_rules
from scripts.magyp.mcba.compare_mcba_current_vs_magyp import current_rows, precision


def run(data_root, current_file):
    coverage = []
    for file in sorted((data_root / "raw/mcba").glob("*/manifest.json")):
        payload, m = load_raw(file.parent)
        records = parse_export(payload, m.public_parameters["date_from"], m.public_parameters["date_to"])
        d, end = date.fromisoformat(m.public_parameters["date_from"]), date.fromisoformat(m.public_parameters["date_to"])
        while d <= end:
            rows = [r for r in records if iso_date(r["Fecha"]) == d.isoformat()]
            prices = [number(r["Promedio x Kg."]) for r in rows if number(r["Promedio x Kg."]) is not None]
            coverage.append({"requested_date": d.isoformat(), "rows": len(rows),
                **{name: len({r[field] for r in rows if r[field] is not None and r[field] != ""}) for name, field in
                  (("products", "Especie"), ("varieties", "Variedad"), ("origins", "Procedencia"),
                   ("packages", "Envase"), ("qualities", "Calidad"), ("sizes", "Tamaño"), ("grades", "Grado"))},
                "min_price": min(prices) if prices else None, "max_price": max(prices) if prices else None,
                "hash": m.sha256, "capture_timestamp": m.captured_at_utc, "capture_id": m.capture_id,
                "date_from": m.public_parameters["date_from"], "date_to": m.public_parameters["date_to"],
                "acquisition": m.acquisition_classification or "MANUAL_ONLY",
                "publication_status": "rows_observed" if rows else "no_rows_in_export_unconfirmed",
                "calendar_hint": "weekend" if d.weekday() >= 5 else "weekday"})
            d += timedelta(days=1)
    folder = data_root / "reports"
    atomic_write(folder / "MCBA_COVERAGE_VALIDATION.csv", csv_bytes(coverage, list(coverage[0])))
    rows = read_jsonl(data_root / "analytical/mcba/market_price_observation.jsonl")
    rules = load_rules()
    label_counts = Counter((field, r[field]) for r in rows for field in ("product", "variety", "origin", "package") if r[field])
    labels = []
    for (field, value), count in sorted(label_counts.items()):
        rule, confidence = normalization_rule(field, value, rules)
        labels.append({"field": field, "raw_value": value, "normalized_value": normalized_label(field, value, rules),
                       "count": count, "normalization_rule": rule, "confidence": confidence})
    atomic_write(folder / "MCBA_LABEL_NORMALIZATION.csv", csv_bytes(labels, list(labels[0])))
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["observation_date"], r["product"]].append(r)
    summaries = []
    for (day, product), group in sorted(grouped.items()):
        details = [r["price"] for r in group if r["observation_level"] == "detail" and r["price"] is not None]
        for r in group:
            if r["observation_level"] == "species_summary":
                simple = mean(details) if details else None
                summaries.append({"date": day, "product": product, "summary_price": r["price"],
                                  "detail_rows": len(details), "simple_mean_of_details": simple,
                                  "difference": r["price"] - simple if r["price"] is not None and simple is not None else None,
                                  "formula_status": "not_documented", "observation_id": r["observation_id"]})
    if summaries:
        atomic_write(folder / "MCBA_SPECIES_SUMMARY_VALIDATION.csv", csv_bytes(summaries, list(summaries[0])))
    current = current_rows(current_file)
    observed_dates = sorted({r["observation_date"] for r in rows if r["observation_date"]})
    product_rows = []
    for day in observed_dates:
        for product in ("FRUTILLA", "ZANAHORIA"):
            m = [r for r in rows if r["observation_date"] == day and r["product_normalized"] == product]
            c = [r for r in current if r["fecha"] == day and precision(r) == "day" and r["especie"].upper() == product]
            for origin in sorted({r["origin"] or "" for r in m} | {r["procedencia"] or "" for r in c}):
                product_rows.append({"date": day, "product": product, "origin_raw": origin,
                    "magyp_rows": sum((r["origin"] or "") == origin for r in m),
                    "current_rows": sum((r["procedencia"] or "") == origin for r in c),
                    "interpretation": "labels_not_yet_equated; presentation_difference_is_not_product_loss"})
    atomic_write(folder / "MCBA_PRODUCT_COVERAGE_DIFFERENCES.csv", csv_bytes(product_rows, list(product_rows[0])))
    print(f"[COVERAGE] {len(coverage)} captura/día; {len(observed_dates)} días con datos; {len(labels)} etiquetas")
    return coverage, labels, summaries


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", type=Path, default=ROOT / "data/magyp")
    p.add_argument("--current", type=Path, default=ROOT / "PRECIOS_MAYORISTAS_INTEGRADO.csv")
    args = p.parse_args()
    run(args.data_root, args.current)
