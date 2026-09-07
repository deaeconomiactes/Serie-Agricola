# Reporte de exportación manual SIO

## Objetivo

Validar si el archivo descargado desde Exportar Operaciones permite construir una base tabular más completa que el endpoint GetOperaciones.

## Archivo procesado

- Nombre: `SIO_exportar_operaciones_2026-09-07.csv`.
- Tipo: exportación manual tabular.
- Filas: 396971.
- Columnas: 21.
- Fecha de integración: 2026-09-07.

## Columnas originales detectadas

- `FECHA OPERACION`
- `FECHA CONCERTACION`
- `NRO. OPERACION`
- `OPERACION`
- `TIPO`
- `PRECIO`
- `PRODUCTO`
- `CANT. (TN)`
- `CALIDAD`
- `CALIDAD ADICIONAL`
- `PROCEDENCIA PCIA`
- `PROCEDENCIA LOCALID.`
- `PRECIO/TN MONEDA`
- `PRECIO/TN MONTO`
- `LUGAR ENTREGA`
- `FECHA ENTR. DESDE`
- `FECHA ENTR. HASTA`
- `CONDICION PAGO`
- `ES FINAL`
- `COSECHA`
- `¿ES ÚLTIMA INSTANCIA?`

## Mapeo aplicado

| Columna original | Campo destino | Evidencia | Confianza | Observaciones |
| --- | --- | --- | --- | --- |
| FECHA OPERACION / FECHA CONCERTACION | fecha | fecha de operación/concertación observada | alta | se conserva la fecha normalizada |
| PRODUCTO | commodity | producto de la exportación | alta | se normaliza contra el catálogo SIO |
| PRECIO/TN MONTO | precio | precio original | alta | se conserva precio_original_texto |
| PRECIO/TN MONEDA | moneda | campo monetario explícito | alta | no se infiere por contexto |
| CANT. (TN) | volumen | cantidad explícita en toneladas | alta | se conserva volumen_unidad=TN |
| PROCEDENCIA PCIA / PROCEDENCIA LOCALID. | procedencia | procedencia de la operación | alta | se combinan los campos de procedencia disponibles |
| LUGAR ENTREGA | lugar_entrega | lugar de entrega | alta | se conserva como lugar_entrega |
| CONDICION PAGO | condicion_pago | condición de pago | alta | se conserva si tiene dato |

## Resultado de integración

- Filas generadas: 396971.
- Columnas generadas: esquema normalizado estándar de SIO.
- Campos faltantes: ninguno de los campos principales.
- Campos originales no utilizados o conservados sólo como evidencia: NRO. OPERACION, OPERACION, TIPO, PRECIO, CALIDAD, CALIDAD ADICIONAL, FECHA ENTR. DESDE, FECHA ENTR. HASTA, ES FINAL, COSECHA, ¿ES ÚLTIMA INSTANCIA?.
- Advertencia: la salida normalizada conserva los campos analíticos definidos; las columnas originales no mapeadas quedan registradas en este reporte y no se descartan silenciosamente como evidencia.

## Resultado de auditoría

- Commodities: ACEITE SOJA, ARROZ C.L.A, ARROZ C.L.F, CEBADA CERV., CEBADA FORR., Girasol, Maíz, Soja, Sorgo, TRIGO CAND., TRIGO PAN.
- Fechas: 2026-03-12 a 2026-09-07.
- Monedas: ARS, USD; unidades: TN.
- Precios válidos: 396971; faltantes: 0; cero: 40796; negativos: 0.
- Volumen con dato: 396971; procedencia: 396971; lugar de entrega: 396971; condición de pago: 396971.
- Duplicados por ID: 0.
- Aptitud piloto: 396971/396971; aptitud dashboard: 0/396971.

## Comparación con endpoint GetOperaciones

- La exportación manual debe compararse por cantidad de filas, columnas y cobertura, no sólo por una respuesta puntual del endpoint.
- Trae más filas que la muestra piloto de GetOperaciones de 15 filas: sí.
- Trae moneda explícita: sí; unidad explícita: sí.
- La exportación manual no valida `pCurrentPage`; evita el problema operativo de la paginación del endpoint sólo como descarga manual.

## Decisión metodológica

B. Exportación manual parcialmente apta; requiere ajustes.

## Recomendación próxima

Mantener un flujo documentado de descarga manual recurrente si se confirma la procedencia, licencia, cobertura y estabilidad del archivo. Definir periodicidad, conservar raw fuera de Git y versionar sólo processed/reportes controlados. No integrar al dashboard todavía.
