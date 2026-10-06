# MCBA fase 2 — adquisición autónoma, cobertura y semántica

Fecha de evaluación: 2026-10-06. Rama: `codex/magyp-data-platform-mcba`.
Base de trabajo: commit `1fa2e5e`; cambios locales pendientes de revisión.

**Clasificación: COMPLEMENT_ONLY.** Python reproduce una exportación oficial sin
intervención humana mediante Playwright/Edge headless. No se ha validado una API HTTP
autónoma ni estabilidad suficiente para sustituir los Excel o la base integrada.
Se mantiene la arquitectura canónica existente y la publicación sólo en el piloto.

## 1. Método final y 2. autonomía

`BROWSER_AUTOMATION_REQUIRED`: adaptador separado `acquisition.py`, filtros públicos
GeneXus, evento de exportación y captura del XLSX. Parser y normalizador sólo reciben
bytes/manifest, sin dependencia de Playwright. `MANUAL_ONLY` sigue disponible para
importar exportaciones. `HTTP_AUTONOMOUS` es un contrato probado con mocks, no una
implementación validada del servicio. `--acquisition http` falla explícitamente.

La fase anterior observó 403 al reproducir un POST directo. Esta fase no repitió
ese intento ni buscó evadirlo: automatizó los controles públicos con el estado que
genera el propio sitio. Cuatro exportaciones completas funcionaron; dos intentos
de ventana 2025 fallaron al cargar inicialmente la página. Por tanto, autonomía
operativa demostrada en muestras, estabilidad histórica todavía pendiente.

## 3. Secuencia GeneXus

Origen oficial: [consulta MCBA MAGyP](https://ssma.magyp.gob.ar/frutas.precios.aspx).

1. GET HTTPS inicial, scripts/CSS de GeneXus/WorkWithPlus y sesión efímera. Se observó
   una segunda carga de la página, sin cambio de dominio ni downgrade a HTTP.
2. El navegador conserva en memoria `GXState`, `GridContainerDataV` y controles
   `vDDO_FRUTAS_PRECIOS_FECHAAUXDATE`/`...DATETO`; fechas públicas DD/MM/YYYY.
3. Abrir el filtro, completar ambas fechas y disparar `DDO_GRID.ONOPTIONCLICKED`.
   POST JSON al mismo `.aspx`, observado HTTP 200, 35 parámetros y 2 elementos `hsh`.
4. Esperar respuesta y comprobar fechas visibles dentro de la ventana solicitada.
5. Pulsar `EXPORT`: POST JSON, evento `'DOEXPORT'`, observado 200, 34 parámetros y
   1 elemento `hsh`. La respuesta genera un archivo temporal abierto en otra página.
6. Capturar el evento de descarga del popup. Dos GET del export observados, 200.
   Validar límite, estructura XLSX, columnas, filas y fechas antes de guardar RAW.

Distinción de estado (no se persisten valores):

| Categoría | Observado | Interpretación / límite |
|---|---|---|
| A: formulario/protocolo | Fechas, eventos, claves `MPage`, `cmpCtx`, `grids`, `objClass`, `parms`, `pkgName` | Parámetros públicos de fecha y nombres del protocolo documentados; no contrato API estable |
| B: transitorio | GXState, GridContainerDataV, `hsh`, ruta temporal XLSX | Gestionado exclusivamente por GeneXus/navegador; no reutilizable como URL estable |
| C: seguridad | Nombres `ajax_security_token`, `x-gxauth-token`, `gxajaxrequest` | Se observan encabezados; no se determina cuál es anti-CSRF, autenticación o integridad ni se extraen valores |
| D: sesión | Nombres ASP.NET_SessionId, GX_CLIENT_ID, GX_SESSION_ID, GxTZOffset | Observados en contexto público; necesidad individual no probada; sin persistencia |
| E: navegador | Accept, Content-Type, Origin, Referer, User-Agent, Sec-CH-UA* | Generados por navegador; no se afirma que todos sean indispensables |

No se hace replay del estado ni se almacenan HTML completos, payloads POST, cookies,
tokens, nombres de archivo temporal con identificadores, HAR, trazas o perfiles.
Diagnósticos guardan únicamente nombres, conteos, endpoints sanitizados y filas públicas.
La grilla tiene 23 columnas incluyendo códigos ocultos; el XLSX expone 11. No se
afirman IDs oficiales o códigos que no estén en el export.

## 4. Requests y controles

Cuatro capturas autónomas exitosas registran **63 requests cada una: 252**. Incluyen
bootstrap JS/CSS y recarga inicial; no son 252 consultas de datos históricos. Un
intento fallido de 2025 quedó registrado con **51 requests**. Total contabilizado
en los cinco diagnósticos versionables: **303**, desglosado en
`MCBA_PHASE2_REQUEST_SUMMARY.csv` y `MCBA_ACQUISITION_*.json`.

También hubo pruebas preliminares fallidas para ajustar esperas/selectores y el
listener del popup, otro timeout de 2025 sin diagnóstico persistido, dos GET de
encabezados oficiales y búsquedas oficiales de documentación. Ese tráfico no tiene
inventario completo persistido: **303 no es el total de toda la investigación**.
No hubo backfill masivo ni reintentos automáticos; después de los dos fallos 2025 se
detuvo la adquisición.

Ventanas de 1–7 días, presupuesto predeterminado 80 requests por sesión (máximo
configurable 120), timeout predeterminado 25 s por operación (máximo 60; muestra con
40), XLSX máximo 2 MB y límites de descompresión/filas del parser. Allowlist HTTPS
oficial, imágenes/fuentes/media bloqueados, sin proxies ni certificados ignorados.
User-Agent nativo incluyendo identificación headless más sufijo del piloto.
No se afirma límite total de duración igual al timeout: aplica por etapa/operación.

Los 0 registros de un día dentro de un export de rango se reportan como ausencia
no confirmada, con indicio de fin de semana. Un rango completamente vacío no se
exporta/publica automáticamente; puede terminar como fallo controlado, no como
demostración de ausencia oficial. No se validó calendario de publicaciones/feriados.

## 5. Períodos y 6. cobertura observada

| Día observado | Filas analíticas | Procedencia de la evidencia |
|---|---:|---|
| 2024-10-02 | 356 | Export autónomo de rango; también RAW previo manual |
| 2024-10-03 | 358 | Export autónomo de rango |
| 2025-10-02 | 363 | Sólo RAW previo manual; autonomía 2025 no validada |
| 2026-08-19 | 354 | Export autónomo de rango |
| 2026-08-20 | 359 | Export autónomo de rango |
| 2026-08-21 | 357 | Export autónomo de rango |
| 2026-08-24 | 359 | Rango y export autónomo individual; también RAW previo |
| 2026-10-05 | 370 | Export autónomo individual reciente |

La ventana 19–24/08/2026 devuelve 1.429 filas de cuatro días; 22 y 23 no tienen
filas y son fin de semana, sin prueba de calendario oficial. El rango 02–03/10/2024
devuelve 714. Ventana 02–03/10/2025: dos timeouts iniciales, no RAW nuevo.
No se demuestra cobertura mensual, continuidad anual ni histórico completo.
`MCBA_COVERAGE_VALIDATION.csv` registra 13 combinaciones captura/día, incluidas
capturas repetidas y días vacíos; no son 13 días independientes.

## 7–11. Filas y dimensiones

**7 capturas RAW conservadas, 3.950 filas NORMALIZED y 2.876 ANALYTICAL** en ocho días.
ANALYTICAL selecciona la última captura completa por fecha; no cuenta repetidamente
el 02/10/2024 ni el 24/08/2026 por tener varias versiones. Hashes distintos del
XLSX no prueban por sí solos revisión económica: pueden cambiar metadatos del libro.

| Dimensión no vacía en ANALYTICAL | Valores distintos |
|---|---:|
| Productos | 89 |
| Variedades, incluyendo etiqueta Prom.Esp. | 121 |
| Procedencias | 30 |
| Envases | 10 |
| Calidad | 5 |
| Tamaño | 59 |
| Grado | 15 |

Grano conservado: fecha/tipo/especie/variedad/procedencia/envase/calidad/tamaño/grado/
nivel de observación, con precio original, fila de origen, capture_id, SHA-256 y URL.
ID técnico reproducible; no equivale a un ID del organismo. No se agrega por producto
únicamente. Campos de export: Fecha, Tipo, Especie, Variedad, Procedencia, Envase,
Calidad, Tamaño, Grado, Kg, Promedio x Kg. Dimensiones desconocidas siguen nulas.

## 12. Prom.Esp.

**2.240 detail y 636 species_summary**; unknown implementado para producto ausente,
sin casos en muestra válida. Prom.Esp. ocupa Variedad, con dimensiones de presentación
vacías: evidencia estructural de resumen por especie, no una variedad comercial.
Se retiene como fila oficial y se separa por observation_level en todas las capas.
Nunca se incorpora al promedio de detalle ni se suma como volumen.

Contraste diagnóstico: en 617 de 636 casos el resumen coincide con la media simple
del detalle dentro de 0,02; en 19 difiere. **No valida fórmula universal ni ponderación**.
`MCBA_SPECIES_SUMMARY_VALIDATION.csv` conserva los contrastes y formula_status.
El [boletín oficial MCBA](https://mercadocentral.gob.ar/img/boletin/noticiasdetulado-13-2023.pdf)
describe construcción de promedios mensuales desde relevamientos diarios y precios
modales de diversas presentaciones; no documenta la fórmula de este campo GeneXus.
Falta definición oficial específica antes de escoger serie productiva.

## 13. Kg

Kg=0 en las 2.876 filas analíticas. Se preserva kg_raw, se añade
kg_semantics_status=unknown y volume=null. Sin evidencia de que sea volumen comercial,
no se interpreta como ausencia de operaciones ni se pondera precio con este campo.
La unidad del precio por kg no demuestra la semántica de la columna Kg.

## 14. Moneda

Encabezados oficiales comprobados con GET HTTP 200 el 06/10/2026:
[frutas](https://ssma.magyp.gob.ar/frutas.preciospromediof.aspx) y
[hortalizas](https://ssma.magyp.gob.ar/frutas.preciospromedioh.aspx) indican precios
en pesos por kilo en MCBA y atribución a Corporación del Mercado Central.
La evidencia aplica a ambos tipos. ARS es la regla explícita para pesos locales
argentinos; el XLSX no entrega un código ISO. Se documenta ARS/kg y no se hace conversión.

Los manifests ya capturados se mantienen intactos: **2.506 filas analíticas contextual**,
**370 documented** (captura reciente posterior a verificar ambos encabezados). Nuevas
capturas usan documented; no se reescribe la evidencia histórica. currency_basis es
el campo legado de contexto; currency_evidence expresa la distinción actual.

## 15. Encoding y 16. aliases

Hay 39 filas analíticas con carácter sospechoso preservado. PI¥A/JALAPE¥O/ESPA¥A
tienen propuestas individuales manual_review. Un
[archivo oficial de frutas 2017](https://www.magyp.gob.ar/new/0-0/programas/dma/frutas/series_frutas_17/01_frutas_2017-04-03.php)
también muestra PI¥A/ESPA¥A: la anomalía no nace exclusivamente del parser XLSX actual.
La causa concreta de codificación y el reemplazo no están confirmados. No se reemplaza
¥ globalmente ni se eliminan tildes indiscriminadamente.

191 reglas experimentales en `config/mcba_aliases.json`: **169 validated**, sólo
equivalencias deterministas Unicode/caja/espacios; **19 observed**, códigos y nombres
semánticos observados (p. ej. Ca/CAJA, Buenos Aires/BS. AS.); **3 manual_review**.
Validated participa en normalización; observed sólo en matching probable;
manual_review jamás se aplica. Cada regla incluye dimensión, original, destino,
estado, evidencia y notas. Producto/variedad/procedencia/envase conservan raw y
normalizado. `MCBA_LABEL_NORMALIZATION.csv` registra 250 etiquetas con conteo,
regla y confianza; muestra explícitamente qué propuestas siguen pendientes.

## 17. Frutilla / Zanahoria

**Ambos productos están presentes en los ocho días MAGyP**. La discrepancia de la
fase anterior correspondía a determinadas presentaciones, no a ausencia del producto.

| Día | Frutilla MAGyP / actual | Zanahoria MAGyP / actual |
|---|---:|---:|
| 19/08/2026 | 6 / 12 | 5 / 6 |
| 20/08/2026 | 6 / 6 | 5 / 6 |
| 21/08/2026 | 5 / 6 | 5 / 6 |
| 24/08/2026 | 5 / 6 | 5 / 6 |

El 19/08 la duplicación del RF actual explica el doble de filas de Frutilla. El
24/08 una presentación actual de Frutilla/Tucumán (7.600) y otra de Zanahoria/
Chantenay/Mendoza (722,22) no tienen par único MAGyP; sí hay otras presentaciones de
Zanahoria/Mendoza. No se demuestra alias de producto, categoría alternativa ni causa
única (revisión, filtro, cobertura/export o dimensiones perdidas en el integrado).
Consultar `MCBA_PRODUCT_COVERAGE_DIFFERENCES.csv` y referencias del matching.
Octubre 2026 sin base actual comparable no se marca pérdida de cobertura.

## 18. Matching

Comparación sólo sobre cuatro días compartidos de agosto 2026: 1.429 MAGyP frente a
1.561 actuales. No se enfrenta un día a un promedio mensual.

| Categoría | Resultado |
|---|---:|
| exact | 0 pares |
| normalized_exact | 299 pares |
| probable | 987 pares |
| ambiguous | 377 entidades: 127 MAGyP y 250 actuales |
| current_only | 25 filas |
| magyp_only | 16 filas |

**1.286 parejas mutuamente únicas**, sin diferencias de precio superiores a 0,011.
Ambiguous cuenta filas de ambos lados, no parejas. Referencias a todos los candidatos
y matching_rule permiten auditar por qué no se asignaron. Clave: mercado/fecha/tipo/
producto/variedad/procedencia/envase/unidad; moneda incompatible excluye candidatos.
Calidad/tamaño/grado están en MAGyP pero no estructurados en la base diaria actual;
no se afirma igualdad de esas dimensiones. Precio ausente no permite match.

Hallazgo en base actual, conservada intacta: 19/08 tiene **481 filas**, de ellas 229
RH y 126 RF más otra copia de las 126 RF dentro de un ZIP anidado. Son **126 grupos
de duplicados exactos y 126 filas excedentes** respecto de la clave económica
disponible. Esto explica gran parte de ambiguous; no se fuerza correspondencia.
Los archivos son `FRUTRAS_AGOSTO-26.zip/RF190826.XLS` y
`FRUTAS_AGOSTO-26 (2).zip/FRUTRAS_AGOSTO-26.zip/RF190826.XLS`.

1.077 MAGyP y 782 actuales quedan sólo como diagnóstico mensual no comparable;
no tienen diferencia de precio. Monthly piloto añade coverage_days por combinación,
expected_days=null, coverage_ratio=null, aggregation_status=partial_period y base
de calendario no verificada. No equivale al promedio mensual oficial ni a K_mes.

## 19. Tests y regeneración

**52 tests offline pasan: 13 common + 23 MCBA anteriores + 16 de fase 2.** Cubren
inmutabilidad, hash, revisiones, idempotencia, publicación/rollback, XLSX/schema/HTML/
fecha/precio, estado GeneXus simulado sin valores secretos, HTTP simulado/fallback,
popup de export, ventanas, observation_level, Kg, moneda, aliases/encoding,
ambigüedad bidireccional, partial_period, coverage_days y separación temporal.
El mock completo no requiere Playwright instalado ni acceso a internet.
La ejecución sin solapamiento también genera CSV con esquema y sin faltantes falsos.

Regeneración real desde los siete RAW: NORMALIZED → ANALYTICAL → DASHBOARD,
**25 archivos con SHA-256 idéntico antes y después**, incluidos RAW/manifests y
marcador de publicación. No se altera fecha de captura al reconstruir. Red/descarga
están fuera de esta prueba: una nueva captura es una nueva versión, no overwrite.
Muestra sin precio ausente/cero/negativo, duplicado candidato o extremo; 636
origin_missing corresponden a summaries. Esto no garantiza calidad de todo el histórico.

## 20. Archivos y ejecución

Cambios: acquisition.py, fetch_mcba.py, model.py, normalize_mcba.py, labels.py,
matching.py, compare_mcba_current_vs_magyp.py, validate_coverage_mcba.py; manifest
compatible en common/platform.py; requirements-browser.txt; config/magyp_sources.json
(sólo MCBA), config/mcba_aliases.json; test_phase2.py; docs de arquitectura y esquema.
Salidas regeneradas: cuatro CSV de piloto MCBA, _SUCCESS, comparación CSV/MD,
métricas y nuevos reportes de adquisición/cobertura/etiquetas/resúmenes/productos.
RAW/NORMALIZED/ANALYTICAL pesados permanecen locales e ignorados por Git. Respaldar RAW
en almacenamiento externo antes de migrar; no existe recuperación reproducible del
XLSX a partir de la URL temporal descartada. El reporte de fase 1 permanece histórico.

```powershell
python -m pip install -r scripts/magyp/requirements-browser.txt
# Edge instalado, o instalar Chromium explícitamente para --browser-channel chromium.
python scripts/magyp/mcba/fetch_mcba.py --date-from 2026-08-19 --date-to 2026-08-24 --allow-web --timeout 40
python scripts/magyp/mcba/fetch_mcba.py --date 2026-10-05 --dry-run
python scripts/magyp/mcba/normalize_mcba.py
python scripts/magyp/mcba/build_analytical_mcba.py
python scripts/magyp/mcba/build_dashboard_mcba.py
python scripts/magyp/mcba/compare_mcba_current_vs_magyp.py
python scripts/magyp/mcba/validate_coverage_mcba.py
python -m unittest discover -s tests/magyp_common -v
python -m unittest discover -s tests/magyp_mcba -v
```

Comandos de fetch son ejemplos; no se programan ni se ejecutan de nuevo automáticamente.
Contratos v2/PARSER 2.0.0 aceptan RAW v1 sin modificarlo. La captura diagnóstica
individual 24/08 se incorporó desde bytes de un primer probe exitoso: su Content-Type
fue declarado al incorporar, no conservado en aquel diagnóstico. Los otros tres
fetch CLI conservan el Content-Type efectivamente observado; usar esos para verificar
metadata de transporte. No se modifica retrospectivamente aquel manifest inmutable.

## 21. Nueva clasificación

**COMPLEMENT_ONLY**, con adquisición **BROWSER_AUTOMATION_REQUIRED**.
Cumple autonomía controlada en muestras, fuente oficial, grano detallado preservado,
unidad/moneda documentadas con nivel de evidencia, Kg correctamente excluido,
aliases controlados y regeneración idempotente. No cumple todavía histórico autónomo
2025 estable, continuidad suficiente, fórmula oficial Prom.Esp., equivalencia mensual
ni reconciliación satisfactoria de todas las presentaciones/dimensiones.

## 22. Recomendación de migración

Continuar el piloto con una muestra adicional pequeña, espaciada y revisada: verificar
2025 en otra sesión y días separados sin retries automáticos, calendario de publicación
y equivalencia de un mes completo contra Excel. Solicitar definición de Prom.Esp./Kg
al organismo y confirmar los tres aliases pendientes antes de aplicarlos. Auditar
las copias RF actuales en tarea separada y comparar archivos originales por calidad,
tamaño y grado. Ensayar captura fallida/observabilidad y respaldo RAW en almacenamiento
externo antes de decidir workflow, límites de continuidad y fuente productiva.

No se migró el dashboard productivo ni se modificaron integrado, Excel, frontend,
SIO, FOB, Corrientes, Cantidades o workflows. Sin cron, commit, push, merge o deploy.
