# Reporte de prueba de endpoint SIO

## Fecha de ejecución

2026-09-04

## Comando ejecutado

`python .\explorar_sio_granos.py --test-endpoint get-operaciones --allow-web --save-response --max-requests 1`

## Endpoint probado

https://www.siogranos.com.ar/consulta_publica/operaciones_informadas_ultimas.aspx/GetOperaciones

## Método

POST

## Payload enviado

```json
{
  "pPageSize": 10,
  "pCurrentPage": 1
}
```

## Resultado HTTP

200

## Content-Type

application/json

## Tamaño de respuesta

3656 bytes

## Diagnóstico de respuesta

- JSON válido: sí.
- Contiene datos/lista detectable: sí.
- Cantidad aproximada de registros: 15.
- Respuesta mapeable automáticamente: no; la respuesta expone filas posicionales sin nombres semánticos.
- Requiere sesión: no determinado.
- Requiere parámetros adicionales: no determinado.
- Devuelve HTML: no.
- Error de transporte: ninguno.
- Respuesta guardada como: SIO_test_GetOperaciones_20260904102034.json.
- Claves principales: PageCount, CurrentPage, RecordCount, Items.

## Campos detectados

No se detectaron campos esperables con nombre semántico. Campos JSON realmente detectados: d, PageCount, CurrentPage, RecordCount, Items, ID, Row.

## Próximo paso recomendado

La respuesta SIO contiene datos estructurados, pero no es mapeable automáticamente: validar el esquema de las filas posicionales con el request/respuesta observado en DevTools antes de integrar.

La prueba no paginó, no envió otros parámetros y no generó CSV integrado.
