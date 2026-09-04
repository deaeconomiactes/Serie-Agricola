# Reporte de auditoría de commodities SIO

Fecha de auditoría: 2026-09-04

## Resumen

- Moneda explícitamente informada: no (0/15).
- Moneda inferida: no (0/15).
- Moneda sin especificar: sí (15/15).
- Porcentaje de filas con moneda válida/explícita: 0.0%.
- Conteo por moneda explícita: ninguna.
- Muestra piloto de una sola página GetOperaciones: sí; filas piloto: 15.
- Filas totales: 15.
- Columnas mapeadas con dato: fecha, operacion, tipo_precio, commodity, volumen, procedencia, precio, zona, condicion_pago.
- Columnas faltantes/no separadas: moneda, precio_total, precio_puesto_en, frecuencia.
- Commodities detectados: CEBADA FORR., Girasol, Maíz, Soja, TRIGO PAN.
- Años disponibles: 2026.
- Meses disponibles: 2026-09.
- Rango de fechas: 2026-09-04 a 2026-09-04.
- Fecha máxima: 2026-09-04; días desde último dato: 0.
- Precios válidos: 15; faltantes: 0; cero: 0; negativos: 0.
- Monedas especificadas: 0/15; sin especificar: 15.
- Unidades de precio especificadas: 15/15; sin especificar: 0.
- Unidades de volumen especificadas: 15/15; sin especificar: 0.
- Campos originales de precio: Precio/TN Monto; campos originales de volumen: Cant. (TN).
- Precio unitario con dato: 15; precio total con dato: 0; inconsistencias detectadas: 0.
- Volumen con dato numérico: 15; procedencia con dato: 15; lugar de entrega (zona) con dato: 15; condición de pago con dato: 15.
- apto_piloto: sí (15/15 filas).
- apto_dashboard: no (0/15 filas).
- Series utilizables para dashboard analítico futuro: 0 de 5.

## Moneda y comparabilidad

Moneda explícitamente informada: no (0/15 filas). Moneda inferida: no (0/15 filas). Moneda sin especificar: sí (15/15 filas).
Comparabilidad monetaria: no.
Los valores no deben compararse ni usarse para variaciones monetarias mientras la moneda permanezca embebida o no informada explícitamente. La auditoría conserva `moneda=Sin especificar` y no habilita `apto_dashboard`.

## Actualidad de la información

Fecha máxima disponible: 2026-09-04.
Días desde el último dato: 0.
Commodities actualizados (últimos 7 días): CEBADA FORR., Girasol, Maíz, Soja, TRIGO PAN.
Commodities recientes o actualizados (últimos 30 días): CEBADA FORR., Girasol, Maíz, Soja, TRIGO PAN.
Commodities sin dato reciente: ninguno.
Cobertura últimos 7 días: 15 registro(s). Cobertura últimos 30 días: 15 registro(s).

| Commodity | Fecha máxima | Días | Últimos 7 días | Últimos 30 días | Estado |
| --- | --- | --- | --- | --- | --- |
| CEBADA FORR. | 2026-09-04 | 0 | 1 | 1 | Actualizado |
| Girasol | 2026-09-04 | 0 | 1 | 1 | Actualizado |
| Maíz | 2026-09-04 | 0 | 4 | 4 | Actualizado |
| Soja | 2026-09-04 | 0 | 7 | 7 | Actualizado |
| TRIGO PAN | 2026-09-04 | 0 | 2 | 2 | Actualizado |

## Recomendación de automatización

SIO Granos debe mantenerse como exploración separada hasta validar la procedencia, la definición del precio, los permisos de uso, la estabilidad de la consulta pública y la homogeneidad de moneda, unidad, frecuencia y tipo de precio.
Si hay datos recientes y la consulta/exportación pública es estable, conviene automatizar con ventanas de hasta 180 días y auditoría previa. Si no hay exportación estable, mantener la descarga manual en raw/ y conservar la respuesta original.
No publicar en el dashboard ni mezclar con BCR o frutas/hortalizas antes de esa validación.

## Series y aptitud analítica

| Commodity | Moneda | Unidad | Tipo | Frecuencia | Apto piloto | Apto dashboard | Calidad | Aptitud analítica |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CEBADA FORR. |  | TN | Precio Hecho | Sin especificar | Sí | No | Baja | No |
| Girasol |  | TN | Precio Hecho | Sin especificar | Sí | No | Baja | No |
| Maíz |  | TN | Precio Hecho | Sin especificar | Sí | No | Media | No |
| Soja |  | TN | Precio Hecho | Sin especificar | Sí | No | Media | No |
| TRIGO PAN |  | TN | Precio Hecho | Sin especificar | Sí | No | Media | No |

Casos problemáticos: 18. Ver CASOS_PROBLEMATICOS_COMMODITIES_SIO.csv.

## Próximos pasos

Validar una respuesta real de SIO y revisar especialmente fecha, condición de pago, operación, volumen, procedencia, precio puesto en, unidad, moneda y permisos. No inventar datos ni usar fuentes alternativas como equivalentes de SIO/BCR sin evidencia.
