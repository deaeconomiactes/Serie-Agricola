# Actualización y frescura de precios

El reporte canónico liviano es `data/magyp/reports/PRICE_FRESHNESS_STATUS.json`.
Se genera con `python scripts/magyp/build_price_freshness.py`. No consulta fuentes.
Contiene una entrada por familia y conserva fechas de observación y actualización
exitosa por separado. Se lee desde el dashboard; no se mezclan precios, monedas,
unidades ni frecuencias entre fuentes.

Estados: UPDATED, NO_OP_ALREADY_CURRENT, NO_PUBLICATION, SOURCE_UNAVAILABLE,
MAGYP_LAST_VALID/LAST_VALID, PIPELINE_ERROR, STATIC y NOT_REPORTED.
STATIC sólo corresponde a fuentes manuales; NOT_REPORTED significa que falta
metadata explícita, sin inventar éxito o fallo por la edad de los datos.
Las fechas futuras legacy se excluyen del indicador, igual que en la interfaz,
sin editar las planillas originales. Una fecha mensual representa el mes publicado.
Las horas SIO sin zona se conservan como hora de origen; no se convierten a UTC.

## Flujos preparados

- MCBA: Edge self-hosted Windows, día civil argentino, 12/16/20 h Argentina,
  hasta tres intentos existentes. No se alteró adquisición, parser ni reglas de
  publicación incremental. Cada resultado MCBA_RUN_STATUS alimenta el reporte.
  Metadata puede publicarse aunque no haya precios nuevos; los CSV se preservan.
  UPDATED sólo llega al despliegue después de validar/publicar los datos.
- Referencias MAGyP: lunes a viernes 20 h Argentina. Cinco familias independientes.
  Cada intento guarda un sidecar operacional ignorado por Git, consolidado después
  en el reporte. HTTP no disponible se distingue de schema inválido. FOB vacío
  reconocido es NO_PUBLICATION y conserva el último bundle. Un schema desconocido
  sigue fallando. Una familia fallida no impide publicar otras salidas válidas.
  Allowlist ampliado sólo por el JSON liviano; RAW queda fuera de Git.
- SIO: snapshot transaccional diario 10:30 h Argentina. No cambia GetOperaciones,
  deduplicación ni semántica de eventos. Se agrega reporte tras la generación válida
  y deploy explícito con workflow_dispatch; no depende del push de GITHUB_TOKEN.
  Si falla la captura de red, se conservan CSV y se publica SOURCE_UNAVAILABLE.
  JSON inválido u otro fallo no reconocido se informa PIPELINE_ERROR.
- Corrientes y mensual MCBA: STATIC, actualización manual, sin nuevas APIs.
  No se deriva mensual MCBA desde diario. Histórico local mensual de granos separado.

## Evidencia de esta entrega (20/10/2026)

Se consultaron una vez las cinco fuentes MAGyP (más el diccionario FAS) y una vez
el snapshot SIO. Se normalizaron y validaron las salidas antes de actualizar los CSV
locales. FOB devolvió HTTP 200 sin publicación para 20/10; conserva 19/10.
SIO incorporó operaciones del 20/10. No se descargaron históricos masivos.

MCBA: se leyó la corrida productiva real 39354603566, no los logs de tests sintéticos:
fecha solicitada 2026-10-20, Edge msedge, filtered_grid TIMEOUT, SOURCE_UNAVAILABLE.
Conserva observación 05/10 y captura válida 06/10. No se lanzó otra adquisición
Edge ni se modificó su configuración. No se puede prometer disponibilidad del sitio.

Los nuevos workflows no se ejecutaron remotamente porque esta entrega no hace
commit/push/deploy. Su validación aquí es offline y actionlint; las adquisiciones
MAGyP referencias y SIO sí fueron reales. El estado publicado sólo avanzará a
producción después de que el usuario integre y despliegue estos cambios.
