# Guía de actualización SIO con GitHub Actions

## Arquitectura

GitHub Pages no ejecuta Python ni consulta SIO. El workflow ejecuta la actualización antes de publicar los archivos estáticos:

`GitHub Actions → SIO → snapshot → histórico liviano → dashboard CSV → GitHub Pages`

Cada corrida consulta una sola vez `GetOperaciones`, sin paginar. El JSON de respuesta se usa como snapshot temporal y no se versiona. La memoria persistente es `dashboard/COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv`, un CSV liviano deduplicado que permite que la siguiente corrida continúe desde el estado publicado.

## Ejecución diaria

El workflow `.github/workflows/update-sio-commodities.yml` tiene un schedule diario aproximado a las 10:30 de Argentina:

```text
30 13 * * *
```

El horario está expresado en UTC. GitHub Actions puede iniciar una tarea con demora; la hora es orientativa.

## Ejecución manual

1. Abrir la pestaña **Actions** del repositorio.
2. Seleccionar **Actualizar commodities SIO**.
3. Elegir **Run workflow**.
4. Revisar el resumen de la corrida y los archivos modificados.

La ejecución manual usa el mismo flujo que la diaria y publica sólo si existen cambios.

## Qué hace el workflow

1. Descarga el repositorio y configura Python.
2. Instala `requirements.txt` si el repositorio lo incorpora.
3. Consulta una vez las últimas operaciones de SIO.
4. Integra el snapshot y actualiza el histórico liviano.
5. Audita actualidad, moneda, unidad, duplicados y precios cero.
6. Regenera los CSV dashboard-ready.
7. Commitea sólo salidas livianas si hubo cambios.

El commit automático usa el mensaje:

```text
chore: actualizar commodities SIO diario
```

No se hace force push. El workflow no versiona JSON raw, HTML, HAR, cURL, configuraciones locales ni bases completas.

## Archivos versionados por el workflow

- `data/commodities_sio/dashboard/COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv`
- `data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_*.csv`
- `data/commodities_sio/reports/REPORTE_ACTUALIZACION_DIARIA_SIO.md`
- `data/commodities_sio/reports/RESUMEN_ACTUALIDAD_COMMODITIES_SIO.csv`

El histórico liviano contiene sólo los campos necesarios para reconstruir las series y conservar trazabilidad. ARS y USD permanecen separados; los precios cero pueden conservarse como evidencia, pero nunca alimentan gráficos, rankings, promedios o semáforos.

## Archivos fuera de Git

- `data/commodities_sio/raw/`
- `data/commodities_sio/devtools/`
- `data/commodities_sio/processed/COMMODITIES_SIO_LATEST_SNAPSHOT.csv`
- `data/commodities_sio/processed/COMMODITIES_SIO_HISTORICO_SNAPSHOTS.csv`
- `COMMODITIES_SIO_EXPORTACION_MANUAL.csv`
- `COMMODITIES_SIO_ANALITICO_PRECIOS.csv`
- configuraciones locales y credenciales

## Cómo revisar los logs

En **Actions**, abrir la ejecución y revisar especialmente los pasos **Capturar snapshot latest**, **Integrar snapshot e histórico**, **Auditar resultado** y **Publicar salidas livianas**. Los logs deben indicar fecha de corrida, operaciones capturadas, nuevas, duplicados omitidos y archivos regenerados, sin imprimir tokens ni el contenido completo del raw.

## Si SIO falla

El workflow debe detenerse antes del commit. No se borra el histórico liviano publicado ni se reemplazan los CSV dashboard-ready de la corrida anterior. Revisar el error de red o de estructura, volver a ejecutar manualmente cuando corresponda y auditar cualquier cambio de columnas antes de reactivar el schedule.

La cobertura acumulada sólo representa las operaciones que estaban presentes en los snapshots observados desde el inicio del monitoreo. No es un histórico completo de SIO y no reemplaza BCR ni el histórico local mensual de precios internos.

## Desactivar el schedule

Para pausar la actualización automática, comentar o eliminar el bloque `schedule` del workflow y conservar `workflow_dispatch` si se desea mantener la ejecución manual. También se puede desactivar el workflow desde la pestaña **Actions** de GitHub.
