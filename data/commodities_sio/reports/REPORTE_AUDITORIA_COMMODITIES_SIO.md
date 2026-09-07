# Reporte de auditoría de commodities SIO

Fecha de auditoría: 2026-09-07

## Resumen

- Moneda explícitamente informada: sí (15/15).
- Moneda inferida: no (0/15).
- Moneda sin especificar: no (0/15).
- Porcentaje de filas con moneda válida/explícita: 100.0%.
- Conteo por moneda explícita: ARS=8, USD=7.
- Precios válidos por moneda: ARS=8, USD=7.
- Estado apto_dashboard: si=0, parcial_piloto=15, no=0.
- Muestra piloto de una sola página GetOperaciones: sí; filas piloto: 15.
- Filas totales: 15.
- Columnas mapeadas con dato: fecha, operacion, tipo_precio, commodity, volumen, procedencia, precio, zona, condicion_pago.
- Columnas faltantes/no separadas: precio_total, precio_puesto_en, frecuencia.
- Commodities detectados: CEBADA FORR., Girasol, Maíz, Soja, TRIGO PAN.
- Años disponibles: 2026.
- Meses disponibles: 2026-09.
- Rango de fechas: 2026-09-04 a 2026-09-04.
- Fecha máxima: 2026-09-04; días desde último dato: 3.
- Precios válidos: 15; faltantes: 0; cero: 0; negativos: 0.
- Precios válidos para serie (positivos): 15/15.
- Monedas especificadas: 15/15; sin especificar: 0.
- Unidades de precio especificadas: 15/15; sin especificar: 0.
- Unidades de volumen especificadas: 15/15; sin especificar: 0.
- Campos originales de precio: Precio/TN Monto; campos originales de volumen: Cant. (TN).
- Precio unitario con dato: 15; precio total con dato: 0; inconsistencias detectadas: 0.
- Volumen con dato numérico: 15; procedencia con dato: 15; lugar de entrega (zona) con dato: 15; condición de pago con dato: 15.
- apto_piloto: sí (15/15 filas).
- apto_dashboard pleno: no (0/15 filas); estado piloto: parcial_piloto (15/15 filas).
- Series utilizables para dashboard analítico futuro: 0 de 7.

## Archivos auditados

| Archivo | Tipo | Filas | Finalidad | Aptitud |
| --- | --- | ---: | --- | --- |
| `data/commodities_sio/processed/COMMODITIES_SIO_INTEGRADO.csv` | integración piloto principal | 15 | referencia piloto base | parcial_piloto |
| `data/commodities_sio/processed/COMMODITIES_SIO_MUESTRA_PAGINADA.csv` | muestra técnica de paginación | 44 | diagnóstico de request, páginas y duplicados | no |
| `data/commodities_sio/processed/COMMODITIES_SIO_EXPORTACION_MANUAL.csv` | exportación manual | 396971 | archivo descargado localmente | parcial_piloto |

## Muestra paginada técnica

La muestra contiene 44 fila(s) y es evidencia técnica separada: no reemplaza `COMMODITIES_SIO_INTEGRADO.csv`.
Estado de paginación registrado: duplicada.
No es apta para dashboard cuando `estado_paginacion=duplicada`; se conserva para diagnosticar duplicados y paginación.

## Exportación manual

La exportación manual es una tercera salida separada y no reemplaza `COMMODITIES_SIO_INTEGRADO.csv` ni la muestra paginada.
- Filas: 396971.
- Rango de fechas: 2026-03-12 a 2026-09-07.
- Monedas: ARS, USD; unidades: TN.
- Productos: ACEITE SOJA, ARROZ C.L.A, ARROZ C.L.F, CEBADA CERV., CEBADA FORR., Girasol, Maíz, Soja, Sorgo, TRIGO CAND., TRIGO PAN.
- Duplicados por ID: 0.
- Aptitud piloto: 396971/396971; aptitud dashboard: 0/396971.
- Diferencia frente a GetOperaciones: proviene de un archivo descargado manualmente; requiere validar columnas, moneda, unidad, cobertura y licencia antes de cualquier automatización o publicación.

## Precios cero y aptitud analítica

La exportación manual contiene 40796 precio(s) cero sobre 396971 fila(s) (10.28%). Los ceros se conservan para trazabilidad, pero sólo las filas con `precio_valido_para_serie=sí` pueden alimentar series, promedios, rankings o semáforos.
Clasificación principal: cero_explicito=34920, operacion_sin_precio=5876.
La base no se considera plenamente apta para indicadores de precio hasta aplicar este filtro y revisar los casos cero.

## Moneda embebida en campo de precio

`Row[10]` contiene el campo original de precio. El símbolo monetario se extrae sólo si aparece explícitamente: `U$S`/`US$`/`USD` se normaliza a `USD`, y `$` sin esos marcadores se normaliza a `ARS`. No se infiere moneda por contexto y se conserva `precio_original_texto`.

## Moneda y comparabilidad

Moneda explícitamente informada: sí (15/15 filas). Moneda inferida: no (0/15 filas). Moneda sin especificar: no (0/15 filas).
Comparabilidad monetaria: no.
Los precios sólo deben compararse dentro de una misma moneda; en esta muestra hay ARS y USD explícitos, por lo que no corresponde calcular variaciones monetarias conjuntas. El estado queda como `parcial_piloto` y no como `si` pleno.

## Actualidad de la información

Fecha máxima disponible: 2026-09-04.
Días desde el último dato: 3.
Commodities actualizados (últimos 7 días): CEBADA FORR., Girasol, Maíz, Soja, TRIGO PAN.
Commodities recientes o actualizados (últimos 30 días): CEBADA FORR., Girasol, Maíz, Soja, TRIGO PAN.
Commodities sin dato reciente: ninguno.
Cobertura últimos 7 días: 15 registro(s). Cobertura últimos 30 días: 15 registro(s).

| Commodity | Fecha máxima | Días | Últimos 7 días | Últimos 30 días | Estado |
| --- | --- | --- | --- | --- | --- |
| CEBADA FORR. | 2026-09-04 | 3 | 1 | 1 | Actualizado |
| Girasol | 2026-09-04 | 3 | 1 | 1 | Actualizado |
| Maíz | 2026-09-04 | 3 | 4 | 4 | Actualizado |
| Soja | 2026-09-04 | 3 | 7 | 7 | Actualizado |
| TRIGO PAN | 2026-09-04 | 3 | 2 | 2 | Actualizado |

## Recomendación de automatización

SIO Granos debe mantenerse como exploración separada hasta validar la procedencia, la definición del precio, los permisos de uso, la estabilidad de la consulta pública y la homogeneidad de moneda, unidad, frecuencia y tipo de precio.
Si hay datos recientes y la consulta/exportación pública es estable, conviene automatizar con ventanas de hasta 180 días y auditoría previa. Si no hay exportación estable, mantener la descarga manual en raw/ y conservar la respuesta original.
No publicar en el dashboard ni mezclar con BCR o frutas/hortalizas antes de esa validación.

## Series y aptitud analítica

| Commodity | Moneda | Unidad | Tipo | Frecuencia | Apto piloto | Apto dashboard | Calidad | Aptitud analítica |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CEBADA FORR. | USD | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Baja | No |
| Girasol | USD | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Baja | No |
| Maíz | ARS | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Baja | No |
| Maíz | USD | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Media | No |
| Soja | ARS | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Alta | No |
| Soja | USD | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Media | No |
| TRIGO PAN | ARS | TN | Precio Hecho | Sin especificar | Sí | parcial_piloto | Media | No |

Casos problemáticos: 4. Ver CASOS_PROBLEMATICOS_COMMODITIES_SIO.csv.

## Próximos pasos

Validar una respuesta real de SIO y revisar especialmente fecha, condición de pago, operación, volumen, procedencia, precio puesto en, unidad, moneda y permisos. No inventar datos ni usar fuentes alternativas como equivalentes de SIO/BCR sin evidencia.
