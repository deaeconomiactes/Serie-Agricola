# Auditoría de precios mayoristas 2026

## 1. Resumen ejecutivo

Se auditaron **78,445 filas** de `PRECIOS_MAYORISTAS_2026_INTEGRADO.csv`. Esta base contiene precios mayoristas diarios y se mantuvo separada de las cantidades 2024/2025.

La cobertura temporal válida va de **2026-01-02** a **2026-12-25**, con **510 series Alta** y **166 series Media**.

## 2. Cobertura general

- Filas totales: 78,445
- Archivos de origen: 346
- Meses: 2026-01, 2026-02, 2026-03, 2026-04, 2026-05, 2026-06, 2026-07, 2026-08, 2026-12
- Rubros: Frutas, Hortalizas
- Especies únicas: 187
- Precios válidos (> 0): 100.0%

## Cobertura geográfica

- Mercado informado: **61,744 de 78,445 registros (78.7%)**.
- Procedencia informada: **64,488 de 78,445 registros (82.2%)**.
- Mercados detectados: Mercado Central de Buenos Aires.
- Procedencias detectadas: Corrientes, Buenos Aires, Mendoza, Río Negro, Brasil, Salta, Entre Ríos, Jujuy, Chile, Mar del Plata, Tucumán, Ecuador, San Juan, S.Bs.As., Santa Fe, Se Bs.As, Sgo.Est., Perú, Córdoba, Formosa, Misiones, San Pedro, España, Bolivia, Chaco, Paraguay, Egipto, Grecia, Colombia, Italia.
- Mercado inferido por fuente: **61,744 registros**.
- Mercado proveniente de columna explícita: **0 registros**.
- Procedencia proveniente de columnas explícitas: **64,488 registros**.

Los registros provenientes de listas mensuales de frutas y hortalizas 2026 se etiquetan como Mercado Central de Buenos Aires porque esa es la fuente de las listas. La procedencia se conserva únicamente cuando aparece explícitamente en la fuente original.

Mercado representa el mercado/lista/fuente comercial de precios; procedencia representa el origen geográfico del producto. No se mezclan automáticamente.

## 3. Cobertura temporal

El detalle se encuentra en `RESUMEN_COBERTURA_PRECIOS_2026.csv`.

## 4. Cobertura por mercado

El detalle se encuentra en `RESUMEN_MERCADOS_PRECIOS_2026.csv`.

## 5. Cobertura por procedencia

El detalle se encuentra en `RESUMEN_PROCEDENCIAS_PRECIOS_2026.csv`.

## 6. Series utilizables

El nivel de análisis es rubro, mercado, procedencia (si existe), especie, variedad y unidad. La procedencia no es requisito de calidad: la clasificación se basa principalmente en observaciones, fechas distintas, meses distintos y precios válidos.

- Series Alta: 510
- Series Media: 166
- Series Baja: 320

## 7. Calidad y limitaciones

- Fechas inválidas o faltantes: 3.
- Precios faltantes/no numéricos: 0.
- Precios cero: 0.
- Precios negativos: 0.
- Outliers por especie (Q1 -/+ 3*IQR), no eliminados: 2,417.

La base sirve para monitoreo operativo de precios mayoristas. No permite inferir escasez, producción, causalidad, elasticidades ni relaciones precio-cantidad.
