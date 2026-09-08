# Arquitectura multi-fuente de commodities

Esta carpeta prepara una futura arquitectura para integrar varias fuentes de commodities agrícolas sin mezclarlas con frutas y hortalizas ni con los módulos actuales del dashboard.

## Fuentes posibles

- BCR/Cámara Arbitral: referencia local preferida para precios de pizarra, con descarga manual/API autorizada.
- SIO Granos: alternativa local prioritaria a evaluar por sus operaciones y precios de referencia.
- World Bank Pink Sheet: referencia internacional mensual/anual.
- BCRA IPMP: índice agregado diario de materias primas, contextual y no equivalente a un precio spot.
- FAOSTAT/FAO: estadística agrícola internacional, con reglas propias por dominio.
- granos.ar: alternativa técnica no oficial, sujeta a validar procedencia, licencia y estabilidad.

Cada fuente debe conservar sus propias reglas: unidad, moneda, mercado, tipo de precio, frecuencia, cobertura, fecha de actualización y condiciones comerciales. No se debe unir una serie local de pizarra con un índice, una referencia internacional o un futuro sólo porque comparten commodity y fecha.

## Estructura prevista

- `raw/`: descargas originales por fuente.
- `processed/`: datos normalizados conservando la procedencia.
- `reports/`: auditorías multi-fuente y comparabilidad.
- `catalogo_fuentes_commodities.csv`: estado y criterios de cada fuente.

El futuro CSV integrado multi-fuente se llamaría `COMMODITIES_AGRICOLAS_INTEGRADO.csv`. Esta etapa sólo deja documentación, carpetas y catálogo; todavía no se implementan descargadores alternativos.

## Regla de separación

Commodities sigue siendo una tercera familia separada de cantidades frutihortícolas y precios mayoristas frutihortícolas. La eventual integración visual requerirá una validación metodológica previa y no modificará el dashboard hasta contar con datos comparables y autorizados.
