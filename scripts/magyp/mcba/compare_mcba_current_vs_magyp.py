"""Comparación multiconjunto y sin equivalencia implícita día/mes."""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import atomic_write, csv_bytes, read_jsonl
from scripts.magyp.mcba.model import canonical, number


def current_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        all_rows = list(csv.DictReader(f, delimiter=";"))
    if not all_rows or "mercado" not in all_rows[0] or "fecha" not in all_rows[0]:
        raise ValueError("Schema de base actual no reconocido")
    return [dict(r, _current_row=i + 2) for i, r in enumerate(all_rows)
            if canonical(r["mercado"]) in {"MERCADO CENTRAL DE BUENOS AIRES", "MCBA"}]


def precision(row):
    if row.get("fecha_precision") == "mensual":
        return "month"
    # Regla específica auditada: fuentes 2026 RF/RH; fecha ISO diaria y archivo día.
    origin = row.get("archivo_origen", "").upper()
    if row["fecha"].startswith("2026-") and ("/RF" in origin or "/RH" in origin):
        return "day"
    return "unknown"


def units(row):
    return row.get("unidad_precio_observado") or row.get("unidad") or ""


def current_price(row):
    return number(row.get("precio_observado") or row.get("precio_promedio") or row.get("precio"))



def coverage(rows, magyp=False):
    fields = {"product": "product" if magyp else "especie", "variety": "variety" if magyp else "variedad",
              "origin": "origin" if magyp else "procedencia", "package": "package" if magyp else "envase"}
    dates = [r["observation_date" if magyp else "fecha"] for r in rows
             if r["observation_date" if magyp else "fecha"]]
    return {"rows": len(rows), "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
            **{name + "_distinct": len({canonical(r[field]) for r in rows if r.get(field)})
               for name, field in fields.items()}}


def compare(current, magyp):
    from scripts.magyp.mcba.matching import mutual_unique_matches
    dates = {r['observation_date'] for r in magyp}
    periods = {r['period'] for r in magyp}
    monthly = [r for r in current if precision(r) == 'month' and r['fecha'][:7] in periods]
    daily = [r for r in current if precision(r) == 'day' and r['fecha'] in dates]
    common_dates = {r['fecha'] for r in daily}
    comparable = [r for r in magyp if r['observation_date'] in common_dates]
    result = []
    for match in mutual_unique_matches(daily, comparable):
        m = comparable[match['magyp_index']] if match['magyp_index'] is not None else None
        c = daily[match['current_index']] if match['current_index'] is not None else None
        out = report_row(match['status'], m, c, len(match['candidate_indices']))
        out['matching_rule'] = match['rule']
        out['candidate_references'] = [daily[i].get('_current_row', i) for i in match['candidate_indices']] if m else [comparable[i]['observation_id'] for i in match['candidate_indices']]
        result.append(out)
    # Diagnóstico temporal; nunca se declara match ni diferencia de precio día/mes.
    monthly_periods = {r['fecha'][:7] for r in monthly}
    for m in magyp:
        if m['observation_date'] not in common_dates and m['period'] in monthly_periods:
            out = report_row('monthly_not_comparable', m, None, 0)
            out.update(matching_rule='not_comparable_precision', candidate_references=[])
            result.append(out)
    for c in monthly:
        out = report_row('current_monthly_not_comparable', None, c, 0)
        out.update(matching_rule='not_comparable_precision', candidate_references=[])
        result.append(out)
    return result, daily, monthly


def report_row(status, magyp, current, ambiguous):
    m, c = magyp or {}, current or {}
    cp, mp = current_price(c) if current else None, m.get("price")
    return {"match_status": status, "date_magyp": m.get("observation_date"), "date_current": c.get("fecha"),
            "date_precision_current": precision(c) if current else None,
            "period": m.get("period") or c.get("fecha", "")[:7], "market": "MCBA",
            "type_magyp": m.get("type"), "type_current": c.get("rubro"),
            "product_magyp": m.get("product"), "product_current": c.get("especie"),
            "variety_magyp": m.get("variety"), "variety_current": c.get("variedad"),
            "origin_magyp": m.get("origin"), "origin_current": c.get("procedencia"),
            "package_magyp": m.get("package"), "package_current": c.get("envase"),
            "quality_magyp": m.get("quality"), "size_magyp": m.get("size"), "grade_magyp": m.get("grade"),
            "extra_dimensions_current": c.get("observaciones"),
            "price_magyp": mp, "price_current": cp,
            "price_difference": mp - cp if mp is not None and cp is not None else None,
            "unit_magyp": m.get("price_unit"), "unit_current": units(c),
            "currency_magyp": m.get("currency"), "currency_current": c.get("moneda"),
            "name_difference": bool(current and magyp and any(canonical(m.get(mf)) != canonical(c.get(cf))
                                    for mf, cf in (("product", "especie"), ("variety", "variedad"),
                                                   ("origin", "procedencia"), ("package", "envase")))),
            "candidate_count": ambiguous, "observation_id": m.get("observation_id"),
            "capture_id": m.get("capture_id"), "raw_sha256": m.get("raw_sha256"),
            "current_row": c.get("_current_row"), "current_file": c.get("archivo_origen"),
            "source_url": m.get("source_url")}


def run(data_root, current_file):
    current = current_rows(current_file)
    magyp = read_jsonl(data_root / "analytical/mcba/market_price_observation.jsonl")
    rows, daily, monthly = compare(current, magyp)
    match_counts = Counter(r["match_status"] for r in rows)
    categories = ["exact", "normalized_exact", "probable", "ambiguous",
                  "current_only", "magyp_only", "monthly_not_comparable", "current_monthly_not_comparable"]
    flag_counts = Counter(f for r in magyp for f in r["quality_flags"])
    flags = ["price_missing", "price_zero", "price_negative", "currency_missing", "unit_missing",
             "product_missing", "date_missing", "origin_missing", "duplicate_candidate", "extreme_value_candidate"]
    stats = {"classification": "COMPLEMENT_ONLY", "current_all": coverage(current),
             "current_daily_overlap": coverage(daily), "current_monthly_overlap": coverage(monthly),
             "magyp_pilot": coverage(magyp, True), "matches": {k: match_counts[k] for k in categories},
             "name_differences": sum(r["name_difference"] for r in rows),
             "ambiguous_candidates": sum(r["candidate_count"] > 1 for r in rows),
             "current_precision": dict(Counter(precision(r) for r in current)),
             "current_unit_labels": dict(Counter(units(r) for r in current)),
             "magyp_units": dict(Counter(r["price_unit"] for r in magyp)),
             "magyp_currencies": dict(Counter(r["currency"] for r in magyp)),
             "flags": {k: flag_counts[k] for k in flags}}
    stats["parse_warnings"] = dict(Counter(f for r in magyp for f in r["parse_warnings"]))
    folder = data_root / "reports"
    columns = list(report_row('', None, None, 0)) + ['matching_rule', 'candidate_references']
    atomic_write(folder / "MCBA_CURRENT_VS_MAGYP.csv", csv_bytes(rows, columns))
    stats['price_differences_matched'] = sum(r['price_difference'] is not None and abs(r['price_difference']) > 0.011 for r in rows if r['match_status'] in {'exact','normalized_exact','probable'})
    stats['magyp_dates_not_daily_comparable'] = sorted({r['observation_date'] for r in magyp} - {r['fecha'] for r in daily})
    atomic_write(folder / 'MCBA_PILOT_METRICS.json', (json.dumps(stats, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    report = """# Comparación MCBA — fase 2

Clasificación **COMPLEMENT_ONLY**. Adquisición automatizada con navegador validada;
no se valida reemplazo de promedio mensual, continuidad completa ni equivalencia de todas las dimensiones.

## Reglas

Sólo fechas diarias efectivamente presentes en ambas fuentes. Fechas MAGyP fuera del
histórico actual se informan separadamente, no como pérdida current_only/magyp_only.
Las filas mensuales se incluyen como diagnóstico not_comparable_precision; el ancla
01 del mes no es un día observado. No se calculan diferencias día/mes.

Exact: etiquetas literales y precio. Normalized_exact: NFKC/mayúsculas/espacios y
reglas validated. Probable: sólo reglas observed explícitas en config/mcba_aliases.json.
Manual_review nunca se aplica; no se eliminan diacríticos globalmente. $/kg→ARS/kg
es equivalencia contextual exclusiva de MCBA, con originales reportados.

Claves: mercado MCBA/fecha/tipo/producto/variedad/procedencia/envase/unidad; moneda
explícita incompatible excluye candidato. Coincidencias de precio toleran 0.011.
Sólo parejas MUTUAMENTE ÚNICAS. Múltiples candidatos en cualquiera de las dos fuentes
producen ambiguous, con referencias a todos los candidatos; nunca se elige el primero
ni el precio más cercano. La categoría probable con regla unique_dimensions_price_difference
conserva discrepancias de precio. Quality/size/grade no estructurados en base diaria actual:
no se afirma equivalencia de esas dimensiones. Matching_rule registra qué se usó.

## Métricas

```json
""" + json.dumps(stats, ensure_ascii=False, indent=2) + """
```

## Límites

Prom.Esp. se conserva separado como species_summary. Kg sigue unknown y volumen null.
Moneda documentada como pesos/kg en encabezados oficiales de frutas y hortalizas,
ISO ARS por regla explícita de pesos locales argentinos; RAW legado conserva evidencia contextual.
Monthly tiene coverage_days y aggregation_status=partial_period; expected_days/ratio null
hasta validar calendario oficial. No sustituye K_mes.

Frutilla/Zanahoria y labels ¥ se investigan en MCBA_PHASE2_REPORT.md y los reportes de
cobertura/normalización. No asumir pérdida de producto por una presentación ausente en un día.
No se modifica PRECIOS_MAYORISTAS_INTEGRADO.csv ni frontend.
"""
    atomic_write(folder / "MCBA_CURRENT_VS_MAGYP.md", report.encode("utf-8"))
    print(f"[COMPARE] {len(current)} filas actuales; {len(magyp)} MAGyP; {stats['matches']}")
    return stats


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", type=Path, default=ROOT / "data/magyp")
    p.add_argument("--current", type=Path, default=ROOT / "PRECIOS_MAYORISTAS_INTEGRADO.csv")
    args = p.parse_args()
    run(args.data_root, args.current)


if __name__ == "__main__":
    main()
