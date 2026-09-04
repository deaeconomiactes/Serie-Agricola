# Reporte de unidades y moneda SIO

Fecha de revisión: 2026-09-04

## Objetivo

Revisar la identificación de precio, unidad, volumen y moneda en el piloto exploratorio de SIO Granos, preservando las etiquetas originales y evitando inferencias no respaldadas por la fuente.

## CSV revisado

Se revisó `data/commodities_sio/processed/COMMODITIES_SIO_INTEGRADO.csv`, generado desde una respuesta real local de `GetOperaciones`. La muestra contiene 15 filas y 5 commodities: CEBADA FORR., Girasol, Maíz, Soja y TRIGO PAN.

## Columnas disponibles

El CSV conserva los campos normalizados y los metadatos de procedencia relevantes:

- `precio`: valor seleccionado para el piloto.
- `precio_unidad`: valor unitario cuando la fuente lo identifica explícitamente.
- `precio_total`: reservado para un monto total explícito; no se completa por cálculo.
- `precio_tipo_original`: tipo o texto original asociado al precio.
- `campo_precio_original` y `valor_precio_original`: etiqueta y valor originales.
- `campo_moneda_original` y `valor_moneda_original`: etiqueta y valor originales si la fuente expone un campo de moneda.
- `unidad`: unidad del precio cuando surge de la etiqueta fuente.
- `volumen` y `volumen_unidad`: cantidad y unidad de volumen.
- `campo_volumen_original`: etiqueta original del volumen.
- `moneda`: moneda separada sólo cuando la fuente la informa como campo identificable.

## Campos de precio detectados

La respuesta de SIO expone la etiqueta `Precio/TN Monto` y valores originales con formato como `377,00` acompañado por texto de moneda. En el CSV:

- `precio` se carga con el valor numérico parseable.
- `precio_unidad` conserva el mismo valor porque la etiqueta explicita precio por tonelada.
- `precio_total` queda sin dato: no se observó un campo explícito de precio total.
- `campo_precio_original` conserva `Precio/TN Monto`.
- `valor_precio_original` conserva el texto fuente completo.

No se mezclan precio unitario y precio total, ni se calcula un total a partir de volumen.

## Campos de volumen detectados

La etiqueta fuente `Cant. (TN)` respalda que `volumen_unidad=TN`. El volumen se conserva en `volumen` y la etiqueta se conserva en `campo_volumen_original`.

## Moneda

La moneda aparece embebida en el valor original del campo de precio, no como una columna separada validada de moneda. Por eso `moneda` queda `Sin especificar` en esta etapa. No se infiere ARS, USD, `$`, `U$S` ni ninguna otra moneda a partir del texto embebido.

## Unidad de precio

La unidad `TN` sí está respaldada por la etiqueta explícita `Precio/TN Monto`; por eso el integrador completa `unidad=TN` y `precio_unidad` con el valor numérico parseado. Esto identifica la unidad física del precio, pero no resuelve la moneda.

## Unidad de volumen

La unidad `TN` está respaldada por la etiqueta explícita `Cant. (TN)`; por eso el integrador completa `volumen_unidad=TN`.

## Decisiones adoptadas

- Mantener los campos originales y sus etiquetas.
- Completar unidades únicamente cuando están explícitas en la etiqueta fuente.
- No convertir ni calcular valores monetarios.
- Mantener `mapping_status: validado` sólo en el archivo local ignorado, respaldado por evidencia local; el ejemplo versionado permanece `pendiente_validacion`.
- Mantener la integración y auditoría como pipeline exploratorio separado, sin publicación visual.

## Riesgos

- No asumir ARS, USD, `$` o `U$S` como moneda de la serie sin un campo o documentación fuente que lo confirme.
- No presentar `precio_unidad` como `precio_total`.
- No combinar series si difieren en moneda, unidad, frecuencia o tipo de precio.
- La muestra es un piloto de una sola página y no prueba cobertura histórica, paginación ni estabilidad del origen.
- No publicar en el dashboard hasta resolver la moneda y validar homogeneidad metodológica.

## Recomendación

El piloto es apto para integración controlada y auditoría técnica: tiene fecha, commodity, precio válido, fuente, campo de precio original y unidades respaldadas por etiquetas. No es apto todavía para el dashboard: la moneda no está separada/validada y la cobertura corresponde a una sola página. Mantener descarga manual o automatización controlada sólo después de validar la consulta y sus condiciones de uso.
