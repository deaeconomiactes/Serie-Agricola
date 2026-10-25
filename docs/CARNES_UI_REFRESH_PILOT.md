# Carnes — piloto institucional, iteración 2

Evolución posterior: [tercera iteración analítica](CARNES_ANALYTICS_PILOT.md).
Este documento conserva el alcance y las mediciones de la segunda iteración.

23/10/2026. Implementación local pendiente de revisión visual humana.
Rama `codex/ui-refresh-institucional-carnes`, base `main` en `5590208`.
Checkout `C:/Users/acer/Oficina/Serie-Agricola-ui-carnes`.
Sin commit, push, merge ni publicación. El checkout original conserva su rama
y los cambios previos de configuración/AGENTS.md.

## Referencias estudiadas antes de editar

Se abrieron las tres referencias en el navegador y se inspeccionaron sus capturas.

- [Tabler Dark](https://preview.tabler.io/?theme=dark): escala compacta, navegación
  horizontal, superficies neutrales, jerarquía tipográfica y bordes discretos.
- [Gentelella v4](https://preview.colorlib.com/theme/gentelella/production/index.html):
  composición del análisis con una superficie dominante y panel de apoyo.
- [USWDS: tablas](https://designsystem.digital.gov/components/table/): tabla para
  comparación fila/columna, caption, headers con scope, números alineados a la
  derecha y región desplazable que recibe foco por teclado.

Se reproduce el lenguaje visual con el código existente. No se copiaron códigos
de esas referencias ni se importaron Tabler, Bootstrap, frameworks o dependencias.
Se preservan la navegación superior, el español, el acento verde/agua y la
trazabilidad institucional de Serie Agrícola.

## Composición final

1. **Encabezado integrado:** «Carnes / familia» y estado alineado a la derecha.
   Fuente, último período de la selección, unidad y cobertura de archivos en una
   línea flexible. Captura disponible en el detalle y ayuda del enlace de fuente.
2. **Familias visibles:** botones nativos con estado `aria-pressed`, sin selector
   desplegable visible ni navegación administrativa agregada.
3. **Filtros compactos:** año, mes, frecuencia, fuente y «Más filtros» comparten
   una franja sin tarjeta exterior. Los labels siguen visibles y asociados.
   Provincia, categoría, dentición y clasificación mantienen todas sus opciones
   y restricciones. Especie permanece como atributo de publicación.
4. **Más filtros:** panel contextual en escritorio; despliegue dentro del flujo
   hasta 1000 px. Escape lo cierra y devuelve foco al disparador. Los controles
   incompatibles con provincia siguen ocultos y deshabilitados.
5. **KPIs:** tarjetas independientes, más jerarquía numérica, sin contenedor
   exterior. En nacional se oculta la tarjeta vacía «Seleccioná una provincia»;
   al seleccionar provincia reaparece la participación con el cálculo original.
   No se cambia ningún valor, nota, fórmula o denominador. Producción/Peso
   mantienen dos indicadores; no se inventan métricas para completar la grilla.
6. **Análisis principal:** evolución y ranking en relación 2/3 + 1/3; ambos
   alineados, sin selector adicional ni contenedores anidados. Todas las provincias
   siguen representadas. Sin ranking aplicable, la evolución ocupa todo el ancho.
7. **Análisis secundario:** composición/comparación en un panel propio de ancho
   completo, cuando la familia y selección lo permiten. Sin ocultar categorías.
8. **Detalle bajo demanda:** la tabla principal comienza cerrada detrás de
   «Ver detalle de observaciones». Mantiene diez filas iniciales, ampliación de
   diez en diez y descarga de toda la selección. El panel lateral mantiene todos
   los campos de observación y el despliegue de trazabilidad técnica.
9. **Metodología/estados:** explicación extensa desplegable. Condición provisoria,
   ámbito, especies no separables, base de peso desconocida y total de peso
   ausente siguen advertidos a la vista. Estados públicos en español.

CSS delimitado a Carnes, salvo el fondo del body condicionado exclusivamente a
Carnes activo. La navegación superior existente permanece. `app.js`/`index.html`
sólo cambian versiones de recursos para renovar caché. Se conserva Chart.js,
su carga diferida y las funciones de adquisición, validación y cálculo.

## Evidencia y aceptación visual

Archivos locales fuera de Git en `C:/Users/acer/Oficina/carnes-ui-evidence/`:

- `iteracion2-antes-despues-1440.png`: comparación a la misma escala, página
  completa del piloto anterior y nueva composición, con viewport original de
  1440 × 1050. La captura anterior se generó antes de modificar código.
- `iteration2-before/msedge-1440-slaughter.png` y
  `iteration2-after/msedge-1440-slaughter.png`: originales sin reducir.
- Ambas carpetas incluyen Faena/apertura, Producción, Peso y detalle lateral
  a 1440 y 900 px. Los nombres usan `slaughter`, `production`, `carcass_weight`
  y `detail` como sufijos de archivo.
- `iteration2-after/{msedge|chrome}-{1440|1000|900|640}.png` y reportes JSON:
  evidencias responsive y funcionales.
- `iteration2-equivalence.json`: comparación de estado, serie completa, ancla,
  solicitudes y valores/notas de los cuatro KPIs internos. Todo coincide.
  La visibilidad de la tarjeta provincial vacía cambia deliberadamente.
- `iteration2-before/` conserva además los cuatro recursos previos; `capture.py`
  es el recorrido auxiliar para reproducir capturas.

La página inicial a 1440 px pasa de **2249 a 1821 px de altura**, aun mostrando
ahora el análisis secundario por categorías. La tabla abierta desaparece de la
lectura inicial. Encabezado, filtros y análisis se recomponen; no es sólo un
cambio de paleta. Capturas comparadas lado a lado e inspeccionadas visualmente.
La aprobación estética final corresponde al usuario.

## Payload de esta iteración

Bytes de código normalizados a LF en ambos lados, para no atribuir diferencias
de finales de línea Windows al diseño. Son tamaños de recursos, no overhead HTTP.
Detalle en `iteration2-payload.json`.

| Recurso | Piloto anterior | Iteración 2 | Diferencia |
|---|---:|---:|---:|
| index.html | 44.563 | 44.565 | +2 |
| app.js | 207.422 | 207.424 | +2 |
| carnes.js | 44.308 | 44.107 | −201 |
| styles.css | 44.179 | 45.323 | +1.144 |
| Diferencia total | | | **+947 bytes** |

Gzip local estimado: +223 bytes combinados; no es una medición de compresión del
hosting. La apertura de Carnes conserva **177.440 bytes de datos / 4 solicitudes**
(índice, estado y faena 2026/2025). Sin recursos remotos o datos nuevos.

## Pruebas y límites

- Frontend: `node --test tests/magyp_frontend/*.cjs`: **99 aprobadas**.
- Carnes Python: `python -m unittest discover -s tests/carnes -v`: **29 aprobadas**.
- Edge/Chrome: `python tests/carnes/browser_ui_checks.py --channel msedge|chrome --output ...`: **ambos aprobados**, sin errores JavaScript.
  Valida tabla inicialmente cerrada y apertura/cierre por teclado; detalle técnico,
  Escape y retorno del foco; filtros, 2019, anual/acumulado, estados, fallback,
  cambios rápidos, históricos y retorno a otros módulos. CSV descargado comparado
  campo por campo con las doce observaciones de una serie que muestra diez.
- Responsive: 1440, 1000, 900 y 640 px, sin scroll horizontal de página.
  La tabla usa scroll local con foco; headers `scope=col`, caption y números a
  la derecha. Foco visible y estados con texto, sin depender sólo del color.
- `node --check carnes.js`, `node --check app.js`, `git diff --check`.

No se modifican datos, pipelines, fuentes, workflows ni metodología. Las funciones
de cálculo y selección económica conservan su comportamiento previo. No se
realizó auditoría formal WCAG con lector de pantalla ni pruebas en Safari/Firefox.
La comparación visual no mide tiempos de comprensión con usuarios reales.
Encabezado y pie globales conservan su texto frutihortícola previo, fuera del piloto.

## Posibles componentes del design system

Encabezado integrado con metadata; navegación visible de familias; toolbar con
filtros progresivos; KPIs sin contenedor exterior; relación de análisis 2/3 + 1/3;
observaciones cerradas por defecto y detalle lateral trazable. Generalizar sólo
después de revisar este piloto.

Evidencia de negocio revisada: brief y ampliación del usuario,
`docs/CARNES_UI_IMPLEMENTATION.md`, `data/carnes/README.md`, implementación y
fragmentos DASHBOARD locales. Las referencias externas se usaron únicamente
para diseño visual/accesibilidad, no como fuentes de cifras económicas.
