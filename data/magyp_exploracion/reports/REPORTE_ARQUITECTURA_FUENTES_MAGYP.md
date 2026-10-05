# Exploración técnica de fuentes oficiales MAGyP

Fecha de relevamiento: **5 de octubre de 2026**. Investigación independiente de la auditoría anterior. Rama: `codex/explorar-apis-magyp`, creada desde `main` actualizado (`fe12c17`). No se implementó ninguna migración ni se alteraron fuentes, bases, interfaz, workflows o pipeline SIO productivos.

## Respuestas a las siete decisiones

1. **¿Podemos reemplazar los Excel del MCBA?** Hay una candidata oficial granular y públicamente accesible: [consulta integral MCBA](https://ssma.magyp.gob.ar/frutas.precios.aspx). Se comprobó consulta en tres días de 2024–2026 y exportación XLSX de un día de 2024. **Todavía no está validada como reemplazo automático**: falta reproducir el transporte GeneXus sin navegador, comprobar continuidad, documentar el promedio y comparar con los Excel mensuales. Recomendación actual: **INVESTIGAR**, con objetivo de **REEMPLAZAR la adquisición manual** si supera esas condiciones. Conservar archivos e históricos originales.
2. **¿Podemos reemplazar Corrientes?** No se encontró una fuente equivalente alojada en MAGyP entre las rutas examinadas. El enlace institucional antiguo apunta a un sitio provincial que no resolvió DNS en la prueba HTTPS. **MANTENER** la fuente actual y consultar al proveedor. `CTES.` en MCBA es procedencia: no representa precios del Mercado de Corrientes.
3. **¿Podemos mejorar/reemplazar SIO?** Sí, se comprobó una grilla pública distinta del snapshot actual, con ID, filtros, dos páginas sin solapamiento, Canje, Anulación y Rectificación. Sin embargo, esa pantalla declara **últimas 72 horas** y una fecha de 2024 devuelve cero. La **exportación pública por fecha de declaración** sí entregó 1.296 registros de soja declarados el 02/10/2024, incluidos eventos y última instancia. **COMPLEMENTAR** con ambos mecanismos; mantener el snapshot como fallback hasta validar contratos, incrementalidad y semántica. No hay evidencia de una API histórica REST completa y estable que permita sustituir todo el pipeline inmediatamente.
4. **¿Qué incorporar a Commodities?** Primero **FOB oficial**, por API documentada y probada; luego **pizarra/Cámara y FAS teórico**, como referencias distintas, y **SIO mejorado/exportación**, conservando los eventos. Mantener precios internos mensuales existentes. Agregados de precios y volumen SIO pueden complementar controles. Futuros y monitor de comercio requieren investigación adicional de definición, permisos y acceso histórico.
5. **¿Máxima granularidad?** MCBA: día × empresa/sucursal × tipo × especie × variedad × procedencia × envase × calidad × tamaño × grado, con precio publicado y códigos disponibles en la grilla. SIO: evento declarado, contrato, concertación, producto/calidad, origen, moneda/precio/toneladas, entrega/pago y marcas de instancia, conservando dos fechas. FOB: día × posición × intervalo de embarque × circular, con versiones de captura. No reducir esas dimensiones en NORMALIZED.
6. **¿Qué actualizar con GitHub Actions?** Una futura integración FOB puede usar GET diario sin sesión; las tablas HTML de internos/pizarra/futuros y los PHP del monitor permiten consultas anónimas acotadas, pero requieren validaciones y parsers. La grilla SIO admite POST JSON anónimo probado, limitado aquí a muestras recientes. MCBA, FAS y exportación SIO necesitan primero validar transporte de sesión/eventos, límites y cadencia. **No se creó ni cambió ningún workflow.**
7. **¿Arquitectura?** RAW inmutable fuera de Git → NORMALIZED sin pérdida y con reglas explícitas → ANALYTICAL con métricas por concepto de precio y tratamiento documentado de eventos → DASHBOARD con CSV livianos por fuente. Publicar sólo tras controles; ante fallas conservar la última salida válida. Los detalles y condiciones están abajo.

## Alcance, evidencia y límites

Se recorrieron enlaces del [portal de mercados agropecuarios](https://www.magyp.gob.ar/mercadosagropecuarios/), sus páginas de [frutas](https://www.magyp.gob.ar/mercadosagropecuarios/frutas.php), [granos](https://www.magyp.gob.ar/mercadosagropecuarios/granos.php) y [carnes](https://www.magyp.gob.ar/mercadosagropecuarios/carnes.php), formularios públicos y JavaScript servido por sus sitios. Las afirmaciones de respuesta HTTP corresponden a requests efectivamente realizados; los endpoints descubiertos en código, sin ejecución, se identifican como tales. La documentación local se utilizó para comparar con el pipeline actual, no para dar por probado un acceso remoto.

El script `explorar_fuentes_magyp.py` no integra datos. Por defecto sólo valida un plan; exige `--allow-web` para consultar. Usa HTTPS y allowlist de hosts, sin credenciales, máximo 10 requests por ejecución, 1,5 segundos entre ellos, timeout de 25 segundos, sin reintentos automáticos y límite de 1,5 MB por respuesta. Para POST de `GetOperaciones` impone páginas 1–2, hasta 50 registros y fechas explícitas de hasta siete días. No recorre paginaciones, rangos históricos ni catálogos completos automáticamente.

Se realizaron **siete POST JSON de muestra** a la nueva grilla SIO, con cinco filas por página; dos exportaciones por interfaz pública, cada una limitada a un día (MCBA y SIO/soja); dos fechas aisladas de la API FOB; GET de páginas, código y pequeños agregados. Las vistas MCBA 2025/2026 se inspeccionaron sin exportar. Los GET de los dos gráficos MCBA terminaron en timeout: no se reintentaron. Una interacción de descarga puede generar varias peticiones del navegador; los límites del script no son un contador global de navegación. No se descargó un histórico masivo ni se iteraron las decenas de miles de páginas MCBA.

Las respuestas de exploración quedaron fuera del repositorio, en un directorio temporal. Los metadatos locales registran URL, método, parámetros no sensibles, UTC de captura, status, tamaño, truncamiento y SHA-256. El estado de seguridad de formularios se elimina de la evidencia HTML; el hash original y el hash almacenado pueden diferir por esa limpieza. Sólo se versionan el explorador, este informe y los dos CSV livianos; `.gitignore` permite explícitamente esos artefactos.

**Disponibilidad observada no equivale a cobertura continua, autorización de redistribución ni SLA.** No se identificaron cuotas documentadas ni licencia específica en las páginas revisadas. No se asume permiso comercial, continuidad de servicio o ausencia de restricciones por el hecho de acceder anónimamente. No se halló OpenAPI para los servicios examinados; FOB sí tiene instrucciones oficiales de consumo JSON.

## Catálogo y criterio de recomendación

`../catalogo_fuentes_magyp.csv` contiene 17 fuentes y 32 atributos: endpoint real o descubierto, método, parámetros, formato, campos, granularidad, frecuencia, historia comprobada/pendiente, dimensiones, moneda/unidad, concepto de precio, volumen/eventos/estado, autenticación, límites, documentación, redistribución, automatización, estabilidad y condiciones de decisión.

`COMPARACION_GRANULARIDAD_MAGYP.csv` compara las mismas 17 fuentes con la referencia actual pertinente. Un producto compartido no demuestra equivalencia entre conceptos de precio.

| Fuente | Recomendación actual | Decisión técnica |
|---|---|---|
| MCBA integral | INVESTIGAR | Candidata a REEMPLAZAR adquisición manual después de validar transporte y equivalencia |
| MCBA diario | COMPLEMENTAR | Control de unidad/precio diario; no sustituye detalle de presentaciones |
| MCBA gráficos | INVESTIGAR | Acceso y metodología pendientes |
| Corrientes: enlace institucional | MANTENER | Conservar fuente actual; enlace provincial no accesible en la prueba |
| SIO snapshot actual | MANTENER | Fallback hasta validar una alternativa completa |
| SIO grilla 72 h | COMPLEMENTAR | Más campos, eventos y paginación observada; no histórico |
| SIO exportación pública | COMPLEMENTAR | Historia de declaraciones y 21 campos; transporte automático pendiente |
| SIO monitor de precios | COMPLEMENTAR | Agregados por fecha/producto/zona; no microdatos |
| SIO volumen | COMPLEMENTAR | Volúmenes por cosecha/concepto; no sumarlos indiscriminadamente |
| Monitor comercio | INVESTIGAR | Indicadores con fechas y universos distintos |
| Precios internos mensuales | MANTENER | Fuente existente; no reemplazarla por SIO o pizarra |
| Pizarra/Cámara | COMPLEMENTAR | Referencia de plaza separada y potencialmente provisional |
| FAS teórico | COMPLEMENTAR | Paridad teórica; regímenes D.E.C./D.E.R. separados |
| FOB oficial API | COMPLEMENTAR | Primera candidata a nueva integración automática |
| Futuros locales | INVESTIGAR | Contrato/posición, significado del precio y derechos pendientes |
| Futuros externos | INVESTIGAR | Separar mercados, productos y vencimientos |
| SIO Carnes | INVESTIGAR | Sólo mapa para etapa futura |

Ninguna fuente recibe **REEMPLAZAR incondicional**: aún no se verificó equivalencia completa con una serie productiva. La condición de reemplazo MCBA y de mejora de adquisición SIO se documenta expresamente; la falta de esa validación no impide el trabajo preparatorio.

## MCBA: mejor candidato granular

### Acceso y esquema

La [consulta integral](https://ssma.magyp.gob.ar/frutas.precios.aspx) responde GET HTML y usa GeneXus con eventos POST al mismo `.aspx`. El código público declara el evento `DOEXPORT`, filtros de fecha `vTFFRUTAS_PRECIOS_FECHA`/`_TO`, filtros dimensionales `_DESCRIPCION`/`_SELS` y rangos numéricos. El estado es dinámico; **no se reprodujo un POST independiente del navegador**. No debe tratarse ese evento como una API documentada.

La grilla expone 23 campos: fecha; empresa y sucursal con ID/etiqueta; tipo, especie, variedad, procedencia, envase, calidad, tamaño y grado con ID/etiqueta; `Kg`; `Promedio x Kg.`. No se observó un ID único de observación. La exportación XLSX tiene **11 columnas**: Fecha, Tipo, Especie, Variedad, Procedencia, Envase, Calidad, Tamaño, Grado, Kg, Promedio x Kg. No conserva los códigos ni empresa/sucursal; capturarlos desde grilla requeriría un acceso automatizado adicional validado.

La página de [promedios diarios](https://ssma.magyp.gob.ar/frutas.preciospromedio.aspx) enlaza detalles [frutas](https://ssma.magyp.gob.ar/frutas.preciospromediof.aspx?Frutas_Precios_Fecha=20261002) y [hortalizas](https://ssma.magyp.gob.ar/frutas.preciospromedioh.aspx?Frutas_Precios_Fecha=20261002). El encabezado expresa **pesos por kilo** y atribuye información a Corporación MCBA. Parte de los rótulos se resuelve al cargar JavaScript: un parser que lea sólo texto HTML inicial puede omitir dimensiones.

### Muestras verificadas

| Fecha consultada | Evidencia | Alcance |
|---|---|---|
| 02/10/2024 | XLSX de un día, 18.920 bytes, 356 observaciones | 281 detalles y 75 filas con variedad `Prom.Esp.`; las 356 tienen `Kg=0` y precio positivo |
| 02/10/2025 | Filtro y 10 filas en interfaz | 37 páginas indicadas; no se recorrieron |
| 02/10/2026 | 10 filas en interfaz y detalles diarios | Frutas/hortalizas, variedades y procedencias visibles |

Ejemplos observados: limón GENOVA/E. RIOS; manzana GRANNY SMI/R. NEGRO; palta HASS/PERU; cebolla OPTIMA/BRASIL; chaucha ESMERALDA/CTES., con presentación, calidad, tamaño y grado. Empresa/sucursal observadas: MCBA, IDs 1/0. No se comprobó que la aplicación cubra otras plazas.

`Prom.Esp.` representa un resumen publicado: debe tener un **grano/serie separado del detalle**. Incluir ambos en una media produce doble conteo. `Kg=0` no prueba volumen cero, peso del bulto ni cantidad comercializada. La muestra no permite recuperar el peso de bulto presente en los Excel tradicionales, ni precios mínimo/máximo. No se verificó ponderación, tratamiento de presentaciones ausentes ni regla de cálculo mensual.

Los enlaces de gráficos `frutas.msddiario.aspx` y `frutas.msdmensual.aspx` se identificaron en código, pero sus GET agotaron 25 segundos. No se infiere de su nombre que exista una API mensual ni que su media reproduzca la de los Excel.

### Condiciones de sustitución

La referencia local incluye PHOR24_K/PFRU24_K y PHOR25_K/PFRU25_K, con precios mensuales `K_ENER...K_DICI`, dimensiones y peso de bulto; el flujo de 2026 ya contiene observaciones diarias. Consultar `data/precios_mayoristas/reports/REPORTE_INTEGRACION_PRECIOS_MCBA_2024_2025.md` para las reglas existentes.

Antes de migrar: reproducir una exportación de un día mediante requests autónomos; verificar rangos y tamaño; comparar muestras mensuales coincidentes de frutas y hortalizas, detalle y resumen; conservar etiquetas originales; validar fechas faltantes y revisiones; confirmar definición de `Kg` y promedio; documentar campos irrecuperables y redistribución. **No reconstruir un promedio mensual con una media diaria arbitraria** ni utilizar esta fuente para completar silenciosamente la serie Excel. La nueva serie debe identificarse como MAGyP/MCBA hasta demostrar equivalencia.

## Corrientes

La página vigente de frutas examinada no expone un servicio equivalente para Corrientes. El [índice oficial antiguo](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/frutas/index.php) contiene “Precios Diarios del Mercado de Corrientes” hacia `http://www.mptt.gov.ar/site13/index.php/preciosmercado`. La prueba de su equivalente HTTPS falló por resolución DNS. No se hicieron reintentos ni búsquedas de endpoints adivinados.

Esto demuestra un enlace institucional, **no una API vigente ni ausencia universal de datos**. Mantener los archivos del Mercado de Corrientes/Martín Micelli usados actualmente y solicitar al organismo provincial una publicación estructurada con cobertura, definición y permisos. No convertir procedencias MCBA en cotizaciones correntinas.

## SIO Granos: recentismo, historia y eventos

### Grilla pública distinta del snapshot

Pantalla: [operaciones informadas](https://www.siogranos.com.ar/consulta_publica/operaciones_informadas.aspx). Endpoint probado:

```text
POST https://www.siogranos.com.ar/consulta_publica/operaciones_informadas.aspx/GetOperaciones
Content-Type: application/json; charset=utf-8
```

No confundirlo con `operaciones_informadas_ultimas.aspx/GetOperaciones`, usado por el pipeline existente. La nueva pantalla dice **últimas 72 hs**.

Payload probado (campos vacíos conservados porque forman parte de la firma):

```json
{
  "pPageSize": "5", "pCurrentPage": "1",
  "fFechaConcertacionDesde": "02/10/2026", "fFechaConcertacionHasta": "02/10/2026",
  "fIDOperacion": "", "fIDTipo": "", "fIDTipoOIV": "", "fIDProducto": "",
  "fCantDesde": "", "fIDCalidad": "", "fIDProvincia": "", "fIDLocalidad": "",
  "fIDMoneda": "", "fPrecioTNDesde": "", "fIDZona": "",
  "fFechaEntregaDesde": "", "fFechaEntregaHasta": "", "fIDCondicionPago": ""
}
```

Respuesta JSON envuelta en `d`: `PageCount`, `CurrentPage`, `RecordCount`, `Items`; cada item tiene `ID` y `Row`. Con cinco filas por página: 1.219 registros declarados por el servidor, 244 páginas; páginas 1 y 2 devolvieron cinco IDs distintos cada una, sin solapamiento. **No se recorrió el resto ni se comprobó consistencia de paginación ante altas concurrentes**. El mismo rango en 2024 devolvió cero; no es evidencia de inexistencia de operaciones históricas.

`Row` contiene 15 posiciones: ID; fecha de concertación; número de operación; evento; Compraventa/Canje; tipo de precio; producto; toneladas; calidad; provincia/localidad; precio/moneda; lugar/condición de entrega; fechas de entrega; pago; fuera de término. Algunas posiciones combinan valores con saltos de línea, por lo que conviene conservar también el vector original.

Filtros de interfaz: `fIDOperacion` 1 Contrato, 3 Ampliación, 4 Anulación, 5 Rectificación, 6 Fijación; `fIDTipo` 1 Compraventa, 2 Canje; producto SOJA 18. En consultas del 02/10/2026 se verificaron Anulación (2 registros informados), Canje (167) y Rectificación (13); sólo se guardaron hasta cinco filas de cada prueba. También se verificó Compraventa. Los IDs internos existen, pero **su estabilidad global y relación con el exportador no están documentadas**.

### Exportación histórica pública

[Formulario exportador](https://www.siogranos.com.ar/consulta_publica/operaciones_informadas_exportar.aspx): GET para formulario; POST WebForms al mismo endpoint, evento `btn_generar_csv`, estado transitorio `__VIEWSTATE`/`__EVENTVALIDATION` (valores nunca versionados). La exportación anónima mediante navegador funcionó; no se probó aún POST autónomo. El script explorador no implementa un exportador WebForms.

La interfaz indica **hasta 180 días por fecha de declaración**. No debe usarse el valor por defecto vacío porque puede exportar una ventana extensa. Parámetros visibles: `txtFechaOperacionDesde/Hasta` (declaración), `txtFechaConcertacionDesde/Hasta`, `ddlOperacion`, `ddlTipo`, `ddlPrecio`, `ddlProducto`, `ddlCalidad`, `txtCantidad`, `ddlProvincia`, `ddlLocalidad`, `ddlMoneda`, `txtPrecioTN`, `ddlLugar`, `txtFechaEntregaDesde/Hasta`, `ddlCondicionPago`, `ddlEsDestinoFinal`.

Muestra: declaración desde/hasta **02/10/2024**, producto **SOJA (18)**, sin filtro de concertación. CSV de 669.230 bytes, **UTF-16 LE sin BOM**, delimitador `;`, con una columna vacía terminal. Las 21 columnas significativas son:

```text
FECHA OPERACION; FECHA CONCERTACION; NRO. OPERACION; OPERACION;
TIPO; PRECIO; PRODUCTO; CANT. (TN); CALIDAD; CALIDAD ADICIONAL;
PROCEDENCIA PCIA; PROCEDENCIA LOCALID.; PRECIO/TN MONEDA;
PRECIO/TN MONTO; LUGAR ENTREGA; FECHA ENTR. DESDE;
FECHA ENTR. HASTA; CONDICION PAGO; ES FINAL; COSECHA;
¿ES ÚLTIMA INSTANCIA?
```

| Comprobación | Resultado de la muestra |
|---|---|
| Registros | 1.296, todos declaración 02/10/2024 y producto SOJA |
| Eventos | Contrato 1.020; Fijación 248; Rectificación 16; Anulación 12 |
| Tipos | Compraventa 1.127; Canje 169 |
| Última instancia | Sí 1.240; No 56 |
| Número de operación | 1.268 distintos: 28 repeticiones adicionales |
| Concertación | Desde 04/10/2021 hasta 02/10/2024, fechas parseadas cronológicamente |
| Precio cero | 14 registros: conservar, no convertirlos en precio válido automáticamente |

**Concertaciones de 2021 declaradas en 2024 no prueban disponibilidad de declaraciones de 2021.** Sólo quedó verificado un día histórico de declaraciones. Los campos de timestamp, cosecha, calidad adicional, última instancia y procedencia separada hacen al exportador más rico que la grilla reciente. El CSV no incluye el ID interno observado en `Items`; no inventar una correspondencia.

`ES FINAL` es condición de destino final, **no vigencia**. `¿ES ÚLTIMA INSTANCIA?` no basta por sí sola para decidir que un contrato sigue activo: una anulación puede ser su última instancia. Número de operación repetido no es duplicado automático; puede representar eventos diferentes. Contrato, ampliación, fijación y toneladas pueden referir al mismo negocio: no sumarlos como contratos independientes.

### Recomendación de mejora

Mantener el pipeline vigente como fallback. Prototipar después, fuera de esta tarea, extracción incremental **por declaración**, con ventanas pequeñas y solapamiento para detectar cambios, guardando cada captura/evento. Usar grilla 72 h como complemento y control, no como histórico. Validar orden, ID, números de contrato entre años, eventos de anulación/rectificación de contratos antiguos, estabilidad de exportación y cálculo de volúmenes/precios vigentes. Los timestamps con `a.m./p.m.` requieren parsing explícito; no asumir zona horaria si no está documentada.

## Referencias y agregados de Commodities

### FOB oficial: acceso más listo para automatizar

La [documentación oficial de precios FOB API](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/fob_oficiales/_archivos/000021_Precios%20Fob%20Api.php) propone consumo JSON y fecha `dd/mm/aaaa`; informa ausencia de publicación sábados, domingos y feriados. Señala problemas técnicos con un host previo y proporciona este enlace alternativo, probado:

```text
GET https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/ws/ssma/precios_fob.php?Fecha=02/10/2026
```

Respuesta `posts[]`, con `fecha`, `circular`, `posicion`, `precio`, `mesDesde`, `añoDesde`, `mesHasta`, `añoHasta`. Content-Type observado `text/html` aunque el cuerpo es JSON: validar por estructura. Dos fechas aisladas: **02/10/2026, 142 registros/43 posiciones**; **04/01/1993, 115 registros/90 posiciones**. La segunda confirma una muestra antigua, no continuidad desde 1993.

La API no devuelve nombre del producto, moneda, unidad, plaza ni tipo de operación. El portal publica referencias FOB en USD/t, pero no basta para asignar ese contrato a todas las posiciones sin un diccionario oficial. Conservar `posicion` textual, circular y período de embarque; **no agrupar únicamente por producto/fecha** ni asumir que la posición es un código NCM completo sin verificar su definición.

El [índice diario DINEM](https://dinem.magyp.gob.ar/dinem_fob.wp_fob_consall.aspx) publica fecha, circular, comunicado y modificación. Para 02/10/2026: circular 2072, comunicado 184, modificación 1; se comprobaron las vistas enlazadas de [precios](https://dinem.magyp.gob.ar/dinem_fob.wp_fob_conslista.aspx?20261002,2072,184,1) y [modificaciones](https://dinem.magyp.gob.ar/dinem_fob.wp_fob_conslistamod.aspx?20261002,2072,184,1). La leyenda establece vigencia para operaciones con cierre de venta en el día publicado y un valor único cuando no se especifica embarque. El JSON no contiene un campo de modificación ni un diccionario de nombres: esos enriquecimientos siguen pendientes. Conservar versiones de captura para detectar revisiones.

**COMPLEMENTAR**. Futuro GET incremental por día hábil con pequeña ventana de revisión y validación de schema/unidades/diccionario; distinguir feriado sin publicación de respuesta vacía inesperada. Es la primera incorporación recomendada; no confundir FOB oficial con un precio negociado, SIO o futuro.

### Precios internos mensuales

El enlace “Precios Internos” del portal devuelve HTML del informe actual (URL completa en catálogo), con meses **enero–septiembre 2026**, productos trigo, maíz, sorgo, soja, girasol y cebada forrajera, y plazas Dársena, Rosario, Bahía Blanca, Córdoba y Quequén según producto. Encabezado: pesos argentinos por tonelada; `S/C` significa sin cotización. Atribución: datos de Bolsa de Cereales de Buenos Aires, publicados por MAGyP.

Aunque una plantilla menciona precios diarios, la tabla comprobada es **mensual**. No redefinir frecuencia por el título técnico de página. Existe enlace XLSX de históricos, no descargado. Los años del pipeline local no se dieron por verificados remotamente en esta exploración. **MANTENER** la fuente mensual existente y su independencia; un parser HTML future debe identificar año/mes/plaza y preservar `S/C` como etiqueta y valor ausente.

### Pizarra / Cámara

Enlace oficial “Precios Cámara” de granos (URL completa en catálogo): GET HTML, seis productos × plazas Buenos Aires, Bahía Blanca, Quequén, Rosario y Córdoba, pesos/tonelada. Último día observado: **01/10/2026**; advertencia de cotizaciones provisorias sujetas a ajuste. En la muestra sólo Rosario presenta cuatro cotizaciones positivas y abundan ceros en otras celdas.

Conservar ceros crudos y una marca de interpretación pendiente; no tratarlos como precios transados ni convertirlos indiscriminadamente sin confirmar metodología. No se encontró rango histórico ni API documentada. **COMPLEMENTAR** con serie identificada por publicador, Cámara/plaza/producto/día; una página replicada por MAGyP no reemplaza automáticamente la serie institucional BCR ni resuelve sus permisos.

### FAS teórico

[Consulta DINEM FAS](https://dinem.magyp.gob.ar/dinem_fas.cfas_all.aspx): GET HTML/GeneXus, filtros de fecha `FAS_TeoHis_Dia`/`_To`, grillas con trigo pan, maíz, cebada cervecera/forrajera, sorgo, soja, girasol y aceites de soja/girasol. En estado público se observan códigos de columnas y valores. Dos regímenes separados **D.E.C. y D.E.R.**: la primera fila observada de D.E.C. es 02/10/2026; D.E.R. es 31/10/2025. No usar el segundo como precio vigente del primero.

El portal expresa la referencia FAS en pesos por tonelada; verificar diccionario por producto antes de extender ese contrato a toda la tabla. Es **teórico**, no transacción, no tiene volumen de operación. Historia completa, exportación y POST autónomo pendientes. **COMPLEMENTAR**, preservando régimen y fecha; no usarlo para rellenar SIO o precios internos.

### Monitor SIO: precio y volumen

[Monitor público](https://monitorsiogranos.magyp.gob.ar/monitorsiogranos.html) y JavaScript servido por el host permiten identificar:

| Endpoint bajo `/v5_ajax/` | Método y parámetro `cosas` JSON codificado en query | Estado |
|---|---|---|
| `cuadrosCotizaciones_min.php` | GET; fechaDesde, fechaHasta, producto, puerto | Probado un día |
| `funcionUltimaFechaParaMostrar_min.php` | GET sin parámetros en la prueba | Probado: fecha 05/10/2026 y hora `:00`, no interpretable como hora válida |
| `volumenesZonas_min.php` | GET; fechaDesde, producto | Descubierto, no ejecutado |
| `preciosZonas_min.php` | GET; fechaDesde, producto | Descubierto, no ejecutado |
| `precioVolumen_min.php` | GET; fechaDesde, producto, pedrozona | Descubierto, no ejecutado |
| `caracteristicasZonasFechas_min.php` | GET; fechaDesde, fechaHasta, IDproducto, IDzona | Descubierto, no ejecutado |
| `sql_data_check_min.php` | GET; fecha, producto, puerto | Descubierto, no ejecutado |
| `tieneDatos_min.php` | GET; fecha | Descubierto, no ejecutado |

Prueba de cotizaciones: fechaDesde/Hasta `02/10/2026`, producto `18` (soja), puerto `23` (Rosario Norte en UI). JSON: `minimos`, `maximos`, `prom`, `modal`; fecha de concertación y valores; mínimo 555.000, máximo 560.000, promedio 559.571, modal 560.000. Moneda/unidad no vienen en la respuesta y la metodología del promedio/modal no se verificó: no declararlo ponderado. Content-Type también es HTML con cuerpo JSON. **COMPLEMENTAR** agregados publicados y controles, sin sustituir eventos.

[SIO volumen](https://sios.magyp.gob.ar/sio_ministerio.constoneltab.aspx) devuelve GET HTML/GeneXus con filtros de fechas y cosechas; conceptos precio hecho, precio a fijar, fijaciones y total contratos, en toneladas. No se probó exportación ni API microdatos. **COMPLEMENTAR** después de definir qué mide cada cantidad y evitar doble conteo.

El [monitor de comercio](https://monitorssma.magyp.gob.ar/siogranos.dashboardgranos.aspx) publica agregados de ventas, compras de industria/exportación, DJVE, FAS/FOB y cosecha. Las fechas de indicadores difieren (precios/ventas 02/10 y compras 23/09 en la muestra). **INVESTIGAR** como contexto separado; no hay evidencia de una nueva API histórica de eventos SIO.

### Futuros

Las páginas oficiales de “Mercado a Término de Buenos Aires” y “Futuros Chicago, Kansas, Winnipeg” son GET HTML (URLs completas en catálogo).

Locales: fechas 01/10 y 30/09/2026, disponible y vencimientos mensuales, trigo, maíz, soja Rosario y girasol Rosario; el enlace institucional indica dólares por tonelada. Falta confirmar si cada valor representa ajuste, último precio u otra medida, contratos, volumen e historia. No convertir “disponible” en futuro ni construir serie continua sin reglas de vencimiento/roll.

Externos: tablas de Chicago (trigo, maíz, avena, soja, harina y aceite de soja) y Kansas (trigo), posiciones mensuales, USD/t, fechas 02/10 y 01/10/2026. La misma publicación incluye referencias físicas FOB Buenos Aires/Golfo que deben mantenerse aparte de futuros. El nombre Winnipeg del enlace no prueba cobertura actual de ese mercado en la muestra. **INVESTIGAR** ambas fuentes y derechos de datos de los mercados originales.

## SIO Carnes: sólo mapa para etapa futura

El [portal SIO Carnes](https://siocarnes.magyp.gob.ar/) atribuye el sistema a liquidaciones electrónicas AFIP y DTe SENASA, con consulta pública sin CUIT individual. Se inspeccionó únicamente HTML/código de [grilla](https://siocarnes.magyp.gob.ar/GrillaSIOCarnes/Grilla), **sin llamar su servicio de datos ni exportar**.

Endpoint descubierto: `GET /GrillaSIOCarnes/Listado`, Bootstrap Table con paginación servidor y tamaños 10/25/50; parámetros `limit`, `offset`, `id_zona`, `id_provincia`, `id_Partido`, `fechaDesde`, `fechaHasta`, `id_Animal`. Rutas de exportación declaradas: `/GrillaSIOCarnes/FilasExportar?periodo=...` y `/GrillaSIOCarnes/Exportar?periodo=...`, no ejecutadas.

Dimensiones y medidas declaradas en UI: especie bovina/porcina, categoría/raza, origen y destino/zona, fecha, cabezas, kilos vivos/equivalente carne y precio según grilla (lista exacta de atributos en catálogo). Sin respuesta no se valida schema, moneda, unidad de cada columna, IDs ni historia. Hay discrepancia entre conteos de zonas del texto institucional y opciones actuales de interfaz. **INVESTIGAR**, sin proponer integración ganadera ahora.

## Arquitectura recomendada para una implementación posterior

### RAW: captura identificable, segura y versionada

Guardar cada respuesta/exportación en almacenamiento externo a Git, por fuente y UTC de captura, con manifest: URL/método/parámetros públicos, fecha solicitada, status, content-type, encoding, hash, tamaño, parser y documentación del contrato. Conservar versiones de datos publicadas; nunca sobreescribir la anterior al recibir una revisión. No persistir cookies, encabezados de autorización, estados WebForms/GeneXus de seguridad ni credenciales; mantenerlos sólo en memoria si fueran necesarios. Para HTML saneado conservar hash original y hash almacenado sin guardar sus secretos.

RAW no significa conservar material de sesión sensible. La publicación GitHub Pages debe contener únicamente datos públicos auditables y autorizados; revisar permisos antes de redistribuir datos originales o derivados.

### NORMALIZED: conservar el grano y campos originales

| Fuente | Identidad candidata, pendiente de validación donde corresponde | Campos que no deben perderse |
|---|---|---|
| MCBA detalle | Fuente + día + códigos dimensionales completos | Etiquetas originales, empresa/sucursal, envase/calidad/tamaño/grado, precio, Kg y marca detalle/resumen |
| MCBA resumen | Fuente + día + dimensiones del resumen + tipo de resumen | `Prom.Esp.` original; no mezclar con detalle |
| SIO grilla | Fuente + ID interno + versión de captura | Número de contrato aparte, vector Row y filtros consultados |
| SIO export | Fuente + identificador de evento derivado documentado + versión | Los 21 campos; timestamp declaración y concertación distintos; no usar sólo NRO como PK |
| FOB | Fuente + fecha + posición + intervalo embarque + circular + versión | Posición textual, comunicado/modificación si se incorporan desde fuente confirmada, moneda/unidad por diccionario |
| Internos/pizarra/FAS/futuros | Fuente + fecha/período + producto + plaza/régimen/mercado/vencimiento | Frecuencia y concepto separados, etiquetas faltantes/provisionalidad |

Para SIO export, una huella de la fila sirve para detectar repetición exacta **de una captura**, no prueba identidad jurídica del evento. No colapsar dos eventos idénticos sin un contrato del proveedor. Mantener ordinal y referencia RAW cuando no haya clave segura. Distinguir evento observado, versión publicada y contrato económico.

Fechas: parsear según formato explícito, conservar original; no inventar timezone. Decimales: reglas de coma/punto por fuente. Moneda: preservar `$`, `U$S` y etiqueta original; asignar ARS/USD sólo con contexto confirmado. Unidad: mantener original; precio $/kg → $/t mediante multiplicación por 1.000 sólo para la misma observación y si fuera útil, marcado como derivado; eso no vuelve equivalentes mercados o conceptos. No convertir moneda sin tipo de cambio, fecha y metodología explícitos. `Kg` de MCBA no se convierte en volumen.

### ANALYTICAL: métricas comparables sin fusionar conceptos

Separar series: cotización MCBA por presentación; resumen MCBA; precio interno mensual; pizarra provisional/final; FAS por régimen; FOB por posición/embarque; SIO por precio hecho/a fijar, evento y moneda; futuros por mercado/contrato. No hacer un promedio conjunto entre ellas.

En SIO mantener dos vistas: historial de eventos y estado de contratos **sólo después de validar reglas de rectificación/anulación/fijación**. Calcular precios con exclusiones explícitas (precio cero, a fijar, falta de moneda/unidad, eventos no pertinentes), sin eliminar esos registros de RAW/NORMALIZED. Determinar denominador de toneladas evitando duplicar contrato/fijación. Publicar conteos excluidos y cobertura. Usar agregado oficial del monitor como comparación, no como prueba automática de igualdad metodológica.

Para MCBA mantener los promedios publicados; un mensual derivado es una serie nueva con regla y días incluidos visibles. No asegurar equivalencia con Excel sin controles coincidentes y documentación de ponderación. Conservar faltantes, días publicados y revisiones. Para futuros, los vencimientos siguen separados; una serie continua necesita regla de roll explícita.

### DASHBOARD y actualización

Producir CSV pequeños separados por fuente/concepto, con ID de serie, producto, plaza, variedad cuando corresponda, moneda/unidad, frecuencia, fecha de observación, actualización y enlace de procedencia. La interfaz estática consume esos CSV; no APIs privadas ni bases completas. Agregados siempre conservan referencias a inputs/manifiestos y reglas reproducibles.

Un futuro workflow: descargar acotadamente → validar esquema/fechas/dimensiones → conservar RAW → generar NORMALIZED/ANALYTICAL → comparar con última salida → publicar CSV en forma atómica sólo si controles pasan. Timeout, error HTML inesperado, schema cambiado o vacío anómalo: abortar publicación, preservar último CSV válido y registrar estado de actualización separado. No rellenar faltantes de una fuente con otra.

| Fuente | Preparación para Actions | Validación faltante antes de producción |
|---|---|---|
| FOB API | Alta: GET documentado y probado | Diccionario, moneda/unidad, revisiones, licencia, días sin publicación |
| SIO grilla reciente | Media: POST JSON público probado | Ventana real, orden/páginas bajo cambios, ID, eventos, fallback |
| SIO export histórico | Media/baja: export público verificado | POST autónomo, estado de sesión, tamaño/rango, claves/instancias, cobertura |
| Internos HTML | Fuente actual mantenible | Parser del informe mensual y cambios de año/formato |
| Pizarra HTML | Media para capturar novedades | Ceros, ajustes, fecha vigente e historia |
| Monitor SIO PHP | Media: un agregado probado | Diccionarios y ponderación; límites de endpoints no ejecutados |
| MCBA / FAS GeneXus | Baja hasta prototipo | Sesión/eventos/exportación autónoma, límites, metodología y cobertura |
| Futuros | Investigación | Precio exacto/contrato/mercado, derechos, historia |
| Corrientes / Carnes | Fuera de implementación actual | Proveedor equivalente / contrato del servicio, respectivamente |

## Evidencia reproducible y verificaciones

Hashes de archivos acotados, guardados fuera del repositorio:

| Archivo/respuesta | SHA-256 original |
|---|---|
| MCBA XLSX 02/10/2024, 356 observaciones | `ed2d683757fc3110db83c31a6ae000c8bf3a92580df3c8e6f3dfcee4c9136b1d` |
| SIO CSV soja, declaración 02/10/2024, 1.296 eventos | `54d61aaef7460df0c46e7e80e7c9c6c34fd0eca8f276fbd5dffedafe5ce97b98` |
| SIO grilla 02/10/2026, página 1 | `012ba783c855a7290d12797e1dd2a5ff93e2faf163d3335b3496a35c6df631e3` |
| SIO grilla 02/10/2026, página 2 | `aa970a5f9b313bfb2834aeb59b01386116a02ce63d2d4add064d050f87a9d04f` |
| API FOB 02/10/2026 | `50d94bd38b9b124f9f2c41e36f915f36c76057b037ad379bfcb4e067e45886d0` |
| API FOB 04/01/1993 | `3d03d61f024311623d3aff8b047a55267a82328f04199b2324a97c46ca1604b9` |
| Índice FOB diario DINEM | `cde38006de6b77e1ff3f10354ad0c1c830a8219583f727deae5c85420c1176dc` |
| Vista FOB circular 2072 / comunicado 184 | `f70eedbde85ed47ed8fd26f09f9d996932d1b9cd52d7c5ccbb8a0b429a50cf85` |
| Vista modificaciones FOB del mismo día | `71d86233c83e588590f4c85ba7cf49752c38bedd9b5aa0480d86893682c0a763` |

Los CSV de catálogo son resultados de investigación, no precios ni nuevas bases integradas. Para repetir una muestra HTTP, primero revisar el dry run; para SIO mantener la fecha acotada y todos los argumentos de la firma. Las fechas antiguas de FOB o exportador no deben generalizarse a cobertura completa.

```powershell
python explorar_fuentes_magyp.py --self-test
python explorar_fuentes_magyp.py --url https://www.magyp.gob.ar/mercadosagropecuarios/precios.php
python explorar_fuentes_magyp.py --allow-web --url 'https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/ws/ssma/precios_fob.php?Fecha=02/10/2026' --label fob_muestra
python explorar_fuentes_magyp.py --inspect-file 'RUTA_LOCAL_DE_EVIDENCIA.csv'
```

Verificaciones de esta entrega: controles del explorador (hosts/credenciales, límites de SIO y eliminación de estado de seguridad); compilación Python; coherencia de 17 IDs/recomendaciones entre ambos CSV; esquema completo del catálogo; diff restringido a artefactos de investigación y excepciones `.gitignore`. No se ejecutó una integración productiva ni se demuestra equivalencia estadística por estas pruebas.
