# Reporte de descubrimiento técnico SIO Granos

## Fecha de ejecución

2026-09-04

## Comando ejecutado

`.\explorar_sio_granos.py --discover-web --save-response --max-requests 5 --days-back 30 --products maiz`

## Requests realizados

| Número | URL | Tipo de recurso | Status code | Guardado como | Observaciones |
| --- | --- | --- | --- | --- | --- |
| 1 | https://www.siogranos.com.ar/consulta_publica/ | HTML público | 200 | SIO_descubrimiento_01_consulta_publica.html | respuesta recibida |

## HTML analizado

- Título: SIO Granos.
- Tamaño: 17027 bytes.
- Scripts detectados: 3.
- Grillas detectadas: JQGrid, jqGrid, jqgrid, grid, #grid, jsonReader, colNames, colModel, Grid.
- Columnas detectadas: ID, Fecha Concertación, Nro. Operación, Operación, Tipo, Precio, Producto, Cant.   (TN), Calidad, Procedencia   Pcia./LOCALID., Precio/TN   Monto, Lugar   Entrega, Fecha Entr.   DESDE/HASTA, Condición Pago, Fuera de Termino, fecha_concertacion, nroOperacion, operacion, tipo, precio, producto, cant, calidad, procedencia, preciotn, lugarentrega, fechaentrega, condicionpago, fueratermino.
- Formularios detectados: 0.
- Inputs/selects detectados: ninguno.
- Llamadas AJAX/JavaScript detectadas: datatype:, $.ajax, dataType:, contentType:.
- Referencias de exportación: operaciones_informadas_exportar.aspx.

## Scripts analizados

| Archivo/script | Tipo | Evidencia útil | Endpoints candidatos | Observaciones |
| --- | --- | --- | --- | --- |
| https://www.siogranos.com.ar/consulta_publica/JQGridReq/jquery-1.9.0.min.js | script interno | ; ;  | ninguno | No descargado: librería genérica. |
| https://www.siogranos.com.ar/consulta_publica/JQGridReq/jquery.jqGrid.js | script interno | ; ;  | ninguno | No descargado: librería genérica. |
| https://www.siogranos.com.ar/consulta_publica/JQGridReq/grid.locale-en.js | script interno | ; ;  | ninguno | No descargado: librería genérica. |

## Endpoints candidatos

| Endpoint | Evidencia | Tipo probable | Parámetros detectados | Confianza | Requiere validación | Observaciones |
| --- | --- | --- | --- | --- | --- | --- |
| https://www.siogranos.com.ar/consulta_publica/operaciones_informadas_ultimas.aspx/GetFechaActual | Referencia encontrada en https://www.siogranos.com.ar/consulta_publica/ | WebMethod/PageMethod AJAX | pPageSize, pCurrentPage | alta | sí | No se ejecutó este endpoint durante el descubrimiento. |
| https://www.siogranos.com.ar/consulta_publica/operaciones_informadas_ultimas.aspx/GetOperaciones | Referencia encontrada en https://www.siogranos.com.ar/consulta_publica/ | WebMethod/PageMethod AJAX | pPageSize, pCurrentPage | alta | sí | No se ejecutó este endpoint durante el descubrimiento. |
| https://www.siogranos.com.ar/consulta_publica/compra_vta_preciohecho_inmediata.aspx | Referencia encontrada en https://www.siogranos.com.ar/consulta_publica/ | página ASP.NET pública | no detectados | media | sí | No se ejecutó este endpoint durante el descubrimiento. |
| https://www.siogranos.com.ar/consulta_publica/compra_vta_preciohecho_mas30dias.aspx | Referencia encontrada en https://www.siogranos.com.ar/consulta_publica/ | página ASP.NET pública | no detectados | media | sí | No se ejecutó este endpoint durante el descubrimiento. |
| https://www.siogranos.com.ar/consulta_publica/operaciones_informadas.aspx | Referencia encontrada en https://www.siogranos.com.ar/consulta_publica/ | página ASP.NET pública | no detectados | media | sí | No se ejecutó este endpoint durante el descubrimiento. |
| https://www.siogranos.com.ar/consulta_publica/operaciones_informadas_exportar.aspx | Referencia encontrada en https://www.siogranos.com.ar/consulta_publica/ | página ASP.NET pública | no detectados | media | sí | No se ejecutó este endpoint durante el descubrimiento. |
| https://www.siogranos.com.ar/consulta_publica/consulta_localidad_zona.aspx | Referencia encontrada en https://www.siogranos.com.ar/consulta_publica/ | página ASP.NET pública | no detectados | media | sí | No se ejecutó este endpoint durante el descubrimiento. |

## Columnas y campos detectados

- ID
- Fecha Concertación
- Nro. Operación
- Operación
- Tipo
- Precio
- Producto
- Cant.   (TN)
- Calidad
- Procedencia   Pcia./LOCALID.
- Precio/TN   Monto
- Lugar   Entrega
- Fecha Entr.   DESDE/HASTA
- Condición Pago
- Fuera de Termino
- fecha_concertacion
- nroOperacion
- operacion
- tipo
- precio
- producto
- cant
- calidad
- procedencia
- preciotn
- lugarentrega
- fechaentrega
- condicionpago
- fueratermino

## Hipótesis técnica

- La página contiene una grilla/configuración JavaScript y referencias a servicios ASP.NET; los endpoints y parámetros requieren validación adicional.
- No se enviaron formularios ni se ejecutaron endpoints candidatos durante este descubrimiento.
- Los parámetros se informan sólo cuando aparecen literalmente en el HTML/script analizado.

## Recomendación próxima

Realizar prueba controlada del endpoint candidato con máximo 1 request.
