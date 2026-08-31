# Auditoría de precios mayoristas

## 1. Resumen ejecutivo

Se auditaron **108,331 filas** de `PRECIOS_MAYORISTAS_INTEGRADO.csv`. Esta base de precios se mantuvo separada de las cantidades 2024/2025.

Los archivos de salida que conservan el sufijo `2026` son copias legacy de compatibilidad y ya no representan exclusivamente ese año.

La cobertura temporal válida va de **2024-12-29** a **2026-12-25**, con **581 series Alta** y **180 series Media**.

## 2. Cobertura general

- Filas totales: 108,331
- Archivos de origen: 346
- Meses: 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02, 2026-03, 2026-04, 2026-05, 2026-06, 2026-07, 2026-08, 2026-12
- Rubros: #Ref!, Frutas, Hortalizas, Subproductos
- Especies únicas: 251
- Precios válidos (> 0): 99.9%

## Cobertura geográfica

- Mercado informado: **108,331 de 108,331 registros (100.0%)**.
- Procedencia informada: **94,374 de 108,331 registros (87.1%)**.
- Mercados detectados: Mercado Central de Buenos Aires, Mercado de Corrientes.
- Procedencias detectadas: Corrientes, Buenos Aires, Mendoza, Río Negro, Jujuy, Salta, Brasil, Entre Ríos, Chile, Mar del Plata, Tucumán, Ecuador, San Juan, S.Bs.As., Santa Fe, Misiones, Formosa, Se Bs.As, Sgo.Est., Perú, Chaco, Córdoba, San Pedro, España, Bolivia, Paraguay, Egipto, Grecia, Colombia, San Luis.
- Mercado inferido por fuente: **108,331 registros**.
- Mercado proveniente de columna explícita: **0 registros**.
- Procedencia proveniente de columnas explícitas: **94,374 registros**.

Los registros de listas mensuales de frutas y hortalizas se etiquetan como Mercado Central de Buenos Aires. Los registros provenientes del archivo MARTIN MICELLI 26-08-2026.xlsx se etiquetan como Mercado de Corrientes. La procedencia se conserva como origen declarado del producto cuando la fuente lo informa.

Mercado representa el mercado/lista/fuente comercial de precios; procedencia representa el origen geográfico del producto. No se mezclan automáticamente.

## 3. Cobertura temporal

El detalle se encuentra en `RESUMEN_COBERTURA_PRECIOS.csv`.

## 4. Cobertura por mercado

El detalle se encuentra en `RESUMEN_MERCADOS_PRECIOS.csv`.

## 5. Cobertura por procedencia

El detalle se encuentra en `RESUMEN_PROCEDENCIAS_PRECIOS.csv`.

## 6. Series utilizables

El nivel de análisis es rubro, mercado, procedencia (si existe), especie, variedad y unidad. La procedencia no es requisito de calidad: la clasificación se basa principalmente en observaciones, fechas distintas, meses distintos y precios válidos.

- Series Alta: 581
- Series Media: 180
- Series Baja: 530

## 7. Calidad y limitaciones

- Fechas inválidas o faltantes: 3.
- Precios faltantes/no numéricos: 56.
- Precios cero: 0.
- Precios negativos: 0.
- Outliers por especie (Q1 -/+ 3*IQR), no eliminados: 2,305.

La base sirve para monitoreo operativo de precios mayoristas. No permite inferir escasez, producción, causalidad, elasticidades ni relaciones precio-cantidad.
