# Reporte de auditoría de commodities SIO

Fecha de auditoría: 2026-09-04

## Resumen

- Moneda explícitamente informada: sí (30/30).
- Moneda inferida: no (0/30).
- Moneda sin especificar: no (0/30).
- Porcentaje de filas con moneda válida/explícita: 100.0%.
- Conteo por moneda explícita: ARS=16, USD=14.
- Precios válidos por moneda: ARS=16, USD=14.
- Estado apto_dashboard: si=0, parcial_piloto=30, no=0.
- Muestra piloto de una sola página GetOperaciones: sí; filas piloto: 30.
- Filas totales: 30.
- Columnas mapeadas con dato: fecha, operacion, tipo_precio, commodity, volumen, procedencia, precio, zona, condicion_pago.
- Columnas faltantes/no separadas: precio_total, precio_puesto_en, frecuencia.
- Commodities detectados: CEBADA FORR., Girasol, Maíz, Soja, TRIGO PAN.
- Años disponibles: 2026.
- Meses disponibles: 2026-09.
- Rango de fechas: 2026-09-04 a 2026-09-04.
- Fecha máxima: 2026-09-04; días desde último dato: 0.
- Precios válidos: 30; faltantes: 0; cero: 0; negativos: 0.
- Monedas especificadas: 30/30; sin especificar: 0.
- Unidades de precio especificadas: 30/30; sin especificar: 0.
- Unidades de volumen especificadas: 30/30; sin especificar: 0.
- Campos originales de precio: Precio/TN Monto; campos originales de volumen: Cant. (TN).
- Precio unitario con dato: 30; precio total con dato: 0; inconsistencias detectadas: 0.
- Volumen con dato numérico: 30; procedencia con dato: 30; lugar de entrega (zona) con dato: 30; condición de pago con dato: 30.
- apto_piloto: sí (30/30 filas).
- apto_dashboard pleno: no (0/30 filas); estado piloto: parcial_piloto (30/30 filas).
- Series utilizables para dashboard analítico futuro: 0 de 7.

## Moneda embebida en campo de precio

`Row[10]` contiene el campo original de precio. El símbolo monetario se extrae sólo si aparece explícitamente: `U$S`/`US$`/`USD` se normaliza a `USD`, y `$` sin esos marcadores se normaliza a `ARS`. No se infiere moneda por contexto y se conserva `precio_original_texto`.

## Moneda y comparabilidad

Moneda explícitamente informada: sí (30/30 filas). Moneda inferida: no (0/30 filas). Moneda sin especificar: no (0/30 filas).
Comparabilidad monetaria: no.
Los precios sólo deben compararse dentro de una misma moneda; en esta muestra hay ARS y USD explícitos, por lo que no corresponde calcular variaciones monetarias conjuntas. El estado queda como `parcial_piloto` y no como `si` pleno.

## Actualidad de la información

Fecha máxima disponible: 2026-09-04.
Días desde el último dato: 0.
Commodities actualizados (últimos 7 días): CEBADA FORR., Girasol, Maíz, Soja, TRIGO PAN.
Commodities recientes o actualizados (últimos 30 días): CEBADA FORR., Girasol, Maíz, Soja, TRIGO PAN.
Commodities sin dato reciente: ninguno.
Cobertura últimos 7 días: 30 registro(s). Cobertura últimos 30 días: 30 registro(s).

| Commodity | Fecha máxima | Días | Últimos 7 días | Últimos 30 días | Estado |
| --- | --- | --- | --- | --- | --- |
| CEBADA FORR. | 2026-09-04 | 0 | 1 | 1 | Actualizado |
| Girasol | 2026-09-04 | 0 | 2 | 2 | Actualizado |
| Maíz | 2026-09-04 | 0 | 9 | 9 | Actualizado |
| Soja | 2026-09-04 | 0 | 15 | 15 | Actualizado |
| TRIGO PAN | 2026-09-04 | 0 | 3 | 3 | Actualizado |

## Recomendación de automatización

SIO Granos debe mantenerse como exploración separada hasta validar la procedencia, la definición del precio, los permisos de uso, la estabilidad de la consulta pública y la homogeneidad de moneda, unidad, frecuencia y tipo de precio.
Si hay datos recientes y la consulta/exportación pública es estable, conviene automatizar con ventanas de hasta 180 días y auditoría previa. Si no hay exportación estable, mantener la descarga manual en raw/ y conservar la respuesta original.
No publicar en el dashboard ni mezclar con BCR o frutas/hortalizas antes de esa validación.

## Series y aptitud analítica

| Commodity | Moneda | Unidad | Tipo | Frecuencia | Apto piloto | Apto dashboard | Calidad | Aptitud analítica |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CEBADA FORR. | USD | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Baja | No |
| Girasol | USD | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Media | No |
| Maíz | ARS | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Alta | No |
| Maíz | USD | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Media | No |
| Soja | ARS | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Alta | No |
| Soja | USD | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Alta | No |
| TRIGO PAN | ARS | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Media | No |

Casos problemáticos: 6. Ver CASOS_PROBLEMATICOS_COMMODITIES_SIO.csv.

## Próximos pasos

Validar una respuesta real de SIO y revisar especialmente fecha, condición de pago, operación, volumen, procedencia, precio puesto en, unidad, moneda y permisos. No inventar datos ni usar fuentes alternativas como equivalentes de SIO/BCR sin evidencia.
