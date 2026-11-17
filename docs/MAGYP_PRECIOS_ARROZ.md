# Precios MAGyP de arroz

**Verificación de fuente:** 17 de noviembre de 2026. **Último mes con valores publicados en ambas páginas:** octubre de 2026. La fecha de ese último dato no debe interpretarse como una cotización de noviembre.

## Fuentes y definición

| Familia | Fuente primaria | Qué representa | Unidad publicada |
|---|---|---|---|
| Interna | [MAGyP — Precios de Arroz Cáscara Internos](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/regionales/_archivos/000010_Precios%20Locales/000020_Arroz/000001_Precios%20de%20Arroz%20C%C3%A1scara%20Internos.php?accion=imp) | Precio mensual de arroz cáscara largo fino y largo ancho del mercado interno. La tabla no identifica provincia ni plaza. | ARS por quintal métrico (QQ) |
| Internacional | [MAGyP — Arroz Mensual U$S por Ton FOB](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/regionales/_archivos/000020_Precios%20Internacionales/000052_Arroz/000001_Arroz%20Mensual%20U%24S%20x%20Ton%20FOB.php) | Referencias mensuales internacionales FOB para distintas etiquetas de origen/calidad. La página atribuye los datos a Osiriz/InfoArro. | USD por tonelada (TN) |

El precio interno corresponde a arroz **cáscara**. No describe arroz elaborado ni un precio minorista, y no necesariamente corresponde a productores correntinos. Largo fino y largo ancho permanecen como series independientes. El arroz SIO `ARROZ C.L.F.` ya existente es una serie de operaciones informadas; conserva su frecuencia, dimensiones y metodología propias y no se empalma con MAGyP.

## Cobertura y últimos valores verificados

### Precio interno

La tabla cubre septiembre de 1992 a octubre de 2026: 405 meses con valores y cinco meses sin precio publicado en el intervalo: agosto de 2014, mayo y junio de 2017, octubre de 2018 y septiembre de 2026. Los huecos no se interpolan. La página repite dos veces adicionales la fila de junio de 2026 con valores idénticos; el pipeline cuenta una observación y conserva las ubicaciones duplicadas en la trazabilidad. Los valores de agosto de 2023 terminados en `*` mantienen el marcador original; la página no explica su significado.

Último período con datos en la consulta del 17/11/2026: octubre de 2026.

| Variedad | Precio MAGyP | Conversión de unidad | Equivalencia USD/A3500 |
|---|---:|---:|---:|
| Largo fino | 40.000,00 ARS/QQ | 400,00 ARS/KG | 26,2292 USD/QQ |
| Largo ancho | 48.000,00 ARS/QQ | 480,00 ARS/KG | 31,4750 USD/QQ |

Un quintal métrico equivale exactamente a 100 kilogramos. Por eso ARS/KG se deriva como ARS/QQ ÷ 100 y conserva el valor original en ARS/QQ y la regla en cada registro.

La equivalencia USD no es una cotización publicada por MAGyP. Para cada mes completo con precio interno y datos A3500, se calcula `ARS/QQ ÷ media aritmética de las cotizaciones diarias A3500 publicadas en el mismo mes`. Se omite mayo de 2022 porque la serie A3500 del proyecto comienza el 17 de ese mes; también se omite el mes en curso, que aún no está completo. La cobertura derivada disponible en esta captura va de junio de 2022 a octubre de 2026. En octubre de 2026 el promedio utilizado es 1.525,0191 ARS/USD, con 21 observaciones del 1 al 30 de octubre. No se usa un tipo de cambio actual para precios históricos. Esta equivalencia no debe describirse como el promedio mensual oficial del BCRA.

### Referencia internacional FOB

Hay precios observados desde enero de 2017 hasta octubre de 2026. No se encontraron observaciones para julio y diciembre de 2017; enero, julio, agosto, septiembre y diciembre de 2018. No se rellenan esos meses. La tabla vigente mostraba noviembre y diciembre de 2026 vacíos al momento de la consulta; se conservan como faltantes y no se presentan como precios.

Últimos valores positivos publicados, todos para octubre de 2026:

| Etiqueta original MAGyP | USD/TN FOB |
|---|---:|
| Usa2/4 | 673 |
| Thai100 | 492 |
| Tai Parb | 505 |
| Inde 5 | 386 |
| Viet5 | 417 |
| Uru5 | 598 |
| Thai25 | 469 |
| Viet25 | 405 |
| Pak 25 | 384 |
| A1Super | 411 |

Las páginas de 2017–2024 contienen doce etiquetas; desde 2025 contienen diez. Se conservan los rótulos que la fuente muestra, incluidas las etiquetas históricas `Thai5` e `Inde 25`. No se les asignan equivalencias ni se fusionan con otra calidad. No se combina FOB con el precio interno.

## Publicación, trazabilidad y actualización

- `scripts/magyp/rice_prices.py` descarga las páginas públicas sin credenciales y guarda HTML RAW, manifiesto, URL, fecha, estado HTTP, tamaño y SHA-256 bajo `data/magyp/raw/rice_prices/` (directorio fuera de Git). Los artefactos de Actions retienen RAW y salidas por 90 días.
- Cada fila de dashboard conserva fuente, fecha mensual, unidad, moneda, etiqueta original, localizador de tabla/celda, `capture_id` y hash SHA-256 del HTML. Las conversiones internas agregan los campos de la regla aplicada y el hash/URL del archivo A3500 ya disponible en el proyecto.
- Las salidas `data/magyp/dashboard/commodities/rice_internal.csv.gz` y `rice_fob.csv.gz` son CSV gzip y sólo se reemplazan tras validar esquema, fechas, unidades, precios, trazabilidad e integridad histórica. El dashboard descomprime el bundle al cargar; el CSV descargable desde la interfaz sigue siendo texto CSV. Ante `SOURCE_UNAVAILABLE`, `PIPELINE_ERROR`, tabla incompleta o reducción/conflicto del histórico, se preservan los últimos bundles válidos y se informa el estado en `data/magyp/reports/RICE_PRICES_STATUS.json`.
- `UPDATED` indica una salida con cambios; `NO_PUBLICATION` indica consulta válida sin cambios publicables; `SOURCE_UNAVAILABLE` indica que no se obtuvo la fuente; `PIPELINE_ERROR` indica un fallo técnico o de validación. El último dato observado se informa por separado del día de consulta.
- `.github/workflows/update-magyp-rice-prices.yml` consulta semanalmente los lunes a las 11:21 de Argentina y puede ejecutarse manualmente. Publica los CSV y el estado sólo desde `main`, y dispara el despliegue explícito del dashboard cuando cambia una observación o el estado visible de la fuente.
- La actualización no consulta la página en el navegador: GitHub Pages sirve CSV estáticos. La licencia o permiso de redistribución no está declarado en las páginas consultadas; el dashboard atribuye la fuente y esta condición queda pendiente de confirmación institucional.

## Dashboard

El selector de Commodities ofrece las familias “Arroz cáscara interno” y “Arroz internacional FOB” por separado. El módulo muestra fuente, unidad, período efectivo, última observación, evolución mensual, variaciones mensual e interanual, filtro Desde/Hasta, accesos rápidos de 12 meses/5 años/todo y descarga CSV del período filtrado. El CSV mantiene los campos de origen, conversiones y trazabilidad disponibles. La fuente interna inicia en ARS/QQ; ARS/KG y USD/QQ se pueden seleccionar como series explícitas con su moneda y unidad.

## Verificación

La implementación incluye pruebas de parseo de fechas y unidades, etiquetas y huecos FOB, duplicados idénticos y conflicto de precios, fórmulas de unidad y A3500, integridad histórica, conservación de la última salida ante ausencia de publicación/fuente y validación de bundles. También se probó el dashboard en Chrome a escritorio y con emulación móvil de 390 px: filtros por período, atajos, visualización interna y FOB, selección ARS/KG y USD/QQ, y descarga CSV. El navegador reportó 120 observaciones FOB para nov/2025–oct/2026 y 11 observaciones de largo fino para ese rango, con campos de trazabilidad; se verificó el contenido del CSV FOB guardado localmente.
