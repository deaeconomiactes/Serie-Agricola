"""Comparación multiconjunto y sin equivalencia implícita día/mes."""
import argparse
import csv
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import atomic_write, csv_bytes, read_jsonl
from scripts.magyp.mcba.model import canonical, number

# Alias exploratorios; sólo generan coincidencias PROBABLES. No transforman la base.
PACKAGE_ALIASES = {"CA": "CAJA", "JA": "JAULA", "BO": "BOLSA", "TO": "TORO", "PE": "PERDIDO",
                   "AT": "ATADO", "BA": "BANDEJA", "RT": "RISTRA 100", "TT": "TORITO", "GR": "GRANEL"}
ORIGIN_ALIASES = {"BUENOS AIRES": "BS. AS.", "CORRIENTES": "CTES.", "ENTRE RIOS": "E. RIOS",
                  "RIO NEGRO": "R. NEGRO", "SAN JUAN": "S. JUAN", "SAN PEDRO": "S. PEDRO",
                  "MAR DEL PLATA": "M.D.PLAT"}


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


def keys(row, magyp=False, aliases=False, omit_unit=False):
    if magyp:
        values = [row["observation_date"], row["type"], row["product"], row["variety"],
                  row["origin"], row["package"], row["price_unit"]]
    else:
        values = [row["fecha"], row.get("rubro"), row["especie"], row["variedad"],
                  row["procedencia"], row["envase"], units(row)]
    values = [canonical(x) or "" for x in values]
    # $/kg se conserva como tal en el reporte; equivalencia contextual local a ARS/kg.
    if values[-1] == "$/KG":
        values[-1] = "ARS/KG"
    if aliases:
        # Sólo para candidatos probables, nunca modifica etiquetas ni IDs canónicos.
        values = ["".join(c for c in unicodedata.normalize("NFKD", v) if not unicodedata.combining(c))
                  for v in values]
        values[4] = ORIGIN_ALIASES.get(values[4], values[4])
        values[5] = PACKAGE_ALIASES.get(values[5], values[5])
    return tuple(values[:-1] if omit_unit else values)


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
    dates = {r["observation_date"] for r in magyp}
    periods = {r["period"] for r in magyp}
    monthly = [r for r in current if precision(r) == "month" and r["fecha"][:7] in periods]
    daily = [r for r in current if precision(r) == "day" and r["fecha"] in dates]
    # No joins por precio sin dimensiones. Consumo 1:1 evita multiplicar coincidencias.
    available = set(range(len(daily)))
    indexed = {}
    for alias, omit_unit in ((False, False), (True, False), (True, True)):
        index = defaultdict(list)
        for i, row in enumerate(daily):
            index[keys(row, aliases=alias, omit_unit=omit_unit)].append(i)
        indexed[alias, omit_unit] = index
    result = []
    for row in magyp:
        matched = None
        status = "magyp_only"
        ambiguous = 0
        for alias, omit_unit in ((False, False), (True, False), (True, True)):
            candidates = [i for i in indexed[alias, omit_unit].get(keys(row, True, alias, omit_unit), [])
                          if i in available]
            same_price = [i for i in candidates if current_price(daily[i]) is not None and row["price"] is not None
                          and abs(current_price(daily[i]) - row["price"]) <= 0.011]
            if same_price:
                matched = same_price[0]
                ambiguous = len(same_price)
                status = "unit_difference" if omit_unit else "probable" if alias else "exact_available_dimensions"
                break
        if matched is None:
            candidates = [i for i in indexed[True, False].get(keys(row, True, True), []) if i in available]
            if candidates:
                matched = min(candidates, key=lambda i: abs((current_price(daily[i]) or 0) - (row["price"] or 0)))
                ambiguous = len(candidates)
                status = "price_difference"
        cur = daily[matched] if matched is not None else None
        if matched is not None:
            available.remove(matched)
        if cur is None and row["period"] in {r["fecha"][:7] for r in monthly}:
            status = "monthly_not_comparable"
        result.append(report_row(status, row, cur, ambiguous))
    for i in sorted(available):
        result.append(report_row("current_only", None, daily[i], 0))
    for row in monthly:
        result.append(report_row("current_monthly_not_comparable", None, row, 0))
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
    categories = ["exact_available_dimensions", "probable", "price_difference", "unit_difference",
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
    atomic_write(folder / "MCBA_CURRENT_VS_MAGYP.csv", csv_bytes(rows, list(rows[0])))
    atomic_write(folder / "MCBA_PILOT_METRICS.json", (json.dumps(stats, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    report = """# Comparación MCBA actual vs MAGyP

Clasificación: **COMPLEMENT_ONLY**. La muestra oficial valida el procesamiento;
no prueba adquisición autónoma, continuidad histórica ni equivalencia mensual.

## Método y límites

Se compara `PRECIOS_MAYORISTAS_INTEGRADO.csv` sin modificarlo. Mercado se selecciona
por MCBA/Mercado Central de Buenos Aires. 2024–2025 `fecha_precision=mensual`
se compara únicamente en cobertura mensual: el primer día es ancla, no observación diaria.
Para 2026 se considera diario sólo archivo RF/RH con fecha ISO; otros casos quedan unknown.
Un día de MAGyP no reproduce K_mes de PFRU/PHOR. No hay coincidencias día/mes declaradas.

Join multiconjunto 1:1: fecha, tipo, especie, variedad, procedencia, envase,
unidad y mercado; luego precio con tolerancia 0.011 (centavos publicados).
NFKC, mayúsculas y espacios son normalización textual; no se corrigen variedades.
`$/kg` se interpreta ARS/kg por contexto local, sin cambiar el original del reporte.
Exact_available_dimensions significa igualdad sólo de dimensiones disponibles;
calidad/tamaño/grado no están estructurados en la base diaria actual y no se valida
su equivalencia. Candidate_count >1 informa ambigüedad, no ID oficial validado.

Probable admite exclusivamente los alias exploratorios detallados abajo; requieren
diccionario para pasar a una equivalencia validada. Además elimina diacríticos sólo
para candidatos probables; los originales y las claves canónicas conservan acentos.
Diferencia de precio conserva
ambos importes. No se consideran precios iguales por cercanía entre productos.
Unidades o moneda vacías se reportan; no se convierten ni rellenan series.

## Métricas reproducibles

```json
""" + json.dumps(stats, ensure_ascii=False, indent=2) + """
```

## Alias exploratorios

""" + json.dumps({"package": PACKAGE_ALIASES, "origin": ORIGIN_ALIASES}, ensure_ascii=False, indent=2) + """

## Dimensiones y cobertura

Export: Fecha, Tipo, Especie, Variedad, Procedencia, Envase, Calidad, Tamaño, Grado,
Kg, Promedio x Kg. Conservados los 11 campos originales y trazabilidad por captura.
No exporta EmpresaID/SucursalID ni códigos de dimensiones disponibles en la grilla;
no se inventan. Precio min/max/modal, volumen, ID oficial y definición de Kg no informados.
Prom.Esp. se conserva como species_summary, separado de detail; nunca se promedian juntos.
ARS/kg es contexto oficial, no campo explícito del XLSX. Evidencia:
[precio promedio en pesos por kilo MCBA](https://ssma.magyp.gob.ar/frutas.preciospromediof.aspx).

La cobertura del piloto se limita a fechas exportadas, no acredita todos los días entre extremos.
La mediana mensual piloto es parcial de días observados, no reemplaza el promedio oficial mensual.
La muestra XLSX presenta `¥` (U+00A5) en etiquetas como PI¥A, JALAPE¥O y ESPA¥A,
mientras la base actual conserva ñ. Se conserva el carácter publicado, se marca
suspicious_source_character_preserved y no se corrige ni declara coincidencia automática.
Las diferencias de cobertura incluyen Frutilla/Tucumán y Zanahoria/Chantenay/Mendoza
presentes en la base diaria actual; deben contrastarse con export/grilla y revisiones oficiales.
Los registros fuera de los períodos del piloto se contabilizan en cobertura total;
no se etiquetan current_only porque no fueron consultados a MAGyP.

## Decisión y siguiente fase

Mantener Excel e integrado productivo. Validar generación autónoma del XLSX GeneXus,
estabilidad de filtros y semántica del promedio. Después comparar una pequeña muestra
2024/2025 mensual oficial contra K_mes y varias fechas diarias 2026. Confirmar códigos,
diccionarios envase/procedencia, licencia/redistribución, moneda y Kg con el organismo.
No implementar SIO avanzado ni sustituir Corrientes, FOB o dashboard en esta etapa.
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
