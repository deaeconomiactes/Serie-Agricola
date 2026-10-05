# MAGyP: infraestructura reproducible y piloto FOB v1

Implementación local del 05/10/2026. **Sólo FOB tiene adquisición implementada.** No se conecta este CSV a `app.js` ni se modifica el dashboard productivo. El workflow es manual y entrega un artefacto para revisión: no tiene cron, permisos de escritura, commits, push ni deploy.

Referencia de arquitectura: [informe de exploración](../data/magyp_exploracion/reports/REPORTE_ARQUITECTURA_FUENTES_MAGYP.md).

## Capas y ubicación

```text
data/
  raw/magyp/
    fob/<timestamp_UTC_UUID>/response.json + manifest.json
    sio/.gitkeep
    mcba/.gitkeep
    referencias/.gitkeep
  normalized/magyp/
    fob/<sha256_dataset>.csv + latest.json + pipeline_state.json
    sio/.gitkeep
    mcba/.gitkeep
  analytical/commodities/fob.csv
  dashboard/commodities/fob.csv
```

RAW, NORMALIZED y ANALYTICAL son locales y están excluidos de Git, salvo `.gitkeep`. Sólo `data/dashboard/commodities/fob.csv` es candidato a versionado entre las salidas. Se puede trasladar RAW a almacenamiento durable externo con `MAGYP_RAW_ROOT` o `--raw-root`: esa raíz contiene `fob/`, `sio/`, etc. La opción `--data-root` cambia la raíz de todas las capas para entornos aislados. Los tres comandos deben compartir esas rutas.

El repositorio prepara la estructura; **no implementa todavía un backend de objetos ni su sincronización**. Las capturas locales deben respaldarse. El workflow utiliza `runner.temp`: es almacenamiento efímero, adecuado para verificar una fecha, no para acumular historia productiva. Antes de habilitar publicación automatizada se debe implementar almacenamiento durable, recuperar capturas anteriores y comprobar cobertura. El builder bloquea una salida que pierda días ya presentes en el CSV previo por falta de RAW.

## Fuente y contrato FOB

Proveedor/publicador: MAGyP. Documentación: [API de precios FOB oficiales](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/fob_oficiales/_archivos/000021_Precios%20Fob%20Api.php).

```text
GET https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/ws/ssma/precios_fob.php?Fecha=DD/MM/YYYY
```

Una fecha por request; acceso público sin credenciales. Timeout 25 s, máximo 1,5 MB, sin reintentos, rangos, backfill ni redirecciones automáticas. No depende de `requests`, pandas u otras librerías: Python 3.12 y biblioteca estándar.

El cuerpo esperado es JSON con `posts[]`, incluso si el Content-Type es `text/html`. Schema estricto v1: `fecha`, `circular`, `posicion`, `precio`, `mesDesde`, `añoDesde`, `mesHasta`, `añoHasta`. Campos nuevos o ausentes requieren revisar el parser, no se absorben silenciosamente. Versión: `fob-1.0.0`.

Grano: **fuente × fecha de observación × posición textual × intervalo de embarque × circular × captura**. No se agregan registros por producto. No hay diccionario validado: **no se asignan producto, NCM, moneda, unidad, plaza ni volumen**. Ceros de precio parseables se conservan; no se interpreta su significado económico. Los datos son referencia oficial, no transacciones individuales.

## RAW y manifest

Cada intento crea un directorio exclusivo con timestamp UTC y UUID. Una captura válida conserva exactamente los bytes JSON recibidos y su manifest. Se escriben en directorio temporal y se hace visible el directorio definitivo al terminar. No se reemplaza una captura anterior, aunque sea el mismo día, el mismo hash o una revisión. Una interrupción deja como máximo un directorio temporal que no participa en normalización; revisar y retirar manualmente sólo después de comprobar que no hay proceso activo.

El manifest implementado contiene:

```json
{
  "source": "magyp_fob",
  "requested_date": "2026-10-02",
  "captured_at_utc": "2026-10-05T12:26:22.736542Z",
  "capture_id": "<timestamp_UTC_UUID>",
  "url": "<endpoint con Fecha pública>",
  "origin_url": "<documentación oficial>",
  "method": "GET",
  "public_parameters": {"Fecha": "02/10/2026"},
  "status": 200,
  "content_type": "text/html; charset=UTF-8",
  "encoding": "utf-8-sig",
  "size_bytes": 23066,
  "sha256": "<hash de los bytes recibidos>",
  "parser_version": "fob-1.0.0",
  "schema_version": "v1",
  "response_file": "response.json",
  "validation": {"valid": true, "classification": "valid", "record_count": 142, "errors": []},
  "calendar": {"source_url": "", "sha256": "", "non_publication_dates": {}}
}
```

El ejemplo resume el contrato con tamaño y Content-Type de la captura local. `size_bytes` es el tamaño efectivamente leído. Si se excede el límite, se rechaza el intento y el tamaño corresponde a la lectura acotada. Ante error HTTP no se lee la página de error: el hash corresponde a los bytes disponibles, que pueden ser vacíos.

**Seguridad:** no se persisten cookies, headers de sesión, tokens, credenciales, viewstate/eventvalidation ni HTML de error. Si el cuerpo/schema es inválido, se guarda sólo un manifest de intento rechazado (`response_file: null`), hash, metadata y códigos fijos de error; no se retiene ese cuerpo. Tampoco se imprimen cuerpos ni tracebacks con valores remotos. Para éxito/ausencia explicada se guarda únicamente JSON que cumple el contrato. No hay autenticación implementada.

## NORMALIZED

Campos:

```text
source, observation_date, capture_timestamp, capture_id,
observation_id, record_id, row_number,
circular, position_raw, price_raw, observation_date_raw,
shipment_month_from, shipment_year_from, shipment_month_to, shipment_year_to,
raw_sha256, raw_manifest, source_url, schema_version
```

Conserva **todas las versiones válidas**, sin deduplicar capturas distintas ni eliminar la revisión anterior. `position_raw` mantiene exactamente la cadena recibida, incluidos ceros iniciales; `price_raw` conserva su representación textual parseada, sin redondeos binarios. Los bytes originales permiten recuperar el léxico JSON exacto. `observation_date_raw` conserva la fecha original; `row_number` registra orden dentro de la captura. `raw_manifest` es una ruta relativa al directorio RAW FOB, sin exponer un path local en el CSV dashboard.

IDs SHA-256 reproducibles:

- `observation_id`: serialización canónica de fuente, fecha, posición, ventana numérica y circular textual. Identifica el grano candidato entre capturas; **no es un ID económico publicado por MAGyP**.
- `record_id`: serialización canónica de observation_id, capture_id y raw_sha256. Identifica su versión. Reprocesar la misma captura conserva el ID; una nueva captura tiene otro ID aunque repita los bytes.

El CSV normalizado se nombra por hash de su contenido. `latest.json` registra archivo, hash, conteo, lista de capturas y versiones de parser/schema. Se valida integridad RAW y conteo antes de escribir el pointer. No se reutiliza un parser anterior automáticamente tras cambiar versión.

## ANALYTICAL y DASHBOARD

ANALYTICAL mantiene el grano original y selecciona **la captura válida más reciente de cada día**, ordenada por timestamp UTC y capture_id como desempate. Una revisión sustituye el conjunto completo del día en la vista actual, incluyendo el retiro de posiciones; las versiones anteriores permanecen en RAW/NORMALIZED. No se mezclan precios de capturas distintas de un mismo día ni se calcula un “FOB único”.

```text
date, position, shipment_window, circular, price, source,
observation_id, record_id, capture_id, capture_timestamp,
raw_sha256, source_url, schema_version
```

`shipment_window` es `YYYY-MM/YYYY-MM`; `price` se parsea con Decimal y se serializa sin redondeo ni conversiones de moneda/unidad. No se agregan dimensiones económicas no confirmadas.

DASHBOARD genera `data/dashboard/commodities/fob.csv`, con el mismo grano y columnas anteriores, sustituyendo `capture_timestamp` por `updated_at_utc`. Los IDs/hash permiten rastrear cada fila al manifest; `source_url` mantiene el enlace de consulta. Son 13 columnas, sin payload RAW ni metadata de sesión. **Es un archivo para revisión y futura conexión: el frontend actual no lo carga.**

## Validaciones y calendario

Se rechazan HTTP distinto de 200, errores de red, redirecciones, exceso de tamaño, HTML inesperado, JSON inválido o miembros repetidos, ausencia/tipo incorrecto de `posts`, cambios de schema, fecha inválida o distinta de la solicitada, precio no decimal/negativo/no finito, posición vacía/no textual, circular inválida, ventana de embarque fuera de rango o invertida, duplicados exactos y claves candidatas conflictivas dentro de una captura. **No se elimina silenciosamente el duplicado:** se rechaza la captura completa.

Las ventanas v1 requieren meses 1–12 y años 1–9999, inicio no posterior al fin. Una codificación futura distinta, como ventanas nulas o ceros con otro significado, exige revisar el contrato antes de aceptar datos.

Un `posts: []` con HTTP 200:

- Sábado/domingo: `no_publication`, éxito sin cambiar salidas.
- Día incluido en calendario explícito: `no_publication`, éxito sin cambiar salidas.
- Otro día hábil: `unexpected_empty`, fallo que bloquea publicación.

No se incorporó una lista de feriados inferida. Para usar un calendario que el operador haya verificado contra una fuente oficial:

```json
{
  "source_url": "https://FUENTE_OFICIAL_DEL_CALENDARIO",
  "non_publication_dates": {"YYYY-MM-DD": "Motivo oficial verificado"}
}
```

Pasar `--calendar RUTA.json` al fetch; su referencia, fechas y SHA-256 se guardan en el manifest. El script valida estructura, pero **no valida automáticamente que la referencia sea oficial ni que MAGyP no publique en ese feriado**: es responsabilidad del operador. No se usa un calendario de ejemplo como calendario real. Si un fin de semana contiene datos válidos, se procesan normalmente. Un HTTP 500 en fin de semana sigue siendo error de servicio.

## Control de publicación y fallbacks

```text
fetch → validar RAW → normalizar → analytical en memoria
      → dashboard en memoria → validar ambas salidas
      → archivo temporal + flush/fsync → os.replace
```

La última escritura de datos es el replace atómico de `fob.csv` dentro del mismo filesystem. Antes del replace se verifica también que los bytes leídos del temporal coincidan con los bytes validados. Si hay fallo antes del replace, el dashboard previo queda byte a byte intacto. ANALYTICAL se reemplaza antes que DASHBOARD: son dos archivos y **no constituyen una transacción multiartefacto**; una falla de disco en el segundo replace puede dejar ANALYTICAL más reciente, mientras DASHBOARD conserva su versión válida. Ambos son reconstruibles desde RAW.

`pipeline_state.json` invalida el permiso de publicar **antes** de pedir datos. Un fallo/incompletitud de fetch bloquea normalize/build aunque exista un normalizado viejo. Fallos de normalización o build también bloquean build. `latest.json`, su hash y la lista actual de capturas deben coincidir. Se verifica que la nueva salida conserve los días del dashboard anterior. Una revisión legítima puede retirar posiciones de un día; no puede borrar otros días porque falte RAW.

Recovery: corregir el problema y ejecutar una nueva captura válida, normalize y build; si el fallo fue exclusivamente de build, se puede revalidar con normalize y volver a build. No editar `pipeline_state.json` para forzar una publicación. El lock exclusivo protege las escrituras concurrentes sobre la misma raíz. Una interrupción puede dejar `.pipeline.lock`: verificar que no exista un proceso activo y retirar el lock manualmente. Usar un único escritor por almacenamiento; el diseño no sustituye un lock distribuido.

No se rellenan faltantes FOB con otra fuente. Logs: `[FETCH]`, `[VALIDATE]`, `[NORMALIZE]`, `[PUBLISH]`; cada CLI falla con código 1 cuando corresponde. Un vacío explicado tiene código 0 y no publica filas vacías.

## Ejecución

Desde la raíz del repositorio:

```powershell
python scripts/magyp/fetch_fob.py --date 2026-10-02 --dry-run
python scripts/magyp/fetch_fob.py --date 2026-10-02
python scripts/magyp/normalize_fob.py
python scripts/magyp/build_commodities.py
python -m unittest discover -s tests/magyp -v
```

Cada comando admite `--dry-run` sin red ni escrituras. Normalize/build no descargan datos. Fetch siempre crea una nueva captura: la idempotencia consiste en no duplicar observaciones en la vista actual, no sobrescribir RAW y obtener bytes idénticos al repetir normalize/build sobre las mismas capturas. Una nueva captura cambia actualización/record_id aun si repite precios.

Para RAW externo (usar en los tres comandos):

```powershell
$env:MAGYP_RAW_ROOT = 'D:/datos_magyp/raw/magyp'
python scripts/magyp/fetch_fob.py --date 2026-10-02
python scripts/magyp/normalize_fob.py
python scripts/magyp/build_commodities.py
```

No cambiar de RAW root sin recuperar las capturas históricas requeridas. Para pruebas aisladas usar `--data-root RUTA_TEMPORAL --raw-root RUTA_RAW_TEMPORAL` en los tres scripts.

## Prueba local y tests

Una consulta real acotada: **02/10/2026 → HTTP 200 → 142 registros**, captura UTC `2026-10-05T12:26:22.736542Z`. Hash RAW:

```text
50d94bd38b9b124f9f2c41e36f915f36c76057b037ad379bfcb4e067e45886d0
```

NORMALIZED: 142 filas en esta ejecución; ANALYTICAL/DASHBOARD: 142 filas. CSV dashboard: 64.076 bytes. Ninguna consulta masiva o histórica adicional fue necesaria.

**26 tests** con JSON/HTML sintéticos, sin internet: JSON válido, Content-Type HTML con JSON válido, posts ausente/vacío, ausencia explicada por fin de semana/calendario, precio/fecha inválidos, schema cambiado, miembros JSON repetidos, duplicados exactos/identidad conflictiva, error HTTP/HTML, inmutabilidad y revisiones, conservación de IDs, idempotencia, hash corrupto, bloqueo de salida vieja, fallo de validación/replace, vacío sin borrar salida, no retener cuerpos con posibles secretos, lock y pérdida de historia en runner nuevo. Los tests escriben sólo en directorios temporales.

## Workflow preparado

`.github/workflows/update-magyp-fob.yml`: `workflow_dispatch` con fecha obligatoria, checkout, Python 3.12, fetch/validación, normalize, build, tests y upload sólo del CSV liviano. Sin cron ni autorización para publicar. Los inputs se transmiten por variable de entorno y argumento entre comillas; la fecha se valida antes de usarla.

No se ejecutó este workflow ni se hizo commit, push o deploy en esta etapa. Su siguiente fase requiere almacenamiento durable y controles de cobertura, además de revisión del usuario; no habilitar commits automáticos en un runner sin historial RAW.

## Contratos y fuentes pendientes

`scripts/magyp/contracts.py` define `SourceFetcher`, `RawManifest`, `Normalizer`, `ValidationResult`, `PublishResult`. Los Protocols permiten implementaciones futuras sin herencia obligatoria; FOB aplica esos contratos mediante los métodos fetch/normalize y resultados tipados. No hay fetchers SIO ni MCBA implementados.

**SIO, próximo paso:** piloto separado para reproducir exportación pública por fecha de declaración y reconciliarla con grilla 72 h. Validar paginación bajo cambios, ID vs número de contrato, incrementalidad, eventos tardíos, rectificaciones, anulaciones, última instancia y destino final. Diseñar event log antes de obtener contratos vigentes o volúmenes netos. Mantener snapshot existente como fallback.

**MCBA, próximo paso:** prototipo acotado de exportación autónoma GeneXus de un día; verificar campos/códigos perdidos frente a Excel, `Prom.Esp.` separado del detalle, significado de Kg, cobertura y equivalencia mensual. No sustituir adquisición manual ni reconstruir promedios sin metodología confirmada.

Corrientes mantiene su fuente. Precios internos, pizarra/FAS, futuros y SIO Carnes no se adquieren ni se integran. Tampoco se alteran series históricas, Excel, pipeline SIO, workflows anteriores o dashboard productivo. Para FOB quedan pendientes diccionario oficial de posición/producto, moneda/unidad, reglas de revisiones y permisos de redistribución; no se infieren de sus nombres o valores.
