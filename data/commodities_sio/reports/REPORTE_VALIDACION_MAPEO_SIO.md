# Reporte de validación de mapeo SIO

## Objetivo

Validar si el mapeo posicional del endpoint `GetOperaciones` permite construir un CSV piloto confiable de una sola página, sin habilitar paginación masiva ni integración visual.

## Fuente utilizada

- Endpoint: `https://www.siogranos.com.ar/consulta_publica/operaciones_informadas_ultimas.aspx/GetOperaciones`.
- Método: `POST`.
- Payload: `{ "pPageSize": 10, "pCurrentPage": 1 }`.
- Archivo raw usado: `data/commodities_sio/raw/SIO_test_GetOperaciones_20260904102034.json` (ignorado por Git).
- Fecha de descarga observada en el nombre del archivo: `2026-09-04 10:20:34`.
- Registros disponibles en `d.Items`: 15.
- Cada registro contiene `ID` y `Row` de longitud 15.

## Mapeo aplicado

El mapeo local validado coincide con el orden de `colNames`/`colModel` documentado en el HTML local y con la longitud de `Row`.

| Posición Row | Campo destino | Evidencia | Estado |
|---:|---|---|---|
| 0 | id | `colNames[0]`: ID | Aplicado |
| 1 | fecha | `colNames[1]`: Fecha Concertación | Aplicado |
| 2 | numero_operacion | `colNames[2]`: Nro. Operación | Aplicado al mapeo; no exportado al CSV actual |
| 3 | operacion | `colNames[3]`: Operación | Aplicado |
| 4 | tipo_operacion | `colNames[4]`: Tipo | Aplicado al mapeo; no exportado al CSV actual |
| 5 | tipo_precio | `colNames[5]`: Precio; valores `Precio Hecho` | Aplicado |
| 6 | commodity | `colNames[6]`: Producto | Aplicado |
| 7 | volumen | `colNames[7]`: Cant. (TN) | Aplicado |
| 8 | calidad | `colNames[8]`: Calidad | Aplicado al mapeo; no exportado al CSV actual |
| 9 | procedencia | `colNames[9]`: Procedencia Pcia./LOCALID. | Aplicado |
| 10 | precio | `colNames[10]`: Precio/TN Monto | Aplicado |
| 11 | lugar_entrega | `colNames[11]`: Lugar Entrega | Aplicado a `zona` |
| 12 | fecha_entrega | `colNames[12]`: Fecha Entr. DESDE/HASTA | Aplicado al mapeo; no exportado al CSV actual |
| 13 | condicion_pago | `colNames[13]`: Condición Pago | Aplicado |
| 14 | fuera_de_termino | `colNames[14]`: Fuera de Termino | Aplicado al mapeo; no exportado al CSV actual |

## Resultado de integración

- Filas generadas: 15.
- Fuente de todas las filas: una única respuesta de una página `GetOperaciones`.
- Commodities detectados: Soja, Maíz, Girasol, Trigo Pan y Cebada Forr.
- Columnas con datos mapeados: `fecha`, `commodity`, `tipo_precio`, `precio`, `volumen`, `procedencia`, `zona`, `operacion` y `condicion_pago`.
- Campos faltantes o no separados: `moneda`, `unidad`, `volumen_unidad`, `precio_puesto_en` y `frecuencia`.
- La moneda no se completó aunque el texto del monto contiene símbolos/letras; queda pendiente separar y validar ese dato.
- La unidad de precio no se completó; no se asumió `$ / TN`.
- Cada fila conserva `archivo_origen`, `fecha_integracion` y la observación `integración piloto una página GetOperaciones`.
- No se generaron datos ficticios ni se hizo paginación.

## Resultado de auditoría

- Filas auditadas: 15.
- Rango de fechas: `2026-09-04` a `2026-09-04`.
- Precios válidos: 15; faltantes: 0; cero: 0; negativos: 0.
- Volumen con dato numérico: 15; la grilla lo rotula como TN.
- Procedencia con dato: 15.
- Lugar de entrega con dato: 15.
- Condición de pago con dato: 15.
- Moneda y unidad separadas: ninguna; por eso las series no son todavía aptas para dashboard analítico.
- Aptitud preliminar: 0 de 5 series utilizables bajo los controles actuales de homogeneidad.
- Problemas detectados: metadatos de moneda/unidad/frecuencia no separados, destino distinto de `precio_puesto_en` y campos posicionales todavía dependientes del orden de la grilla.

## Decisión

**A. Mapeo validado para piloto de una página.**

El mapeo es suficiente para una muestra técnica de 15 filas porque el orden de la grilla coincide con el array `Row` y los valores resultan coherentes con las etiquetas observadas. Esta decisión no autoriza paginación, extracción masiva ni publicación en el dashboard.

## Recomendación próxima

Preparar, sólo después de una revisión metodológica, una paginación controlada y extracción limitada de los últimos 30 días. Antes de eso, definir cómo separar moneda y unidad del campo `Precio/TN Monto`, conservar los campos actualmente no exportados y repetir la auditoría sobre una segunda respuesta manual o una validación de DevTools. Mantener SIO separado de BCR y de frutas/hortalizas.
