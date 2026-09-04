# Reporte de diagnóstico de paginación SIO

## Objetivo

Diagnosticar si el endpoint GetOperaciones admite paginación real y con qué parámetros.

## Evidencia revisada

- `data/commodities_sio/reports/REPORTE_DESCUBRIMIENTO_SIO.md`
- `data/commodities_sio/reports/REPORTE_ENDPOINT_SIO.md`
- `data/commodities_sio/reports/REPORTE_MAPEO_GETOPERACIONES_SIO.md`
- `data/commodities_sio/reports/REPORTE_MUESTRA_PAGINADA_SIO.md`
- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html` (ignorado por Git, si está disponible)
- respuestas JSON raw locales de `GetOperaciones` (ignoradas por Git)

## Resultado de muestra paginada

- Páginas solicitadas: 3 (límite solicitado: 3).
- Page size: 15.
- Requests realizados: 3.
- Registros brutos: 45; registros únicos por ID/Row: 15.
- Porcentaje de duplicación: 66.7% (30/45 filas excedentes).
- IDs repetidos en exceso: 30.
- IDs repetidos: 8460968, 8461025, 8461031, 8461035, 8461037, 8461039, 8461041, 8461043, 8461050, 8461053, 8461054, 8461061, 8461062, 8461065, 8461066.
- Página 2/3 idéntica a página 1: sí.

| Página | Payload exacto | Status | Registros | IDs/Rows respecto de página 1 | Raw | Observaciones |
| --- | --- | ---: | ---: | --- | --- | --- |
| 1 | `{"pPageSize":15,"pCurrentPage":1}` | 200 | 15 | línea base | data/commodities_sio/raw/SIO_test_pagination_page_1_20260904114841918428.json | respuesta recibida sin retry; payload exacto registrado |
| 2 | `{"pPageSize":15,"pCurrentPage":2}` | 200 | 15 | idéntica a la página anterior (IDs y Rows) | data/commodities_sio/raw/SIO_test_pagination_page_2_20260904114842044691.json | respuesta recibida sin retry; payload exacto registrado; páginas repetidas |
| 3 | `{"pPageSize":15,"pCurrentPage":3}` | 200 | 15 | idéntica a la página anterior (IDs y Rows) | data/commodities_sio/raw/SIO_test_pagination_page_3_20260904114842204461.json | respuesta recibida sin retry; payload exacto registrado; páginas repetidas |

## Parámetros usados

Se usó únicamente el payload respaldado por el JavaScript local de la grilla:

```json
{"pPageSize": 15, "pCurrentPage": 1}
{"pPageSize": 15, "pCurrentPage": 2}
{"pPageSize": 15, "pCurrentPage": 3}
```

No se enviaron filtros de producto, fecha o moneda.

## Parámetros candidatos observados

| Parámetro | Evidencia | Fuente de evidencia | Confianza | Requiere prueba | Observaciones |
| --- | --- | --- | --- | --- | --- |
| pPageSize | Clave enviada por el JavaScript del PageMethod; se alimenta de jqGrid rowNum. | C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html | alta | sí | El payload se probó en la muestra y no demostró paginación. |
| pCurrentPage | Clave enviada por el JavaScript del PageMethod; se alimenta de jqGrid page. | C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html | alta | sí | El payload se probó con páginas 1/2/3 y las respuestas deben compararse. |
| page | Aparece como argumento de getGridParam("page") dentro de jqGrid. | C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html | media | sí | No se observó serializado como clave del POST. |
| rows | Aparece como rowNum de jqGrid, que alimenta pPageSize. | C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html | media | sí | No se observó serializado como clave del POST. |
| jqGrid pager | La página usa jqGrid, #pager y jsonReader page/total/records. | C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html | alta | no | Evidencia de grilla, no de un payload alternativo. |

## Hipótesis

- `pCurrentPage` puede ser aceptado por el JavaScript pero ignorado o normalizado por el endpoint.
- El endpoint puede requerir estado de sesión u otros datos de la grilla que no aparecen en la evidencia local disponible.
- jqGrid puede manejar `page` y `rows` internamente, pero no se observó evidencia de que esas claves sean el POST real del PageMethod.
- La respuesta puede devolver siempre las últimas operaciones o requerir otro endpoint/exportación.
- `PageCount`, `CurrentPage` y `RecordCount` pueden no estar siendo informados correctamente por la respuesta observada; no se usan para inventar páginas.

## Próximo paso recomendado

La evidencia más fuerte identifica `pPageSize`/`pCurrentPage`, pero la prueba controlada no valida paginación si las páginas repiten IDs/Rows. No ampliar la extracción. Usar DevTools del navegador para observar el request real y la respuesta de la grilla; si coincide con este payload y sigue repitiendo contenido, limitar el uso a la última página disponible o evaluar la exportación manual. No probar variantes arbitrarias sin nueva evidencia.

## Resultado de integración

- Filas leídas antes de deduplicar: 195.
- Archivos procesados: 14.
- Páginas procesadas: 3.
- Duplicados exactos eliminados: 151; con ID: 151; por Row: 151.
- Conflictos conservados para revisión: 0.
- Filas finales: 44.
- Estado derivado de paginación: duplicada.
- Observación: paginación no validada; páginas repetidas.
- Columnas principales: fecha, año, mes, commodity, fuente, tipo_precio, precio_tipo_original, precio_unidad, campo_precio_original, valor_precio_original, precio_original_texto, moneda, moneda_explicitamente_informada, moneda_inferida, campo_moneda_original, valor_moneda_original, unidad, precio, volumen, volumen_unidad, campo_volumen_original, procedencia, zona, lugar_entrega, operacion, condicion_pago, archivo_origen, fecha_integracion, observaciones, apto_piloto, apto_dashboard, pagina_origen, id_operacion_sio, muestra_tipo, muestra_paginas.
## Paginación y duplicados

- Páginas procesadas: 3.
- Filas brutas: 45.
- Filas únicas por ID/Row: 15.
- Duplicados por ID: 30.
- Duplicados exactos por Row: 30.
- Porcentaje de duplicación: 66.7%.
- estado_paginacion: `duplicada`.
- Si las páginas repiten contenido, no se habilita `apto_dashboard=si`; el estado se mantiene en `parcial_piloto` o `no`.
