# SIO: granularidad transaccional y límites de interpretación

Implementación local del 23/10/2026; aplica DATA_SOURCE_POLICY.md y atiende A07 de
DASHBOARD_INSTITUTIONAL_AUDIT.md. No adquiere fuentes nuevas ni reconstruye
contratos, rectificaciones/anulaciones o su última instancia.

## Evidencia disponible

Entrada productiva: `data/commodities_sio/dashboard/COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv`.
Contiene **590 eventos**, **590 IDs distintos**, 38 fechas, 8 etiquetas de producto,
39 textos de lugar de entrega, 322 procedencias, ARS/USD y TN. El tipo de precio
observado es Precio Hecho. Son snapshots observados, no la totalidad del mercado.

Los 590 eventos tienen fecha, precio positivo, volumen, lugar y captura registrados.
**Condición comercial, pago y tipo de operación no se conservaron en la memoria
histórica: 590 faltantes en cada campo**. No se rellenan desde otra operación ni
se confunden con Compraventa/Canje o con el evento Contrato/Rectificación/Anulación.
Los eventos disponibles incluyen 571 Contrato, 15 Rectificación y 4 Anulación;
tener precio positivo no demuestra vigencia contractual.

La auditoría del 22/10 documentó 103/207 filas diarias con múltiples lugares.
Al iniciar esta implementación, main tenía **106/212**: la actualización corriente
había agregado observaciones. La comparación usa el baseline de main, no fuerza
el conteo histórico a 207.

## Grano anterior y problema

- Diario: fecha, producto, moneda, unidad, tipo de precio, condición y fuente;
  lugares almacenados como una lista dentro del agregado.
- Mensual: omitía también condición comercial.
- Últimos y semáforo perdían esas separaciones; el frontend indicaba Sin plaza.
- Se usaban medianas de agregados distintos para un KPI global. El ponderado por
  volumen podía representar sólo los eventos con volumen, sin advertir cobertura.

## Grano nuevo: `sio-transactions-v2`

`series_id` es SHA-256 de la tupla, en orden explícito en `scripts/sio/grain.py`:

```text
producto + moneda + unidad + tipo_precio + condicion_comercial
+ lugar_entrega + precio_puesto_en + procedencia + condicion_pago
+ tipo_operacion + operacion/evento + calidad + fecha_entrega
+ fuera_de_termino + fuente
```

Clave diaria: fecha de concertación + series_id. Clave mensual: año-mes de
concertación + el mismo series_id. Identidad independiente de precio/captura.
El rango de entrega jamás sustituye la fecha de observación.

Se obtienen **494 series por dimensiones informadas**, **529 filas diarias**,
**513 mensuales**, **494 últimos** y **513 de semáforo**. Los 590 eventos se
reconcilian una vez en diario, mensual y semáforo. Últimos conserva sólo la última
observación de cada serie, no pretende contener todos los eventos históricos.

Una serie no certifica igualdad de condiciones que la fuente histórica no
registró. Los faltantes quedan vacíos, con quality_flags y advertencia visible.
Información nueva de condición/pago genera su propia serie; no se pega a un
histórico con condiciones desconocidas.

El texto completo de lugar se conserva, incluidos “En origen”/“En destino”. Un
campo auxiliar identifica únicamente ese sufijo literal. **No se interpreta
como equivalente al campo independiente precio_puesto_en**, ni se descompone
una procedencia concatenada en provincia/localidad sin evidencia adicional.

## Estadísticas y variaciones

- Conteo de eventos con precio positivo, mediana, promedio descriptivo, mínimo y máximo.
- Volumen total sólo si todos los eventos tienen volumen finito no negativo y
  unidad comparable a la unidad de precio. Un cero explícito sigue siendo cero.
- Con volumen faltante, negativo o en otra unidad: total y ponderado vacíos;
  volumen_conocido y conteo válido identifican la cobertura parcial.
- Ponderado sólo con cobertura completa y volumen total positivo; no se usa en
  un KPI como precio único de plaza.
- Ceros/faltantes de precio no fabrican observaciones; quedan cuantificados en
  el reporte. No se insertan días o meses sin publicación.
- Mensual significa **agregación derivada de operaciones/eventos SIO**, no precio
  mensual oficial. Mes previo es el mes calendario precedente, con igual serie.
- Variaciones de 7/30 días usan última observación disponible a esa distancia o
  anterior y la misma identidad; no interpolan. Interanual compara mismo mes.
- Las variaciones describen eventos de composición posiblemente cambiante incluso
  dentro de dimensiones informadas; no son un índice de contratos homogéneos.

## Control Maíz USD/TN — 09/09/2026

Mediana anterior: **193,45**, calculada sobre cuatro eventos de cuatro lugares.

| Lugar publicado | Procedencia publicada | Eventos | Mediana USD/TN |
|---|---|---:|---:|
| Zona 7En destino | BUENOS AIRESGENERAL VILLEGAS | 1 | 161,73 |
| Zona 5En origen | BUENOS AIRESLIMA | 1 | 191,90 |
| Rosario NEn destino | LA PAMPAREALICO | 1 | 195,00 |
| Rosario SEn destino | SANTA FERUFINO | 1 | 195,00 |

Condición comercial/pago/tipo de operación: desconocidos en esos cuatro eventos.
No se atribuyen condiciones de otra captura. No hay un nuevo “precio de plaza”
193,45 ni una equivalencia entre precios En origen y En destino.

## Preservación y publicación

El builder no modifica el histórico transaccional ni RAW. Agrega trazabilidad a
los CSV: IDs de eventos, capturas registradas, URL institucional, hash de la entrada,
hashes RAW/capture_id cuando existan y flags de calidad. No inventa hashes RAW
para el histórico que no los guardó. Los IDs sin fuente usan fingerprint técnico,
no un identificador contractual supuesto.

El integrador conserva adicionalmente campos ya publicados por GetOperaciones:
tipo, número de operación, pago, calidad, rango de entrega y fuera de término,
archivo/hash RAW y hash de fila. Los IDs antiguos sin esos campos permanecen
desconocidos; no hay recuperación masiva de RAW ni cambios en el criterio de
última instancia. La clave técnica sin ID ahora incluye condiciones y unidades.

CSV de memoria y salidas usan saltos LF para que el hash sea reproducible entre
Windows, Linux y el contenido versionado. La publicación prepara/valida todas
las salidas antes de reemplazarlas; si falla reemplazo, restaura los archivos
anteriores. Un schema inválido, ausencia de histórico o salida vacía devuelve
error sin publicar una muestra como sustituto.

La secuencia, schedule, adquisición y estados del workflow SIO se conservan.
Su allowlist incorpora únicamente el reporte SIO_GRAIN_AUDIT.json para que la
auditoría de grano siga a los CSV. No cambian workflows de otras familias.

## UI y performance

SIO continúa dentro de Commodities, separado de las cinco familias de referencia.
“Lugar de entrega” reemplaza el rótulo de plaza para SIO; faltante real y agregado
histórico con varios lugares tienen etiquetas distintas. Se habilitan condiciones
de operación y procedencia, conservando producto, moneda, unidad, tipo y frecuencia.
Múltiples series piden “Seleccioná una serie”; no calculan mediana de medianas.

Gráficos/ranking/semáforo identifican la serie completa y las tablas permiten
abrir detalle de eventos/capturas. La vista mensual y últimos usan su agregado
mensual, sin sustituirlo por la última cotización diaria. Las otras fuentes
conservan sus cálculos y controles.

Los cinco CSV suman aproximadamente **1,59 MB** para esta captura. El navegador
consume sólo esas salidas, sin cargar la memoria completa, RAW ni analítico.
Se conservan los límites visuales de 6 series en evolución y 10 en ranking y
semáforo, con aviso de filtros. Mayor granularidad aumenta filas, no datos de origen.

## Ejecución y controles

```text
python preparar_commodities_dashboard.py
python -m unittest discover -s tests/sio -v
node --test tests/magyp_frontend/*.cjs
python -m unittest discover -s tests/magyp_common -v
```

Reporte de comparación y perfil: `data/commodities_sio/reports/SIO_GRAIN_AUDIT.json`.
Prueba optativa de navegador: `tests/sio/browser_grain_checks.py`, con Edge/Chrome,
servidor local y salida de capturas fuera de Git. No consulta SIO.

Validación local realizada: **13 tests SIO, 92 frontend y 74 Python comunes**
aprobados; actionlint y git diff --check sin errores. Edge y Chrome comprobaron
filtros, mensual/diario, detalle, selección multiserie y vuelta a Precio interno,
a 1440/1000/900/640 px, sin desbordamiento de página ni errores JavaScript.
La selección de control Rosario N / LA PAMPAREALICO muestra 195 USD/TN.
El histórico original permanece idéntico byte a byte y su SHA-256 coincide con
input_sha256 del reporte. No se modificaron MCBA, Corrientes, Carnes, Cantidades,
las cinco familias MAGyP de referencia ni el reporte global de frescura.
