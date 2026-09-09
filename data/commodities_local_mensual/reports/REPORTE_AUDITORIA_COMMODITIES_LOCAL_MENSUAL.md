# Reporte de auditoría — commodities locales mensuales

Fecha de auditoría: 2026-09-08

## Dataset y grano

- Archivo auditado: `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_local_mensual/processed/COMMODITIES_LOCAL_MENSUAL_INTEGRADO.csv`.
- Grano esperado: una observación mensual por commodity, fuente, mercado, tipo de precio, moneda y unidad; si se agregan datos diarios, la regla debe quedar en `observaciones`.
- Filas integradas: **0**.
- Filas elegibles para dashboard: **0**.
- Estado general: **sin datos**.

## Cobertura

- Fecha mínima: **sin fecha**.
- Fecha máxima: **sin fecha**.
- Años: sin datos.
- Períodos mensuales: sin datos.
- Fuentes: sin datos.
- Commodities: sin datos.
- Monedas: sin datos.
- Unidades: sin datos.
- Frecuencias: sin datos.
- Tipos de precio: sin datos.

## Controles de calidad

- Fechas inválidas o faltantes: **0**; fechas futuras: **0**.
- Commodity faltante: **0**; fuente faltante: **0**.
- Moneda faltante: **0**; unidad faltante: **0**; tipo de precio faltante: **0**.
- Precio faltante/no numérico: **0**; precio cero: **0**; precio negativo: **0**.
- Duplicados exactos según clave normalizada: **0**.
- Grupos con más de una moneda, unidad, frecuencia o tipo de precio: **0**.

Los ceros, negativos y precios sin moneda o unidad explícita se conservan para trazabilidad en el integrado, pero no deben alimentar las salidas dashboard-ready. Las mezclas detectadas deben resolverse por filtro o por una dimensión explícita; no se agregan silenciosamente.

## Salidas

- `RESUMEN_COBERTURA_COMMODITIES_LOCAL_MENSUAL.csv`: cobertura por fuente, commodity, período y dimensiones metodológicas.
- Las salidas dashboard-ready deben ser compactas y mantenerse separadas de SIO, BCR y World Bank.

## Recomendación

No hay archivos integrados. Coloque una fuente local documentada en `raw/`, ejecute la integración y vuelva a auditar. No se inventan datos ni se habilita una serie visual vacía como si tuviera cobertura.
