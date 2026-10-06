# MCBA fase 3 — readiness productivo

Evaluación: 2026-10-06. Rama **codex/magyp-data-platform-mcba**, commit base **5fb5987**.
Estado inicial limpio, verificado antes de editar. Arquitectura congelada:
MAGyP → RAW → NORMALIZED → ANALYTICAL → DASHBOARD PILOTO.

**Clasificación final: COMPLEMENT_ONLY. Recomendación: piloto adicional; no migrar aún.**
Chromium funciona en un entorno Python aislado y se logró cubrir octubre de 2025
mediante cinco exportaciones válidas. Sin embargo, tres ventanas necesitaron un
reintento manual y las pruebas aisladas fallaron. Cloud/CI aún no fue ejecutado y
la equivalencia con K_mes no está resuelta. Kg y los aliases marginales pendientes
no son el motivo de esta clasificación.

## Adquisición, entorno y fallos

Método **BROWSER_AUTOMATION_REQUIRED**: Playwright 1.58.0 + Chromium compatible,
headless, contextos sin perfil persistente, sesión en memoria, controles GeneXus
públicos y export XLSX. Sin replay HTTP, bypass, cambios de dominio ni downgrade.
Se conserva la misma allowlist HTTPS, validación de XLSX, límite 2 MB y presupuesto
80 requests por sesión. Timeout 40 s por operación; no es un límite global de sesión.

Python **3.12.10**, venv nuevo sin system-site-packages; openpyxl 3.1.5, Chromium
**145.0.7632.6 / build 1208**, dependencias directas/transitivas fijadas. Instalación
con `requirements-browser.txt` y `python -m playwright install chromium`. Fuente de
instalación CI: [documentación oficial Playwright](https://playwright.dev/python/docs/ci).
Entorno limpio aquí significa Python aislado + Chromium descargado en **Windows**;
no una VM Linux limpia ni una ejecución real de GitHub Actions.

Dos fechas aisladas 2025, cada una en nueva sesión:

| Fecha / intento | Resultado | Etapa | Duración s | Requests | Filas / XLSX válido |
|---|---|---|---:|---:|---|
| 02/10 inicial | fallo, timeout | initial_get | 42,531 | 30 | 0 / no |
| 15/10 inicial | fallo, timeout | initial_get | 41,484 | 58 | 0 / no |
| 02/10 único retry explícito | fallo, PipelineError | initial_get | 59,235 | 30 | 0 / no |

El smoke conocido 24/08/2026 también falló: initial_get, timeout, 42,328 s, 51 requests.
La prueba del retry 02/10 cambió temporalmente la espera a DOMContentLoaded; no
resolvió la recarga inicial pendiente y se restituyó la espera `load` existente.
No se atribuye causalidad al año consultado: estos fallos fueron anteriores al filtro.

Luego cinco ventanas de octubre terminaron correctamente con Chromium: demuestra
disponibilidad de datos 2025 y compatibilidad local real; **no elimina la evidencia
de inestabilidad de las sesiones aisladas**. Diagnósticos persistidos completos en
`MCBA_PHASE3_ATTEMPT_*.json`; tabla aislada en `MCBA_2025_ACQUISITION_VALIDATION.csv`.

## Mes completo solicitado

Octubre de 2025 se eligió por tener histórico mensual actual K_mes y una fecha MAGyP
previamente conocida. Ventanas no superpuestas de hasta siete días:

| Ventana | Inicial | Retry explícito | XLSX final, filas | Requests del éxito |
|---|---|---|---:|---:|
| 01–07/10 | fallo initial_get, 30 requests | éxito | 1.822 | 62 |
| 08–14/10 | fallo date_controls, 29 requests | éxito | 1.486 | 62 |
| 15–21/10 | fallo initial_get, 51 requests | éxito | 1.512 | 62 |
| 22–28/10 | éxito | no | 1.910 | 62 |
| 29–31/10 | éxito | no | 1.137 | 62 |

Cada ventana tuvo un intento inicial; las tres fallidas tuvieron un único retry
expresamente iniciado después de observar recuperación del sitio. Pausas de 10 s
entre ventanas; sin retries automáticos. El validador ahora impide repetir una
ventana sin `--explicit-retry` e impide el tercer intento. Las sesiones aisladas
anteriores y las ventanas mensuales son ensayos distintos, identificados por purpose.
No se repitieron otra vez las fechas aisladas ni se hizo backfill anual.

**12 sesiones totales de fase 3: 5 éxitos, 7 fallos, 589 requests oficiales registrados.**
310 requests corresponden a éxitos; 279 a fallos. Incluyen recursos de arranque UI,
no 589 descargas históricas. Instalación del navegador/paquetes y consulta de
documentación no se cuentan como requests al servicio MAGyP. No hubo tráfico extra
de captura fuera del ledger en esta fase. Los diagnósticos incluyen sólo endpoints
sanitizados, nombres públicos, conteos y hasta diez filas visibles de la grilla;
sin URLs temporales identificables, cookies/tokens/hidden state, HAR o perfiles.

| Métrica del mes | Resultado |
|---|---:|
| calendar_days / days_requested | 31 / 31 |
| days_with_data | 21 |
| days_without_data | 10 |
| days_unverified | 0 |
| successful_exports / failed_exports | 5 / 3 |
| coverage_ratio_requested | 1,00 |
| rows_magyp | 7.867 |
| rows_current | 372, todas mensuales |
| rows_current_daily_comparable | 0 |
| month_coverage_status | complete_requested_window |

coverage_ratio_requested = días incluidos en ventanas con XLSX válido / días únicos
solicitados. Cuenta cobertura de la solicitud, **no días de publicación esperados**.
Los diez días sin filas tienen calendar_status=unknown, sin atribuirles feriado o fin
de semana. Una captura fallida registra rows=null; no equivale a cero publicaciones.
`MCBA_MAGYP_MONTH_VALIDATION.csv` contiene los 31 días, captura, conteos de dimensiones
y extremos de precio. No se usa expected_days ni se declara una mensual oficial.

## Comparación válida A / B / C

**A. Diario detail contra detail:** no evaluable para octubre 2025. La base actual
tiene precisión mensual y fecha ancla 01/10; no se fabrican días actuales ni se
enfrentan los 7.867 registros diarios a esas 372 filas como si fueran pares diarios.

**B. Agregados de días observados de ambas fuentes:** no evaluable sin días actuales
compartidos. Se construye sólo el agregado MAGyP, por combinación completa de
dimensiones, moneda y nivel detail: media de medias diarias sobre días observados,
con método/días/referencias. La mediana del dashboard piloto sigue siendo otra salida
identificada; no se compara una mediana con una media sin etiquetarlas.

**C. Histórico mensual actual K_mes:** contraste descriptivo de etiquetas/candidatos
contra los agregados detail MAGyP. No equivalencia de fórmula verificada. Base actual:
`PHOR25_K.xlsx`/serie de frutas correspondiente, identificadas por archivo_origen y
fila/columna del integrado. Los XLS originales no están disponibles en este workspace.
No se afirma que diferencias sean errores de precio o de fuente.

Grano mensual calculado: **376 combinaciones detail MAGyP frente a 372 actuales**.
Quality/size/grade están estructurados en MAGyP; en el actual suelen estar dentro de
observaciones con códigos CAL/TAM/GRADO, no homologados. Matching conservador no
los inventa: exige unicidad mutua y conserva candidatos cuando faltan dimensiones.

| Matching C | Cantidad | % del reporte |
|---|---:|---:|
| exact | 0 | 0,00% |
| normalized_exact | 0 | 0,00% |
| probable | 206 pares | 38,01% |
| ambiguous | 317 entidades | 58,49% |
| current_only | 8 | 1,48% |
| magyp_only | 11 | 2,03% |

Denominador de porcentajes: **542 filas de reporte = parejas únicas + entidades
sin pareja**, contando ambiguos por lado. Ambiguous = **159 MAGyP y 158 actuales**;
no son 317 pares. Reglas/candidatos/aliases usados se registran por fila.

Entre las 206 parejas descriptivas, 182 difieren más de 0,011 pesos/kg y 24 están
dentro de la tolerancia. Diferencia absoluta máxima **1.030,16 pesos/kg**; diferencia
relativa absoluta máxima **13,263%**, con denominador precio actual. Se preservan
diferencias firmadas además de absolutas. Estas cifras **no validan consistencia de
precios mensuales oficiales** ni prueban inconsistencia de la fuente, porque la
fórmula K_mes no está documentada como equivalente a media de días MAGyP.

Presentaciones sólo actuales incluyen Alcaucil/Ñ. Frances y Chaucha/Española,
Ciruela de España, y etiquetas originales Jalape±O / Red Cha±Ar. Hay anomalías
¥ en MAGyP y ± en dos filas actuales: no se asume que sólo MAGyP tiene encoding anómalo.
Sólo MAGyP incluye también Damasco/San Juan, Durazno/Rojito/Jujuy y Pimiento/Morrón/
Corrientes. Se trata de combinaciones de presentación, no necesariamente pérdida
de cobertura de todo el producto. CSV C conserva todas las dimensiones originales;
no se fuerzan asignaciones ni se corrigen estas discrepancias automáticamente.

Archivos `MCBA_MONTH_MATCHING_DAILY.csv`, `...OBSERVED_AGGREGATES.csv` (sólo esquema
cuando no hay comparación válida), `...HISTORICAL_MONTHLY.csv`,
`MCBA_MONTH_OBSERVED_AGGREGATES.csv` y `MCBA_MONTH_READINESS_METRICS.json` separan A/B/C.
La comparación diaria de agosto de fase 2 se conserva como evidencia previa, no
como validación diaria de este mes ni sustituto de la metodología mensual.

## Duplicados actuales y política analítica

Se confirma el 19/08/2026: **481 filas actuales, 126 grupos y 126 filas excedentes**
con igualdad de fecha/rubro/especie/variedad/procedencia/envase/moneda/unidades/
precio/observaciones, preservando CAL/TAM/GRADO. Las dos rutas RF incluyen una copia
en ZIP anidado, ambas de 126 filas; RH aporta 229. Clasificación **economic_duplicate**
confirmada por datos; source_file_duplicate inferido por procedencia, sin equivalencia
binaria verificada al faltar XLS/ZIP para hash. Hash del integrado sí se conserva.

Vista exclusivamente diagnóstica sin repeticiones: 355 filas. Media aritmética global
de filas cambia de 3.155,439 a 3.144,866 pesos/kg; no es un índice económico válido.
Conteos por producto/rankings de filas se inflan y aumenta el peso relativo de frutas
frente a hortalizas. La replicación uniforme de toda RF no altera su media dentro de
cada producto, aunque sí pesos/comparaciones globales. No se elimina ninguna fila.
Ver `MCBA_CURRENT_DUPLICATE_AUDIT.md` y `MCBA_CURRENT_DUPLICATE_GROUPS.csv`.
Octubre 2025 no tiene duplicados económicos exactos con esa clave.

Política propuesta en `docs/MCBA_PRODUCTION_POLICY.md`:

- Detail para series desagregadas; species_summary oficial separado; Prom.Esp. no es
  variedad comercial y no se intenta reconstruir su fórmula. Octubre contiene
  **6.169 detail y 1.698 species_summary**.
- Kg=0 en todas las 7.867 filas del mes. kg_raw preservado, kg_semantics_status=unknown,
  volume/volume_unit=null. Validación bloquea cero u otra contaminación de volumen.
  Kg no se usa para ponderar y no es un veto a migrar precios.
- Nuevas capturas: ARS + price_unit=kg + currency_evidence=documented. Encabezados de
  [frutas](https://ssma.magyp.gob.ar/frutas.preciospromediof.aspx) y
  [hortalizas](https://ssma.magyp.gob.ar/frutas.preciospromedioh.aspx) documentan pesos/kg.
  No se inventa código ISO entregado por XLSX ni hay conversión numérica. RAW legado
  mantiene evidencia/unidad originales; nunca se reescriben manifests.
- **193 reglas: 169 validated, 19 observed, 5 manual_review**. Sólo validated se aplica
  automáticamente; observed únicamente diagnóstico; manual_review nunca. Las tres
  pendientes previas siguen pendientes. El mes agregó ¥. FRANCES y ESPA¥OLA como
  hipótesis individuales, sin promoción; 114 filas del mes tienen anomalía conservada
  (1,45%). `MCBA_PHASE3_ENCODING_ANOMALIES.csv` clasifica encoding_anomaly por fuente,
  incluyendo dos filas actuales con ±, conservadas intactas. No replace
  global ni eliminación de diacríticos. Estos casos acotados no son veto automático.

## Tests, piloto y CI

**71 tests offline pasan en el venv limpio: 13 common + 58 MCBA**, conservando todos
los anteriores y añadiendo 19 de fase 3. Cubren adapter Chromium/timeout/cleanup,
config CI manual, fallo sin overwrite, retry explícito/máximo dos, cobertura mensual
y revisiones, múltiples ventanas, calendario desconocido, niveles separados, Kg
nunca volumen, unidades desconocidas, aliases, duplicados y matching/agregados.
Los mocks no se presentan como prueba de adquisición real o éxito Linux.

Regeneración real desde RAW: **36 archivos con SHA-256 idéntico antes/después**, cero
requests; incluye RAW/manifests, NORMALIZED, ANALYTICAL y dashboard. Validado en
`MCBA_PHASE3_IDEMPOTENCE_VALIDATION.json`. `git diff --check` aprobado.

Piloto total actualizado: **12 RAW, 11.817 NORMALIZED, 10.380 ANALYTICAL** en 28 días,
8.126 detail y 2.254 summaries. Las capturas revisadas no duplican días analíticos.
Nuevo export preferido `MCBA_MAGYP_DETAIL.csv`; DAILY/LATEST/MONTHLY conservan nivel
explícito. Cinco CSV piloto, con trazabilidad; sin frontend nuevo ni publicación Pages.
MONTHLY mantiene partial_period y denominador de publicaciones desconocido incluso
con ventana completa solicitada: no cambia a precio mensual oficial.

Workflow `.github/workflows/magyp-mcba-pilot.yml` **preparado, no ejecutado**:
workflow_dispatch exclusivamente; allow_web=false por defecto, una captura opcional
en runner.temp, Linux/Python 3.12/Chromium, tests offline, permiso contents:read,
sin cron/commit automático. Artifact sólo tests/diagnósticos públicos livianos
seleccionados, nunca RAW ni perfiles/traces. Estructura inspeccionada y verificada por
tests offline; no se afirma ejecución CI ni validación del parser YAML de GitHub.
La instalación local del navegador sí se hizo desde cero; cloud queda pendiente.

RAW pesado/bases completas ignorados por Git y preservados localmente. Falta ensayar
respaldo/restauración externa antes de usar adquisición CI productiva: el smoke no
sube RAW y el runner es efímero. La URL temporal no permite recuperar el XLSX original.

## Criterios de readiness

| Criterio | Evidencia / estado |
|---|---|
| 1. Headless autónomo reproducible | Chromium real funciona en 5 ventanas; estabilidad insuficiente: 7 fallos globales |
| 2. Entorno limpio / CI | Venv Windows limpio validado; cloud Linux no ejecutado |
| 3. 2025 reproducible | Datos mensuales recuperados; ensayos aislados fallidos, retries necesarios |
| 4. Mes completo solicitado | Sí, complete_requested_window, 31 días cubiertos |
| 5. Granularidad >= actual | Diario y dimensiones de precio preservadas; no superset de todos los campos Excel/códigos/Kg bulto |
| 6. Moneda / unidad | Resueltas para nuevas capturas; legado trazable |
| 7. Detail / summary | Separados y probados; fórmula summary no necesaria para series detail |
| 8. Kg sin contaminación | Cumple, excluido; no bloquea precios |
| 9. Aliases productivos controlados | Cumple política; cinco pendientes acotadas, sin aplicación |
| 10. Consistencia de matching/precios | Mes A/B no evaluable; C sólo diagnóstico, sin equivalencia de fórmula verificada |
| 11. Discrepancias explicadas/acotadas | Encoding identificado; ambigüedades y metodología mensual requieren reconciliación |
| 12. Idempotencia | Cumple, 36 hashes idénticos |
| 13. RAW preservable | Local inmutable/hash verificado; respaldo externo y cloud pendientes |
| 14. Fallos preservan outputs | Cumple tests/ensayos; siete fallos no crearon RAW ni reemplazaron salidas válidas |

## Entregable solicitado — 30 puntos

| Nº | Resultado |
|---|---|
| 1 | Rama codex/magyp-data-platform-mcba |
| 2 | Commit base 5fb5987 |
| 3 | BROWSER_AUTOMATION_REQUIRED |
| 4 | Chromium real: 5 exports válidos, 7 sesiones fallidas |
| 5 | Python aislado Windows validado; CI preparado, no ejecutado |
| 6 | 2025: fechas aisladas fallidas; mes completo recuperado tras retries controlados |
| 7 | Octubre 2025 |
| 8 | 31 días solicitados |
| 9 | 21 días con datos, 10 sin filas (calendario desconocido) |
| 10 | 3 fallos mensuales + 4 fuera del ensayo mensual |
| 11 | 7.867 filas MAGyP del mes |
| 12 | 372 actuales mensuales; 0 diarias comparables |
| 13 | 85 productos MAGyP |
| 14 | 97 variedades/etiquetas, incluyendo summary |
| 15 | 28 procedencias |
| 16 | 10 envases |
| 17 | 5 calidades / 45 tamaños / 12 grados |
| 18 | C: exact 0 / normalized 0 / probable 206 / ambiguous 317 entidades |
| 19 | Sólo MAGyP: 11 combinaciones del agregado descriptivo |
| 20 | Sólo actual: 8 combinaciones mensuales |
| 21 | 182 parejas C difieren >0,011; máximo absoluto 1.030,16; relativo 13,263% |
| 22 | 126 filas excedentes el 19/08/2026; 0 grupos exactos en octubre 2025 |
| 23 | Prom.Esp. separado, fórmula no reproducida |
| 24 | Kg unknown, volumen y unidad null, no ponderaciones |
| 25 | Nuevas capturas ARS / kg / documented, RAW histórico intacto |
| 26 | 5 manual_review; 19 observed no productivos; 169 validated |
| 27 | 71 tests; idempotencia real; diff check aprobado |
| 28 | Archivos detallados abajo |
| 29 | COMPLEMENT_ONLY |
| 30 | Piloto adicional; no migrar aún |

Archivos modificados: acquisition.py (metadata pública de motor y canal permitido),
fetch_mcba.py (unidad separada), matching.py (equivalencia explícita de etiquetas de
unidad), model.py (validaciones semánticas/export DETAIL), requirements-browser.txt,
registro MCBA y aliases, docs de arquitectura/esquema; cinco CSV piloto y _SUCCESS.
Nuevos: validate_acquisition_mcba.py, validate_readiness_mcba.py, test_phase3.py,
MCBA_PRODUCTION_POLICY.md, workflow manual y reportes CSV/JSON/MD de esta fase.
Reportes de fase 2 se mantienen como evidencia histórica, sin reinterpretarlos como
salidas del mes completo. RAW nuevos y bases completas no se versionan.

## Recomendación para la siguiente decisión

Ejecutar el smoke manual Linux después de revisar/publicar el workflow por una acción
humana separada; no se ejecutó ni publicó en esta tarea. Validar varias sesiones
espaciadas con criterios de éxito/fallo y respaldo RAW/restauración. Reconciliar
K_mes y sus atributos fuente usando XLS originales/metodología, o definir una
migración exclusivamente aditiva de precios diarios detail que mantenga K_mes como
otra serie. No usar el agregado calculado como reemplazo silencioso de K_mes.

No se modificaron PRECIOS_MAYORISTAS_INTEGRADO.csv, Excel, frontend, fuentes actuales,
SIO, FOB, Corrientes, Cantidades ni workflows existentes. Sin backfill anual, cron,
commit, push, merge o deploy.
