# Reporte de mapeo posicional GetOperaciones SIO

## Objetivo

Identificar qué posición del array `Row` corresponde a cada campo observable de la grilla SIO, sin integrar todavía las filas al pipeline productivo.

## Fuentes locales revisadas

- `data/commodities_sio/reports/REPORTE_DESCUBRIMIENTO_SIO.md`.
- `data/commodities_sio/reports/REPORTE_ENDPOINT_SIO.md`.
- `data/commodities_sio/raw/SIO_test_GetOperaciones_20260904102034.json` (respuesta real local, ignorada por Git).
- `data/commodities_sio/raw/SIO_descubrimiento_01_consulta_publica.html` (HTML real local, ignorado por Git).
- No existe un archivo JavaScript raw separado; la configuración de la grilla fue observada dentro del HTML.

## Estructura JSON observada

- La respuesta es un objeto JSON con clave principal `d`.
- Dentro de `d` existen `PageCount`, `CurrentPage`, `RecordCount` e `Items`.
- `d.Items` contiene aproximadamente 15 elementos en la respuesta revisada.
- Cada elemento contiene un `ID` y un array `Row`.
- El `Row` observado tiene 15 posiciones, numeradas de 0 a 14.
- `RecordCount` aparece como 0 aunque `Items` contiene elementos; no se usa ese valor como evidencia de ausencia de datos.
- Los valores de `Row` no incluyen nombres de campo; su interpretación depende del orden de columnas de la grilla.

## Columnas detectadas en grilla

El HTML contiene `colNames` y `colModel` con las siguientes columnas, en este orden observable:

- ID.
- Fecha Concertación.
- Nro. Operación.
- Operación.
- Tipo.
- Precio.
- Producto.
- Cant. (TN).
- Calidad.
- Procedencia Pcia./LOCALID.
- Precio/TN Monto.
- Lugar Entrega.
- Fecha Entr. DESDE/HASTA.
- Condición Pago.
- Fuera de Termino.

## Mapeo posicional propuesto

El orden de la tabla tiene evidencia estructural alta porque coincide la lista `colNames` del HTML con el largo 15 de `Row`. La confianza alta se refiere al orden visual/estructural; la semántica final de los valores, unidad y moneda aún requiere validación.

| Posición Row | Campo propuesto | Evidencia | Confianza | Observaciones |
|---:|---|---|---|---|
| 0 | ID | `colNames[0]` y clave `ID`; primera posición de `Row` | Alta | Identificador de operación, no precio. |
| 1 | fecha | `colNames[1]`: Fecha Concertación; segundo valor de `Row` | Alta | Fecha de concertación observable. |
| 2 | numero_operacion | `colNames[2]`: Nro. Operación | Alta | Debe conservarse como identificador, no como commodity. |
| 3 | operacion | `colNames[3]`: Operación | Alta | En ejemplos observados aparece `Contrato`. |
| 4 | tipo_operacion | `colNames[4]`: Tipo | Alta | En ejemplos observados aparecen `Compraventa` o `Canje`. |
| 5 | tipo_precio | `colNames[5]`: Precio | Media | Valores observados como `Precio Hecho`; la etiqueta no debe confundirse con el monto numérico. |
| 6 | commodity | `colNames[6]`: Producto | Alta | Ejemplos observados: SOJA, MAIZ, GIRASOL, TRIGO PAN, CEBADA FORR. |
| 7 | volumen | `colNames[7]`: Cant. (TN) | Alta | La grilla explicita TN; validar parsing decimal. |
| 8 | calidad | `colNames[8]`: Calidad | Alta | No debe mapearse como moneda ni unidad de precio. |
| 9 | procedencia | `colNames[9]`: Procedencia Pcia./LOCALID. | Alta | Contiene provincia/localidad en un único valor visible. |
| 10 | precio | `colNames[10]`: Precio/TN Monto | Alta | Es el candidato al valor numérico; la moneda aparece embebida en el texto observado. |
| 11 | lugar_entrega | `colNames[11]`: Lugar Entrega | Alta | Puede incluir destino y texto `En destino`; no asumir que equivale a precio puesto en. |
| 12 | fecha_entrega | `colNames[12]`: Fecha Entr. DESDE/HASTA | Alta | Es rango de entrega, no fecha de concertación. |
| 13 | condicion_pago | `colNames[13]`: Condición Pago | Alta | Ejemplos observados: Contra entrega, A plazo, Anticipado a la entrega. |
| 14 | fuera_de_termino | `colNames[14]`: Fuera de Termino | Alta | Valor booleano textual observado; no usar como condición de pago. |

Aunque existe evidencia estructural fuerte, el archivo de configuración conserva `mapping_status: pendiente_validacion`. El integrador no utilizará estas posiciones mientras el mapeo no sea validado explícitamente.

## Ejemplos anonimizados / seguros

Se muestran estructuras recortadas y con identificadores, localidades, montos y fechas reemplazados:

```json
{
  "ID": "<id>",
  "Row": [
    "<id>", "<fecha concertación>", "<nro operación>", "Contrato",
    "Compraventa", "Precio Hecho", "SOJA", "<cantidad TN>", "Fábrica",
    "<provincia>\\r<localidad>", "<monto>\\n<moneda>",
    "<destino>\\rEn destino", "<fecha desde>\\n<fecha hasta>",
    "Contra entrega", "False"
  ]
}
```

La fila de ejemplo sólo documenta posiciones; no constituye un dato para integrar.

## Riesgos

- El endpoint puede cambiar su estructura o dejar de estar disponible.
- La grilla puede cambiar el orden de `colNames` o de `Row` sin aviso.
- `Row` no es autodescriptivo y los nombres se encuentran en una página JavaScript/HTML separada.
- La etiqueta `Precio` observada en la grilla parece describir el tipo (`Precio Hecho`), mientras que el monto está en `Precio/TN Monto`; ambos deben permanecer separados.
- Moneda, unidad de precio, unidad de volumen y contenido de destino requieren validación específica.
- No debe integrarse masivamente sin validar el mapeo contra una respuesta y configuración de grilla vigentes.
- No debe usarse en el dashboard hasta auditar fecha, moneda, unidad, condición de pago, duplicados y procedencia.

## Recomendación

Usar DevTools para observar la configuración completa de la grilla o descargar una exportación manual y contrastarla con `Row`. Luego, si se confirma el orden en una muestra adicional, preparar una integración piloto de una sola página con mapeo explícito versionado. Hasta entonces, mantener `mapping_status` como `pendiente_validacion` y no generar CSV integrado desde `Row`.
