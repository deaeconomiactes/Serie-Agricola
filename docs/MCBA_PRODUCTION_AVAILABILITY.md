# MCBA: disponibilidad de fuente y publicación productiva

El workflow Windows self-hosted usa Edge instalado (Chromium sólo si falta Edge),
workflow_dispatch y tres ventanas diarias: 15:00, 19:00 y 23:00 UTC
(12:00, 16:00 y 20:00 Argentina). El runner debe permanecer encendido y conectado.
La fecha automática es el día civil argentino; no se realiza backfill.

El comando productivo usa run_productive, que valida el bundle existente antes de
consultar la fuente. Una fecha ya presente produce NO_OP_ALREADY_CURRENT sin red.
No se buscan revisiones de fechas ya capturadas en este modo programado.

- UPDATED: XLSX, schema, fechas y filas válidos; normalización, analytical y bundle
  incremental. Sólo tras tests/validación se permite commit de allowlist y deploy explícito.
- SOURCE_UNAVAILABLE: timeout, conexión, HTTP 5xx/401/403/404/429 o navegación sin
  respuesta. Conserva CSV y finaliza con éxito operativo, sin commit/deploy.
- NO_PUBLICATION: export reconocido por el parser con encabezados válidos y cero
  filas. Un timeout o una grilla que no logra confirmar el filtro NO demuestra ausencia:
  se registra SOURCE_UNAVAILABLE. No se infiere ausencia por fin de semana.
- PIPELINE_ERROR: schema/XLSX inválido, fecha incorrecta, contrato/bundle corrupto,
  excepción no reconocida o error del procesamiento. Conserva último válido y falla.
- MAGYP_LAST_VALID identifica el fallback conservado; no implica actualización exitosa.

MCBA_RUN_STATUS.json (artifact de diagnóstico de cada intento) registra result,
source, source_url, requested_date, attempted_at, last_observation_date y
last_successful_update. MCBA_MAGYP_UPDATE_STATUS.json publicado sólo se versiona
con UPDATED. Los CSV SUMMARY ya contienen source_url, date_max y last_update;
el frontend existente conserva la fuente, observación y actualización del último
bundle exitoso. No se reemplaza last_update por la hora de un fallo.

El precheck sólo bloquea HTTP 401/403/404 explícito; una respuesta inconclusa o 5xx
permite la adquisición Edge. Máximo tres sesiones completas y 10 segundos entre
intentos transitorios, sin ampliar los límites existentes. Un HTTP 200 no acredita
publicación. Los RAW permanecen en artifacts separados, no en Git ni Pages.

La validación de esta entrega es offline, con export sintético que atraviesa
fetch/parse/normalize/analytical/dashboard. La disponibilidad futura del servidor
no se garantiza. Las pruebas reales anteriores fallaron sin alterar los CSV.
