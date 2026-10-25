# Carnes · presentación con referencia Gentelella v4

Iteración local del 23/10/2026. Rama `codex/ui-refresh-institucional-carnes`. Sin commit, push ni merge. `main` permanece en `152b04c30514dc674029d26cd6de0017777ff30e`.

## Referencias estudiadas antes de editar

- [Repositorio oficial](https://github.com/ColorlibHQ/gentelella), rama master, diseño v4; la demo identifica v4.1.1.
- [Analytics Dashboard oscuro](https://preview.colorlib.com/theme/gentelella/production/index2.html): panel dominante, distribución asimétrica, segunda fila y matriz de intensidad.
- [Component playground](https://preview.colorlib.com/theme/gentelella/production/playground.html): encabezados de cards, subtítulos, controles nativos, tablas con separadores horizontales y alineación numérica.
- [Theme generator](https://preview.colorlib.com/theme/gentelella/production/theme.html) y [tokens v4](https://github.com/ColorlibHQ/gentelella/blob/master/src/scss/v4/_tokens.scss): superficies oscuras diferenciadas, geometría moderada, Inter, escala de espacio basada en 4 px y sombras discretas.

Se estudió la presentación visual en el navegador. No se copiaron HTML, CSS, JS, assets, dependencias ni páginas del template. Se conserva Chart.js.

## Cambio estructural

| Elemento | Antes de esta iteración | Ahora |
|---|---|---|
| Encabezado | Carnes / familia en una misma línea | Identificador de módulo, familia dominante, estado y metadata integrados |
| Navegación y filtros | Elementos sueltos | Franja contextual con familias y controles compactos |
| Resumen | Cuatro cards equivalentes | Magnitud principal destacada, jerarquía ejecutiva y acceso a observaciones |
| Hechos calculados | Franja anterior al gráfico | Panel de cambios destacados junto a la composición |
| Segunda fila | Composición a todo el ancho | Composición 2/3 + hechos verificables 1/3 |
| Peso medio | Dos gráficos apilados a 1440 | Evolución dominante con comparación publicada por categoría lateral |
| Producción sin desglose comparable | Evolución y composición omitida | Evolución amplia; se mantiene la omisión de desgloses no disponibles |
| Detalle | Botón de disclosure aislado | Panel compacto bajo demanda con búsqueda, paginación y descarga existentes |
| 900 px | Secuencia vertical | Evolución completa, composición y ranking en segunda fila; hechos debajo |

No se añadieron magnitudes ni visualizaciones para llenar espacios. El número de KPIs sigue dependiendo de la disponibilidad comparable. Tampoco se cambió la regla que omite referencias históricas con historia homogénea insuficiente.

## Alcance y conservación

En `carnes.js` sólo cambia `View.build()`: estructura DOM y acceso a la tabla. El resto del archivo se comparó como texto completo con el respaldo anterior y es idéntico, incluidos loaders, selección, fórmulas, render numérico y validaciones. `app.js` e `index.html` sólo actualizan las versiones de caché. Los estilos nuevos están limitados a Carnes.

Las definiciones, fórmulas, dimensiones, comparabilidad, faltantes y patrones transferibles siguen documentados en [CARNES_ANALYTICS_PILOT.md](CARNES_ANALYTICS_PILOT.md).

## Evidencia visual

Fuera de Git: `C:/Users/acer/Oficina/carnes-ui-evidence/`.

- `gentelella-before/`: respaldo de los cuatro archivos de presentación, snapshots y capturas anteriores.
- `gentelella-after/`: capturas nuevas y reportes de navegador.
- `gentelella-review.html`: galería antes/después, imágenes completas sin recorte.

Para cada ancho, 1440 y 900 px: Faena, Producción, Peso, Más filtros de Faena, tabla abierta de Faena y diálogo de detalle de Faena. Los controles compartidos se verifican además por familia en las pruebas de navegador.

## Validación

- 27 tests Node de Carnes: aprobados.
- Pruebas de interfaz en Edge y Chrome: aprobadas; navegación, filtros, accesibilidad por teclado, detalle, búsqueda, paginación, CSV y ausencia de desborde global a 1440/1000/900/640 px.
- Pruebas analíticas en Edge y Chrome: comparación independiente contra CSV, YTD, MM12, concentración, composición, referencias históricas, heatmap y cambio rápido de familia.
- Snapshots antes/después idénticos para las tres familias: estado, series completas, KPIs, observación ancla y contador de solicitudes.
- Carga inicial: 4 solicitudes, 177.440 bytes. Historia adicional bajo demanda.
- `node --check carnes.js`, `node --check app.js` y `git diff --check`.

La aceptación visual se revisó sobre las capturas completas; los cambios de distribución se contrastaron con el estado inmediato anterior, no con una versión antigua de main.
