# Reporte de precios cero SIO

## Objetivo

Auditar precios cero en la exportación manual SIO antes de usar la base para análisis o dashboard.

## Resumen ejecutivo

- Filas totales: 396971.
- Precios positivos: 356175.
- Precios cero: 40796 (10.28%).
- Precios faltantes: 0.
- Decisión metodológica: Conservar los registros en la base completa, pero excluir precio=0 de toda serie, promedio, ranking y semáforo. No imputar ni reemplazar el valor original.

## Distribución de precios cero

### commodity

| Valor | Registros |
| --- | ---: |
| Soja | 18413 |
| Maíz | 14294 |
| TRIGO PAN | 5965 |
| Girasol | 1048 |
| Sorgo | 398 |
| CEBADA CERV. | 289 |
| CEBADA FORR. | 227 |
| ARROZ C.L.F | 85 |
| TRIGO CAND. | 57 |
| ARROZ C.L.A | 20 |

### moneda

| Valor | Registros |
| --- | ---: |
| Sin especificar | 40795 |
| ARS | 1 |

### tipo_precio

| Valor | Registros |
| --- | ---: |
| Compraventa | 37723 |
| Canje | 3073 |

### operacion

| Valor | Registros |
| --- | ---: |
| Contrato | 34917 |
| Anulación | 3645 |
| Rectificación | 2181 |
| Rectificación Ampliación | 50 |
| Fijación | 3 |

### condicion_pago

| Valor | Registros |
| --- | ---: |
| Contra entrega | 30974 |
| A plazo | 8661 |
| Anticipado a la entrega | 1161 |

### procedencia

| Valor | Registros |
| --- | ---: |
| CÓRDOBA | 12323 |
| BUENOS AIRES | 10211 |
| SANTA FE | 8563 |
| ENTRE RÍOS | 3455 |
| SANTIAGO DEL ESTERO | 1908 |
| CHACO | 1183 |
| LA PAMPA | 887 |
| SAN LUIS | 739 |
| SALTA | 684 |
| TUCUMÁN | 386 |
| CIUDAD AUTÓNOMA DE BUENOS AIRES | 289 |
| CATAMARCA | 61 |
| FORMOSA | 55 |
| CORRIENTES | 29 |
| JUJUY | 16 |
| RÍO NEGRO | 2 |
| SAN JUAN | 2 |
| NEUQUÉN | 1 |
| MISIONES | 1 |
| LA RIOJA | 1 |

### lugar_entrega

| Valor | Registros |
| --- | ---: |
| Rosario S/En destino | 8397 |
| Rosario N/En destino | 7468 |
| Zona 7/En destino | 3182 |
| Zona 8/En destino | 2839 |
| Zona 9/En destino | 2543 |
| Zona 6/En destino | 2278 |
| Zona 13/En destino | 1594 |
| Cordoba/En destino | 1505 |
| Zona 15/En destino | 1357 |
| Zona 11/En destino | 910 |
| Quequen/En destino | 906 |
| Zona 10/En destino | 869 |
| B.Blanca/En destino | 853 |
| Zona 14/En destino | 769 |
| Rosario N/En origen | 559 |
| Zona 18/En destino | 552 |
| Zona 2/En destino | 518 |
| Zona 25/En destino | 512 |
| Zona 12/En destino | 481 |
| Zona 15/En origen | 392 |
| Zona 17/En origen | 386 |
| Zona 17/En destino | 384 |
| Zona 5/En destino | 265 |
| Zona 16/En origen | 221 |
| Zona 16/En destino | 147 |
| Bs As/En destino | 133 |
| Cordoba/En origen | 125 |
| Zona 3/En destino | 117 |
| Zona 7/En origen | 103 |
| Zona 11/En origen | 97 |
| Zona 4/En destino | 92 |
| Zona 25/En origen | 37 |
| Zona 4/En origen | 36 |
| Zona 18/En origen | 32 |
| Zona 8/En origen | 29 |
| Zona 9/En origen | 23 |
| Quequen/En origen | 21 |
| Zona 6/En origen | 17 |
| Zona 13/En origen | 15 |
| Zona 26/En origen | 13 |
| Zona 26/En destino | 4 |
| Zona 2/En origen | 3 |
| Zona 1/En destino | 3 |
| Zona 3/En origen | 2 |
| Zona 5/En origen | 2 |
| Zona 14/En origen | 2 |
| Rosario S/En origen | 1 |
| B.Blanca/En origen | 1 |
| Zona 12/En origen | 1 |

### año

| Valor | Registros |
| --- | ---: |
| 2026 | 40796 |

### mes

| Valor | Registros |
| --- | ---: |
| 2026-06 | 9531 |
| 2026-08 | 7126 |
| 2026-04 | 6795 |
| 2026-05 | 6335 |
| 2026-07 | 5851 |
| 2026-03 | 3772 |
| 2026-09 | 1386 |

### archivo_origen

| Valor | Registros |
| --- | ---: |
| SIO_exportar_operaciones_2026-09-07.csv | 40796 |

### precio_cero_tipo

| Valor | Registros |
| --- | ---: |
| cero_explicito | 34920 |
| operacion_sin_precio | 5876 |

## Origen probable de los ceros

- `precio_original_texto`: precio_original_texto dice cero=40796.
- La clasificación se basa en el valor original y en el campo operación; no afirma que un cero sea económicamente válido sin documentación adicional.
- Los ceros actuales observados están respaldados por texto original numérico `0`/`0,00`; las categorías de texto sin precio, vacío o parsing fallido quedan contempladas para futuras exportaciones.

## Regla propuesta

- Conservar registros y valor original para trazabilidad.
- Excluir `precio=0` de promedios, evolución, rankings y semáforos.
- Mantenerlos visibles sólo en auditoría/calidad.
- No imputar precio ni convertir cero en missing sin conservar el valor original.
- Usar `precio_valido_para_serie=sí` como filtro analítico.

## Impacto en dashboard

No debe graficarse precio cero como precio de mercado. Los indicadores deben usar sólo `precio_valido_para_serie=sí` y mostrar una nota metodológica si SIO se integra en el futuro.

## Casos problemáticos

Se generó `data/commodities_sio/reports/CASOS_PRECIOS_CERO_SIO.csv` con todos los registros con precio cero y su clasificación.
