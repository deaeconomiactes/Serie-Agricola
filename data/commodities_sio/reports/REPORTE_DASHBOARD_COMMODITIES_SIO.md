# Reporte de dashboard de commodities SIO

## Fuente y criterio

- Fuente de preparación: `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/processed/COMMODITIES_SIO_ANALITICO_PRECIOS.csv`.
- Se usó la base analítica completa local; el dashboard sólo recibe agregados livianos.
- Filas leídas: 351600; filas analíticas válidas utilizadas: 351600.
- Rango temporal: 2026-03-12 a 2026-09-07.
- Commodities: ACEITE SOJA, ARROZ C.L.A, ARROZ C.L.F, CEBADA CERV., CEBADA FORR., Girasol, Maíz, Soja, Sorgo, TRIGO CAND., TRIGO PAN.
- Monedas: ARS, USD; unidades: TN.
- Regla: sólo `precio_valido_para_serie=sí`, precio positivo, fecha válida, commodity, fuente, moneda explícita y unidad explícita. Los precios cero quedan fuera.
- Las series se separan por commodity, moneda, unidad y tipo_precio; ARS y USD no se agregan conjuntamente.

## Archivos generados

| Archivo | Filas | Tamaño (MB) | Uso |
| --- | ---: | ---: | --- |
| `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_DIARIO.csv` | 3581 | 1.170 | evolución diaria y volumen |
| `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_MENSUAL.csv` | 238 | 0.033 | series mensuales y variaciones |
| `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_ULTIMOS.csv` | 39 | 0.003 | último dato por serie |
| `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_RESUMEN.csv` | 1 | 0.001 | indicadores de fuente y cobertura |
| `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_SEMAFORO.csv` | 238 | 0.015 | variaciones mensuales por serie |

## Filtros y visualizaciones

- Filtros: commodity, moneda, unidad, tipo de precio y frecuencia diaria/mensual.
- KPIs: última actualización, commodities, operaciones analíticas, moneda seleccionada y mediana del último dato.
- Gráficos: evolución de mediana, ranking reciente, volumen por commodity y semáforo mensual.
- La mediana es la métrica principal de visualización; el promedio y el ponderado por volumen quedan como contexto.

## Limitaciones y aptitud

- La fuente corresponde a operaciones informadas SIO y no equivale a precio de pizarra BCR, futuros ni precios mayoristas frutihortícolas.
- Los agregados no corrigen la limitación de paginación de GetOperaciones ni garantizan actualización automática.
- La aptitud es exploratoria y parcial para piloto; no productiva hasta validar actualización, frecuencia, procedencia, permisos e interpretación.
- Los estados `Baja`, `Estable`, `Suba moderada`, `Suba fuerte`, `Revisar` y `Sin dato` describen variación de precios; no representan escasez ni desabastecimiento.
- La base completa no se carga en el navegador ni se versiona cuando supera el tamaño razonable para Git.
