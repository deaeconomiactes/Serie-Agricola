# Reporte de moneda SIO

Fecha de análisis: 2026-09-04

## Objetivo

Determinar si la moneda del precio puede recuperarse de forma explícita o validable en la respuesta SIO.

## Fuentes revisadas

- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html`
- `data/commodities_sio/raw/SIO_test_GetOperaciones_20260904102034.json`
- `data/commodities_sio/reports/REPORTE_DESCUBRIMIENTO_SIO.md`
- `data/commodities_sio/reports/REPORTE_ENDPOINT_SIO.md`
- `data/commodities_sio/reports/REPORTE_MAPEO_GETOPERACIONES_SIO.md`
- `data/commodities_sio/reports/REPORTE_VALIDACION_MAPEO_SIO.md`
- `data/commodities_sio/reports/REPORTE_UNIDADES_MONEDA_SIO.md`
- `data/commodities_sio/processed/COMMODITIES_SIO_INTEGRADO.csv`

## Evidencia encontrada

### Evidencia directa

- Marcadores textuales encontrados en archivos locales: U$S (7), símbolo $ (32).
- Los símbolos `$` hallados en HTML/JavaScript también corresponden a selectores jQuery; no se consideran por sí solos evidencia de moneda.
- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html`: `símbolo $` en contexto `cument).ready(function () { var timerRefresh; $("#grid").on('reloadGrid', function () { if (document.getElementById("gr`.
- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html`: `símbolo $` en contexto `eInputs(); } } ); $("#grid").jqGrid({ datatype: function () { $.ajax({`.
- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html`: `símbolo $` en contexto `.jqGrid({ datatype: function () { $.ajax({ url: 'operaciones_informadas_ultimas.aspx/GetFechaActual',`.
- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html`: `símbolo $` en contexto `success: function (json) { $('#lblFechaActual').text(json.d); } })`.
- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html`: `símbolo $` en contexto `} }) $.ajax({ url: "operaciones_informadas_ultimas.aspx/GetOperaciones", //PageMet`.
- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html`: `símbolo $` en contexto `data: "{'pPageSize':'" + $('#grid').getGridParam("rowNum") + "','pCurrentPage':'" + $('#grid').getGri`.
- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html`: `símbolo $` en contexto `GridParam("rowNum") + "','pCurrentPage':'" + $('#grid').getGridParam("page") + "'}", //Parametros de entrada del PageMe`.
- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html`: `símbolo $` en contexto `merRefresh = setTimeout(function () { $('#grid').trigger('reloadGrid'); }, 120000);`.
- `data/commodities_sio/raw/SIO_test_GetOperaciones_20260904102034.json`: `U$S` en contexto `cho","SOJA","200,00","Fábrica","SANTA FE\rAARON CASTELLANOS","377,00\nU$S","Rosario N\rEn destino","01/11/2026\n30/11/2026","Contra entrega","False"]},{"ID":8460720,"Row":["`.
- `data/commodities_sio/raw/SIO_test_GetOperaciones_20260904102034.json`: `U$S` en contexto `cio Hecho","MAIZ","110,00","Cámara","CATAMARCA\rALTA GRACIA","180,00\nU$S","Rosario S\rEn destino","04/09/2026\n30/09/2026","Contra entrega","False"]},{"ID":8460653,"Row":["`.
- `data/commodities_sio/raw/SIO_test_GetOperaciones_20260904102034.json`: `U$S` en contexto `ta","Precio Hecho","MAIZ","120,00","Cámara","SANTA FE\rDIAZ","190,00\nU$S","Rosario N\rEn destino","04/09/2026\n03/10/2026","Contra entrega","False"]},{"ID":8460642,"Row":["`.
- `data/commodities_sio/raw/SIO_test_GetOperaciones_20260904102034.json`: `U$S` en contexto `o Hecho","GIRASOL","150,00","Cámara","BUENOS AIRES\rCHILLAR","400,00\nU$S","Quequen\rEn destino","01/03/2027\n31/03/2027","Contra entrega","False"]},{"ID":8460636,"Row":["84`.
- `data/commodities_sio/raw/SIO_test_GetOperaciones_20260904102034.json`: `U$S` en contexto `SOJA","3200,00","Fábrica","SANTA FE\rPUERTO Gral SAN MARTIN","360,00\nU$S","Rosario N\rEn destino","01/05/2027\n31/05/2027","Contra entrega","False"]},{"ID":8460567,"Row":["`.
- `data/commodities_sio/raw/SIO_test_GetOperaciones_20260904102034.json`: `U$S` en contexto `o","CEBADA FORR.","200,00","Cámara","BUENOS AIRES\rNECOCHEA","215,60\nU$S","Quequen\rEn destino","15/12/2026\n15/01/2027","Contra entrega","False"]},{"ID":8460542,"Row":["84`.
- `data/commodities_sio/raw/SIO_test_GetOperaciones_20260904102034.json`: `U$S` en contexto `a","Precio Hecho","MAIZ","30,00","Cámara","SANTA FE\rGALVEZ","202,00\nU$S","Rosario N\rEn destino","15/09/2026\n15/10/2026","Contra entrega","False"]}]}}`.

### Evidencia indirecta

- Los reportes locales previos documentan la presencia de texto monetario embebido en el valor original, pero no validan una columna separada.
- Los valores de `Row` contienen marcadores monetarios en las posiciones 10; el mapeo estructural las asocia al precio, no a una columna `moneda`.

### Sin evidencia

- No se encontró un campo JSON con nombre `moneda`, `currency` o equivalente.
- Las columnas `colNames`/`colModel` observadas no contienen una columna separada de moneda.
- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html` no presenta una etiqueta HTML visible de moneda.

## Revisión de posiciones Row

- Archivo de mapeo revisado: `mapeo_getoperaciones_sio.local.json`.
- Longitudes de Row observadas: 15.
- Posiciones con marcadores monetarios: 10.
- Posiciones Row no utilizadas por el mapeo: ninguna.
- Se revisaron los valores no utilizados y no apareció una posición adicional identificable como moneda; la posición de precio conserva el texto original.

## Resultado

C. Moneda no determinable con los archivos actuales.

La presencia de `U$S` o `$` dentro del valor original del precio no se trata como una moneda separada y validada. No permite por sí sola completar `moneda` ni habilitar comparaciones monetarias.

## Decisión metodológica

- Si la moneda es explícita en un campo respaldado por la respuesta, permitir completar `moneda`.
- Si la moneda no es explícita, mantener `moneda=Sin especificar`.
- Si sólo hay evidencia débil o embebida en un valor, no completar moneda automáticamente; marcar observación.
- No asumir ARS ni USD por tratarse de SIO.

## Impacto en aptitud dashboard

`apto_piloto` puede permanecer en sí porque la muestra tiene fecha, commodity, precio válido, fuente y unidades respaldadas. `apto_dashboard` debe permanecer en no mientras la moneda no quede validada y no exista homogeneidad monetaria. Sin moneda no se deben comparar precios ni variaciones monetarias en el dashboard.

## Próximo paso recomendado

Buscar una exportación manual o respuesta de navegador/DevTools que exponga una columna o metadato de moneda. Si `GetOperaciones` no la devuelve, evaluar otro endpoint o parámetro sólo mediante una prueba controlada y documentada; no hacer paginación masiva ni llamadas desde el dashboard.
