# Comparación MCBA actual vs MAGyP

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
    "rows": 361,
    "date_min": "2026-08-24",
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
    "rows": 1078,
    "date_min": "2024-10-02",
    "date_max": "2026-08-24",
    "product_distinct": 89,
    "variety_distinct": 113,
    "origin_distinct": 30,
    "package_distinct": 10
  },
  "matches": {
    "exact_available_dimensions": 81,
    "probable": 274,
    "price_difference": 0,
    "unit_difference": 0,
    "current_only": 6,
    "magyp_only": 4,
    "monthly_not_comparable": 719,
    "current_monthly_not_comparable": 782
  },
  "name_differences": 274,
  "ambiguous_candidates": 0,
  "current_precision": {
    "day": 61744,
    "month": 8708
  },
  "current_unit_labels": {
    "$/kg": 70452
  },
  "magyp_units": {
    "ARS/kg": 1078
  },
  "magyp_currencies": {
    "ARS": 1078
  },
  "flags": {
    "price_missing": 0,
    "price_zero": 0,
    "price_negative": 0,
    "currency_missing": 0,
    "unit_missing": 0,
    "product_missing": 0,
    "date_missing": 0,
    "origin_missing": 236,
    "duplicate_candidate": 0,
    "extreme_value_candidate": 0
  },
  "parse_warnings": {
    "kg_semantics_unverified": 1078,
    "official_record_id_not_exported": 1078,
    "currency_from_official_context": 1078,
    "currency_context_transfer_requires_confirmation": 687,
    "suspicious_source_character_preserved": 14
  }
}
```

## Alias exploratorios

{
  "package": {
    "CA": "CAJA",
    "JA": "JAULA",
    "BO": "BOLSA",
    "TO": "TORO",
    "PE": "PERDIDO",
    "AT": "ATADO",
    "BA": "BANDEJA",
    "RT": "RISTRA 100",
    "TT": "TORITO",
    "GR": "GRANEL"
  },
  "origin": {
    "BUENOS AIRES": "BS. AS.",
    "CORRIENTES": "CTES.",
    "ENTRE RIOS": "E. RIOS",
    "RIO NEGRO": "R. NEGRO",
    "SAN JUAN": "S. JUAN",
    "SAN PEDRO": "S. PEDRO",
    "MAR DEL PLATA": "M.D.PLAT"
  }
}

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
