# Reporte de request observado en DevTools SIO

## Objetivo

Identificar el payload real usado por la grilla SIO para paginar operaciones.

## Archivo analizado

- Tipo: cURL local.
- Archivo: `data/commodities_sio/devtools/getoperaciones_.page2.curl.txt`.
- El archivo fuente no se copia ni se versiona; este reporte omite cookies, autorizaciones, tokens e IDs de sesión.

## Endpoint observado

- `/Consulta_publica/operaciones_informadas_ultimas.aspx/GetOperaciones`

## Método

- POST

## Requests candidatos detectados

| Endpoint | Método | Tipo | Contiene payload | Parámetros detectados | Evidencia | Confianza | Observaciones |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/Consulta_publica/operaciones_informadas_ultimas.aspx/GetOperaciones` | POST | cURL | sí | pPageSize, pCurrentPage | cURL local; no ejecutado | alta | GetOperaciones detectado |

## Parámetros de paginación observados

| Parámetro | Valor observado | Posible función | Evidencia | Confianza |
| --- | --- | --- | --- | --- |
| pPageSize | `20` | tamaño de página del PageMethod | Payload local sanitizado. | alta si pertenece a GetOperaciones; media en otro request SIO. |
| pCurrentPage | `1` | número de página del PageMethod | Payload local sanitizado. | alta si pertenece a GetOperaciones; media en otro request SIO. |

## Headers no sensibles

- `accept: application/json, text/javascript, */*; q=0.01`
- `content-type: application/json; charset=UTF-8`
- `origin: https://www.siogranos.com.ar`
- `referer: https://www.siogranos.com.ar/Consulta_publica/`
- `user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0`
- `x-requested-with: XMLHttpRequest`

No se listan `Cookie`, `Authorization`, tokens, credenciales ni IDs de sesión.

## Payload sanitizado

### /Consulta_publica/operaciones_informadas_ultimas.aspx/GetOperaciones

```json
{'pPageSize':'20','pCurrentPage':'1'}
```

## Comparación con payload anterior

Payload anterior controlado:

```json
{"pPageSize": 15, "pCurrentPage": 1/2/3}
```

- Parámetros observados en DevTools: pPageSize, pCurrentPage.
- Parámetros del payload anterior que no aparecen: ninguno.
- Parámetros adicionales observados: ninguno.
- La comparación describe sólo la captura local; no infiere parámetros ausentes.

## Diagnóstico

A. El payload real de GetOperaciones queda claro en esta captura local. El nombre local refiere página 2, mientras el valor observado es `pCurrentPage=1`; puede corresponder a indexación base cero o requerir confirmar la captura, sin asumir una de esas opciones.

## Recomendación próxima

A. El payload real parece identificable. Preparar una prueba controlada separada con máximo 2 requests, sólo después de revisar manualmente sus valores y condiciones de uso.

Este análisis es local: no ejecuta cURL ni realiza requests web.
