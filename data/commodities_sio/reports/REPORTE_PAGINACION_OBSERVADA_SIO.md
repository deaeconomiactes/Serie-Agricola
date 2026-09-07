# Reporte de paginación observada SIO

## Objetivo

Validar el efecto real de `pCurrentPage` usando exclusivamente el payload observado en DevTools y un máximo de tres requests.

## Payload observado en DevTools

```json
{"pPageSize":"20","pCurrentPage":"1"}
```

No se enviaron filtros, fechas ni parámetros adicionales.

## Requests realizados

- Endpoint: `https://www.siogranos.com.ar/consulta_publica/operaciones_informadas_ultimas.aspx/GetOperaciones`
- Límite solicitado: 3; límite efectivo: 3.

| pCurrentPage | pPageSize | Status | Content-Type | Registros | IDs detectados | Hash ID/Row | Raw | Notas |
| ---: | ---: | ---: | --- | ---: | --- | --- | --- | --- |
| 0 | 20 | 200 | application/json | 15 | 8463753, 8463737, 8463706, 8463676, 8463670, 8463662, 8463660, 8463651, 8463648, 8463645, 8463618, 8463616, 8463612, 8463609, 8463606 | 4e09276374125786 | data/commodities_sio/raw/SIO_GetOperaciones_observed_pCurrentPage_0_20260907092400331960.json | respuesta recibida sin retry; payload observado exacto |
| 1 | 20 | 200 | application/json | 15 | 8463753, 8463737, 8463706, 8463676, 8463670, 8463662, 8463660, 8463651, 8463648, 8463645, 8463618, 8463616, 8463612, 8463609, 8463606 | 4e09276374125786 | data/commodities_sio/raw/SIO_GetOperaciones_observed_pCurrentPage_1_20260907092400468797.json | respuesta recibida sin retry; payload observado exacto |
| 2 | 20 | 200 | application/json | 15 | 8463753, 8463737, 8463706, 8463676, 8463670, 8463662, 8463660, 8463651, 8463648, 8463645, 8463618, 8463616, 8463612, 8463609, 8463606 | 4e09276374125786 | data/commodities_sio/raw/SIO_GetOperaciones_observed_pCurrentPage_2_20260907092400617887.json | respuesta recibida sin retry; payload observado exacto |

## Comparación

| Comparación | Filas iguales | IDs iguales | Hash Row igual | Conclusión |
| --- | --- | --- | --- | --- |
| 0 vs 1 | sí | sí | sí | idénticas |
| 1 vs 2 | sí | sí | sí | idénticas |
| 0 vs 2 | sí | sí | sí | idénticas |

## Diagnóstico

- **C. pCurrentPage no cambia la respuesta.** Las tres respuestas tienen las mismas firmas ID/Row.

## Recomendación

No ampliar la extracción mediante `GetOperaciones`. El próximo camino técnico es capturar el botón **Exportar Operaciones** en DevTools o usar una descarga manual desde el navegador. Si se repite la captura de grilla, limpiar Network y capturar únicamente el clic en la página 2.

## Alcance

Este resultado es técnico y no reemplaza `COMMODITIES_SIO_INTEGRADO.csv`, no publica información en el dashboard y no habilita una extracción masiva.
