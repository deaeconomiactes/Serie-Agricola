# Serie Agrícola · sistema de diseño institucional

Estado: referencia aprobada en el piloto Carnes. Aplicación posterior: Precios Mayoristas. Trabajo local en `codex/ui-refresh-institucional-carnes`, sin integración automática a main.

## Propósito y alcance

El sistema organiza información agropecuaria para responder cuánto, cómo cambió, dónde se concentra, cómo se compara y qué límites tiene la comparación. La unidad de diseño es la pregunta analítica con su fuente, no una card que haya que llenar.

Carnes fija el lenguaje visual; no fija la cantidad de KPIs, los gráficos, las dimensiones ni una grilla idéntica para todos los módulos. Su diseño aprobado se conserva. Un módulo adopta componentes y reglas según su lógica económica. No se importa un template administrativo ni se incorporan cuentas, actividad de usuarios o controles sin función real.

## Referencia implementada y conservación

- Carnes: `carnes.js`, método `View.build()`; bloque inicial de `styles.css`; recursos `assets/carnes/`. Las funciones analíticas, fuentes y loaders son independientes de la presentación.
- Mayoristas: estructura en `index.html`, estilos `mayoristas-ui.css`, comportamiento de disclosures y detalle en `mayoristas-ui.js`. `app.js` conserva cálculos, selección, Chart.js, fuentes y carga.
- El código de Carnes no se refactoriza para crear una abstracción compartida durante esta adopción. Los tokens de Mayoristas reproducen valores aprobados. Una extracción técnica común requerirá revisar regresiones, no rediseñar el piloto.

## Principios

1. La fuente y el concepto económico acompañan al valor. Unidad original y comparable, precio y cantidad, mercado y procedencia tienen significados diferentes.
2. Primero nivel y cambio; después distribución y comparación; finalmente detalle y metodología.
3. Los componentes sin base comparable se omiten o explican su indisponibilidad. Nunca se simula información para completar una grilla.
4. Se priorizan jerarquía, alineación, espacios y superficies discretas. Los bordes delimitan tareas o paneles; no encierran cada línea de texto.
5. La compacidad evita recorridos innecesarios, pero mantiene labels legibles, foco visible y controles reales.
6. El diseño no altera datos, filtros, agregaciones ni la identidad de series.

## Tokens visuales

Los valores proceden del piloto aprobado. Son una base para componentes institucionales, no una paleta universal para todas las series de un gráfico.

| Token conceptual | Valor | Uso |
|---|---|---|
| Fondo | `#0b121b` | Superficie de la aplicación |
| Panel | `#111e2a` | Cards y grupos analíticos |
| Inset | `#0d1823` | Encabezado o superficie secundaria |
| Control | `#132332` | Inputs y selects |
| Borde de control | `#293a4b` | Controles y foco no activo |
| Borde sutil | `#ffffff0a` | Separación entre regiones |
| Texto principal | `#eef3f7` | Valores y títulos |
| Texto secundario | `#a7b8c9` | Labels, metadata y notas |
| Texto auxiliar | `#8195aa` | Información de menor jerarquía |
| Menta | `#66d4b0` | Selección, foco, serie principal |
| Fondo activo | `#193b3d` | Familia o sección seleccionada |
| Radio de control | `4px` | Inputs y acciones |
| Radio de panel | `6px` | Cards y encabezados |
| Divisor | `1px` | Separación discreta |

Acentos de símbolos: menta, rosa, ámbar y azul sobre fondos apagados. Diferencian funciones; no asignan un juicio económico a los valores. Un precio que aumenta no es automáticamente bueno o malo. El color de estado sólo se usa con un significado definido y texto explicativo.

### Espaciado

Escala: 4, 8, 12, 16, 20, 24, 32 px. Uso habitual: 12 px entre cards; 20 px entre rail y contenido; 12–16 px dentro de cards; 20 px de margen exterior en desktop. Un componente puede crecer para labels largos o una unidad compleja. No se fija una altura de pantalla para comprimir información.

### Tipografía

Familia: Inter y fallbacks del proyecto. Pesos 400 para texto, 500 para controles/labels, 600–650 para títulos y cifras. Marca compacta de 15 px; título de módulo 22–26 px; título analítico 15 px; KPI 22–25 px. Texto de trabajo 12–14 px; metadata/labels compactos 11–12 px. Los estados breves pueden usar 10 px; no trasladar esa escala a ejes o texto explicativo.

Cifras comparables alineadas con `tabular-nums`. Evitar mayúsculas en párrafos; reservarlas para etiquetas cortas de sección. Se permite envolver unidades y títulos. La elipsis en un selector no debe ocultar la selección sin permitir consultarla al abrirlo.

## Componentes y reglas de uso

### Navegación global

Una barra superior compacta identifica Serie Agrícola y conserva los módulos existentes y sus nombres accesibles. El módulo activo tiene una superficie menta apagada. No duplicar la navegación global en la sidebar. En nuevas adopciones, el título del documento identifica el módulo activo y Serie Agrícola; al salir se restaura el título previo, sin cambiar otras vistas. Mantener el orden de navegación por teclado y el estado seleccionado. La cabecera específica de Carnes o Mayoristas sólo se aplica al módulo activo; Cantidades y Commodities no cambian por efecto lateral.

### Sidebar contextual

Contiene familias, secciones analíticas o accesos útiles del módulo. En Carnes cambia Faena/Producción/Peso. En Mayoristas navega Evolución, Productos, Mercados y Detalle: no inventa familias económicas ni reemplaza filtros por enlaces.

Los accesos a un detalle cerrado deben abrirlo, desplazarlo a la vista y trasladar el foco a su encabezado. Enlaces externos conservan la fuente correcta. No incluir entradas decorativas o sin destino. Ancho de referencia: 176 px desktop; puede reducirse a 150 px en pantallas intermedias. En móvil pasa a navegación horizontal o secciones compactas.

### Header / hero analítico

Título del módulo, descripción de su alcance y metadata cercana. El estado de actualización procede de la metadata real. Una imagen de contexto es opcional: Carnes usa una fotografía ilustrativa; Mayoristas puede comunicar su contexto sólo con título, icono y fuente. No es obligatorio generar un hero fotográfico por módulo.

La imagen debe ser discreta, decorativa, sin competir con cifras ni simular evidencia estadística. Conservar su origen y licencia en documentación. El encabezado no contiene una frase comercial ni una llamada a publicar/registrarse.

### Estados

Distinguir carga, error, última vista válida, fuente no disponible, dato provisorio, falta de base comparable y serie finalizada. Usar texto además de color. Mantener `role=status` y anuncios existentes. Los errores de integridad o los límites de unidad no se esconden en un panel cerrado. Metadata extensa de actualización puede quedar bajo demanda, con el aviso principal visible.

### Filtros compactos

Primer nivel: selectores que más modifican la pregunta. Más filtros: dimensiones de precisión, presentación o comparabilidad menos frecuentes. Las selecciones activas siguen siendo consultables; al cambiar una dimensión no se alteran silenciosamente sus reglas.

Siempre mantener label asociado, IDs y eventos existentes. No sustituir multiselección por un selector simple para ahorrar espacio. Los desplegables deben quedar por encima de charts y no cortarse por `overflow:hidden`. Escape cierra el panel contextual y retorna foco a su summary. Los estados de carga conservan última selección válida según el loader.

Alturas de referencia: 32–36 px, padding 5–9 px; tamaños de interacción mayores cuando la densidad táctil lo requiere. No usar todo el ancho de la pantalla para un único filtro si no lo necesita.

### KPI cards

Un KPI responde una pregunta concreta. Mostrar label, valor, unidad/período y contexto comparativo cuando exista. Símbolo de una biblioteca real, con color funcional discreto; el valor sigue siendo protagonista.

Mostrar habitualmente 3–4 KPIs principales; la disponibilidad manda. No rellenar cuatro cards si sólo hay dos magnitudes válidas. Los conteos de cobertura y la fecha de último dato suelen funcionar mejor como metadata que como KPIs ejecutivos.

En Mayoristas, los extremos mínimo/máximo describen la selección: no son desviación estándar, intervalo de confianza ni dispersión de un único producto si se seleccionaron varios. Las variaciones conservan exactamente su período y definición actual. Un promedio simple de una selección no se presenta como índice de mercado ni precio de canasta ponderado.

### Cards analíticas

Encabezado con título descriptivo y nota breve. Cuerpo con una visualización dominante y espacio suficiente para ejes y tooltip. Chart.js sigue siendo el motor actual. No modificar sus datasets para aproximar la curva de un mock.

Proporción 2/3 + 1/3 útil cuando hay una evolución y una distribución complementaria; no es una obligación. En Mayoristas, evolución y ranking pueden formar el primer bloque, con rango y variaciones a continuación. En una serie única, no forzar un ranking sin dimensión válida. Si un panel desaparece por las compuertas existentes, la grilla debe aprovechar el ancho libre.

Priorizar líneas temporales, barras horizontales para rankings, barras de comparación y matrices sólo si sus dimensiones lo permiten. No crear gauges, scores, mapas, donuts con muchas categorías o gráficos repetidos para imitar una referencia.

### Tabla y detalle bajo demanda

La tabla aparece mediante un disclosure nativo con summary claro. Conserva encabezados, valores exactos, unidades, fuentes y notas metodológicas. Búsqueda y paginación son operaciones de presentación sobre filas ya calculadas; no cambian los resultados analíticos. Paginación habitual: 10 filas; informar cantidad filtrada y total. El detalle mantiene scroll horizontal local cuando las columnas lo exigen.

No limitar una descarga a la página visible sin indicarlo. No prometer CSV si el módulo no tiene esa descarga. Las tablas no sustituyen rankings ni organizan el layout de página. Una matriz mensual es una tabla analítica válida; no se la denomina patrón estacional histórico sin ese cálculo.

### Metodología y trazabilidad

Mantener una nota económica breve junto al bloque relevante y el texto extendido bajo demanda. La unidad comparable, el carácter simple/no ponderado y las diferencias de fuente no son detalles técnicos prescindibles. El detalle de observación permite auditar; una imagen decorativa o un color nunca reemplaza la fuente.

## Responsive y accesibilidad

| Ancho orientativo | Regla |
|---|---|
| Desktop >1100 px | Rail contextual, filtros en barra, KPIs en fila, grilla analítica según contenido |
| Intermedio 701–1100 px | Rail reducido, filtros y KPIs en varias filas, evolución con ancho suficiente; evitar charts estrechos |
| Móvil ≤700 px | Navegación contextual horizontal, controles en 1–2 columnas, cards apiladas, tablas con scroll propio |
| Muy estrecho ≤420 px | KPI en una columna cuando el valor/unidad lo requiera |

Validar al menos 1440, 1000, 900 y 640 px, así como zoom y teclado. No debe aparecer scroll horizontal de la página; un contenedor tabular sí puede tenerlo. El orden del DOM debe acompañar la lectura. Foco visible de 2 px en menta con separación. No retirar controles de teclado ni ocultar mensajes de error para ajustar el layout. Evitar cambiar cálculos cuando sólo se pretende mejorar la presentación.

## Aplicación por módulo

| Módulo | Preguntas y énfasis | Reutilizar | Adaptar / no trasladar |
|---|---|---|---|
| Carnes, aprobado | Magnitud publicada, cambio, acumulado, concentración/composición | Referencia visual y componentes existentes | Conservar límites provincia/categoría, peso publicado y comparabilidad |
| Mayoristas | Precio, cambio, extremos, evolución, productos, mercado/fuente | Shell, controles, cards, estados, detalle | No copiar cabezas, YTD físico o concentración territorial; no sumar precios ni atribuir cambios a escasez |
| Cantidades, futuro | Volumen, destinos, especies, estacionalidad | Navegación, jerarquía, fuentes, detalle | Agregaciones físicas según unidad; no reutilizar promedio de precios |
| Commodities, futuro | Nivel/cambio de cada referencia de precio | Presentación institucional y trazabilidad | Mantener separadas operaciones, pizarra, FAS/FOB, referencias internacionales, monedas y plazas |

## Criterios de aceptación de una adopción

- La composición responde a preguntas del módulo y no duplica las cards de Carnes por conveniencia.
- Todo componente visible tiene dato, definición o acción válida. Faltantes y estados se comunican.
- Antes/después a 1440 y 900 px, más comprobación de 1000/640 y estados de filtros/detalle.
- Comparación exacta de KPIs, datasets de charts, filas y solicitudes de carga, en selecciones representativas.
- Pruebas existentes del módulo y verificación de que Carnes aprobado no cambia.
- Sin cambios en fuentes, cálculos, loaders, shards o pipelines; sin merge automático.
