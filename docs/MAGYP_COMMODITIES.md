# Commodities MAGyP: integración local para revisión

Relevamiento y smoke: **09/10/2026**. Rama `codex/magyp-data-platform-mcba`, punto de partida `d82fcbc`, sin cambios pendientes iniciales. No hay commit, push, merge ni deploy. MCBA, Corrientes, Cantidades y Carnes se preservan; SIO y el histórico mensual siguen siendo opciones independientes.

## Fuentes, vigencia y cobertura comprobada

Los enlaces se comprobaron desde el [portal oficial de granos](https://www.magyp.gob.ar/mercadosagropecuarios/granos.php). `scripts/magyp/grains/references.py` contiene las URL completas; no descubre ni enumera rutas durante una actualización.

| Familia | Última observación comprobada | Período en la salida inicial | Frecuencia | Grano y definición | Decisión |
|---|---|---|---|---|---|
| Precio interno | Septiembre 2026 | Enero–septiembre 2026 | Mensual | Mes × producto original × plaza; ARS/TN explícitos, fuente declarada BCBA | Automatizar informe actual. Complementa y actualiza adquisición mensual; histórico 2020–agosto 2026 conservado aparte |
| Pizarra / Cámara | 07/10/2026 | Un día | Diaria cuando publica | Día × producto × cámara/plaza; ARS por contexto y $/Tn explícitos; **provisional** | Nueva referencia separada; no reemplaza BCR sin cotejo |
| FAS teórico D.E.C. | 08/10/2026 | 28/09–08/10/2026, nueve días publicados | Diaria | Día × código/producto × régimen; siete granos ARS/TN por contexto del portal | Nueva referencia de paridad, no operación ni precio interno |
| FAS D.E.R. | 31/10/2025 | 21–31/10/2025, nueve días publicados | Histórico en la grilla actual | Régimen reducido independiente | Conservar como historia identificada; no presentar como vigente |
| FOB oficial API | 08/10/2026 solicitado | Un día | Días con publicación | Día × posición textual × embarque × circular; moneda/unidad/producto no informados | Integrar posiciones originales sin inventar diccionario ni “FOB único” |
| Futuros externos | 08/10/2026 | 07–08/10/2026 | Cierres diarios | Mercado Chicago/Kansas × producto × posición/vencimiento × día; USD/TN explícitos | Nueva referencia por vencimiento, sin serie continua ni roll |
| Futuros locales | 08/10 aparente, sin año explícito en columnas | Dos columnas de fecha abreviada | Diaria según título | Posiciones mensuales y “Disponible”, maíz/soja con cotizaciones | Pendiente: tipo exacto de valor, fecha completa y contrato. No inferir el año desde un vencimiento ni mezclar disponible con futuros |
| SIO Granos | 09/10/2026 en request controlado | Dashboard existente: 09/09–05/10/2026 | Snapshots de operaciones recientes | Eventos/operaciones con condiciones, moneda/unidad, toneladas; no referencia spot | Mantener circuito separado existente. No migrar exportación/grilla sin validar eventos e incrementalidad |

**Historia comprobada no equivale a cobertura completa.** No se descargaron históricos masivos. Pizarra/FAS/futuros capturan la pantalla pública actual, sin paginar ni prometer recuperación retrospectiva. FOB admite `GET .../ws/ssma/precios_fob.php?Fecha=DD/MM/YYYY`, según [documentación oficial](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/fob_oficiales/_archivos/000021_Precios%20Fob%20Api.php); se probó un día reciente, no el inicio del histórico.

El [portal de cotizaciones](https://www.magyp.gob.ar/mercadosagropecuarios/precios.php) corroboró los siete valores FAS D.E.C. y la unidad $/t. Soja/girasol representan capacidad de pago de industria aceitera exportadora; girasol incluye bonificaciones por materia grasa. Los dos aceites FAS conservan precios y códigos, pero **moneda/unidad quedan “Sin identificar”**, porque no se validó evidencia específica. Las etiquetas abreviadas `Cebada C.`, `Cebada F.`, `Ac.Soja` y `Ac.Girasol` se conservan como publica el JS oficial.

La página de futuros externos declara **cotizaciones de cierre** y USD/TN. Sus bloques físicos “FOB BS. AS.” y “FOB GOLFO” se excluyen del parser de futuros. No se les atribuye el significado de FOB oficial API. La página local no declara de forma suficiente ajuste/último/cierre y no tiene año explícito en los dos encabezados; no se integró bajo una convención inventada.

SIO respondió HTTP 200 con un elemento de contrato del 09/10/2026. Los contadores `PageCount/CurrentPage/RecordCount` eran cero pese al elemento devuelto: no se infiere paginación ni cobertura de esa respuesta. La verificación se hizo en un directorio temporal; no cambió ningún CSV o pipeline SIO. La grilla 72h/exportación histórica y el tratamiento de anulaciones/rectificaciones/última instancia permanecen sujetos a validación adicional antes de migrar adquisición.

Acceso observado: anónimo. No se identificaron cuotas, SLA ni licencia específica de redistribución en las pantallas revisadas. Se atribuye la publicación; disponibilidad técnica no constituye una garantía contractual. Futuros conserva además la atribución al mercado original.

## Arquitectura y trazabilidad

```text
GET oficial controlado
  → RAW público inmutable + manifest
  → NORMALIZED por captura (todas las celdas, sin perder dimensiones)
  → ANALYTICAL por familia (última versión de cada día/mes completo)
  → DASHBOARD CSV único por familia, validado y reemplazado atómicamente
  → módulo Commodities existente
```

Directorios bajo `data/magyp/`: `raw/commodities/{familia}/{timestamp_UTC_UUID}/`, `normalized/commodities/{familia}/`, `analytical/commodities/` y `dashboard/commodities/`. RAW/NORMALIZED/ANALYTICAL quedan ignorados por Git; sólo salidas de dashboard y reportes se preparan para revisión.

RAW es una **proyección JSON del contenido público** (filas, texto visible y las dos grillas numéricas FAS), no una copia del formulario HTML. Se excluyen cookies, scripts, tokens, credenciales, viewstate, eventvalidation y demás inputs. El manifest conserva **dos hashes**: `response_sha256` del cuerpo recibido y `sha256` del JSON público almacenado, con tamaños diferenciados. No se promete reconstruir el HTML original desde la proyección. Ninguna captura anterior se sobrescribe.

Manifest: fuente/familia, URL pública, método GET, parámetros públicos (Fecha sólo para FOB), fecha solicitada, UTC, HTTP status, content-type, encoding, tamaños, hashes, parser/schema, capture_id, conteo y representación. FAS incorpora URL/hash del diccionario JS y las columnas verificadas. El primer smoke FAS usó el diccionario contrastado por separado; la segunda captura ya verifica y registra el JS en la misma corrida. No se modificó la primera captura.

NORMALIZED conserva fecha/período, producto/posición y etiquetas originales, plaza, frecuencia, moneda/unidad/evidencia, condición/embarque, circular, régimen/código, precio original y decimal parseado, `value_status`, URL, UTC, capture_id, raw_sha256 y schema. No se agregan volumen, producto FOB, NCM ni unidad faltante. `S/C`/guion/vacío, cero y precio positivo tienen estados distintos. Los ceros no desaparecen de RAW/NORMALIZED/observaciones auditables.

IDs SHA-256 técnicos, no identificadores de negocio publicados:

- `series_id`: familia, producto, plaza, tipo, moneda, unidad, condición/ventana, circular y código cuando existen.
- `observation_id`: series_id + fecha.
- `record_id`: observation_id + captura + hash RAW.

ANALYTICAL selecciona la **captura completa más reciente de cada fecha**, preservando retiradas/revisiones en la vista actual. No rellena una publicación nueva con valores retirados de la anterior. Las versiones anteriores siguen en RAW/NORMALIZED.

El CSV dashboard tiene `row_kind`: `observation`, `diario`, `mensual`, `ultimos`, `semaforo`, `resumen`. El navegador consume sólo las vistas, sin leer RAW. Las filas observation son la memoria analítica liviana para conservar fechas anteriores en una nueva corrida de Actions desde un checkout limpio. No son reemplazo del archivo RAW histórico externo.

Cada familia se publica como **un único CSV**, evitando combinar archivos de generaciones diferentes. Contiene todas las dimensiones útiles y trazabilidad; tamaño inicial aproximado: internos 258 KB, pizarra 37 KB, FAS 255 KB, FOB 501 KB, futuros 322 KB. No se hace backfill automático; el crecimiento de la memoria publicada deberá evaluarse antes de una operación prolongada y del almacenamiento externo permanente.

## Cálculos conservadores

Internos: el valor mensual publicado se mantiene mensual; no se presenta como un precio diario. Para fuentes diarias, cada fila diaria conserva una observación publicada por serie. El resumen mensual es la **mediana de días capturados de esa misma serie**, marcado como parcial; no se afirma promedio oficial mensual. Los días faltantes no se interpolan.

Las variaciones mensuales/interanuales exigen exactamente el mes anterior/doce meses anteriores. Las de 7/30 días exigen exactamente esa fecha publicada; no sustituyen el intervalo por la observación más cercana. Faltantes producen “Sin dato”. Semáforo: baja <−5%, estable hasta 5%, suba moderada hasta 20%, suba fuerte >20%; magnitud >50% requiere revisar. Sin comparación, no se asigna un estado artificial.

Las referencias no publican volumen: el gráfico correspondiente cuenta cotizaciones positivas y se rotula “Observaciones por referencia”. SIO conserva volumen y conteo transaccional existentes. Los KPIs globales de precio/variación se muestran únicamente al acotar a una serie de referencia; ranking, gráficos y tablas conservan la comparación entre series sin producir un precio único combinado.

## Integración y fallback

Se amplía **Tipo de referencia / Fuente** con internos MAGyP, pizarra, FAS, FOB y futuros externos. SIO y el histórico mensual anterior siguen disponibles. Condición/posición aparece como filtro secundario y columna de contexto sólo en referencias; fuente y fecha de actualización son visibles. Se preservan todos los controles/canvases/tablas anteriores.

Internos tuvo **50 coincidencias exactas** de precio en períodos/plazas comunes (enero–agosto 2026), ARS/TN, y seis observaciones nuevas de septiembre. El reporte `COMMODITIES_INTERNAL_COMPARISON.json` explicita los alias usados **sólo para cotejo**, sin modificar nombres o valores legacy. El nuevo informe actual automatiza la adquisición; **no sobrescribe la base histórica 2020–2026** ni une series por similitud. Ante fallo de carga de internos MAGyP, el selector usa los CSV legacy existentes y anuncia el respaldo histórico. Pizarra/FAS/FOB/futuros son complementos; no reemplazan precios internos, BCR o SIO.

## Validaciones y ejecución

```powershell
python scripts/magyp/grains/references.py --source all --date 2026-10-08 --dry-run
python scripts/magyp/grains/references.py --source all --date 2026-10-08 --allow-web
# Replay local sin red, a partir de RAW ya capturado:
python scripts/magyp/grains/references.py --source all --date 2026-10-08
python -m unittest discover -s tests/magyp_common -p test_references.py -v
node --test tests/magyp_frontend/commodities.test.cjs
```

Usar una fecha publicada para FOB; los otros cuatro GET consultan la pantalla actual y la fecha sirve como control. Una respuesta futura respecto del control se rechaza. No hay bucles de fechas, paginación, backfill ni reintentos. Máximo **seis GET** por corrida all: cinco fuentes y diccionario FAS; 1,5 s entre familias, timeout 20 s, 1,5 MB por cuerpo y 200 KB para diccionario, sin redirects. Dry-run no escribe ni consulta.

Controles: HTTP, tamaño, JSON/HTML parseable, encabezados/bloques/productos/plazas/mercados, diccionario FAS, campos FOB exactos, fecha/embarque/vencimiento, precisión decimal por fuente (pizarra usa coma miles/punto decimal; internos/futuros punto miles/coma decimal), duplicados/conflictos, precio no negativo/finito, no publicación vacía ni futuras, integridad/hash/schema/conteos y vistas del bundle. Umbral operativo de antigüedad: 70 días internos, 10 días las otras familias; es una guardia de publicación, no una frecuencia oficial ni un SLA. La antigüedad del régimen D.E.R. queda explícita y no impide aceptar D.E.C. vigente.

FOB `[]` o `{"posts":[]}` es **NO_PUBLICATION** en cualquier día: conserva el último CSV y continúa sin error por esa ausencia. El estado queda en logs y en el manifest RAW inmutable, con fecha solicitada y hashes; no se interpreta como precio cero. Un schema desconocido/malformado sigue fallando. Una captura vieja válida se puede reproducir usando su fecha de control original. Normalizar el mismo RAW conserva IDs y bytes de salida. Capturar nuevamente conserva otra versión, aunque el contenido se repita.

Un lock evita escritores simultáneos. Publicación valida en memoria antes de `os.replace` sobre el único CSV; falla de descarga/parser/normalización/validación deja el dashboard previo. Fallas de una familia no alteran las otras; la corrida devuelve error si alguna falla. Una interrupción puede dejar staging/lock: revisar proceso antes de limpiar. No se ejecuta frontend contra servicios remotos.

## Automatización y pruebas

`.github/workflows/magyp-commodities-review.yml` conserva su ruta y ejecución manual, y agrega **`0 23 * * 1-5`**: lunes a viernes, aproximadamente 20:00 Argentina (UTC-3). Actions puede iniciar con demora. En schedule se consultan las cinco familias con la fecha del día en `America/Argentina/Buenos_Aires`; en manual la fecha es opcional y se puede seleccionar una familia. Los smoke manuales Linux con publicación FOB y NO_PUBLICATION fueron aprobados por el usuario antes de preparar esta automatización.

Flujo: pruebas offline → fetch/validación/normalización/build independiente → validar cinco CSV → pruebas Python/frontend y `git diff --check` → commit/push de outputs permitidos → despacho explícito de Pages. Si alguna familia genera ERROR, la adquisición continúa con las demás y conserva la salida de la fallida, pero el lote no se commitea ni despliega; los resultados preparados quedan como artefacto. NO_PUBLICATION FOB no bloquea el lote. La validación `scripts/magyp/grains/validate_publication.py` exige los cinco bundles válidos, cada uno de hasta 5 MiB, y rechaza cualquier archivo staged fuera del allowlist.

Únicos archivos que la ejecución productiva puede commitear:

- `data/magyp/dashboard/commodities/internal.csv`
- `data/magyp/dashboard/commodities/board.csv`
- `data/magyp/dashboard/commodities/fas.csv`
- `data/magyp/dashboard/commodities/fob.csv`
- `data/magyp/dashboard/commodities/futures.csv`

Commit y despliegue sólo se ejecutan desde `main`; un manual sobre otra rama valida y genera evidencia sin publicar. No hay force-push: un avance concurrente de main que impida el push detiene la publicación. Si no cambian los CSV, no se crea commit.

El job tiene `contents:write` para guardar los CSV y `actions:write` para ejecutar **`gh workflow run deploy.yml --ref main`** después de una validación y persistencia exitosas. Este `workflow_dispatch` explícito funciona con GITHUB_TOKEN, según [GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow); no depende del evento push del bot. También se despacha con CSV sin cambios para poder recuperar un despliegue anterior fallido. El token se entrega sólo por variable de entorno, no se guarda en datos/logs.

El despliegue existente hace un checkout limpio de main, utiliza su secreto `CSV_PASSWORD` y publica Pages con su grupo de concurrencia actual. No recibe el workspace de adquisición, RAW, staging ni credenciales del job de actualización. Si falla el despacho, el job de actualización falla. El resultado de Pages se sigue en el workflow `deploy.yml`: una aceptación del despacho no equivale a un despliegue exitoso. Si falla el despliegue, queda servido el último sitio válido; el siguiente run válido vuelve a despacharlo. No se modificó `deploy.yml` ni el frontend.

El artefacto conserva RAW público, NO_PUBLICATION y salidas por 30 días, **no es un archivo permanente**; no se versiona RAW, NORMALIZED ni ANALYTICAL. El límite de 5 MiB por CSV detiene crecimiento excesivo antes del commit; archivo externo duradero sigue siendo una decisión de almacenamiento separada. Versiones v7 verificadas en los README oficiales de [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python), [setup-node](https://github.com/actions/setup-node) y [upload-artifact](https://github.com/actions/upload-artifact).

Pruebas específicas: 24 Python de referencias + 3 Python de guardia de publicación + 7 Node de Commodities; regresiones existentes: 13 Node de MCBA/Corrientes/Cantidades y configuración legacy. La guardia se prueba con faltantes, vacíos, schema corrupto, otra familia, exceso de tamaño y archivos staged RAW/secretos/frontend/otros módulos; ninguna validación muta archivos. Evidencia de navegador en `COMMODITIES_BROWSER_CHECK.json`: siete opciones con datos, tres gráficos, rankings, semáforo, tablas, condición/posición y ausencia de errores JavaScript. El smoke diario verifica que “último” usa el precio del último día, sin sustituirlo por mediana mensual. La guía `vercel:verification` se usó para recorrer fuente → CSV → selector → visualización local. Ningún servicio Vercel es dependencia del proyecto.

## Bloqueos pendientes

1. Diccionario oficial FOB por posición: producto, moneda y unidad; no deducir NCM ni mapear prefijos.
2. Unidades/moneda específicas de aceites FAS y alcance del régimen reducido vigente.
3. Futuros locales: fecha completa, medida del precio e identificación contractual. Historia local y permisos institucionales no validados.
4. SIO: paginación fiable, exportación/eventos históricos y reglas de estado/incrementalidad; no deduplicar sólo por número de contrato ni equiparar última instancia con operación vigente.
5. Historia de pizarra/FAS/futuros fuera de la pantalla reciente, calendario de feriados, cuotas/SLA/licencia explícita y archivo RAW externo durable.

La automatización sólo modifica su workflow, guardia de publicación, tests específicos y esta documentación. No hay modificación de MCBA, Corrientes, Cantidades, Carnes, lógica económica, frontend, bases o Excel existentes, CSV SIO/local legacy ni otros workflows. `COMMODITIES_PRESERVATION.json` conserva el control histórico de archivos durante la integración inicial.
