# Reporte de actualización diaria SIO

## Objetivo

Controlar la captura incremental de snapshots de últimas operaciones SIO. Esta actualización no representa un histórico completo.

## Última corrida

- Fecha/hora de captura: 2026-11-09T23:03:09.
- Archivo raw usado: `SIO_latest_GetOperaciones_20261109_230309.json`.
- Histórico persistente usado: `data/commodities_sio/processed/COMMODITIES_SIO_HISTORICO_SNAPSHOTS.csv`.
- Histórico liviano versionable: `data/commodities_sio/dashboard/COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv`.
- Operaciones latest válidas: 6.
- Operaciones nuevas respecto de capturas anteriores: 6.
- Duplicados omitidos respecto de capturas anteriores: 0.
- Filas acumuladas: 813.
- Fecha mínima de operaciones acumuladas: 2026-09-09.
- Fecha máxima de operaciones acumuladas: 2026-11-09.
- Monedas latest: ARS, USD.
- Commodities latest: Maíz, Soja, TRIGO PAN.
- Precios válidos positivos latest: 6.
- Precios cero latest: 0.
- Filas aptas para dashboard por fecha, commodity, moneda, unidad y precio positivo: 6/6.
- Estado: apto para regenerar agregados livianos sólo dentro de las series con metadatos homogéneos.

## Limitaciones

- El snapshot contiene sólo las últimas operaciones devueltas por `GetOperaciones`; no es histórico completo.
- La cobertura depende de la frecuencia de ejecución.
- Si el proceso no corre un día, puede perder operaciones que ya no estén presentes en el snapshot siguiente.
- No se pagina ni se prueban variantes del endpoint.
- SIO no reemplaza BCR ni el histórico local mensual de precios internos.
- Los precios cero se conservan para trazabilidad, pero no son válidos para series, promedios, rankings ni semáforos.

## Recomendación

- Ejecutar como mínimo una vez por día durante el piloto.
- Si se busca mayor cobertura intradiaria, ejecutar cada 3 o 6 horas.
- Mantener monitoreo de duplicados, cambios de estructura, moneda, unidad y fecha.
- Conservar los raw localmente y versionar sólo scripts, reportes y agregados livianos.
