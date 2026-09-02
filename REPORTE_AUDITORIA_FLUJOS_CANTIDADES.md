# Auditoría de flujos de cantidades

## 1. Resumen ejecutivo

- Archivo auditado: `REGISTRO 2025 INTEGRADO.csv`.
- Registros leídos: **49,647**.
- Destinos válidos para el filtro ejecutivo: **Buenos Aires** y **Corrientes**.
- Registros con destino válido: **34,257**.
- Registros con destino sospechoso, vacío o inválido: **15,390**.
- Registros identificados como tomate: **3,733**; genéricos: **698**; sin variedad: **116**.

La auditoría es no destructiva. Los valores originales se conservan en los CSV de casos y no se reescribe la base integrada.

## 2. Orígenes detectados

| Origen normalizado | Registros | Peso tn |
| --- | --- | --- |
| Corrientes | 24131 | 129336.549 |
| Mendoza | 5483 | 252604.451 |
| Buenos Aires | 4636 | 518784.709 |
| Río Negro | 2047 | 241926.316 |
| Jujuy | 1987 | 57339.074 |
| Entre Ríos | 1310 | 329242.548 |
| Salta | 1301 | 146702.866 |
| Santa Fe | 1206 | 53384.094 |
| Mar del Plata | 1126 | 25199.683 |
| Brasil | 1082 | 70392.19 |
| San Juan | 776 | 40335.036 |
| Tucumán | 664 | 103696.059 |
| Chile | 512 | 25266.459 |
| Misiones | 467 | 26644.866 |
| Santiago del Estero | 403 | 37126.614 |
| Neuquén | 394 | 12659.824 |
| Formosa | 294 | 9568.827 |
| Córdoba | 287 | 76325.868 |
| Chaco | 266 | 1901.423 |
| Ecuador | 212 | 90325.457 |
| San Pedro | 126 | 2191.012 |
| Bolivia | 98 | 36055.349 |
| Paraguay | 97 | 21290.47 |
| España | 92 | 732.609 |
| San Luis | 76 | 25513.634 |
| Se Bs.As | 73 | 222497.6 |
| Sud. Bs As | 62 | 172024.636 |
| Perú | 59 | 926.594 |
| Chubut | 54 | 1453.636 |
| La Rioja | 40 | 1117.69 |
| Catamarca | 39 | 3730.16 |
| Egipto | 39 | 600.633 |
| Colombia | 38 | 2930.463 |
| Ciudad Autónoma de Buenos Aires | 28 | 139.85 |
| La Pampa | 22 | 84.7 |
| Santa Cruz | 21 | 288.49 |
| Italia | 17 | 199.775 |
| Puerto Rico | 13 | 3.9 |
| Grecia | 12 | 163.491 |
| Grl.Belg | 12 | 9419.8 |
| (vacío / inválido) | 11 | 29.039 |
| Sur. Bs As | 11 | 269.764 |
| México | 10 | 350.066 |
| Gral Belgrano | 5 | 3158.948 |
| V.Dolor. | 3 | 107.6 |
| S.Bs.As. | 2 | 30.8 |
| China | 1 | 21.0 |
| Portugal | 1 | 20.2 |
| Rosario | 1 | 48.0 |

Las variantes de escritura se detallan en `RESUMEN_ORIGENES_CANTIDADES.csv`.

## 3. Destinos detectados

| Destino original | Destino normalizado | Clasificación | Registros |
| --- | --- | --- | --- |
| CORRIENTES | Corrientes | válido | 30436 |
| BSAS | Buenos Aires | válido | 3821 |
| MENDOZA | — | sospechoso | 2462 |
| SALTA | — | sospechoso | 1220 |
| BRASIL | — | sospechoso | 1082 |
| R. NEGRO | — | sospechoso | 1017 |
| JUJUY | — | sospechoso | 905 |
| SAN JUAN | — | sospechoso | 773 |
| E. RIOS | — | sospechoso | 709 |
| SANTA FE | — | sospechoso | 707 |
| M.D.PLAT | — | sospechoso | 693 |
| RÍO NEGRO | — | sospechoso | 607 |
| CHILE | — | sospechoso | 512 |
| ENTRE RÍOS | — | sospechoso | 487 |
| MAR DEL PLATA | — | sospechoso | 433 |
| SANTA FÉ | — | sospechoso | 367 |
| TUCUMAN | — | sospechoso | 358 |
| MISIONES | — | sospechoso | 317 |
| NEUQUEN | — | sospechoso | 253 |
| TUCUMÁN | — | sospechoso | 249 |
| FORMOSA | — | sospechoso | 213 |
| SGO.EST. | — | sospechoso | 213 |
| ECUADOR | — | sospechoso | 212 |
| CORDOBA | — | sospechoso | 179 |
| NEUQUÉN | — | sospechoso | 141 |
| SGO DEL ESTERO | — | sospechoso | 131 |
| S. PEDRO | — | sospechoso | 116 |
| BOLIVIA | — | sospechoso | 98 |
| PARAGUAY | — | sospechoso | 97 |
| ESPAÑA | — | sospechoso | 92 |
| CÓRDOBA | — | sospechoso | 81 |
| SAN LUIS | — | sospechoso | 73 |
| SE BS.AS | — | sospechoso | 73 |
| SUD. BS AS | — | sospechoso | 62 |
| CHUBUT | — | sospechoso | 53 |
| CHACO | — | sospechoso | 51 |
| LA RIOJA | — | sospechoso | 40 |
| EGIPTO | — | sospechoso | 39 |
| COLOMBIA | — | sospechoso | 38 |
| PERU | — | sospechoso | 37 |
| LA PAMPA | — | sospechoso | 22 |
| PERÚ | — | sospechoso | 22 |
| CATAMARC | — | sospechoso | 21 |
| ITALIA | — | sospechoso | 17 |
| STA.CRUZ | — | sospechoso | 15 |
| PTO.RICO | — | sospechoso | 13 |
| GRECIA | — | sospechoso | 12 |
| GRL.BELG | — | sospechoso | 12 |
| SUR. BS AS | — | sospechoso | 11 |
| (vacío / inválido) | — | sospechoso | 10 |
| SAN PEDRO | — | sospechoso | 10 |
| SANTA CRUZ | — | sospechoso | 6 |
| CATAMARCA | — | sospechoso | 5 |
| GRAL BELGRANO | — | sospechoso | 5 |
| MEXICO | — | sospechoso | 5 |
| MÉXICO | — | sospechoso | 5 |
| V.DOLOR. | — | sospechoso | 3 |
| S.BS.AS. | — | sospechoso | 2 |
| #N/A | — | sospechoso | 1 |
| CHINA | — | sospechoso | 1 |
| PORTUGAL | — | sospechoso | 1 |
| ROSARIO | — | sospechoso | 1 |

62 valores originales de destino fueron detectados.

## 4. Combinaciones origen-destino

Principales combinaciones por cantidad de registros:

| Origen | Destino normalizado | Destino original | Registros | Peso tn |
| --- | --- | --- | --- | --- |
| Corrientes | Corrientes | CORRIENTES | 24131 | 129336.549 |
| Buenos Aires | Buenos Aires | BSAS | 3821 | 513886.72 |
| Mendoza | Corrientes | CORRIENTES | 3021 | 6912.485 |
| Mendoza | — | MENDOZA | 2462 | 245691.966 |
| Salta | — | SALTA | 1220 | 146531.914 |
| Jujuy | Corrientes | CORRIENTES | 1082 | 2863.179 |
| Brasil | — | BRASIL | 1082 | 70392.19 |
| Río Negro | — | R. NEGRO | 1017 | 134210.6 |
| Jujuy | — | JUJUY | 905 | 54475.895 |
| Buenos Aires | Corrientes | CORRIENTES | 815 | 4897.989 |
| San Juan | — | SAN JUAN | 773 | 40330.476 |
| Entre Ríos | — | E. RIOS | 709 | 200848.7 |
| Santa Fe | — | SANTA FE | 707 | 34781.2 |
| Mar del Plata | — | M.D.PLAT | 693 | 15647.2 |
| Río Negro | — | RÍO NEGRO | 607 | 106183.57 |
| Chile | — | CHILE | 512 | 25266.459 |
| Entre Ríos | — | ENTRE RÍOS | 487 | 128060.278 |
| Mar del Plata | — | MAR DEL PLATA | 433 | 9552.483 |
| Río Negro | Corrientes | CORRIENTES | 423 | 1532.146 |
| Santa Fe | — | SANTA FÉ | 367 | 18004.156 |
| Tucumán | — | TUCUMAN | 358 | 69432.3 |
| Misiones | — | MISIONES | 317 | 25869.61 |
| Neuquén | — | NEUQUEN | 253 | 7211.4 |
| Tucumán | — | TUCUMÁN | 249 | 33039.995 |
| Chaco | Corrientes | CORRIENTES | 215 | 479.173 |
| Formosa | — | FORMOSA | 213 | 9082.067 |
| Santiago del Estero | — | SGO.EST. | 213 | 24544.0 |
| Ecuador | — | ECUADOR | 212 | 90325.457 |
| Córdoba | — | CORDOBA | 179 | 47552.9 |
| Misiones | Corrientes | CORRIENTES | 150 | 775.256 |

El detalle completo está en `RESUMEN_ORIGEN_DESTINO_CANTIDADES.csv`.

## 5. Destinos sospechosos

Se detectaron **15,390** registros fuera de las equivalencias válidas. No se eliminan: se excluyen del filtro visible de destino y se conservan en `CASOS_DESTINO_SOSPECHOSO_CANTIDADES.csv`.

Principales valores observados:

| Destino original | Normalización | Clasificación | Registros |
| --- | --- | --- | --- |
| CORRIENTES | Corrientes | válido | 30436 |
| BSAS | Buenos Aires | válido | 3821 |
| MENDOZA | — | sospechoso | 2462 |
| SALTA | — | sospechoso | 1220 |
| BRASIL | — | sospechoso | 1082 |
| R. NEGRO | — | sospechoso | 1017 |
| JUJUY | — | sospechoso | 905 |
| SAN JUAN | — | sospechoso | 773 |
| E. RIOS | — | sospechoso | 709 |
| SANTA FE | — | sospechoso | 707 |
| M.D.PLAT | — | sospechoso | 693 |
| RÍO NEGRO | — | sospechoso | 607 |
| CHILE | — | sospechoso | 512 |
| ENTRE RÍOS | — | sospechoso | 487 |
| MAR DEL PLATA | — | sospechoso | 433 |
| SANTA FÉ | — | sospechoso | 367 |
| TUCUMAN | — | sospechoso | 358 |
| MISIONES | — | sospechoso | 317 |
| NEUQUEN | — | sospechoso | 253 |
| TUCUMÁN | — | sospechoso | 249 |

Campos vacíos o inválidos: MERCADO=11, MUNICIPIO=27319, PROCEDENCIA=11, VARIEDAD=55.

## 6. Revisión de productos agregados

La regla derivada `producto_normalizado` separa `Tomate Redondo`, `Tomate Perita`, `Tomate Cherry`, `Tomate Larga Vida`, `Tomate Platense` y otros tipos existentes. Los casos sin variedad se etiquetan como `Tomate sin variedad especificada`; ningún registro original se elimina.

El detalle de los 3,733 registros relacionados con tomate está en `CASOS_PRODUCTO_AGREGADO_CANTIDADES.csv`.

## 7. Recomendaciones de corrección

1. Mantener `Buenos Aires` y `Corrientes` como únicas opciones visibles del filtro Destino de cantidades.
2. Mantener los destinos sospechosos para auditoría, sin sumarlos a una opción ejecutiva válida.
3. Mantener Origen amplio, normalizando tildes, abreviaturas y errores de planilla.
4. Usar `producto_normalizado` para filtros, rankings y tablas; conservar `ESPECIE` y `VARIEDAD` originales.
5. Cuando se selecciona un producto específico y Origen es `Todos`, desagregar la tabla de cantidades por origen.
6. Revisar en la fuente de integración la asignación de `MERCADO` para los registros cuyo valor coincide con una procedencia.
