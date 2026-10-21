# Corrientes MAGyP — decisión de integración

## Revisión ampliada de fuentes oficiales — 21/10/2026

**Resultado: BLOCKED_BY_SOURCE.** Aplicada `docs/DATA_SOURCE_POLICY.md`.
No se encontró una publicación oficial vigente, reproducible y semánticamente
compatible que permita sustituir o complementar productivamente la carga manual.
Esto expresa el resultado de la búsqueda dirigida, no inexistencia universal.

| Proveedor / evidencia oficial | Resultado de esta revisión |
|---|---|
| [Estadística provincial: publicaciones económicas](https://estadistica.corrientes.gob.ar/publicaciones/economia) y [datos abiertos económicos](https://estadistica.corrientes.gob.ar/datosabiertos/datasets/1) | Portales accesibles. Publicaciones 2026 de indicadores/IPC/OPEX; el catálogo económico ofrece PBG e IPICorr. No se encontró serie mayorista frutihortícola del mercado. Fecha de una publicación estadística no equivale a fecha de cotización. |
| [Subsecretaría de Comercio provincial](https://comercio.corrientes.gob.ar/) y su [nota institucional sobre controles de precios](https://comercio.corrientes.gob.ar/noticia/la-provincia-inspecciona-verdulerias-y-fruterias-de-la-capital-para-evitar-abusos-de-precios?region=true) | Páginas indexadas de controles y consumo; la apertura directa del portal agotó el tiempo. No se identificó API, tabla o descarga de cotizaciones mayoristas del mercado. No se reintentó. |
| [MAGyP: frutas](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/frutas/index.php) | Un GET local controlado: HTTP 200, 43518 bytes, 0,266 s, 21/10/2026 14:37:12 UTC. Sigue enlazando exactamente `http://www.mptt.gov.ar/site13/index.php/preciosmercado`. No es una API propia de MAGyP. |
| Ministerio de Producción / mercado concentrador: destino publicado por MAGyP | No apareció un enlace sucesor verificable. No se volvió a solicitar el destino antiguo: el error DNS corresponde a la evidencia previa del 06/10, no a una nueva prueba de hoy. Sin fecha de publicación actual comprobable. |
| [Datos abiertos de la Municipalidad](https://datos.ciudaddecorrientes.gov.ar/dataset?_tags_limit=0&groups=economia&organization=subsecretaria-de-finanzas) | Catálogo indexado con CSV de combustibles, IPC y otros indicadores; ninguno de los recursos revisados corresponde a precios mayoristas frutihortícolas del mercado. No son equivalentes. |
| [CFI: antecedente institucional del mercado](https://biblioteca.cfi.org.ar/wp-content/uploads/sites/2/2017/06/51021.pdf) | Documento de 2008 sobre relevamientos de ingresos y precios máximos/mínimos. No acredita una exportación de observaciones vigente ni continuidad del servicio. |
| [INTA: antecedentes de investigaciones](https://repositorio.inta.gob.ar/bitstream/handle/20.500.12123/8968/INTA_CRCorrientes_EEABellaVista_Molina_NA_Marketing_hort%C3%ADcola_MCBA_sand%C3%ADa.pdf?isAllowed=y&sequence=1) y [UNNE: frutilla](https://revistas.unne.edu.ar/index.php/rfce/article/download/4367/4093/13912) | Estudios de limón/frutilla referidos a 2004–2018; no se confunden sus períodos de estudio con una base descargada y validada ni con actualización corriente. No sustituyen el período productivo 2024–2026. |

Queda prohibido usar MCBA filtrado por procedencia Corrientes como sustituto
del Mercado de Corrientes: procedencia no equivale a mercado relevado.
Tampoco se incorporaron precios minoristas, programas de precios de supermercados,
declaraciones periodísticas ni gráficos académicos como cotizaciones equivalentes.
No se enumeraron URLs ni se insistió en endpoints caídos. Sin evidencia de una
fuente vigente candidata, no se descargó un histórico masivo ni se creó un inventario
anual con fechas o filas inventadas.

### Comparación y decisión productiva

La fuente productiva vigente sigue siendo la carga manual del archivo
`MARTIN MICELLI 26-08-2026.xlsx`, preservada en la base integrada existente.
Su último dato es el **25/08/2026**, no la fecha del nombre del archivo.

- Se releyó la base sin modificarla: 46587 filas Corrientes, 46413 observaciones
  con precio positivo y fecha válida no futura; 400 fechas entre 29/12/2024 y
  **25/08/2026**. Se mantienen los controles existentes de 115 filas futuras,
  3 fechas inválidas y 56 precios no positivos/no parseables.
- Dimensiones existentes: 171 etiquetas de especie, 19 procedencias/localidades,
  69 envases; sin variedades informadas. Unidad original `$/bulto`; moneda vacía.
  Los precios/kg son conversiones existentes por peso, no una unidad atribuida
  a una nueva fuente. No se normalizaron etiquetas ni se deduplicó la base.
- Nueva fuente: cero observaciones recuperadas y validadas para integración;
  fecha más reciente, frecuencia real, histórico descargable, moneda/unidad,
  estabilidad, licencia y automatización **no verificables** para un sustituto.
- Comparación de precios entre proveedores y cutover: no proceden. Períodos
  reemplazados: ninguno; la fuente manual sigue siendo necesaria en su totalidad.
- El dashboard ya indica `STATIC` / «Fuente estática», último dato 25/08/2026,
  `automatic_update=false` y sin fecha de actualización exitosa inventada.
  Se conserva íntegro el módulo y su funcionalidad. No se crea un workflow ni un
  CSV vacío. No se modifica ningún pipeline, dato productivo ni frontend.
- Validación: 5 tests Python existentes de investigación Corrientes, 2 tests
  frontend de frescura y `git diff --check` aprobados.
  Los antecedentes y la comprobación de preservación del 06/10 se conservan debajo;
  sus fechas y resultados no se presentan como una nueva adquisición.

Para reabrir el tema hace falta evidencia nueva: publicación o exportación oficial
fechada del mercado de Corrientes, con producto, precio, moneda/unidad y acceso
reproducible. Hasta entonces se cierra esta revisión, sin más iteraciones al
endpoint antiguo. El cierre formal versiona únicamente esta documentación;
no autoriza cambios productivos, merge ni deploy.

## Evidencia previa — 06/10/2026

Comprobación acotada del 06/10/2026, rama `codex/magyp-data-platform-mcba`, HEAD `9452166`. El estado inicial estaba limpio; la integración MCBA aceptada y todos los archivos existentes se preservaron.

**Clasificación: D — NO_UTILIZABLE actualmente para esta integración.**
El enlace institucional confirmado no permite recuperar datos. No se clasifica C: no se recuperó una publicación fechada que demuestre desactualización. Tampoco se afirma ausencia universal de fuentes correntinas.

1. **Fuente encontrada:** los índices oficiales MAGyP de [frutas](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/frutas/index.php) y [hortalizas](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/hortalizas/) enlazan a `http://www.mptt.gov.ar/site13/index.php/preciosmercado`. Es una referencia al proveedor provincial; no una API alojada en MAGyP. El portal actual no expuso un enlace Corrientes en su HTML examinado.
2. **Última publicación MAGyP/proveedor:** no verificable. El título del enlace y el año del portal no prueban fecha de las cotizaciones. Última observación válida de la **base actual local**: 25/08/2026; archivo origen `MARTIN MICELLI 26-08-2026.xlsx`. La fecha del nombre del archivo no se usa como fecha de precios.
3. **Frecuencia:** el índice de frutas denomina el enlace “Precios Diarios”; periodicidad efectiva no comprobable. La base actual tiene registros fechados en 400 fechas, entre 29/12/2024 y 25/08/2026; fecha_precision no informada en esas filas. El frontend mantiene su interpretación y agregaciones existentes.
4. **Granularidad:** campos MAGyP/proveedor no recuperados; no se inventan dimensiones. Legacy tiene fecha, rubro, especie, procedencia, localidad, envase, peso de bulto y precios/unidades originales y derivados. Entre registros válidos no futuros: 171 etiquetas de especie, 19 procedencias/localidades y 69 envases; variedad vacía. Calidad/tamaño/grado no se incorporan por no haber evidencia.
5. **Adquisición automatizable:** **no validada ni utilizable actualmente**. Se hicieron 5 GET controlados: tres páginas MAGyP HTTP 200; destino provincial HTTP y HTTPS con error DNS `gaierror`. Límite 500 KB por respuesta, timeout 15 segundos, sin retry, navegador, sesión, descarga histórica ni enumeración de endpoints. La comprobación se puede repetir, pero eso no constituye un pipeline de cotizaciones.
6. **Comparación:** imposible comparar fechas/precios/unidades/presentaciones entre fuentes: cero cotizaciones recuperadas de la ruta MAGyP. Se registró únicamente la referencia local: 46.587 filas Corrientes, 46.413 con precio observado positivo y fecha válida no futura; 46.409 comparables por kg según campos existentes. Se contabilizan por separado 115 fechas futuras, 3 inválidas y 56 precios no positivos/parseables. Nada se deduplicó ni corrigió.
7. **Reemplazo:** ninguno justificado. `CTES.` en MCBA es procedencia y no una cotización del Mercado de Corrientes; no se utiliza como sustituto ni relleno.
8. **Legacy:** se mantiene **como fuente principal actual**, además de respaldo histórico para una transición futura. Unidad original observada `$/bulto`; precios por kg continúan siendo conversiones existentes por peso del envase. Columna moneda vacía: no se agrega automáticamente ARS ni se redefine la unidad. Se preservan base, Excel y series.
9. **Integración realizada:** diagnóstico reproducible, evidencia de solicitudes y decisión documentada. No se cambiaron app.js, index.html, estilos, CSV productivos ni configuración; no se creó CSV MAGyP vacío ni workflow productivo sin fuente viable. Filtros, KPIs, evolución, rankings, semáforo y tablas permanecen intactos.
10. **Verificaciones:** cinco tests offline específicos del diagnóstico (clasificación, límites de URL, exclusión de estado privado, lectura conservadora de legacy y dry-run). Verificación SHA-256 de 268 archivos preexistentes, incluidos MCBA RAW/NORMALIZED/ANALYTICAL, frontend, bases y demás pipelines. No hubo cambios de comportamiento que requieran rehacer el navegador MCBA.
11. **Bloqueo real:** obtener del proveedor provincial el enlace vigente o una exportación oficial fechada accesible y su definición de precio/unidad. Con esa evidencia se podrá decidir principal/complementaria, comparar una ventana común y preparar el pipeline con las garantías existentes. No se activa cron.

## Archivos y reproducción

- `scripts/magyp/investigate_corrientes.py`: diagnóstico; por defecto dry-run sin red ni escrituras.
- `CORRIENTES_MAGYP_SOURCE_CHECK.json`: requests públicos, resultado y referencia local.
- `CORRIENTES_MAGYP_PRESERVATION.json`: resultado de preservación de archivos.

```powershell
python scripts/magyp/investigate_corrientes.py --allow-web --as-of 2026-10-06
python -m unittest discover -s tests/magyp_common -p test_corrientes_investigation.py -v
```

No se hicieron commit, push, merge ni deploy. No se modificaron MCBA, Commodities, SIO, FOB, Cantidades ni Carnes.
