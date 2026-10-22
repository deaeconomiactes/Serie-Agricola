# Carnes: fuentes y plataforma de datos

Revisión: 22/10/2026. Política obligatoria: [DATA_SOURCE_POLICY.md](DATA_SOURCE_POLICY.md).
Esta entrega incorpora datos y contratos reproducibles; no crea la UI definitiva,
no modifica otros módulos ni activa tareas programadas. No reemplaza series existentes.

## Fuentes verificadas y primera versión recomendada

| Familia | Publicación integrada | Cobertura verificada | Grano y limitaciones |
|---|---|---|---|
| Faena | SAGyP / SSPM, conjunto 40 | Anual 1980–2025; mensual enero 1980–agosto 2026 | Nacional, especie, cabezas publicadas. Anual y mensual separados. |
| Producción | SAGyP / SSPM, conjunto 40 | Anual desde 1980; bovina mensual desde enero 1998 hasta agosto 2026 | Toneladas publicadas; base de peso no identificada en el diccionario SSPM. No asignar RCH. |
| Faena bovina detallada | MAGyP / DNCCA, XLSX anuales y avance | 2018–2025 y enero–septiembre 2026 | Provincia, establecimiento, usuario de faena, categoría, dentición, mes, acumulados y participaciones publicados. Tablas redundantes identificadas. |
| Producción bovina y peso medio | MAGyP / DNCCA, informe de producción | Enero–septiembre 2026 | Categoría/dentición; toneladas res con hueso y kg res con hueso. Valores provisorios y acumulados separados. |
| Precio de hacienda | Indicadores mensuales bovinos MAGyP archivados | Enero 1998–agosto 2019 | Novillo, Mercado de Liniers, ARS/kg vivo y USD/kg vivo publicados; no empalmar con MAG Cañuelas. Fuente finalizada. |
| Peso, producción y exportaciones históricos | Mismo CSV de indicadores MAGyP | Enero 1998–agosto 2019 | Peso res y novillo; producción en miles de toneladas RCH; exportaciones en toneladas equivalentes RCH, miles USD y USD/t RCH. Magnitudes separadas. |

Los límites y cantidades exactos por familia, frecuencia, especie, moneda y unidad
están en [CARNES_SOURCE_INVENTORY.csv](../data/carnes/reports/CARNES_SOURCE_INVENTORY.csv)
y su versión JSON. Los límites de cada métrica pueden diferir: un archivo amplio
no demuestra que todas sus columnas cubran el mismo período.

Primera versión recomendada: **faena bovina mensual nacional/provincial y por
categoría**, **producción** y **peso medio**, con paneles independientes. La serie
de precios y exportaciones integrada es histórica y debe identificarse como tal.
No presentar estos archivos finalizados como un precio o exportación corriente.

### Enlaces de origen

- [Catálogo SSPM](https://infra.datos.gob.ar/catalog/sspm/data.json), conjunto 40
  «Faena pecuaria», distribuciones 40.1 y 40.3. Licencia declarada CC BY 4.0.
- [Índice oficial MAGyP / gestión bovina](https://www.magyp.gob.ar/sitio/areas/gestion/bovinos.php?accion=imp).
  Los XLSX se descubren mediante enlaces literales del índice, sin fabricar URLs.
- [Recurso de indicadores mensuales bovinos](https://datos.magyp.gob.ar/dataset/indicadores-mensuales-sector-bovino/archivo/7afe10d1-e9bc-4383-9e3c-c8066bc21f65).
  Se conserva el CSV real enlazado; sus encabezados difieren de algunos alias del portal.
- [Cambio de tipificación bovina](https://www.argentina.gob.ar/normativa/nacional/316048/texto).

Los archivos MAGyP consultados no declaran licencia específica en el recurso
verificado: conservar atribución y revisar términos antes de redistribuciones adicionales.
Acceso HTTP público no equivale a garantía de disponibilidad o licencia irrestricta.

## Fuentes candidatas que no se integran todavía

El inventario incluye candidatos con `rows=null`; no son datasets descargados.

- **Mercado Agroganadero:** HTML institucional con consultas de fecha. Tres muestras
  devolvieron datos (09/12/2005, 01/06/2010 y 21/10/2026). Son fechas muestrales,
  no extremos demostrados de un histórico completo. La tabla presenta mínimos,
  máximos, promedio, mediana, cabezas, kilos e importes; la evidencia inspeccionada
  no declara suficientemente moneda/unidad del precio. No se infiere ARS/kg vivo
  por aritmética. Falta validar diccionario, condiciones de automatización y
  continuidad Liniers/Cañuelas antes de integrar precios corrientes.
- **IPCVA:** informes minoristas mensuales; no equivalen a precios mayoristas ni
  hacienda. Pendiente una fuente tabular estable con geografía/metodología validadas.
- **INDEC COMEX:** cobertura declarada desde marzo 2018, NCM/destino y USD/kg
  producto. No se reprodujo una exportación automática estable; kg producto no
  equivalen a toneladas res con hueso. No inventar equivalencias NCM.
- **MAGyP, información sectorial:** tableros PDF con conceptos diferentes de
  precios/exportaciones. No usar la fecha del título como última observación ni
  sustituir un precio nominal por una referencia constante o un índice.
- **SENASA:** existencias y movimientos bovinos/bubalinos revisados. Stock o
  movimientos no sustituyen faena; no se incorporan como otra medida del mismo flujo.
  Referencias: [existencias](https://datos.magyp.gob.ar/dataset/senasa-existencias-bovinas)
  y [estadísticas bovinas SENASA](https://www.argentina.gob.ar/senasa/mercados-y-estadisticas/estadisticas/animal-estadisticas/bovinos/bovinos-y-bubalinos-sector-primario).

No se encontró todavía una fuente corriente de precios mayoristas de carne con
contrato estructurado y unidad suficientemente verificados. Esto limita esa familia,
no impide publicar las familias físicas que sí están validadas.

## Arquitectura y contratos

```
Índices oficiales → catalog/sources.json
GET público → raw/<source>/<timestamp_UTC+id>/response.* + manifest.json
→ normalized/<source>/<capture>.jsonl.gz
→ analytical/<source>/<capture>.csv.gz
→ dashboard/<source>-<family>-<frequency>-<year>-<hash>.csv.gz
→ dashboard/index.json (publicación atómica por fuente)
```

RAW es inmutable: archivos exclusivos, SHA-256, URL, método, parámetros públicos,
HTTP status, MIME, encoding, bytes, duración, captura UTC y versión. No se guardan
cookies, tokens, sesiones ni headers privados. RAW/NORMALIZED/ANALYTICAL están fuera
de Git; los datos originales completos permanecen disponibles localmente para auditoría.
`encoding` registra sólo el charset declarado en HTTP; no se asigna encoding de
texto a XLSX. Las capturas iniciales conservan inmutable el fallback UTF-8 de su
manifest original: ese campo no describe el contenido binario ni interviene en su lectura.

NORMALIZED conserva valor textual y decimal publicado, fecha de observación y
fin de período, frecuencia, especie, categoría original, dentición, geografía,
mercado, tabla, entidad, moneda, unidad original, base de peso, metodología y
flags. Identifica celdas/filas originales mediante `source_locator`; incluye
`capture_id`, `raw_sha256`, fuente y URL. `observation_id` identifica el grano
económico incluyendo fuente/tabla; `record_id` incorpora captura y hash.

ANALYTICAL conserva ese grano: no suma tablas, no fabrica promedios o conversiones.
La capa DASHBOARD prepara únicamente observaciones nacionales/provinciales y
categorías publicadas. El detalle de establecimientos/usuarios queda en las capas
completas; no se redistribuye innecesariamente información de entidades en frontend.
El índice enlaza fragmentos comprimidos por familia/frecuencia/año y sus hashes,
conteos y fechas. Un futuro consumidor debe cargar sólo los fragmentos requeridos.
El frontend actual no los consume todavía.

Las tablas de totales, provincias, establecimientos y usuarios son vistas
redundantes de la publicación: **no sumarlas entre sí**. Los acumulados incompletos
se identifican `year_to_date` con `period_end`; un acumulado enero–septiembre no
es una observación anual completa. No recalcular el peso medio desde totales.

## Calidad y exclusiones documentadas

- Schemas, hojas y encabezados estrictos; fechas/valores finitos no negativos;
  duplicados económicos rechazados; faltante distinto de cero. Un `observed`
  vacío es inválido. No se redondean cabezas fraccionarias publicadas.
- 2018 declara bovinos **y bubalinos**. No atribuir esos totales sólo a bovinos.
- Cambio de categorías en 2019: categorías antiguas por peso/sexo y nuevas por
  sexo/dentición conservan metodología diferente, sin puente inventado.
- 2019 `POR ESTABLECIMIENTO!Q3` dice `ACUMULADO 2020` aunque el archivo y sus meses
  corresponden a 2019. Se excluye esa columna contradictoria, con flag y RAW íntegro.
- 2020: dos grupos de establecimientos con identidad repetida y valores distintos
  (422: filas 216/270; 47: 219/226). Se ponen en cuarentena 52 celdas de esos grupos,
  no se suman ni se fabrican identificadores. Flags con rangos exactos acompañan
  el archivo; provincias/categorías permanecen independientes y válidas.
- 2021 usa `TOTAL AÑO 2021`; sólo se acepta año coincidente y doce meses completos.
- Fórmulas XLSX sin valor cacheado permanecen faltantes con fórmula original y flag;
  el pipeline no ejecuta fórmulas ni trata el faltante como cero.
- SSPM: metadatos temporales del catálogo están desactualizados; mandan las fechas
  validadas dentro del CSV. Toneladas sin base de peso documentada siguen sin identificar.
- SSPM aves/cabezas: escala pendiente de verificación. Se preserva en RAW y capas
  completas con `bird_count_scale_requires_validation`; se excluye de DASHBOARD.
  No se multiplica por mil por conjetura.
- El inventario cuenta **celdas/observaciones**, incluyendo faltantes y acumulados,
  no animales únicos. `observed_rows` distingue valores presentes; no sumar los
  conteos del inventario como si fueran un total de faena.

## Disponibilidad, atomicidad y operación

Un timeout/HTTP no disponible genera `SOURCE_UNAVAILABLE`, preservando la última
publicación válida. Un catálogo inaccesible permite reutilizar sólo un catálogo
anterior estructuralmente validado; un schema desconocido genera `PIPELINE_ERROR`.
Fuentes independientes siguen procesándose. Un error de parseo/dato/hash no
reemplaza la entrada válida del índice y produce salida no exitosa.

Se valida cada fragmento antes de reemplazar el índice; un único escritor adquiere
lock exclusivo. Archivos nuevos no referenciados por el índice nunca se consideran
publicados. Hash del cuerpo, tamaño, esquema, conteos y trazabilidad se revalidan
sin red. Reprocesar la misma captura es idempotente. Una nueva captura conserva
las anteriores, incluso si el proveedor revisa cifras.

No hay cron ni workflow activado en esta entrega. Se verificó HTTP directo local
en Windows; no se presume idéntica disponibilidad desde GitHub-hosted Linux.
La captura inicial realizó 16 GET públicos controlados, sin retries, sin enumeración
masiva de fechas y sin navegador. No se invocaron APIs privadas.

## Ejecución

Desde la raíz, con Python 3.11 o posterior:

```powershell
python -m pip install -r scripts/carnes/requirements.txt
python scripts/carnes/pipeline.py discover --allow-web
python scripts/carnes/pipeline.py run --allow-web
python scripts/carnes/pipeline.py build
python scripts/carnes/pipeline.py inventory
python scripts/carnes/validate.py
python -m unittest discover -s tests/carnes -v
```

`discover` consulta índices y registra el catálogo; `run` descubre, captura y construye.
No ejecutar ambos seguidos si sólo se necesita una actualización: `run` ya descubre.
`build` e `inventory` trabajan con los RAW locales, sin requests. `--source <id>`
acota el procesamiento; `--data-root <directorio>` permite una prueba aislada.
Sin `--allow-web`, comandos de red son dry-run. Hay límite de 24 solicitudes por
ejecución, pausa de un segundo y límites de tamaño; nuevos archivos que superen
el presupuesto requieren un backfill explícito en lotes, nunca un loop ilimitado.

Las dependencias XLSX se fijan en requirements. Los tests usan fixtures sintéticos,
sin acceso a internet. La actualización operativa está en
`data/carnes/reports/CARNES_UPDATE_STATUS.json`; las series finalizadas se distinguen
mediante `HISTORICAL_ENDED`, no se clasifican como fallidas por su antigüedad.

## Límites para la UI futura

Mantener familias, especies, fuentes y frecuencias separadas; no crear un KPI
global. Mostrar fuente, cobertura, último dato, captura, moneda/unidad y estado.
No empalmar archivos SSPM/MAGyP o histórico/corriente sin validación de solapamiento
y metodología. No convertir kg producto a RCH, monedas ni escalas por inferencia.
Esta entrega prepara datos para esa decisión y no cambia el dashboard existente.
