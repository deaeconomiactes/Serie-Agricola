# Carnes — propuesta de primera UI productiva

Estado: propuesta previa a implementación. La UI comienza después del merge de la
capa de datos; este documento no modifica el dashboard. Fecha: 22/10/2026.

## Estructura

Una pestaña «Carnes», con las mismas tarjetas, filtros, gráficos y tablas del
diseño institucional vigente. Selector de familia: **Faena bovina**, **Producción
bovina**, **Peso medio**. Cada selección tiene datos, unidades y estado propios;
no existe un KPI global entre familias.

Encabezado compacto: fuente institucional, cobertura de la serie seleccionada,
último dato, captura UTC presentada con zona horaria explícita, unidad y estado.
Una nota contextual distingue período completo, provisorio y acumulado parcial.

Los precios Liniers 1998–2019 y las exportaciones 1998–2019 quedan accesibles en
«Series históricas finalizadas», fuera de los paneles principales. No se cargan
al abrir Carnes ni se presentan como datos corrientes. No hay empalme automático
con precios actuales ni conversión entre ARS/USD o kg producto/RCH.

## Filtros y tablas compatibles

| Control | Aplicación |
|---|---|
| Año y mes | Sólo períodos presentes en la fuente/familia; mes sólo para frecuencia mensual. |
| Fuente | Publicaciones compatibles con la familia elegida, con cobertura visible. Sin cambio silencioso de metodología. |
| Frecuencia | Mensual, anual o acumulado publicado, únicamente si existen en esa serie. |
| Provincia | Faena de la tabla provincial MAGyP. No aplicar a producción/peso sin geografía publicada. |
| Categoría y dentición | Tablas nacionales por categoría; dentición sólo bajo clasificación que la publica. |
| Especie | Bovino como alcance inicial; mantener explícito bovinos+bubalinos en 2018. No ofrecer desglose inexistente. |

Provincia y categoría **no son un cruce disponible** en los archivos integrados.
Al seleccionar provincia, los controles nacionales de categoría/dentición no
aplican; al explorar categorías, el ámbito es nacional. La UI debe explicarlo
brevemente y restablecer controles incompatibles, sin aparentar un filtro aplicado.
Los gráficos secundarios pueden mostrar otra tabla nacional sólo con título y
ámbito propios, dejando claro que no responden al filtro provincial.

Tablas de origen permitidas:

- Faena provincial: `slaughter/province`; total nacional publicado o provincias,
  sin sumarlos entre sí. No usar los totales redundantes de establecimientos/usuarios.
- Categorías: tabla nacional de clasificación publicada; no sumar subtotales,
  total general ni categorías de metodologías antiguas/nuevas entre sí.
- Producción/peso: bloque nacional de la métrica y unidad elegidas; el total
  publicado no se obtiene sumando medias de categorías.
- SSPM nacional: historia propia, manteniendo especie, frecuencia y unidad de
  catálogo. Su tonelaje no se rotula RCH si la base de peso no está documentada.

La vista inicial propuesta es faena mensual MAGyP del último período disponible.
Un año puede requerir un archivo anual archivado o el avance corriente, seleccionados
por cobertura real del índice. No sumar fuentes redundantes ni empalmarlas sin
validación explícita. 2018 conserva la especie combinada declarada por el origen.

## KPIs

| Familia | KPIs y reglas |
|---|---|
| Faena | Cabezas del período y ámbito seleccionados; variación interanual comparable; participación provincial sobre el total nacional publicado de la misma tabla/período; categoría principal sólo para tabla nacional de categorías compatible. |
| Producción | Toneladas publicadas de la fuente/unidad seleccionada; variación interanual sólo con base equivalente. |
| Peso medio | Kg res con hueso cuando el bloque lo declara; media publicada, nunca promedio simple entre categorías; variación interanual comparable. |

La comparación interanual exige misma metodología, especie, tabla, geografía,
categoría/dentición, moneda, unidad y frecuencia; para acumulados, mismo mes de
cierre. Nunca comparar enero–septiembre con un año completo. Si falta el año
anterior compatible: «Sin base comparable»; no calcular desde otra fuente.
En particular, producción/peso detallados corrientes sólo tienen 2026 integrado;
no prometer una variación interanual que estos archivos no soportan.

Una selección de varias series no produce un promedio global. Se muestran KPIs
por serie o se solicita seleccionar una. Faltante y cero permanecen distintos.
Una categoría principal sólo se informa si hay base completa/comparable; las
clasificaciones coexistentes de 2019 no se combinan para elegirla.

## Gráficos y tabla

- Faena: evolución de la tabla/serie elegida; ranking provincial del mismo
  período; composición nacional por categoría/dentición con metodología explícita.
- Producción: evolución de toneladas publicadas. Distribución geográfica sólo
  cuando exista esa dimensión; actualmente no se habilita para el bloque nacional.
- Peso: evolución de la media publicada; comparación entre categorías con la
  misma metodología/unidad, sin recalcular medias agregadas.
- Tabla descargable de las observaciones seleccionadas, con fuente, localizador,
  fecha, cierre de período, unidad, flags, captura y enlace institucional.

Mensual/anual/acumulado son selecciones distintas. Para `year_to_date`, mostrar
«Acumulado enero–septiembre 2026», por ejemplo, usando `period_end`; no «2026»
como si fuera año completo. Las series provisorias llevan etiqueta visible.

## Metadata y estados

Usar el estado real por fuente de `CARNES_UPDATE_STATUS.json`, combinado con
`source_lifecycle` del índice. La cobertura histórica, último dato y captura
son campos diferentes. No deducir error por calendario.

| Estado visual | Regla |
|---|---|
| UPDATED | Publicación validada; `NO_OP_ALREADY_CURRENT` se presenta como actualizado, conservando la fecha real de captura. |
| HISTORICAL_ENDED | Archivo legítimamente finalizado; etiqueta «Serie histórica finalizada», sin error por antigüedad. |
| SOURCE_UNAVAILABLE | Incidencia real del updater; conservar último dato y mostrar última captura exitosa. |
| NO_PUBLICATION | Sólo si metadata futura lo declara; no inferirlo de un mes ausente. |
| PIPELINE_ERROR | Error explícito de schema/validación/procesamiento; última versión válida preservada. |

Un error de actualización y la condición histórica pueden coexistir: conservar
la etiqueta histórica y mostrar la incidencia aparte. El descubrimiento caído no
debe reemplazar el estado individual de una fuente que sí se actualizó.

## Archivos frontend previstos, sin editar en esta etapa

- `index.html`: añadir únicamente la pestaña y contenedor Carnes.
- `app.js`: registrar el nuevo módulo y su carga diferida; preservar el estado
  y comportamiento de los módulos actuales.
- `styles.css`: sólo reglas acotadas a Carnes cuando no basten las clases existentes.
- Nuevo `carnes.js`: cargador de índice/fragmentos, selección de tablas, filtros,
  validaciones, KPIs y visualizaciones propios, sin lógica compartida mutable.
- Nuevos tests de Carnes en la suite frontend y pruebas visuales del módulo.

## Payload medido y presupuesto

Datos actuales, bytes comprimidos de los fragmentos; el índice es JSON sin
compresión asumida. Transferencia HTTP real puede variar según hosting.

| Recurso | Tamaño |
|---|---:|
| `dashboard/index.json` completo | 88.542 bytes |
| Faena MAGyP mensual, 2026 | 38.312 bytes / 378 registros |
| Producción MAGyP mensual, 2026 | 15.309 bytes / 144 registros |
| Peso MAGyP mensual, 2026 | 15.885 bytes / 144 registros |
| Mayor fragmento de toda la entrega | 60.795 bytes |
| Todos los fragmentos disponibles (no cargar juntos) | 1.425.456 bytes |

La entrada inicial de faena requiere aproximadamente **127 kB + metadata de
estado**, no todos los años ni otras familias. Cambiar a producción o peso agrega
aproximadamente 15–16 kB si el índice está cacheado. Cargar por fuente/familia/
frecuencia/año; los fragmentos también contienen filas redundantes que el adaptador
debe filtrar por tabla antes de calcular. Las categorías de faena ya están en el
fragmento mensual de faena; no requieren cargar establecimientos ni usuarios.

Validar hash, schema y conteo antes de usar cada fragmento. Cachear por hash y
cancelar/ignorar respuestas de selecciones anteriores. Descomprimir CSV.gz con
soporte verificado en Edge/Chrome; no llamar APIs desde el frontend ni asumir
que GitHub Pages descomprime el archivo automáticamente. Nunca solicitar RAW,
NORMALIZED ni ANALYTICAL. El presupuesto mide transferencia, no memoria expandida.

## Tests de aceptación de la UI, pendientes del merge

1. Carga diferida: cero solicitudes Carnes hasta abrirlo; sólo índice, estado y
   fragmentos necesarios; sin rutas de capas completas/entidades.
2. Filtros significativos, cambios rápidos de selección, cero/dato faltante y
   selección vacía; cada fuente conserva unidad y metodología.
3. KPIs sin mezcla de tablas/familias/especies; peso no promediado; participación
   con denominador compatible; interanual sólo con período y clasificación equivalentes.
4. Acumulado parcial frente a anual completo; provisorio visible; transición de
   categorías 2019 y bovinos+bubalinos 2018 explícitas.
5. Estados UPDATED/HISTORICAL_ENDED/SOURCE_UNAVAILABLE/NO_PUBLICATION/PIPELINE_ERROR;
   última captura y último dato distintos; error no destruye vista válida.
6. Precios y exportaciones históricos disponibles con etiqueta finalizada,
   sin cargar al inicio ni integrarse en KPIs corrientes.
7. Edge/Chrome, escritorio y ancho intermedio; navegación por teclado, etiquetas
   accesibles y regresiones de los módulos existentes.

Estos tests de UI son criterios propuestos: no se presentan como ya ejecutados.
