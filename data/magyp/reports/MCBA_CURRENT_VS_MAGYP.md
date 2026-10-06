# Comparación MCBA — fase 2

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
{
  "classification": "COMPLEMENT_ONLY",
  "current_all": {
    "rows": 70452,
    "date_min": "2024-01-01",
    "date_max": "2026-08-24",
    "product_distinct": 113,
    "variety_distinct": 332,
    "origin_distinct": 52,
    "package_distinct": 12
  },
  "current_daily_overlap": {
    "rows": 1561,
    "date_min": "2026-08-19",
    "date_max": "2026-08-24",
    "product_distinct": 81,
    "variety_distinct": 73,
    "origin_distinct": 28,
    "package_distinct": 10
  },
  "current_monthly_overlap": {
    "rows": 782,
    "date_min": "2024-10-01",
    "date_max": "2025-10-01",
    "product_distinct": 91,
    "variety_distinct": 130,
    "origin_distinct": 30,
    "package_distinct": 11
  },
  "magyp_pilot": {
    "rows": 2876,
    "date_min": "2024-10-02",
    "date_max": "2026-10-05",
    "product_distinct": 89,
    "variety_distinct": 121,
    "origin_distinct": 30,
    "package_distinct": 10
  },
  "matches": {
    "exact": 0,
    "normalized_exact": 299,
    "probable": 987,
    "ambiguous": 377,
    "current_only": 25,
    "magyp_only": 16,
    "monthly_not_comparable": 1077,
    "current_monthly_not_comparable": 782
  },
  "name_differences": 987,
  "ambiguous_candidates": 131,
  "current_precision": {
    "day": 61744,
    "month": 8708
  },
  "current_unit_labels": {
    "$/kg": 70452
  },
  "magyp_units": {
    "ARS/kg": 2876
  },
  "magyp_currencies": {
    "ARS": 2876
  },
  "flags": {
    "price_missing": 0,
    "price_zero": 0,
    "price_negative": 0,
    "currency_missing": 0,
    "unit_missing": 0,
    "product_missing": 0,
    "date_missing": 0,
    "origin_missing": 636,
    "duplicate_candidate": 0,
    "extreme_value_candidate": 0
  },
  "parse_warnings": {
    "kg_semantics_unverified": 2876,
    "official_record_id_not_exported": 2876,
    "currency_from_official_context": 2506,
    "currency_context_transfer_requires_confirmation": 1605,
    "suspicious_source_character_preserved": 39,
    "currency_from_official_documentation": 370
  },
  "price_differences_matched": 0,
  "magyp_dates_not_daily_comparable": [
    "2024-10-02",
    "2024-10-03",
    "2025-10-02",
    "2026-10-05"
  ]
}
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
