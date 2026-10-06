# MCBA MAGyP en Precios Mayoristas

Integración local en `codex/magyp-data-platform-mcba`, sobre 5fb5987. No publica Pages, no modifica las bases legacy y no migra Corrientes ni Commodities.

## Fuentes y frecuencia

La consulta oficial diaria es https://ssma.magyp.gob.ar/frutas.precios.aspx. El adaptador existente reproduce filtros y exportación XLSX con Playwright/Chromium efímero. No existe aquí una API HTTP autónoma validada. Las observaciones comerciales `detail` alimentan la vista diaria; `species_summary` (Prom.Esp.) permanece separada y nunca entra en sus medias, rankings o filtros comerciales.

La publicación mensual oficial **no está operativa**. El GET controlado a https://ssma.magyp.gob.ar/frutas.msdmensual.aspx agotó el timeout; el portal https://www.magyp.gob.ar/mercadosagropecuarios/ respondió HTML, sin contrato de exportación mensual confirmado. Las búsquedas dirigidas a dominios oficiales no aportaron un contrato verificable. Esto no prueba que la fuente mensual no exista.

Mensual y anual continúan usando legacy, con identificación visible. En 2024/2025 existen observaciones mensuales legacy; donde legacy tiene registros diarios, se conserva su agregación visual mensual existente. Esa agregación no se presenta como mensual oficial MAGyP. `MCBA_MAGYP_MONTHLY.csv` es un diagnóstico de mediana de días observados, con cobertura parcial; **el frontend no lo carga**. No se creó `MCBA_MAGYP_MONTHLY_OFFICIAL.csv` ni se inventaron dimensiones.

## Arquitectura y contratos

`RAW → NORMALIZED → ANALYTICAL → DASHBOARD → adaptador → Precios Mayoristas`.

RAW inmutable y JSONL canónicos siguen fuera de Git. Cada captura tiene manifest, SHA-256, fecha solicitada, fecha UTC, método, endpoint y parser. Nunca se guardan cookies, perfiles, tokens ni formularios GeneXus.

El CSV diario preserva dimensiones raw/normalized, rubro, producto, variedad, origen, envase, calidad, tamaño, grado, fecha, precio, moneda, unidad, observation_level, kg_raw, observation_id, capture_id, raw_sha256 y timestamp. `volume` permanece vacío/null; no hay ponderación por Kg. El precio publicado es ARS por kg. Para manifests legados, `price_unit_raw=ARS/kg` se representa como `currency=ARS, price_unit=kg`, sin conversión numérica; la evidencia contextual/documentada original se conserva.

Sólo aliases `validated` se aplican en Python. `observed` y `manual_review` permanecen diagnósticos. El frontend utiliza las etiquetas normalizadas ya publicadas y únicamente cambia mayúsculas/minúsculas para presentación, sin aplicar equivalencias semánticas ni reparar ¥.

## Selección de datos

1. Diaria MCBA: MAGyP validado para las fechas efectivamente capturadas.
2. Actualización fallida: mismo bundle previo y estado visible `MAGYP_LAST_VALID`.
3. Fuera de las fechas cubiertas: legacy diario identificado. Nunca se rellenan productos, variedades u orígenes ausentes en una fecha MAGyP.
4. Mensual/anual MCBA: legacy hasta disponer de mensual oficial reproducible.
5. Corrientes: registros y lógica legacy existentes.

La cobertura se decide antes de filtros de producto/origen. Si el navegador no puede validar el bundle, intenta su copia local validada en IndexedDB. Si tampoco hay copia, no se presume que MAGyP carezca de cobertura: la vista diaria MCBA queda sin datos y con explicación; mensual legacy continúa disponible. La caché sólo almacena CSV de frontend y marcador público, nunca RAW ni sesiones.

El frontend verifica SHA-256 de DAILY/SUMMARY contra `_SUCCESS.json`, contrato, fechas, moneda/unidad, IDs únicos y conteos. La caché también se revalida. `MCBA_MAGYP_UPDATE_STATUS.json` informa el resultado de actualización; no reemplaza la validación del contenido.

## Publicación incremental

`update_mcba_dashboard.py` hace una captura de un día, normaliza, genera analytical y staging, valida el bundle anterior y fusiona por **día completo**. Una revisión reemplaza las observaciones de esa fecha, sin conservar productos retirados ni borrar otras fechas. Rechaza schema diferente, revisiones fuera de orden, capturas mezcladas, filas inválidas, duplicados y respuestas vacías.

Se validan todas las filas antes de publicar. Se usa staging, bloqueo, reemplazo atómico por archivo, rollback ante excepciones y marcador final. No se promete atomicidad multiarchivo ante corte de proceso: el lector detecta generaciones incompletas por hashes y conserva su caché validada. `.gitattributes` fuerza LF en los archivos con hashes para mantener identidad en Windows/Linux/Pages.

No se puede certificar completitud económica con una XLSX de schema válido si el servicio omitiera filas: falta un conteo/ID oficial de publicación verificable. Se validan integridad del archivo, rango, schema, precio y trazabilidad; no se inventa un calendario de publicaciones.

## Ejecución

Requiere Python 3.12 y las dependencias fijadas:

```powershell
python -m pip install -r scripts/magyp/requirements-browser.txt
python -m playwright install chromium
python scripts/magyp/mcba/update_mcba_dashboard.py --date 2026-10-06 --data-root C:/ruta/externa/mcba-captura-unica --dry-run
python scripts/magyp/mcba/update_mcba_dashboard.py --date 2026-10-06 --data-root C:/ruta/externa/mcba-captura-unica --allow-web
python -m unittest discover -s tests/magyp_common -v
python -m unittest discover -s tests/magyp_mcba -v
node --test tests/magyp_frontend/*.test.cjs
python -m http.server 8000
```

Usar una carpeta RAW aislada y vacía por ejecución. Conservar/archivar esa carpeta fuera de Git antes de borrar temporales. No ejecutar un rebuild local parcial sobre el directorio publicado; usar el actualizador incremental para conservar su historia. Los scripts anteriores siguen disponibles para reconstrucción canónica **completa** a partir de todos los RAW.

## Frontend y funcionalidad

`mcba-prices.js` contiene validación, adaptación, respaldo y prioridad. `app.js` conserva gráficos/KPIs/rankings y agrega la selección de datos por frecuencia. Los filtros dependientes se alimentan según fuente, año y mercado; se conserva el año al cambiar frecuencia. Envase/calidad/tamaño/grado están en un bloque expandible. Calidad MCBA es distinta del antiguo indicador de calidad de la serie.

El semáforo siempre consulta el conjunto mensual legacy para MCBA, incluso cuando la evolución es diaria. Las bases y funciones de Cantidades, Commodities y Corrientes no se migraron. El duplicado RF del 19/08/2026 legacy continúa documentado y no se corrige en la base. No se arrastra a las fechas sustituidas por MAGyP.

Cuando la selección diaria incluye fechas MAGyP y fechas legacy sin cobertura, evolución y rankings separan y rotulan ambas fuentes. Los KPIs siguen resumiendo las observaciones seleccionadas; no se afirma equivalencia metodológica entre ambas fuentes.

## GitHub Actions

`.github/workflows/update-magyp-mcba.yml` es manual (`workflow_dispatch`) y prepara un candidato revisable: checkout, Python/Node, Playwright/Chromium, tests, una captura sin retry/backfill, normalización, analytical, merge incremental y validación final.

Sube sólo CSV/marcador/status como candidato Pages. RAW XLSX/manifest van a un artefacto separado de auditoría con retención de 90 días, nunca al repositorio ni al frontend. Los artefactos temporales no son un archivo duradero: definir almacenamiento externo y recuperación antes de automatizar publicación. No hay cron, commit ni deploy. El workflow no se ejecutó en GitHub durante esta tarea; falta validación manual del runner Linux.

Se utiliza la configuración documentada de [setup-node](https://github.com/actions/setup-node) y [upload-artifact](https://github.com/actions/upload-artifact); la publicación al repositorio permanece pendiente de revisión.

## Pendientes

- Validar manualmente GitHub Actions, conectividad del servicio y almacenamiento RAW permanente.
- Investigar exportación mensual oficial y metodología antes de sustituir legacy.
- No asumir historia diaria continua entre los extremos de fecha del piloto.
- Validar adicionalmente equivalencias económicas, calendario, semántica de Kg y anomalías de etiquetas. Esos límites no impiden la integración aditiva diaria autorizada.
