# Carnes: fuentes y plataforma de datos

Revisión: 11/11/2026. Política obligatoria: [DATA_SOURCE_POLICY.md](DATA_SOURCE_POLICY.md).
Esta entrega incorpora actualización diaria MAG y una sección principal de precios
ganaderos. Las series existentes permanecen independientes; el workflow nuevo sólo
escribe archivos de Carnes.

## Fuentes verificadas y primera versión recomendada

| Familia | Publicación integrada | Cobertura verificada | Grano y limitaciones |
|---|---|---|---|
| Faena | SAGyP / SSPM, conjunto 40 | Anual 1980–2025; mensual enero 1980–agosto 2026 | Nacional, especie, cabezas publicadas. Anual y mensual separados. |
| Producción | SAGyP / SSPM, conjunto 40 | Anual desde 1980; bovina mensual desde enero 1998 hasta agosto 2026 | Toneladas publicadas; base de peso no identificada en el diccionario SSPM. No asignar RCH. |
| Faena bovina detallada | MAGyP / DNCCA, XLSX anuales y avance | 2018–2025 y enero–septiembre 2026 | Provincia, establecimiento, usuario de faena, categoría, dentición, mes, acumulados y participaciones publicados. Tablas redundantes identificadas. |
| Producción bovina y peso medio | MAGyP / DNCCA, informe de producción | Enero–septiembre 2026 | Categoría/dentición; toneladas res con hueso y kg res con hueso. Valores provisorios y acumulados separados. |
| Precios ganaderos por categoría | Mercado Agroganadero de Cañuelas (MAG), reporte diario y gráfico oficial | Desde 17/05/2022 al último dato capturado; seis categorías | ARS/kg vivo atribuido con referencia sectorial SAGyP; provisorio/definitivo desde el encabezado del informe. El detalle estadístico mantiene mínimos, máximos, promedio, mediana, cabezas, importe, kilos y kg/cabeza. |
| I.N.M.A.G. y totales diarios | MAG, totales oficiales por día | Desde 17/05/2022 al último dato capturado | Índice en puntos, cabezas e importe en series separadas. `Falta Cerrar` y valores no calculados se conservan como faltantes publicados. No son promedios por categoría. |
| Precio de hacienda | Indicadores mensuales bovinos MAGyP archivados | Enero 1998–agosto 2019 | Novillo, Mercado de Liniers, ARS/kg vivo y USD/kg vivo publicados; no empalmar con MAG Cañuelas. Fuente finalizada. |
| Peso, producción y exportaciones históricos | Mismo CSV de indicadores MAGyP | Enero 1998–agosto 2019 | Peso res y novillo; producción en miles de toneladas RCH; exportaciones en toneladas equivalentes RCH, miles USD y USD/t RCH. Magnitudes separadas. |

Los límites y cantidades exactos por familia, frecuencia, especie, moneda y unidad
están en [CARNES_SOURCE_INVENTORY.csv](../data/carnes/reports/CARNES_SOURCE_INVENTORY.csv)
y su versión JSON. Los límites de cada métrica pueden diferir: un archivo amplio
no demuestra que todas sus columnas cubran el mismo período.

Carnes presenta como sección principal **Precios ganaderos**, y conserva **faena
bovina**, **producción** y **peso medio** en sus vistas existentes. Liniers y sus
precios históricos siguen identificados como serie finalizada; no se empalman con
los precios corrientes de Cañuelas.

### Cobertura capturada el 11/11/2026

| Categoría del gráfico diario MAG | Desde | Último promedio | Observaciones de promedio | Estado para 11/11/2026 |
|---|---:|---:|---:|---|
| Novillos | 17/05/2022 | 11/11/2026 | 722 | UPDATED |
| Novillitos | 17/05/2022 | 11/11/2026 | 731 | UPDATED |
| Vaquillonas | 17/05/2022 | 11/11/2026 | 734 | UPDATED |
| Vacas | 17/05/2022 | 11/11/2026 | 743 | UPDATED |
| Toros | 17/05/2022 | 11/11/2026 | 722 | UPDATED |
| Terneros | 10/11/2023 | 09/01/2026 | 10 | NO_PUBLICATION |

La cobertura es distinta entre categorías. Terneros no tiene un precio diario
reciente en el gráfico oficial; la UI muestra el 09/01/2026 como última fecha y no
lo presenta como una cotización actual. El informe detallado del 11/11/2026 estaba
marcado definitivo: 200 celdas preparadas, 179 con valor publicado. El I.N.M.A.G.
cerró en 4.103,169 puntos el 10/11; el 11/11 MAG publicó `- *` y su nota indica
que no calcula el índice cuando los novillos no superan 300 cabezas. El reporte de
esa fecha publicó 226 novillos. Ese estado queda como `NO_PUBLICATION`, sin
reemplazar el último índice calculado. Los fragmentos MAG comprimidos sumaron
1.056.109 bytes en esta captura.

### Enlaces de origen

- [Catálogo SSPM](https://infra.datos.gob.ar/catalog/sspm/data.json), conjunto 40
  «Faena pecuaria», distribuciones 40.1 y 40.3. Licencia declarada CC BY 4.0.
- [Índice oficial MAGyP / gestión bovina](https://www.magyp.gob.ar/sitio/areas/gestion/bovinos.php?accion=imp).
  Los XLSX se descubren mediante enlaces literales del índice, sin fabricar URLs.
- [Recurso de indicadores mensuales bovinos](https://datos.magyp.gob.ar/dataset/indicadores-mensuales-sector-bovino/archivo/7afe10d1-e9bc-4383-9e3c-c8066bc21f65).
  Se conserva el CSV real enlazado; sus encabezados difieren de algunos alias del portal.
- [Consulta MAG por categoría](https://mercadoagroganadero.com.ar/dll/hacienda1.dll/haciinfo000502), [totales e I.N.M.A.G.](https://mercadoagroganadero.com.ar/dll/hacienda2.dll/haciinfo000011) y [serie gráfica oficial](https://mercadoagroganadero.com.ar/dll/hacienda2.dll/hacigraf000016).
- [MAG: origen institucional y mercado de Cañuelas](https://mercadoagroganadero.com.ar/dll/acerca-de-mercado.html).
- [SAGyP: información sectorial bovina](https://www.magyp.gob.ar/sitio/areas/bovinos/informacion_sectorial/), consultada para unidad y evaluación de antecedentes mensuales.
- [Cambio de tipificación bovina](https://www.argentina.gob.ar/normativa/nacional/316048/texto).

Los archivos MAGyP consultados no declaran licencia específica en el recurso
verificado: conservar atribución y revisar términos antes de redistribuciones adicionales.
Acceso HTTP público no equivale a garantía de disponibilidad o licencia irrestricta.

## Fuentes candidatas que no se integran todavía

El inventario incluye candidatos con `rows=null`; no son datasets descargados.

- **IPCVA:** informes minoristas mensuales; no equivalen a precios mayoristas ni
  hacienda. Pendiente una fuente tabular estable con geografía/metodología validadas.
- **INDEC COMEX:** cobertura declarada desde marzo 2018, NCM/destino y USD/kg
  producto. No se reprodujo una exportación automática estable; kg producto no
  equivalen a toneladas res con hueso. No inventar equivalencias NCM.
- **SAGyP, información sectorial mensual:** la página publica tableros PDF para
  hacienda, carne minorista y comercio. Se evaluó como contexto histórico. Sus
  categorías compuestas y medidas nominales/constantes no forman una tabla diaria
  comparable por categoría; se mantiene fuera de la serie MAG y no se usa la fecha
  del título como fecha de observación.
- **SENASA:** existencias y movimientos bovinos/bubalinos revisados. Stock o
  movimientos no sustituyen faena; no se incorporan como otra medida del mismo flujo.
  Referencias: [existencias](https://datos.magyp.gob.ar/dataset/senasa-existencias-bovinas)
  y [estadísticas bovinas SENASA](https://www.argentina.gob.ar/senasa/mercados-y-estadisticas/estadisticas/animal-estadisticas/bovinos/bovinos-y-bubalinos-sector-primario).

No se encontró todavía una fuente corriente de precios mayoristas de carne con
contrato estructurado y unidad suficientemente verificados. Esto limita esa familia,
no impide publicar las familias físicas que sí están validadas.

## Arquitectura y contratos

```
Índices oficiales → catalog/sources.json / catalog/mag_prices.json
GET público → raw/<source>/<timestamp_UTC+id>/response.* + manifest.json
→ validación y normalización por contrato de fuente
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
Las salidas MAG conservan la referencia al archivo RAW y captura en cada observación.
El histórico diario contiene la evolución promedio; la tabla detallada mantiene sólo
el último informe por clasificación para que el bundle sea liviano. El frontend carga
fragmentos MAG únicamente al abrir Carnes y por categoría seleccionada.

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

El workflow `.github/workflows/update-carnes-mag.yml` consulta las fuentes MAG en
GitHub Actions y conserva evidencia RAW como artefacto de ejecución. Registra
`UPDATED`, `NO_PUBLICATION`, `SOURCE_UNAVAILABLE` o `PIPELINE_ERROR`; una falta de
publicación, caída o error no reemplaza el último dashboard válido. Sólo los CSV
comprimidos, el índice y el estado liviano pueden llegar a Pages. La ejecución
productiva depende de la autorización posterior del PR y de que Actions esté
habilitado en el repositorio.

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

## Interfaz y operación de precios

Mantener familias, especies, fuentes y frecuencias separadas; no crear un KPI
global. Mostrar fuente, cobertura, último dato, captura, moneda/unidad y estado.
No empalmar archivos SSPM/MAGyP o histórico/corriente sin validación de solapamiento
y metodología. No convertir kg producto a RCH, monedas ni escalas por inferencia.
La vista muestra el último dato y el estado de actualización, selección de seis
categorías, evolución diaria, tabla descargable de las clasificaciones detalladas e
I.N.M.A.G. por separado. Los promedios del gráfico y los estadísticos del detalle
conservan metodologías y localizadores propios. Liniers 1998–2019 sigue bajo
«Series históricas finalizadas».

El endpoint gráfico devuelve observaciones anteriores al inicio del mercado en
Cañuelas; el pipeline excluye las anteriores al 17/05/2022 para no reasignar a MAG
la serie de Liniers. La tabla de MAG no imprime unidad en sus columnas de precio.
`ARS/kg vivo` se atribuye como inferencia a partir del tablero sectorial oficial
SAGyP que identifica precios del Mercado Agroganadero en esa unidad; esa limitación
se declara en `catalog/mag_prices.json` y en la UI.
