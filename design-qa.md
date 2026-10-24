# QA visual · Carnes desde la referencia aportada

final result: passed

## Verdad visual y evidencia

- Fuente principal conservada: `C:/Users/acer/Oficina/carnes-ui-evidence/reference-rebuild/source-1.png` (captura aportada, 1366 × 728 px). Fuentes secundarias: `source-2.png`, `source-3.png` en esa carpeta.
- El dashboard está contenido en la primera captura: crop (329,48)–(1035,519), 706 × 471 px. Se normalizó únicamente esa región a 1440 × 960 para comparar la composición. La fuente es una captura reducida de un diseño, no una vista del sitio ejecutable; no permite deducir valores CSS exactos.
- Implementación: `http://127.0.0.1:8767/`, módulo Carnes, Faena, mensual, septiembre 2026, fuente DNCCA, total nacional, dark. Navegador Edge, densidad 1, ancho CSS 1440. PNG completo `msedge-1440-slaughter.png`; recorte del primer viewport 1440 × 960 en `implementation-viewport.png`.
- Comparación conjunta de ambas imágenes: `comparison.png`, 2880 × 992, con sólo 32 px de identificación. Abierta e inspeccionada después de los ajustes. Ambas fuentes se presentan a la misma anchura y sin el escritorio de la captura original.
- Otras evidencias: capturas completas a 900 px; Producción, Peso, Más filtros, tabla y detalle a 1440/900 px. Pruebas responsive adicionales a 1000/640 px.

## Historial de hallazgos y correcciones

1. [P1, corregido] La presentación previa usaba una cabecera frutihortícola y carecía de navegación lateral contextual. Se añadieron marca Serie Agrícola condicionada a Carnes, rail funcional y header compacto con imagen ganadera. La comparación posterior confirma esa estructura; los otros módulos conservan su presentación.
2. [P2, corregido] La primera captura implementada tenía títulos y labels pequeños respecto de la referencia normalizada. Se aumentaron el título de familia a 26 px y títulos analíticos a 15 px, y se revisaron labels, números y espaciado. Evidencia posterior: `comparison.png` y capturas de 900 px.
3. [P2, corregido] Una fila adicional de título/acción sobre los KPIs desplazaba la evolución respecto de la referencia. Se eliminó esa fila y se conservó el acceso a observaciones en la barra lateral y disclosure inferior. La captura posterior muestra KPIs y gráfico más arriba.
4. [P1, corregido] La revisión automática detectó que al reemplazar los estilos había reaparecido el resumen de cantidades en otros módulos. Se restauró la regla previa de visibilidad. Las pruebas de cambio de módulo en Edge y Chrome pasan.

## Superficies revisadas

- Tipografía: Inter existente; jerarquía de marca, título, labels, datos y texto secundario; cifras tabulares. Título de familia semántico h2 y marca con rol heading nivel 1, sólo visibles en Carnes. No se superponen título y estado. Los textos largos envuelven dentro de sus tracks.
- Layout y ritmo: rail de 176 px, gutters de 20/12 px, cabecera compacta, filtros, cuatro KPIs cuando son válidos y grilla de análisis 2/3 + 1/3. Cards con radios de 6 px y bordes discretos. En 900 px se redistribuyen KPIs y se apilan visualizaciones; en 640 las familias pasan a horizontal. Sin desborde global en los anchos probados.
- Colores: slate oscuro y menta, acentos diferenciados en símbolos de KPI. Los colores de las cards no constituyen semáforos ni juicios económicos. Contraste de labels y foco visible conservados.
- Assets: iconos reales Phosphor con licencia; fotografía decorativa generada, exportada como WebP de ~66 kB. Se conserva el símbolo institucional existente. No se usa una captura rasterizada como interfaz ni se dibujan iconos aproximados.
- Texto y contenido: español, fuente y cobertura publicadas, dato provisorio, valores y notas originales. No se copia la estadística ficticia de la referencia.

## Diferencias deliberadas, requeridas por el alcance

La fuente visual tiene donut, índice base 100, una tabla con provincia × categoría y una historia extendida de ejemplo. Se conserva la metodología y los loaders del proyecto: barras de 15 componentes, evolución disponible del año elegido, hechos calculados y tabla cerrada bajo demanda. Eso requiere mayor altura que las visualizaciones simplificadas del mock. No se considera un clon pixel a pixel: se reproduce el sistema de composición y componentes respetando el contenido real.

La fotografía y el icono bovino son recursos de la misma función y proporción, no el mismo archivo de la captura. No se crean búsqueda global, cuentas ni botones administrativos del template.

## Interacciones y resultados

- Edge/Chrome: familias, filtros, más filtros/Escape, metodología lateral, observaciones con foco y cierre por teclado, diálogo/escape, búsqueda, paginación, descarga CSV y retorno a otros módulos. Sin errores JS en las pruebas de interfaz.
- Chrome: validación analítica contra CSV, composición, medias móviles, referencias históricas, heatmap y cambios rápidos de familia.
- 27 tests Node de Carnes aprobados. Snapshot de las tres familias idéntico al anterior: estados, series, KPIs, notas, ancla y contador de solicitudes. Todas las funciones de `carnes.js` fuera de `View.build()` idénticas al respaldo anterior.
- Sintaxis JS y `git diff --check` aprobados. No hubo commit, push, merge o publicación.

## Checklist de implementación

- [x] Composición comparada con la imagen del usuario en una misma evidencia.
- [x] Corregidos los hallazgos P1/P2 y capturada la revisión posterior.
- [x] Funciones principales y responsive verificados.
- [x] Datos y lógica económica conservados.

## Pulido posterior

[P3] La fuente está reducida y sus textos no son una especificación tipográfica exacta. Una captura original sin el escritorio permitiría afinar ópticamente los pesos y tamaños sin cambiar el sistema implementado.
