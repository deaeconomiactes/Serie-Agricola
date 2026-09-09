# Reporte de dashboard de commodities SIO

## Fuente y criterio

- Fuente de preparación: `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/dashboard/COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv`.
- Se usó el histórico acumulado de snapshots SIO; el dashboard sólo recibe agregados livianos.
- Filas leídas: 31; filas analíticas válidas utilizadas: 31.
- Rango temporal: 2026-09-09 a 2026-09-09.
- Actualización del dashboard: 2026-09-09.
- Última captura SIO: 2026-09-09T11:20:00.
- Última operación informada: 2026-09-09.
- Rango de operaciones: 2026-09-09 — 2026-09-09.
- Commodities: CEBADA FORR., Girasol, Maíz, Soja, TRIGO PAN.
- Monedas: ARS, USD; unidades: TN.
- Regla: sólo `precio_valido_para_serie=sí`, precio positivo, fecha válida, commodity, fuente, moneda explícita y unidad explícita. Los precios cero quedan fuera.
- Las series se separan por commodity, moneda, unidad y tipo_precio; ARS y USD no se agregan conjuntamente.

## Archivos generados

| Archivo | Filas | Tamaño (MB) | Uso |
| --- | ---: | ---: | --- |
| `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_DIARIO.csv` | 8 | 0.002 | evolución diaria y volumen |
| `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_MENSUAL.csv` | 8 | 0.001 | series mensuales y variaciones |
| `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_ULTIMOS.csv` | 8 | 0.001 | último dato por serie |
| `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_RESUMEN.csv` | 1 | 0.001 | indicadores de fuente y cobertura |
| `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_SEMAFORO.csv` | 8 | 0.001 | variaciones mensuales por serie |

## Filtros y visualizaciones

- Filtros: commodity, moneda, unidad, tipo de precio y frecuencia diaria/mensual.
- KPIs: última actualización, commodities, operaciones analíticas, moneda seleccionada y mediana del último dato.
- Gráficos: evolución de mediana, ranking reciente, volumen por commodity y semáforo mensual.
- La mediana es la métrica principal de visualización; el promedio y el ponderado por volumen quedan como contexto.

## Limitaciones y aptitud

- La fuente corresponde a operaciones informadas SIO y no equivale a precio de pizarra BCR, futuros ni precios mayoristas frutihortícolas.
- Los agregados no corrigen la limitación de paginación de GetOperaciones ni garantizan actualización automática. Cuando la fuente es el histórico de snapshots, cada corrida incorpora sólo las últimas operaciones observadas y no equivale a histórico completo.
- La aptitud es exploratoria y parcial para piloto; no productiva hasta validar actualización, frecuencia, procedencia, permisos e interpretación.
- Los estados `Baja`, `Estable`, `Suba moderada`, `Suba fuerte`, `Revisar` y `Sin dato` describen variación de precios; no representan escasez ni desabastecimiento.
- La base completa no se carga en el navegador ni se versiona cuando supera el tamaño razonable para Git.
