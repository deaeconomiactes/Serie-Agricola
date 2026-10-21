# Histórico oficial de precios de Commodities

Implementación local, rama `codex/magyp-commodities-history`. Aplica
`DATA_SOURCE_POLICY.md`. No modifica MCBA, Corrientes, SIO, Cantidades ni Carnes.
Los inventarios generados contienen los conteos y límites efectivamente validados;
no se afirma haber agotado todo archivo existente en el organismo.

## Fuentes y semántica verificada

| Familia | Historia verificada | Publicación y significado |
|---|---|---|
| Internos | Desde enero de 1996 | XLSX histórico y ocho páginas anuales enlazadas. Valores **mensuales publicados**, ARS/TN por producto y plaza. No se derivan del diario. |
| Pizarra / Cámara | Desde 02/01/2018 | 2.128 enlaces diarios publicados. Cotizaciones provisionales sujetas a ajuste; ARS/TN por producto y cinco plazas. Cero no significa un precio negociado. |
| FAS | Desde 16/01/2007 | Exportación pública XLSX de D.E.C. Se conserva el grano fecha/producto/régimen. ARS/TN corroborados contextualmente para siete granos; los dos aceites permanecen **Sin identificar** en moneda y unidad. |
| FOB SSPM | 04/01/1993–21/01/2025 | CSV oficial 358.1 con 58 series descriptivas en USD/TN. Son **índices de fecha calendario** publicados, incluidos fines de semana. No son fechas de emisión de circulares MAGyP confirmadas. |
| Futuros externos | Desde 02/01/1995 | 217 matrices anuales enlazadas de Chicago/Kansas (1995–2025) e informes diarios enlazados de 2021/2024/2026. Observación y vencimiento se conservan separados. USD/TN. |

Descubrimiento: [índice oficial de granos MAGyP](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/granos/index.php).
Sólo se lee el prefijo de precios; se detiene al comienzo de estadísticas ajenas
al alcance. No se generan URLs diarias mediante patrones. Los enlaces de ventanas
JavaScript se extraen como literales publicados, sin ejecutar código externo.

FOB: el [catálogo SSPM](https://infra.datos.gob.ar/catalog/sspm/data.json)
identifica la distribución `358.1`, diccionario de columnas, unidad y licencia
CC BY 4.0. Su [CSV](https://infra.datos.gob.ar/catalog/sspm/dataset/358/distribution/358.1/download/precios-fob-oficiales-valores-diarios.csv)
es reproducible. La cobertura real se obtiene del archivo, no del `temporal` del
catálogo, cuyo límite es más antiguo. No se infiere continuidad hasta 2026.

La API FOB actual continúa independiente: posición textual, circular y embarque,
con moneda/unidad no identificadas. **No se mapean** los nombres SSPM a códigos,
NCM o posiciones API. El mercado y tipo de referencia SSPM son distintos, por lo
que el dashboard no los une en una serie ni los promedia con la API.

En futuros, las matrices dicen “promedios mensuales”, pero su contenido incluye
columnas con fechas diarias y filas con vencimientos. Se usan esas cotizaciones;
la columna `Promedio` no se convierte en un día ni se presenta como el precio
mensual del contrato. El tipo `Futuro / histórico publicado` se mantiene separado
de `Futuro / cierre` de los informes diarios, sin equivalencia de cierre inferida.
El año abreviado de una columna se resuelve sólo si coincide con el año explícito
del archivo. No hay contrato continuo ni roll automático.

Las matrices conflictivas de 2021/2024 no se reparan por inferencia: se incorporan
los informes diarios enlazados de esos años con su definición explícita de cierre.
La variante verificada `COTIZACIONES DE CIERRE` / `Dolares Estadounidenses/Tn.` se
normaliza sólo en el contexto a la grafía actual; no se cambian precios, posiciones
ni fechas. El parser corriente conserva sus validaciones originales. Las tablas
físicas FOB de esos mismos informes siguen excluidas del circuito de futuros.

FAS: [exportador oficial DINEM](https://dinem.magyp.gob.ar/dinem_fas.cfas_all.aspx).
La exportación D.E.C. funciona con Edge y controles públicos de fechas. No se
persisten formularios, cookies, perfiles o estado GeneXus. El intento D.E.R.
encontró controles ocultos: no se fuerza ni se usa su historial como vigente;
se conserva el D.E.R. ya existente en su circuito. El status HTTP del manifest
FAS corresponde a la página inicial; el XLSX descargado se valida por contenido.
La publicación advierte un cambio de fórmula de girasol desde 14/02/2019 y una
corrección cambiaria informada desde 14/04/2025. Se conservan flags; no se calcula
variación del girasol entre agregados con conjuntos de regímenes metodológicos
distintos. No se corrigen retrospectivamente precios publicados por cuenta propia.

Las restantes licencias, límites formales y garantías de permanencia no se dan
por documentados. Acceso público no equivale a una garantía contractual de API.

## Arquitectura y trazabilidad

1. `data/magyp/raw/commodities/history/<family>/<capture_id>/`: capturas inmutables
   y manifests. HTTP: proyección de tablas/texto públicos, hash del cuerpo recibido
   y hash de la proyección; XLSX/CSV: archivo recibido. No se guarda HTML de sesión.
2. `data/magyp/normalized/commodities/history/*.jsonl.gz`: registros completos,
   incluidos S/C, blancos, ceros y marcadores originales. Sin convertir moneda.
3. `data/magyp/analytical/commodities/history/*.sqlite`: observaciones deduplicadas
   por ID económico, con payload completo, captura, URL, SHA y localizador de celda.
4. `data/magyp/dashboard/commodities/history/`: diccionarios de series/capturas y
   CSV preparados comprimidos por familia/año, más vistas mensuales. El navegador
   sólo lee estos archivos estáticos y los bundles corrientes; nunca APIs de origen.

RAW, normalizados y SQLite están ignorados por Git. Sólo se versionan shards de
dashboard (cada uno <5 MB), metadatos, código, tests e informes. El diccionario
reconstruye moneda, unidad, producto, mercado, tipo, condición, posición y captura
sin repetirlos cientos de miles de veces. Cada agregado mensual identifica sus
capturas de entrada; la SQLite permite recuperar todas las observaciones y celdas.

Los shards usan hash en el nombre y SHA-256 completo en el índice. Antes de usar
una nueva versión se verifican tamaño, schema, conteos y trazabilidad. El índice
se reemplaza atómicamente al final de cada familia; las familias son independientes.
Una revisión inválida de un recurso previamente aceptado aborta la publicación
de esa familia. Se conserva el índice anterior. Nunca se sustituye con un vacío.

El primer backfill puede excluir archivos inválidos, que quedan individualizados
en `rejected_files`. Los conflictos no se resuelven eligiendo arbitrariamente un
precio. Duplicados con fecha/posición y valor original exactamente iguales pueden
colapsarse; dos valores diferentes rechazan el archivo completo. Fechas imposibles,
fechas que no coinciden con el enlace/año y tablas incompletas se apartan. “No
disponible” y “Sin cotización” tienen estados distintos de un schema incompatible.

## Mensual, diario y actualización corriente

- Internos: valor mensual publicado, sin agregación de precios distintos.
- Pizarra/FAS/futuros: mediana de días con precio positivo de **la misma serie**
  dentro del mes; conserva cantidad de observaciones, mínimo, máximo y media como
  campos separados. Mes parcial, sin interpolar y sin volumen transado inferido.
- SSPM FOB: mediana de los valores del índice calendario, incluidos fines de
  semana publicados. **No equivale a una mediana de ruedas de negociación.**
- Variaciones: mismo mecanismo del bundle corriente, respecto del mes/año exacto
  o de 7/30 días calendario exactos, sin llenar períodos faltantes.
- El bundle corriente tiene prioridad por serie/fecha exactos. Una revisión cero
  o S/C elimina sólo ese día. Los meses afectados se recalculan desde la unión de
  observaciones diarias, con mediana, mínimo, máximo, media y cantidad; nunca se
  promedian dos agregados mensuales ni se borra todo un mes por revisar un día.
  Se comprueba que el detalle descargado tenga todos los días del agregado anterior.
  Se conservan fechas, hashes y capturas de todos los contribuyentes y se recalculan
  las variaciones afectadas y sus sucesores comparables. La mediana usa aritmética
  decimal entera; variaciones con 12 decimales y umbrales de semáforo exactos.
- Internos es una publicación mensual: su revisión se aplica por mes, sin derivarlo
  del diario. Los otros años sin revisiones conservan sus vistas preparadas.
- La prioridad se aplica antes de filtros/KPIs/gráficos, sin promediar subseries.
- El workflow productivo de cinco familias sigue actualizando sus CSV corrientes
  sin depender de RAW históricos. Este cambio no altera sus protecciones ni cron.

El detalle diario se carga por **año de cotización**. Las vistas mensuales permiten
todo el histórico. Esto evita cargar cientos de miles de objetos al abrir cada
fuente. El selector de año es secundario; permanecen controles y visualizaciones.
El vencimiento no determina el eje temporal, los filtros de año ni la frescura.
Monedas/unidades incompatibles permanecen separadas por los controles existentes.

`PRICE_FRESHNESS_STATUS.json` añade cobertura histórica y fuentes efectivas sólo
a Commodities. El éxito histórico se informa anidado como `VALIDATED_BACKFILL`,
separado del estado operativo corriente. Descargar SSPM no convierte un error
de API FOB en `UPDATED`; no cambia su evidencia ni su última captura exitosa.
Los objetos de MCBA, Corrientes y SIO no se modifican por esta ampliación.

## Cutover del histórico local mensual

`COMMODITIES_HISTORY_LEGACY_COMPARISON.json` compara 668 registros, enero de 2020
a agosto de 2026, por mes, producto, plaza, tipo de precio, ARS y TN. El resultado
es **668/668 cubiertos, cero diferencias de precio**. Se aplican sólo alias de
mayúsculas/acentos y el prefijo conocido de plaza; no se convierte ninguna unidad.

El índice autoriza `can_retire_legacy=true` sólo con cobertura completa y precios
comparados iguales. Tras aprobar el cutover final, el archivo manual deja de ser
una fuente del frontend: no tiene carga, selector ni contingencia automática.
Si falla el histórico se conserva el bundle corriente oficial válido; si tampoco
está disponible, se informa la ausencia de datos sin reactivar el archivo manual.
Los originales se conservan en `data/commodities_local_mensual/` para auditoría,
pero `scripts/ci/prepare_pages.py` los excluye del paquete de GitHub Pages.
El reporte de frescura conserva su registro de auditoría con `runtime_active=false`
y ya no necesita leer sus CSV durante la actualización productiva. SIO conserva
exactamente su circuito separado.

El único histórico local mensual comparado corresponde a internos. No reemplaza
Pizarra, FAS, FOB o futuros; el reemplazo para esas familias no es aplicable.

## Ejecución reproducible

Python 3.11+; dependencias:

```powershell
python -m pip install -r scripts/magyp/grains/requirements-history.txt
python scripts/magyp/grains/history_acquire.py --source discover --allow-web
python scripts/magyp/grains/history_acquire.py --source future-catalog --allow-web
python scripts/magyp/grains/history_acquire.py --source internal --allow-web
python scripts/magyp/grains/history_acquire.py --source board --allow-web
python scripts/magyp/grains/history_acquire.py --source futures --allow-web
python scripts/magyp/grains/history_acquire.py --source futures --futures-daily --from-date 2021-01-01 --to-date 2021-12-31 --allow-web
python scripts/magyp/grains/history_acquire.py --source futures --futures-daily --from-date 2024-01-01 --to-date 2024-12-31 --allow-web
python scripts/magyp/grains/history_acquire.py --source futures --futures-daily --from-date 2026-01-01 --to-date 2026-10-21 --allow-web
python scripts/magyp/grains/history_acquire.py --source fob --allow-web
```

Sólo FAS necesita dependencias browser y Edge/Chromium; preferencia Edge instalado:

```powershell
python -m pip install -r scripts/magyp/requirements-browser.txt
python scripts/magyp/grains/history_acquire.py --source fas --fas-regime D.E.C. --from-date 2007-01-01 --to-date 2026-10-21 --allow-web
python scripts/magyp/grains/history_build.py --source all --as-of 2026-10-21
python scripts/magyp/grains/history_validate.py
python scripts/magyp/build_price_freshness.py --commodities-history-only
python -m unittest discover -s tests/magyp_common
node --test tests/magyp_frontend/*.cjs
git diff --check
```

Fechas de ejemplo de la captura validada, no una promesa de publicaciones futuras.
Descargas de archivos: tres requests como máximo en vuelo, inicios separados por
al menos un segundo, sin retries; detener nuevas solicitudes ante 401/403/429.
Límite explícito de recursos y tamaños. URLs ya capturadas se omiten para reanudar;
`--refresh` permite una nueva captura inmutable de los enlaces seleccionados.
Los CSV/XLSX masivos se obtienen una sola vez, no mediante miles de consultas FOB.

La ampliación de historia es un comando reproducible controlado; **no se activa
un backfill completo en cada corrida diaria** ni un nuevo cron. Al aparecer nuevos
archivos se redescubren enlaces y se procesa la familia elegida. Antes de integrar,
validar todos los shards. Mantener generaciones publicadas anteriores durante su
vida de caché; no eliminar archivos referenciados por índices todavía servidos.

Consultar `data/magyp/reports/COMMODITIES_HISTORY_INVENTORY.json`/CSV, el catálogo de
enlaces, registros de descarga y la comparación detallada. Los huecos de origen y
archivos apartados permanecen explícitos; no se sustituyen por otras metodologías.
