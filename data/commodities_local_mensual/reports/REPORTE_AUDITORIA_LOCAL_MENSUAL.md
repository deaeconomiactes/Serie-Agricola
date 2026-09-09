# Reporte de auditoría — histórico local mensual de commodities

Fecha de auditoría: 2026-09-09

## Dataset y grano

- Archivo auditado: `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_local_mensual/processed/COMMODITIES_LOCAL_MENSUAL_INTEGRADO.csv`.
- Grano esperado: una observación por commodity, fuente, plaza/mercado, tipo de precio, moneda, unidad y mes.
- Filas integradas: **668**.
- Precios numéricos: **668**; filas elegibles para dashboard: **668**.
- Estado general: **apta con brechas**.

## Cobertura

- Fecha mínima: **2020-01-01**.
- Fecha máxima: **2026-08-01**.
- Años: `2020`, `2021`, `2022`, `2023`, `2024`, `2025`, `2026`.
- Meses/períodos: **80**.
- Commodities: `Cebada forrajera`, `Girasol`, `Maíz`, `Soja`, `Sorgo`, `Trigo`.
- Fuentes: `Secretaría de Agricultura - Precios Internos de los Principales Granos`.
- Mercados/plazas: `Argentina / mercado interno — B.BLANCA`, `Argentina / mercado interno — CORDOBA`, `Argentina / mercado interno — DARSENA`, `Argentina / mercado interno — QUEQUEN`, `Argentina / mercado interno — ROSARIO`.
- Monedas: `ARS`.
- Unidades: `TN`.
- Tipos de precio: `Precio interno mensual`.

## Controles de calidad

- Fechas faltantes o inválidas: **0**; fechas futuras: **0**.
- Precios faltantes/no numéricos: **0**; precios cero: **0**; precios negativos: **0**.
- Duplicados exactos según dimensiones del integrado: **0**.
- Meses faltantes dentro del rango de cada serie: **440**.
- Campos requeridos faltantes: `commodity`=0, `fuente`=0, `mercado`=0, `tipo_precio`=0, `moneda`=0, `unidad`=0, `frecuencia`=0.

Los precios cero, negativos, sin fecha o sin dimensiones metodológicas no alimentan el dashboard-ready. Las plazas se mantienen separadas dentro de `mercado`; no se combinan silenciosamente con SIO, FOB, FAS ni World Bank.

## Aptitud para dashboard histórico

La aptitud se calcula por serie en `RESUMEN_LOCAL_MENSUAL_SERIES.csv`. Una serie sin precio positivo no es apta; una serie con huecos se marca **apta con brechas** y requiere una lectura explícita de cobertura antes de usar variaciones o comparaciones interanuales.

## Archivos generados

- `RESUMEN_LOCAL_MENSUAL.csv`: indicadores generales de filas, cobertura, validez, dimensiones y continuidad.
- `RESUMEN_LOCAL_MENSUAL_SERIES.csv`: auditoría por serie metodológicamente homogénea.
- `RESUMEN_COBERTURA_COMMODITIES_LOCAL_MENSUAL.csv`: compatibilidad con el reporte anterior, por período y plaza.

## Recomendación

La fuente es utilizable para una prueba histórica con brechas visibles; no interpolar meses faltantes ni presentar continuidad donde no exista.
