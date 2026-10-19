# Actualización productiva MCBA MAGyP

`update-magyp-mcba.yml` es el workflow productivo, inicialmente sólo `workflow_dispatch`. `magyp-mcba-pilot.yml` conserva diagnóstico Chromium opcional, permisos de lectura y ejecución exclusivamente manual. Ninguno se activa en cada push. No se eliminó el piloto.

Ambos inicializan sus carpetas temporales en un step con `$RUNNER_TEMP` y `$GITHUB_ENV`; no usan el contexto `runner.temp` en `env` del job. En producción:

```bash
echo "MCBA_CAPTURE_ROOT=$RUNNER_TEMP/mcba-capture" >> "$GITHUB_ENV"
```

## Flujo productivo

1. Checkout con historia para regresiones; Python 3.12, Node 24 y dependencias Chromium fijadas.
2. Tests offline, una captura MAGyP del día solicitado, validación, normalización, analytical y construcción incremental del bundle diario. Sin backfill ni retries.
3. Guardia `validate_production_mcba.py`: hashes del conjunto, contrato de las filas, cuatro CSV obligatorios, marcador, estado, fecha solicitada y timestamp UTC; máximo 10 MiB por archivo. El mensual previo puede figurar en el marcador para compatibilidad, pero nunca se agrega a la publicación incremental.
4. Repetir tests MCBA/frontend y `git diff --check` con las salidas resultantes.
5. Sólo en main, commit/push sin force de un allowlist cerrado. Una ejecución en rama de revisión genera artefactos y no publica.
6. Despachar explícitamente `deploy.yml` sobre main con `gh workflow run deploy.yml --ref main`. El job dispone de `contents:write` y `actions:write`; no depende del push con GITHUB_TOKEN. Pages realiza su propio checkout limpio y desencriptado existente; no recibe RAW ni el workspace de captura. No se cambió el workflow de Pages.

El despacho no acredita éxito de Pages: su resultado se consulta en `deploy.yml`. Un fallo de despacho hace fallar la actualización; un fallo posterior de Pages conserva el último sitio desplegado. Una ejecución validada puede volver a despacharlo incluso sin cambios de CSV.

## Archivos publicables

- `MCBA_MAGYP_DAILY.csv`
- `MCBA_MAGYP_DETAIL.csv`
- `MCBA_MAGYP_LATEST.csv`
- `MCBA_MAGYP_SUMMARY.csv`
- `_SUCCESS.json`
- `MCBA_MAGYP_UPDATE_STATUS.json`

Todos bajo `data/magyp/dashboard/mcba/`. RAW XLSX/manifests quedan fuera de Git y de Pages, en un artefacto de auditoría separado de 90 días; diagnósticos, 14 días. Esa retención no es un archivo RAW permanente. No se guardan perfiles, cookies, viewstate, tokens ni trazas de sesión.

## Falla de adquisición

El actualizador existente conserva los CSV y registra `MAGYP_LAST_VALID`. El workflow captura el resultado sin abortar prematuramente para validar el bundle previo y ejecutar regresiones. Si ese fallback está íntegro, sólo permite stage/commit de `MCBA_MAGYP_UPDATE_STATUS.json` y un despliegue explícito del estado. Nunca commitea CSV nuevos tras una captura fallida. Al final marca la ejecución como fallida para que el problema sea visible.

Si no existe bundle válido, hay corrupción, falla un test o no puede validarse la metadata, no se commitea ni despliega. Un push concurrente incompatible también falla sin force y conserva el remoto. No se aceptan archivos vacíos para sustituir fuentes.

MAGyP sigue siendo el principal diario MCBA. El fallback/histórico legacy y el mensual legacy conservan su comportamiento. No se modifican la lógica económica, frontend, Corrientes, Cantidades ni Commodities.

## Activación

Después del merge revisado, ejecutar `update-magyp-mcba.yml` manualmente con un día ISO y comprobar tanto la captura como `deploy.yml`. En la rama de revisión también puede hacerse smoke sin publicar. El schedule diario queda comentado, listo para activar sólo tras el smoke exitoso en GitHub/Linux: `0 23 * * *` (aproximadamente 20:00 Argentina). No se habilitó automáticamente.

Validación local: tests completos `tests/magyp_mcba`, suites frontend existentes, guardia sobre bundle real sin mutarlo, actionlint y `git diff --check`. No confundir esas pruebas con una captura real Linux satisfactoria.
