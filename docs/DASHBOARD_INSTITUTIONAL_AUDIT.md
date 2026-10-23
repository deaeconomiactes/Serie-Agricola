# Auditoría institucional transversal del dashboard

Evidencia y mediciones: **22/10/2026**. Cierre: **23/10/2026**.
Base examinada: `main` en `1a7c1eb`.
Política obligatoria: [DATA_SOURCE_POLICY.md](DATA_SOURCE_POLICY.md).

## Dictamen y alcance

**APTO CON SALVEDADES para exploración descriptiva de las fuentes identificadas.**
No equivale a certificar un índice homogéneo de precios ni la representatividad de
SIO por plaza. Se corrigieron errores reproducibles de presentación/cálculo de
Mayoristas y una carga inicial innecesaria. Sigue pendiente una decisión
metodológica P1 sobre la agregación de operaciones SIO por lugar de entrega y
condición comercial. No presentar esa agregación como el precio de una plaza.

Se revisaron código, contratos, metadatos y salidas versionadas; hubo revisión
independiente de consistencia económica y pruebas reales del checkout local en
Microsoft Edge y Google Chrome. No se descargaron fuentes nuevas, no se repitió
el backfill y no se ejecutaron workflows de producción ni despliegues. La frescura
descrita es la registrada en el repositorio, no una comprobación de disponibilidad
actual de los servidores oficiales.

## 1. Fuentes, cobertura y estado por módulo

Las horas con `Z` se informan aquí en UTC; el indicador de la interfaz las convierte
a Argentina. La fecha de observación y la captura son campos diferentes.

| Módulo/familia | Fuente y cobertura examinada | Última observación | Última captura exitosa | Estado registrado | Magnitud/frecuencia |
|---|---|---|---|---|---|
| Cantidades | Registro integrado frutihortícola local, 2024–2025 | 30/12/2025 | No informada en contrato de origen | Archivo estático; no atribuirle actualización automática | TN; registros diarios, agregados visibles |
| MCBA diario | MAGyP; captura publicada conservada | 05/10/2026 | 06/10/2026 13:34Z | SOURCE_UNAVAILABLE | ARS/kg; diaria cuando publica |
| MCBA mensual | Mercado Central; ZIP con XLS diarios oficiales de 2026 | 19/10/2026, observación diaria subyacente | 20/10/2026 12:49Z | NO_OP_ALREADY_CURRENT | ARS/kg; **mensual derivada**, no promedio mensual oficial publicado |
| MCBA histórico mensual | Archivo manual 2024–2025 y huecos reales no cubiertos | Según selección | No informada | Estático | Conservar unidad original y conversión documentada a kg |
| Corrientes | Archivo manual vigente; mercado relevado Corrientes | 25/08/2026 | No informada | STATIC | $/bulto; kg estimado sólo cuando la conversión es admisible; moneda no identificada en inventario |
| Precio interno | MAGyP, 01/1996–09/2026 | 01/09/2026, clave mensual | 21/10/2026 13:30Z | UPDATED | ARS/TN; **mensual publicado** |
| Pizarra/Cámara | MAGyP, 02/01/2018–19/10/2026 | 19/10/2026 | 21/10/2026 13:30Z | UPDATED | ARS/TN; diaria, mensual derivada |
| FAS | MAGyP; D.E.C. vigente, historia desde 16/01/2007; D.E.R. separada | 20/10/2026 | 21/10/2026 13:30Z | UPDATED | ARS/TN donde está documentado; resto Sin identificar |
| FOB SSPM | Histórico independiente 04/01/1993–21/01/2025 | 21/01/2025 | Ver manifiestos históricos | Histórico con huecos; finalización de cobertura no implica caída | USD/TN; sin continuidad artificial con la API |
| FOB API | MAGyP; posición/circular/embarque originales | 19/10/2026 | 21/10/2026 13:11Z | NO_PUBLICATION | Moneda y unidad **Sin identificar**; diaria cuando publica |
| Futuros externos | MAGyP, 02/01/1995–20/10/2026 | 20/10/2026, fecha de cotización | 21/10/2026 13:30Z | UPDATED | USD/TN; mercado, contrato y vencimiento separados; sin roll |
| SIO | Secretaría de Agricultura; snapshots transaccionales publicados | 21/10/2026 | 21/10/2026 18:08:41, **hora sin zona declarada** | UPDATED | ARS o USD, TN; operaciones, no referencia física equivalente |
| Carnes: faena | MAGyP/DNCCA detalle 2018–09/2026; SSPM mensual 1980–08/2026 y anual 1980–2025 | 30/09/2026 en selección detalle | 22/10/2026 11:21Z | UPDATED en publicación corriente | Cabezas; mensual, anual completo o acumulado publicado separados |
| Carnes: producción/peso | MAGyP/DNCCA corriente 01–09/2026; SSPM producción mensual desde 1998 y anual desde 1980 | 09/2026 para detalle corriente | 22/10/2026 11:21Z | UPDATED | Toneladas res con hueso / kg res con hueso; familias separadas |
| Carnes: archivo | Indicadores, precios Liniers y exportaciones 01/1998–08/2019 | 08/2019 | 22/10/2026 11:21Z | HISTORICAL_ENDED | Panel histórico secundario; unidades y monedas por indicador |

Evidencia primaria: `data/magyp/reports/PRICE_FRESHNESS_STATUS.json`, índices y
`_SUCCESS.json` de los bundles, `data/carnes/dashboard/index.json`, sus estados y
manifiestos. El inventario de Commodities conserva `historical_coverage`,
`effective_sources`, `effective_data_last_observation_date` y
`effective_data_last_capture`; no reemplaza el estado de adquisición corriente.
Carnes usa su propio índice/estado, no una fecha inferida del calendario.

El archivo de Cantidades tiene 49.494 registros utilizables (11.185 de 2024 y
38.309 de 2025), con unidad TN. El ejemplo original `0,600;TN` representa 0,6 TN:
**no corresponde dividir nuevamente por mil**. Faltan captura e identificación
institucional verificable a nivel de registro; no se inventaron.

## 2. Cutover, solapamientos y trazabilidad

- Internos manuales: comparación previa **668/668** celdas cubiertas, diferencia
  máxima 0,00. El frontend no carga `local_mensual`, no lo reactiva si falla MAGyP
  y la preparación de Pages excluye su salida retirada. La fila estática en el
  inventario de frescura documenta la migración; no es una opción productiva.
- MCBA: se conserva el histórico manual necesario. Prioridad diaria MAGyP por
  fecha y mensual Mercado Central por período/rubro, antes de filtrar productos.
  Los solapamientos de las bases de origen no equivalen a duplicados de runtime.
  No se reemplaza una variedad faltante con otra fuente dentro de un período ya
  cubierto según el contrato vigente. No se retiraron originales manuales.
- Corrientes permanece estático. El cierre BLOCKED_BY_SOURCE sigue vigente.
  Procedencia Corrientes en MCBA **no** sustituye un relevamiento de ese mercado.
- Commodities: las pruebas cargan las historias mensuales y fragmentos diarios
  tempranos, validan hashes/dimensiones y la prioridad de revisiones compatibles.
  No se mezclan Pizarra, internos, FAS, FOB, futuros ni SIO. SSPM/API FOB conservan
  identificadores/metodologías distintas. No se detectó una duplicación nueva
  causada por el cutover en los contratos examinados; no se afirma una auditoría
  manual de cada observación histórica.
- SIO público: 207 filas diarias, 22 mensuales, 13 últimas, 22 de semáforo; cero
  duplicados de la clave diaria publicada. **103/207 filas diarias contienen más
  de un lugar de entrega**. Esto es heterogeneidad dentro de una agregación, no
  duplicación. No se confundió con un precio homogéneo de plaza.
- Carnes preserva hash RAW, captura, fuente y geografía; el navegador verifica
  hashes de fragmentos preparados. No suma total nacional con provincias,
  establecimientos y usuarios redundantes. Los cambios de clasificación y
  bovinos/bubalinos se identifican; un acumulado enero–septiembre no es año completo.

Los links institucionales y la trazabilidad original continúan en detalle/tablas,
diccionarios y manifiestos. No se reincorporaron URLs extensas en tooltips ni se
atribuyó moneda/unidad a FOB API por analogía con SSPM.

## 3. Hallazgos y correcciones

| ID | Nivel | Evidencia e impacto | Resolución |
|---|---|---|---|
| A01 | **P0** | Ranking Mayoristas consulta un Map por identidad técnica y lo escribe por etiqueta. Con dos observaciones 100 y 300 puede conservar sólo 300, en vez de promedio 200 y conteo 2. Muestra real Banana/Ecuador: 20 observaciones, media 1.692,0532 frente a 1.631,8182 y conteo 1. | **Corregido**: usar la misma clave para lectura/escritura; test multicomponente independiente. |
| A02 | **P1** | Una variación mensual podía comparar enero con marzo si faltaba febrero. También afectaba series divididas y celdas del semáforo. Hay huecos reales en MCBA mensual; no son ceros. | **Corregido**: exigir mes/año calendario precedente; sin base, variación nula. Se conserva la variación acumulada explícita del período. |
| A03 | **P1** | Semáforo Enero–Diciembre con “Todos los años” reunía, por ejemplo, enero de 2025 y enero de 2026 en una celda. | **Corregido**: si los datos abarcan más de un año, pedir selección de un año. No se cambió la matriz ni la metodología de cada mes. |
| A04 | **P2** | KPIs globales de Cantidades aparecían sobre Mayoristas/Commodities; podían leerse como indicadores del módulo activo. | **Corregido**: aplicar la separación ya existente en Carnes; encabezado de cantidades sólo en su módulo. |
| A05 | **P2** | Apertura descargaba 51,9 MB antes de finalizar carga, incluyendo módulos cerrados. | **Corregido parcialmente**: carga diferida por módulo con promesa compartida, estado accesible y reintento al reabrir tras fallo. Apertura queda en 4,23 MB. No se alteraron CSV. |
| A06 | **P2** | Tooltip accesible del estado exponía “Estado publicado por el pipeline”. | **Corregido**: “proceso de actualización”. Sin cambio de estados ni inferencias por fecha. |
| A07 | **P1 pendiente** | SIO agrupa por fecha/producto/moneda/unidad/tipo/condición/fuente, omitiendo lugar de entrega; mensual también omite condición. La interfaz usa “Sin plaza”. Ejemplo maíz USD/TN 09/09/2026: mediana 193,45 reúne Rosario N/S y zonas 5/7, en origen y destino. | **No cambiar arbitrariamente**. Definir si es resumen heterogéneo transaccional o series por lugar/condición antes de su uso como referencia comparable; preservar eventos y trazabilidad. |
| A08 | **P2 pendiente** | Mayoristas aún descarga base integrada de 30,24 MB y ~10,58 MB adicionales; Commodities carga sus familias auxiliares al abrir el módulo. | Requiere salidas preparadas/fragmentación y contrato de carga; no hacer una reestructuración incidental en esta auditoría. |
| A09 | **P2 pendiente** | Cantidades carece de estado/captura institucional comparable a las fuentes automatizadas; Corrientes no identifica moneda en inventario. | Documentar la ausencia; completar sólo con evidencia de origen. No inventar captura ni ARS a partir de `$`. |
| A10 | **P1 pendiente** | Mayoristas “Todos” resume composición de productos/orígenes y fuentes, con distintas coberturas. Se explicita promedio simple y selección; no equivale a un índice de mercado ni canasta constante. | Mantener para exploración descriptiva. Una comparación institucional homogénea requiere definición de canasta/calidad/mercado y ponderación autorizadas. |
| A11 | **P3** | Algunas fechas KPI se parten a 1000 px; título global frutihortícola permanece en Carnes; opciones de origen contienen `#n/a`; comentario antiguo sobre KG no coincide con TN. | Documentado, **sin correcciones cosméticas automáticas**. |

No se modificaron adquisición, normalización, bases históricas, workflows ni
cálculos de Commodities/SIO/Carnes. Las correcciones económicas corresponden sólo
a errores demostrados en funciones de presentación Mayoristas. Las fórmulas
válidas, unidades y prioridades de fuentes permanecen iguales.

## 4. Frescura, filtros, visualizaciones y accesibilidad

Se verificaron los estados explícitos UPDATED, NO_OP_ALREADY_CURRENT,
NO_PUBLICATION, SOURCE_UNAVAILABLE/MAGYP_LAST_VALID/LAST_VALID, STATIC y
PIPELINE_ERROR; Carnes además HISTORICAL_ENDED. Fechas antiguas no generan error
por sí solas. La ausencia de nueva publicación FOB no impide las otras familias.
Las pruebas de publicación verifican conservación de última salida válida frente
a HTTP, schema, XLSX inválido, vacío y hash incorrecto.

Internos sólo ofrece mensual publicado. Pizarra/FAS/FOB/futuros tienen detalle
diario por año y vistas mensuales derivadas cuando corresponde. Cotización y
vencimiento son dimensiones diferentes; el eje y último dato usan observación.
Multiserie de referencia solicita “Seleccioná una serie”, sin un promedio global.
El control de tipo de precio aplica a SIO; volumen se conserva como dato
transaccional y no se inventa para cotizaciones de referencia.

Carnes: provincia/categoría/dentición se habilitan según tabla y familia;
producción y peso no heredan KPIs de cabezas. Falta de peso total publicado se
muestra como tal. Las pruebas cubren cambio rápido de selección, clasificación
2019, acumulado parcial, comparabilidad interanual y conservación de vista ante
fragmento corrupto. Histórico Liniers/exportaciones permanece secundario y finalizado.

Prueba de los cuatro módulos a **1440, 1000, 900 y 640 px en Edge y Chrome**:
sin desbordamiento horizontal de la página ni errores JavaScript. Las tablas
anchas mantienen desplazamiento local; no se eliminaron columnas. Selector
commodity abierto comprobado por captura y por elemento superior bajo el cursor.
Navegación básica por teclado, etiquetas, selección y foco revisados; no constituye
certificación WCAG ni prueba exhaustiva con lector de pantalla. El contraste de
textos secundarios pequeños sigue siendo una revisión de accesibilidad pendiente;
no se declara una relación numérica no medida.

Evidencia visual conservada: [Mayoristas, 1000 px](audit/2026-10-22/prices-1000.png),
[Commodities, 640 px](audit/2026-10-22/commodities-640.png),
[encabezado corregido](audit/2026-10-22/commodities-heading.png),
[Carnes](audit/2026-10-22/carnes.png).
Las capturas completas de la matriz responsive se generan fuera del repositorio.

## 5. Performance

Medición fría local por Resource Timing, sin compresión del servidor Python.
`initial_bytes` representa bytes decodificados locales; `initial_requests`
incluye recursos externos, cuyos tamaños pueden estar ocultos por CORS. Las filas
de navegación son **incrementales** desde la vista anterior, no apertura fría
independiente de cada módulo. No extrapolar tiempos a GitHub Pages.

| module | initial_requests | initial_bytes | largest_payload | lazy_loaded | issues |
|---|---:|---:|---|---|---|
| Apertura antes | 44 | 51.927.275 | Mayoristas integrado: 30.238.719 | Sólo Carnes | Cargaba precios antes de abrirlos |
| Cantidades después | 12 | 4.230.402 | Registro: 3.931.671 | Vista inicial | Base completa preparada local; captura no declarada |
| Mayoristas al abrir | 8 | 40.814.572 | Integrado: 30.238.719 | Sí, por módulo | Falta fragmentación/salida más liviana |
| Commodities al abrir | 24 | 6.884.627 | FOB corriente: 1.471.954 | Sí, por módulo | Carga familias auxiliares conjuntamente; historia diaria por año |
| Carnes al abrir | 5 | 215.494 | Índice: 88.543 | Sí, script + índice + selección | Carga estrictamente fragmentada; sin establecimientos/usuarios completos |

Reducción de bytes iniciales locales: **91,9%**. Primera medición Edge: 67,1 s
antes frente a 20,5 s después; Chrome después 22,6 s. Primera navegación Mayoristas
36,0 s Edge / 25,5 s Chrome y Commodities 6,4 / 4,6 s. Son muestras únicas locales
con recursos externos y carga concurrente de pruebas, **no un benchmark** ni SLA.
La repetición final registró apertura 10,8 s Edge / 13,4 s Chrome, lo que confirma
la variabilidad del entorno. Recuentos, recursos, bytes, estados de las seis
fuentes y resultados responsive se conservan en
[BROWSER_AUDIT_EVIDENCE.json](audit/2026-10-22/BROWSER_AUDIT_EVIDENCE.json).

No se solicitaron rutas RAW/NORMALIZED/ANALYTICAL. Esto no convierte en liviano el
integrado de 30 MB: queda deuda explícita, sin ocultarla por su nombre/ruta. Carnes
usa hash de fragmentos y caché verificada; Commodities usa diccionarios y shards
históricos. Las promesas nuevas evitan cargas duplicadas al reabrir pestañas y
permiten reintento tras fallo. No se añadió un service worker ni caché persistente.
Se actualizaron las versiones de los tres assets modificados en `index.html`
para que una caché previa no mantenga el comportamiento anterior tras publicar.

## 6. Validación reproducible

| Comprobación | Resultado |
|---|---|
| Frontend `node --test tests/magyp_frontend/*.cjs` | **85/85**; incluye 6 regresiones específicas de esta auditoría |
| Carnes Python | **29/29** |
| Python común / referencias / histórico / frescura | **74/74** |
| MCBA Python | **105/105** |
| Mercado Central Python | **20/20** |
| CI/publicación Pages | **6/6** |
| SIO | Regresión de configuración/series contra versión comprometida; rebuild offline de muestra: 46 diarias/30 mensuales, separado de outputs públicos; revisión de claves públicas sin duplicados |
| Navegador Carnes existente | Edge y Chrome; selección, familias, fuente, provincia, categorías, YTD, históricos, fragmento corrupto, otras pestañas |
| Auditoría navegador transversal | Edge y Chrome; 16 combinaciones módulo/ancho por navegador; sin rutas prohibidas; selector abierto y cambios de las seis fuentes |
| actionlint | Sin hallazgos con label self-hosted `serie-agricola` declarado en configuración local de comprobación |
| `git diff --check` | Sin errores |

Los tests existentes se conservaron; la regresión de Mayoristas deja de exigir
igualdad con las variaciones que saltaban meses y sigue comparando filas,
rankings, precios por período y precios/metadata del semáforo. Las nuevas pruebas verifican separadamente
ranking, huecos de calendario y no combinación de años. El test de navegador
Carnes ahora exige el encabezado de cantidades sólo al volver a Cantidades.

Ejecución optativa local, sin consultas a fuentes:

```text
python tests/magyp_frontend/institutional_browser_audit.py --url http://127.0.0.1:8768 --channel msedge --output <directorio-fuera-del-repo>
python tests/magyp_frontend/institutional_browser_audit.py --url http://127.0.0.1:8768 --channel chrome --output <directorio-fuera-del-repo>
python tests/carnes/browser_ui_checks.py --url http://127.0.0.1:8768 --channel msedge --output <directorio-fuera-del-repo>
```

Requiere servidor estático del checkout, Playwright y los navegadores instalados.
No usa secretos ni modifica datasets. El analítico completo SIO no está en este
checkout: su rebuild se comprobó con la muestra versionada, no se atribuye a esa
prueba una reproducción completa del histórico transaccional productivo.

## 7. Límites de aptitud y siguientes decisiones

1. **SIO:** decidir y validar el grano por entrega/condición antes de usar sus
   resúmenes como referencia comparable de plaza. No resolver con una etiqueta
   que esconda la heterogeneidad.
2. **Mayoristas:** no usar selección “Todos” como índice económico o canasta
   constante. El promedio descriptivo no corrige cambios de composición.
3. **Carga:** preparar/fragmentar Mayoristas en una tarea acotada con contrato y
   equivalencia comprobados. Conservar granularidad original fuera del navegador.
4. **Trazabilidad estática:** completar institución/captura de Cantidades y moneda
   Corrientes sólo cuando exista evidencia. Fuente estática no significa caída.
5. **Fuentes externas:** SOURCE_UNAVAILABLE MCBA y NO_PUBLICATION FOB describen el
   último intento registrado; esta auditoría no promete disponibilidad futura.

Con estas salvedades, se preservan los módulos y la separación de familias. No se
emitió una aprobación irrestricta para comparaciones económicas homogéneas de SIO
o agregados composicionales. No se requieren nuevas fuentes para resolver las
deudas identificadas.
