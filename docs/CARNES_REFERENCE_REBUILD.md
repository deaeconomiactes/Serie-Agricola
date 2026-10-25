# Carnes · reconstrucción desde las referencias aportadas

## Referencia visual

Referencia principal: primera captura aportada por el usuario, con Serie Agrícola, navegación lateral de Carnes, encabezado con imagen ganadera, filtros compactos, cards con símbolos y grilla analítica. Las otras dos capturas orientan la geometría de cards y controles. No se utilizan las tres propuestas editoriales descartadas.

La implementación sigue en `codex/ui-refresh-institucional-carnes`, checkout `C:/Users/acer/Oficina/Serie-Agricola-ui-carnes`. No se ejecutaron commit, push, merge ni operaciones sobre main.

## Cambios

- Marca Serie Agrícola y navegación global en una barra compacta, visibles así sólo mientras Carnes está activo.
- Navegación lateral contextual: Faena, Producción, Peso, enlace institucional, metodología, observaciones y series finalizadas. Los accesos abren los componentes reales y trasladan el foco. En pantallas estrechas, las familias vuelven a navegación horizontal.
- Encabezado con icono bovino y fotografía ilustrativa generada; metadata publicada y estado de actualización existentes.
- Filtros compactos y panel de más filtros; se preservan las restricciones entre dimensiones.
- KPIs con símbolos y acentos diferenciados; valores, notas y visibilidad son los mismos del piloto validado.
- Evolución dominante, ranking lateral y segunda fila de composición/cambios destacados. Comparaciones de peso por categoría conservadas.
- Observaciones bajo demanda con búsqueda, paginación, descarga y trazabilidad existentes.
- Pie específico de Carnes; los demás módulos conservan su encabezado y pie.

## Adaptaciones deliberadas a los datos

La referencia es una composición visual, no una fuente estadística. No se copian sus porcentajes, fechas de actualización ni categorías de ejemplo. Se mantienen el total 1.045.293 cabezas, −11 % i.a., acumulado calculado 9.176.312,75 y Top 3 provincial 76,22 % de la selección real.

Se conserva la clasificación publicada de 15 componentes y su comparación con el período homólogo. Continúa en barras: no se introduce el donut de la referencia. Tampoco se introduce el cruce provincia × categoría que aparece en su tabla de ejemplo, ni un índice base 100, ni una serie histórica empalmada. La evolución usa los datos ya cargados por el selector; no se modifican loaders o fragmentos para simular una historia más larga.

Por la extensión de esa clasificación válida, la segunda fila y los detalles continúan por debajo del primer viewport. Se conserva legibilidad y contenido real en lugar de comprimir o omitir categorías.

## Recursos y cambios de código

`carnes.js`: sólo `View.build()` cambia. Todas las funciones fuera de ese método se compararon con el respaldo anterior y son idénticas. `styles.css`: bloque scoped de Carnes. `index.html`: marca/pie condicionales y versión de caché. `app.js`: versión de caché. No se modifican fuentes, observaciones, cálculos, CSV, shards, pipelines o workflows.

Los iconos son archivos de Phosphor Icons, con licencia conservada. La imagen decorativa es WebP de aproximadamente 66 kB. Ver [recursos](../assets/carnes/README.md).

## Validación y evidencia

- 27 tests Node de Carnes aprobados.
- Pruebas de interfaz en Edge y Chrome: navegación, más filtros, selección, metodología desde la barra lateral, observaciones con foco/teclado, diálogo, CSV, búsqueda/paginación y ausencia de desborde global a 1440/1000/900/640 px.
- Pruebas analíticas de navegador: KPIs y composición contra CSV, referencias homogéneas, heatmap, datos faltantes y cambios de familia.
- Snapshots anteriores y nuevos: comparación de estados, series completas, KPIs, notas, anclas y solicitudes.
- Carga inicial de datos: 4 solicitudes, 177.440 bytes; imagen e iconos son recursos visuales separados.
- Sintaxis de JS y `git diff --check`.

Evidencia fuera de Git: `C:/Users/acer/Oficina/carnes-ui-evidence/reference-rebuild/`. Incluye capturas completas de Faena, Producción, Peso, Más filtros, tabla y detalle a 1440 y 900 px, además de comparación con la referencia. El informe de comparación visual está en [design-qa.md](../design-qa.md).
