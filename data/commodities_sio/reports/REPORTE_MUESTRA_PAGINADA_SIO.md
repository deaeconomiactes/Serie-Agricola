# Reporte de muestra paginada SIO

## Objetivo

Validar una extracción limitada de varias páginas del endpoint GetOperaciones.

## Comando ejecutado

`.\explorar_sio_granos.py --sample-pages --allow-web --save-response --pages 3 --page-size 15 --max-requests 3`

## Parámetros

- pages: 3
- page_size: 15
- max_requests: 3
- endpoint: `https://www.siogranos.com.ar/consulta_publica/operaciones_informadas_ultimas.aspx/GetOperaciones`
- payload base: `{"pPageSize": page_size, "pCurrentPage": pagina}`

## Requests realizados

| Página | Status code | Content-Type | Tamaño respuesta | Registros detectados | Archivo raw | Observaciones |
| --- | --- | --- | ---: | ---: | --- | --- |
| 1 | 200 | application/json | 3605 bytes | 15 | data/commodities_sio/raw/SIO_GetOperaciones_page_1_20260904113726207255.json | respuesta recibida sin retry |
| 2 | 200 | application/json | 3605 bytes | 15 | data/commodities_sio/raw/SIO_GetOperaciones_page_2_20260904113726392763.json | respuesta recibida sin retry; contenido idéntico a la página anterior; pCurrentPage no evidenciado por la respuesta |
| 3 | 200 | application/json | 3605 bytes | 15 | data/commodities_sio/raw/SIO_GetOperaciones_page_3_20260904113726590595.json | respuesta recibida sin retry; contenido idéntico a la página anterior; pCurrentPage no evidenciado por la respuesta |

## Resultado de integración

- Filas leídas antes de deduplicar: 105.
- Archivos procesados: 8.
- Páginas procesadas: 3.
- Duplicados exactos eliminados: 75.
- Conflictos conservados para revisión: 0.
- Filas finales: 30.
- Columnas principales: fecha, año, mes, commodity, fuente, tipo_precio, precio_tipo_original, precio_unidad, campo_precio_original, valor_precio_original, precio_original_texto, moneda, moneda_explicitamente_informada, moneda_inferida, campo_moneda_original, valor_moneda_original, unidad, precio, volumen, volumen_unidad, campo_volumen_original, procedencia, zona, lugar_entrega, operacion, condicion_pago, archivo_origen, fecha_integracion, observaciones, apto_piloto, apto_dashboard, pagina_origen, id_operacion_sio, muestra_tipo, muestra_paginas.
## Resultado de auditoría

- Commodities: CEBADA FORR., Girasol, Maíz, Soja, TRIGO PAN.
- Rango de fechas: 2026-09-04 a 2026-09-04.
- Monedas: ARS, USD; mezcla ARS/USD: sí.
- Unidades: TN.
- Precios válidos por moneda: ARS=16, USD=14.
- Volumen válido: 30/30.
- Procedencias con dato: 30; lugares de entrega con dato: 30; condiciones de pago con dato: 30.
- Páginas solicitadas/procesadas: 3; páginas con filas finales: 1; registros finales por página: 1=15.
- Duplicados por id_operacion_sio en CSV final: 0; duplicados compuestos sin ID: 0.
- apto_piloto: sí=30.
- apto_dashboard: parcial_piloto=30.
- Comparabilidad conjunta ARS/USD: no; deben mantenerse series separadas por moneda.
## Riesgos

- La extracción sigue siendo una muestra limitada y no representa toda la serie histórica.
- No publicar todavía en el dashboard ni mezclar monedas.
- El endpoint puede no cubrir todos los productos ni todo el mercado.

## Recomendación próxima

Las páginas 2/3 devolvieron contenido idéntico a la página anterior y no evidenciaron el efecto de `pCurrentPage`; no ampliar la extracción hasta validar la paginación real. Mantener la deduplicación exacta y repetir la prueba sólo con un request validado en DevTools.
