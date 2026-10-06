"""Matching conservador: sólo parejas mutuamente únicas; ambigüedades sin asignar."""
from collections import defaultdict
from scripts.magyp.mcba.labels import canonical, normalized_label, load_rules
from scripts.magyp.mcba.model import number


def price_current(r):
    return number(r.get("precio_observado") or r.get("precio_promedio") or r.get("precio"))


def dimension_key(r, magyp, stage, rules):
    if magyp:
        values = [r["observation_date"], r.get("type"), r.get("product"), r.get("variety"),
                  r.get("origin"), r.get("package"), r.get("price_unit")]
    else:
        values = [r["fecha"], r.get("rubro"), r.get("especie"), r.get("variedad"),
                  r.get("procedencia"), r.get("envase"), r.get("unidad_precio_observado") or r.get("unidad")]
    if stage == "exact":
        return tuple(v or "" for v in values)
    values = [canonical(v) or "" for v in values]
    if values[-1] in {"$/KG", "ARS/KG", "KG"}:
        values[-1] = "KG"  # MCBA: pesos documentados; moneda separada, sin cambiar precios.
    for i, dim in ((2, "product"), (3, "variety"), (4, "origin"), (5, "package")):
        values[i] = normalized_label(dim, values[i], rules, allow_observed=stage == "probable") or ""
    return tuple(values)


def mutual_unique_matches(current, magyp, rules=None):
    rules = load_rules() if rules is None else rules
    remaining_c, remaining_m = set(range(len(current))), set(range(len(magyp)))
    results = []
    for stage, price_agrees in (("exact", True), ("normalized_exact", True), ("probable", True),
                                ("probable", False)):
        index = defaultdict(list)
        for c in sorted(remaining_c):
            index[dimension_key(current[c], False, stage, rules)].append(c)
        adjacency = {}
        reverse = defaultdict(list)
        for m in sorted(remaining_m):
            candidates = []
            for c in index.get(dimension_key(magyp[m], True, stage, rules), []):
                cp, mp = price_current(current[c]), magyp[m].get("price")
                if cp is None or mp is None:
                    continue
                if current[c].get("moneda") and current[c]["moneda"] != magyp[m].get("currency"):
                    continue
                if price_agrees and (cp is None or mp is None or abs(cp - mp) > 0.011):
                    continue
                candidates.append(c)
                reverse[c].append(m)
            if candidates:
                adjacency[m] = candidates
        ambiguous_m = {m for m, cs in adjacency.items() if len(cs) != 1 or len(reverse[cs[0]]) != 1}
        ambiguous_c = {c for m in ambiguous_m for c in adjacency[m]}
        # Conservar todos los participantes del grupo; ninguna selección por orden/precio cercano.
        for m in sorted(ambiguous_m):
            results.append({"status": "ambiguous", "magyp_index": m, "current_index": None,
                            "candidate_indices": adjacency[m], "rule": stage + ":multiple_candidates"})
        for c in sorted(ambiguous_c):
            results.append({"status": "ambiguous", "magyp_index": None, "current_index": c,
                            "candidate_indices": reverse[c], "rule": stage + ":multiple_candidates"})
        remaining_m -= ambiguous_m
        remaining_c -= ambiguous_c
        for m, cs in sorted(adjacency.items()):
            if m not in remaining_m or len(cs) != 1 or cs[0] not in remaining_c:
                continue
            c = cs[0]
            results.append({"status": stage, "magyp_index": m, "current_index": c,
                            "candidate_indices": [c],
                            "rule": stage + (":dimensions_price_tolerance_0.011" if price_agrees else ":unique_dimensions_price_difference")})
            remaining_m.remove(m)
            remaining_c.remove(c)
    results.extend({"status": "magyp_only", "magyp_index": m, "current_index": None,
                    "candidate_indices": [], "rule": "no_candidate"} for m in sorted(remaining_m))
    results.extend({"status": "current_only", "magyp_index": None, "current_index": c,
                    "candidate_indices": [], "rule": "no_candidate"} for c in sorted(remaining_c))
    return results
