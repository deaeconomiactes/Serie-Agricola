# Precios internos MAGyP de arroz cáscara

**Consulta de fuente:** 17 de noviembre de 2026. **Última observación publicada verificada:** octubre de 2026. La fecha de consulta no convierte octubre en una cotización vigente para noviembre.

## Alcance en el dashboard

El arroz cáscara largo fino y largo ancho está integrado como dos commodities seleccionables dentro de la familia existente **Precio interno MAGyP**. No tiene una familia exclusiva. Las variedades no se promedian ni se fusionan.

La fuente oficial publica precios mensuales en ARS por quintal métrico (ARS/QQ). El dashboard ofrece también ARS/KG como conversión simple de unidad: `ARS/QQ ÷ 100`. Un quintal métrico equivale a 100 kilogramos. La descarga usa los filtros de commodities y el rango Desde/Hasta aplicados, e incluye fuente, fecha efectiva, unidad, etiquetas y hash de trazabilidad.

Son referencias de arroz **cáscara del mercado interno**. No son precios minoristas de arroz elaborado y la página no identifica provincia o plaza; por eso no se atribuyen exclusivamente a productores correntinos. El arroz SIO `ARROZ C.L.F.` sigue como serie separada de operaciones informadas, sin empalme con MAGyP.

La interfaz no muestra la conversión USD/A3500. La base de arroz y su evidencia de origen conservan los campos de auditoría del cálculo para revisión posterior; el cargador visible sólo incorpora filas ARS/QQ y ARS/KG y quita los campos A3500 de gráficos, tablas y CSV descargables.

## Fuente, cobertura y últimos valores verificados

[MAGyP — Precios internos de arroz cáscara](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/regionales/_archivos/000010_Precios%20Locales/000020_Arroz/000001_Precios%20de%20Arroz%20C%C3%A1scara%20Internos.php?accion=imp)

La serie abarca septiembre de 1992 a octubre de 2026: 405 meses con observaciones. En ese intervalo no se publicó precio para agosto de 2014, mayo y junio de 2017, octubre de 2018 y septiembre de 2026. Los faltantes se conservan como faltantes. La tabla repite dos veces la fila de junio de 2026 con los mismos valores; el pipeline cuenta una observación y guarda los localizadores repetidos en la trazabilidad. El asterisco de los valores de agosto de 2023 se conserva porque la fuente no explica su significado.

Valores de octubre de 2026, los últimos verificados al 17/11/2026:

| Commodity | Publicado por MAGyP | Conversión simple |
|---|---:|---:|
| Arroz cáscara largo fino | 40.000 ARS/QQ | 400 ARS/KG |
| Arroz cáscara largo ancho | 48.000 ARS/QQ | 480 ARS/KG |

## Actualización, evidencia e integridad

- `scripts/magyp/rice_prices.py` descarga las páginas públicas sin credenciales y guarda HTML RAW, manifiestos, URL, fecha, estado HTTP, tamaño y SHA-256 bajo `data/magyp/raw/rice_prices/`, que está excluido de Git. GitHub Actions conserva el artefacto de evidencia durante 90 días.
- `data/magyp/dashboard/commodities/rice_internal.csv.gz` conserva las observaciones originales, valores de unidad derivados, datos de cálculo y campos de origen. Cada registro incluye fecha, moneda, unidad, tipo de precio, etiqueta, localizador, `capture_id` y hash SHA-256 de la captura. El RAW y los campos completos permanecen para auditoría.
- La aplicación une las filas internas ARS del arroz a Precio interno MAGyP sin modificar el pipeline compartido de los demás precios. La serie incorporada se limita a ARS/QQ y ARS/KG; la conversión de unidad queda identificada como tal.
- `.github/workflows/update-magyp-rice-prices.yml` actualiza los datos semanalmente los lunes a las 11:21 (Argentina) y admite ejecución manual. Las salidas publicadas sólo se reemplazan después de validaciones de esquema, fechas, unidades, valores, trazabilidad e integridad del histórico.
- `NO_PUBLICATION` indica que la fuente se consultó correctamente y no publicó un mes nuevo; `SOURCE_UNAVAILABLE` indica que no respondió; `PIPELINE_ERROR` indica una falla técnica o de validación. En esos estados se conservan los últimos datos válidos. El dashboard comunica el estado y la última observación por separado.
- La página internacional FOB y los artefactos `rice_fob.csv.gz`, `fob.csv.gz`, fuentes RAW, historial y manifiestos se conservan en el repositorio/evidencia para una eventual revisión. No se exponen en las familias, filtros, gráficos, tablas o descargas del dashboard. Las etiquetas FOB no se promedian ni se fusionan. Los pipelines y actualizaciones existentes de otras familias quedan sin cambios.
- La fuente no declara en la página consultada una licencia o permiso de redistribución; queda pendiente la confirmación institucional.

## Pruebas y verificación de interfaz

Las verificaciones de frontend prueban la carga conjunta con el precio interno existente, la separación de largo fino y largo ancho, unidades ARS/QQ y ARS/KG, filtro temporal y salida CSV con trazabilidad sin conversión USD/A3500. También verifican que los selectores no ofrezcan arroz FOB ni la familia FOB general, y que los archivos FOB permanezcan presentes. Las pruebas existentes de SIO, futuros, Pizarra, FAS, carnes y precios mayoristas controlan que sus flujos continúen disponibles.

Los controles Desde/Hasta, períodos rápidos y descarga CSV son generales del módulo y aplican al rango y a los filtros activos. En la vista interna, arroz aparece en el mismo selector de commodities que las demás referencias MAGyP; las tablas, series del gráfico y exportaciones usan esa selección y no incluyen las filas FOB ni la equivalencia USD/A3500.
