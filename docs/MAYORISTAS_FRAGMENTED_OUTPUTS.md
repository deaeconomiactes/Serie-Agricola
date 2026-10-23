# Mayoristas: auditoría de carga y cutover A08

Revisión local del 23/10/2026. Baseline: main `5e6777d`. No cambian datos, metodología ni prioridades. La única selección inicial que cambia es Año: último disponible (2026) en lugar de todos; Todos los años sigue disponible.

## Carga anterior exacta

| Archivo | Bytes | Filas | Propósito | Inicial | Fragmentable | Diferible |
|---|---:|---:|---|---|---|---|
| `PRECIOS_MAYORISTAS_INTEGRADO.csv` | 30238719 | 117039 | history and Corrientes | Sí | Sí | Sí |
| `RESUMEN_SERIES_UTILIZABLES_PRECIOS_2026.csv` | 210407 | 1291 | series quality flags | Sí | No | Sí |
| `data/magyp/dashboard/mcba/MCBA_MAGYP_DAILY.csv` | 5337468 | 10380 | published daily detail and species summary | Sí | Sí | Sí |
| `data/magyp/dashboard/mcba/MCBA_MAGYP_SUMMARY.csv` | 443 | 1 | daily source coverage | Sí | No | Sí |
| `data/magyp/dashboard/mcba/_SUCCESS.json` | 530 | metadata | daily bundle integrity | Sí | No | Sí |
| `data/magyp/dashboard/mcba/MCBA_MAGYP_UPDATE_STATUS.json` | 117 | metadata | daily current status | Sí | No | Sí |
| `data/mercado_central/dashboard/mcba/MCBA_MC_MONTHLY_DERIVED.csv` | 5026742 | 3723 | monthly derived official daily observations | Sí | Sí | Sí |
| `data/mercado_central/dashboard/mcba/_SUCCESS.json` | 146 | metadata | monthly bundle integrity | Sí | No | Sí |
| `data/magyp/reports/PRICE_FRESHNESS_STATUS.json` | 17904 | metadata | shared freshness loaded at boot | Sí (boot compartido) | No | No |

La apertura de Mayoristas requería 8 requests propios y 40.814.572 bytes; la frescura global ya se obtenía al iniciar el dashboard. El CSV 2026 alternativo sólo se solicitaba si fallaba el integrado principal. La prueba anterior terminó en 24,172 s y ~516 MB de heap JS; incluía todos los años.

## Contrato y publicación

Índice: `data/mayoristas/dashboard/index.json`, schema `mayoristas-shards-v1`. Cada descriptor declara fuente, mercado, frecuencia de vista, año, filas, cobertura, schema, SHA-256, bytes comprimidos/expandidos, path, moneda, unidades originales, frecuencia de las observaciones, estado y campos. El índice contiene resúmenes/metadata; nunca observaciones completas.

Se usa JSON UTF-8 comprimido con gzip explícito (`.json.gz`), equivalente al transporte gzip de Carnes. JSON conserva números, null, campos opcionales y textos de los adaptadores sin reconstruir tipos desde CSV. El navegador verifica bytes y SHA-256 antes de descomprimir, limita expansión y valida schema, filas, cobertura y partición. No depende de Content-Encoding.

Particiones: mercado + frecuencia de vista + año + fuente. No se fragmenta por especie/rubro: dos requests para la apertura no justifican multiplicarlos. Son 19 descriptores, 19 archivos comprimidos y 7.634.570 bytes en total; hay contenido idéntico reutilizable por hash entre algunas vistas de Corrientes. Mayor fragmento: 1755898 bytes. Índice: 21118 bytes.

| Vista | Filas de entrada de vista | Bytes gzip de todos los años |
|---|---:|---:|
| diaria | 114840 | 3322053 |
| mensual | 58962 | 1542762 |
| anual | 116983 | 2769755 |

No sumar filas entre vistas: son representaciones alternativas de los mismos inputs. `_runtime_order` restituye exactamente el orden previo antes de cálculos; se elimina al entregar las filas a la UI. No se convierte moneda/unidad; las ausentes se declaran Sin identificar. La frecuencia de vista mensual no transforma observaciones Corrientes diarias en una nueva publicación mensual oficial.

Build: `python scripts/mayoristas/build_dashboard.py` (Python estándar y Node 22). Reutiliza processPriceData, MCBAPrices y MCBAMonthly mediante puente build-only; valida hashes de las publicaciones upstream. Gzip determinístico (sin fecha/nombre), archivos por contenido; el validador Node usa el mismo loader del navegador contra el candidato completo antes de reemplazar atómicamente el índice. Un build fallido deja vigente el índice previo.

Deploy Pages genera/valida fragmentos desde los últimos outputs ya publicados antes de armar el sitio. No se modifican adquisición, normalización ni workflows de actualización de fuentes. prepare_pages excluye integrado principal/alternativo, control de calidad original, publicaciones MCBA completas y archivos Mercado Central del paquete servido. Conserva inputs en el checkout para build/auditoría y otros procesos. Los fragmentos obsoletos se excluyen del paquete según el índice activo. No hay commit automático de estos nuevos fragmentos; se regeneran al desplegar.

## Lazy loading, caché y errores

Apertura: índice + dos fragmentos mensuales de 2026. Se mantienen metadata/frescura existentes. Cambiar año, mercado o frecuencia sólo pide los fragmentos necesarios. Todos los años pide todos los años de esa frecuencia/mercados, explícitamente. Caché en sesión por SHA-256; promesas compartidas; máximo tres solicitudes concurrentes. Una respuesta tardía no sustituye una selección posterior.

Un error de red/HTTP conserva los datos y gráficos de la última vista válida. Un fallo de hash, schema, gzip o JSON muestra PIPELINE/UI DATA ERROR y conserva la vista y controles previos. No busca otra fuente ni descarga el integrado como sustituto. Sin copia en la sesión, informa error de carga; no inventa una vista. El caché no persiste entre recargas y las pestañas abiertas no garantizan disponibilidad indefinida de shards retirados en futuros deploys.

## Equivalencia y prioridades

ECONOMIC_EQUIVALENCE.json contiene 11 controles: MCBA diario 2026; MCBA mensual 2024/2025/2026; Corrientes diario y mensual 2025/2026; MCBA anual 2024/2025/2026. Comparación exacta de filas/orden/campos y hashes de conteos, promedio, mínimo, máximo, especies/variedades, último período, evolución, rankings, variaciones, semáforo y filas de tabla. Sin tolerancia numérica ni cambios económicos.

Diario MCBA conserva MAGyP según cobertura por fecha y el histórico donde la regla vigente lo permite. Mensual aplica Mercado Central por mes/rubro antes de filtrar productos, con histórico sólo en huecos. Anual conserva exactamente la metodología previa. Corrientes conserva fuente estática. No se amplía cobertura ni se reemplaza una metodología; no se cambian datos ni reglas económicas de Commodities/SIO/Carnes/Cantidades. La corrección de lectura CSV SIO solicitada durante el cierre se documenta abajo.

## Medición local

| Medida | Antes | Después Edge | Después Chrome |
|---|---:|---:|---:|
| Requests propios de apertura | 8 | 3 | 3 |
| Bytes de apertura | 40.814.572 | 849.526 | 849.526 |
| Mayor payload inicial | 30.238.719 | 529.057 | 529.057 |
| Tiempo orientativo | 24,172 s | 2,969 s | 1,734 s |
| Heap JS aproximado | 516,2 MB | 83,2 MB | 54,0 MB |

Reducción de bytes: 97,919%. Medidas locales individuales, no benchmark controlado ni SLA. Apertura nueva selecciona 2026; la anterior descargaba todos los años incluso para elegir 2026. Los controles económicos comparan la misma selección. Heap incluye Cantidades/librerías previamente cargadas y depende del GC.

Cambiar a 2024 mensual (ambos mercados): 100.540 bytes nuevos. A 2025: 613.814 bytes. Volver a 2026: 0 bytes. Cambiar MCBA 2026 mensual→diaria: 1.848.776 bytes. No se descargan RAW/NORMALIZED/ANALYTICAL. Evidencia detallada en PERFORMANCE.json.

## Verificación y cierre posterior a sincronizar main

Aprobados: 6 tests frontend de delivery/equivalencia, 6 Python de build/publicación, 105 MCBA, 20 Mercado Central, 74 comunes y 6 CI/publicación. Edge y Chrome: 1440/1000/900/640 px, gráficos, cambios de año/frecuencia, cache, error corrupto, restauración de vista y selección rápida. Sin errores JavaScript/desbordamiento. Actionlint y git diff --check sin errores.

La primera validación obtuvo 97/98; la revisión de cierre solicitada por el usuario sincronizó/rebaseó contra main 5e6777d, que ya incluye el merge del PR #43. No hubo conflictos ni cambios adicionales en Mayoristas. La falla SIO persistía: los CSV v2 versionados son válidos (605 eventos; diario 542 filas, mensual 527, últimos 509, semáforo 527), pero 13 registros contienen saltos de línea entre comillas en fecha_entrega/condicion_serie. El lector frontend separaba líneas físicas, cortaba esos registros y dejaba event_ids vacío. Se corrigió únicamente la delimitación de registros CSV, preservando LF/CRLF dentro de celdas, comillas escapadas y texto original. El test existente se conserva sin cambios; se añade una regresión sintética para ese caso y rechazo de comillas incompletas. No se modifican outputs SIO, contratos, IDs, agregados, semántica ni fuentes.

Límites: DecompressionStream/crypto.subtle requieren navegador moderno y contexto seguro (HTTPS/localhost). Tope por fragmento 12 MB comprimidos/120 MB expandidos; si se supera, el build exige subdividir antes de publicar. Datos manuales históricos/Corrientes siguen siendo necesarios; esta etapa optimiza transporte, no actualidad ni semántica.

Cierre previo al commit: frontend completo **99/99**; 11 controles económicos exactos y reporte idéntico al aprobado (hash de contenido JSON en VERIFICATION.json). Se repitieron los 6 tests delivery/equivalencia, build con validación del candidato, 6 Python Mayoristas, 105 MCBA, 20 Mercado Central, 74 comunes, 6 CI/publicación y 13 SIO; todos aprobados. Actionlint y git diff --check aprobados. Sin regeneración ni modificación de outputs SIO; sólo derivados Mayoristas del checkout actualizado.
