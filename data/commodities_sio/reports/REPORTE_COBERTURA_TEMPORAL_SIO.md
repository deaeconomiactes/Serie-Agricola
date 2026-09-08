# Reporte de cobertura temporal SIO

## Resumen

La cobertura que actualmente alimenta el módulo Commodities SIO comienza el **12/03/2026** y llega hasta el **07/09/2026**. Sólo está disponible el año **2026**, con datos en los meses de marzo, abril, mayo, junio, julio, agosto y septiembre.

El dashboard muestra ese rango porque los CSV dashboard-ready se generaron desde la base analítica SIO disponible. No existe una restricción fija en el frontend que fuerce el inicio en marzo: las fechas visibles provienen de los datos procesados.

## Fuente utilizada

- Base analítica local: `data/commodities_sio/processed/COMMODITIES_SIO_ANALITICO_PRECIOS.csv`.
- Fuente declarada: SIO Granos / Secretaría de Agricultura.
- Registros analíticos utilizados: **351.600**.
- Criterio: fecha válida, commodity, moneda, unidad y tipo de precio informados, `precio_valido_para_serie=sí` y precio positivo.
- Salidas consumidas por el navegador: `data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_*.csv`.
- Las bases completas no se cargan en el navegador ni se versionan cuando permanecen fuera de Git por tamaño.

## Fechas y períodos disponibles

| Indicador | Valor |
|---|---|
| Fecha mínima | 2026-03-12 |
| Fecha máxima | 2026-09-07 |
| Años disponibles | 2026 |
| Meses disponibles | 2026-03 a 2026-09 |
| ¿La cobertura arranca en marzo? | Sí, el primer registro válido es del 12 de marzo de 2026 |

## Registros por mes

| Mes | Registros válidos | Commodities | Monedas |
|---|---:|---:|---|
| 2026-03 | 32.081 | 11 | ARS, USD |
| 2026-04 | 50.537 | 11 | ARS, USD |
| 2026-05 | 68.227 | 11 | ARS, USD |
| 2026-06 | 59.547 | 11 | ARS, USD |
| 2026-07 | 62.160 | 11 | ARS, USD |
| 2026-08 | 65.265 | 11 | ARS, USD |
| 2026-09 | 13.783 | 11 | ARS, USD |
| **Total** | **351.600** | — | — |

Los 11 commodities presentes en cada mes son: `ACEITE SOJA`, `ARROZ C.L.A`, `ARROZ C.L.F`, `CEBADA CERV.`, `CEBADA FORR.`, `Girasol`, `Maíz`, `Soja`, `Sorgo`, `TRIGO CAND.` y `TRIGO PAN`. La cobertura monetaria mensual contiene `ARS` y `USD`; ambas monedas se mantienen separadas en las agregaciones y visualizaciones.

## Causa probable

La causa más probable es que la exportación manual y la base analítica disponible corresponden a una captura reciente, no a una extracción histórica completa. La presencia de marzo como primer mes no demuestra que SIO carezca de datos anteriores; sólo demuestra que esos datos no forman parte de la base actualmente procesada.

La consulta pública observada tiene un límite de hasta 180 días por rango. Para buscar años anteriores será necesario descargar por tramos, auditar cada ventana y verificar continuidad. No se debe completar el período con World Bank ni con otra fuente como si fuera SIO.

## Implicación para el dashboard

El módulo actual sigue siendo válido para el rango disponible y conserva la metodología SIO: operaciones informadas, precios positivos, separación ARS/USD y unidad/tipo de precio explícitos. La ampliación histórica debe permanecer fuera del dashboard hasta contar con evidencia de continuidad y comparabilidad. El plan operativo está en `PLAN_HISTORICO_SIO_POR_TRAMOS.md`.
