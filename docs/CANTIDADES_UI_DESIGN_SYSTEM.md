# Cantidades transadas — adopción institucional

Rama: `codex/ui-refresh-institucional-cantidades`. Base: main `4eb8e29`, con los pilotos Carnes, Mayoristas y Commodities incorporados. Diseño aprobado para publicación mediante PR; integración a main pendiente de revisión.

## Presentación

Se aplica [SERIE_AGRICOLA_DESIGN_SYSTEM.md](SERIE_AGRICOLA_DESIGN_SYSTEM.md): navegación global compacta, sidebar contextual, superficies slate, acento menta, tipografía Inter, controles compactos, foco visible y detalle bajo demanda. No se copian los KPIs económicos de precios ni las magnitudes de Carnes.

La lectura prioriza volumen y distribución: header con selección, TN, frecuencia, fechas observadas y estado **Fuente estática**; filtros año/rubro/producto/procedencia/frecuencia; tres indicadores principales; evolución dominante y Top 10 de productos; composición mensual porcentual; procedencias e insight factual; perfil mensual observado; variedades y registros bajo demanda.

No hay timestamp inventado: la fuente es el archivo integrado del proyecto. El CSV contiene registros de 2024–2025 en TN. «Último dato» se obtiene de las fechas de la selección, no del reloj ni del último commit. Los gráficos originales conservan sus observaciones y algoritmos.

`cantidades-ui.css` sólo afecta Cantidades. `cantidades-ui.js` mueve controles/cards y consulta vistas existentes; `cantidades-analytics.js` calcula descriptores adicionales sobre copias lógicas de las filas, sin escribir datos ni cambiar unidades. `app.js`, loaders, fuentes, pipelines y demás módulos permanecen intactos.

## Métricas y visualizaciones

| Componente | Pregunta | Fórmula / procedencia | Condiciones | Sin base |
|---|---|---|---|---|
| Volumen transado | ¿Cuánto se observó? | Copia exacta de `totalProduction`, calculado por `sumPeso(filteredData)` | Mismos filtros y unidad del módulo existente | Sin registros |
| Producto principal | ¿Qué producto predomina? | Agrupar `peso` por `especie`; máximo por volumen. Participación = volumen del producto / volumen total × 100 | Registros positivos finitos y TN; nombres tal como los interpreta main | Sin registros / sin unidad compatible |
| Concentración Top 5 | ¿Cuánto concentran los productos principales? | Suma de volúmenes de los cinco primeros productos / volumen de **todos** los productos × 100 | Igual selección y TN; con menos de cinco, se incluyen los disponibles | Sin datos; no se fabrica un porcentaje con denominador cero |
| Conteos descriptivos | ¿Qué variedad de categorías hay? | Número de claves distintas de producto/procedencia con peso positivo | Las procedencias son categorías originales, incluidas etiquetas no informadas; no se geocodifican ni fusionan | Cero categorías |
| Evolución | ¿Cómo cambia el volumen? | Gráfico original `chartMonthly`, con mismas series, períodos y datos | Frecuencia diaria/mensual/anual original; no se cambia su agregación ni se incorpora media móvil | Estado original |
| Ranking de productos | ¿Qué productos explican el volumen? | `chartTop10` original, mismo orden y valores | Misma selección; sólo cambia ubicación/presentación | Estado original |
| Composición por rubro | ¿Cómo cambia la distribución mensual? | Para cada mes: TN de frutas u hortalizas / suma de ambas × 100 | Proyección de `chartSeriesMonthly` original, que conserva sus TN y redondeo. No son pp interanuales | Mes sin volumen = hueco, no cero artificial |
| Procedencias | ¿Qué categorías predominan? | Agrupar `peso` por `origen`, ordenar y mostrar Top 10; participación sobre el total completo | No se confunden origen y destino ni se interpreta una categoría como provincia validada | Sin registros |
| Perfil observado | ¿Qué patrón mensual muestra la cobertura? | Heatmap producto × mes original, mismos valores/colores y filtros | Top 20 original; si se seleccionan varios años, los meses combinan esos años. Es perfil observado, no estacionalidad estructural | Celdas originales |

## Comparabilidad y límites

No se calcula variación interanual ni cambio de composición en pp: el archivo no acredita equivalencia de cobertura, procedencia metodológica y completitud anual. Tener doce meses con registros no certifica doce meses completos. Se comunica **Sin base comparable acreditada**, sin rellenar una cuarta card.

No se crean índices HHI, gauges, mapas, medias móviles o bandas estadísticas. El cambio temporal se lee en la evolución original. La historia de dos años no fundamenta una conclusión de estacionalidad estable ni una explicación causal de variaciones.

Se conservan todos los filtros existentes y su comportamiento. Año y frecuencia delimitan el período; no se añade un nuevo filtro de mes que altere la lógica de selección actual. Destino y municipio están bajo «Más filtros»; municipio mantiene su compuerta original para Corrientes.

## Detalle y continuidad

«Ver detalle de registros» ofrece fecha, producto, procedencia, peso y unidad, diez filas, búsqueda y paginación. El CSV contiene **toda la selección vigente**, sin limitarse a búsqueda o página. Incluye también destino, variedad, municipio y rubro. Los valores son los registros ya interpretados por main; no se reconstruye el CSV original ni se inventan IDs/capturas.

El detalle técnico identifica el archivo y muestra la fila interpretada seleccionada. Al cambiar filtros se invalida ese detalle para evitar confundir registros de selecciones distintas.

Las seis cards antiguas, donuts, comparación adicional por destino y matriz tabular antigua salen del recorrido visible. Sus nodos/datasets siguen presentes en un contenedor oculto de compatibilidad porque `app.js` los calcula; así se verifica equivalencia sin tocar la lógica aprobada. La consulta principal de registros es nueva, paginada y bajo demanda. Variedades sigue accesible en un disclosure.

## Responsive, performance y tests

1440 px: rail + evolución 2/3 y ranking 1/3. 1000/900: stack progresivo. 640/375: rail en disclosure, filtros en dos columnas, cards apiladas, tablas y heatmap con scroll local. Foco menta, labels asociados y Escape para disclosures.

No hay nuevas consultas de datos. La tabla de registros construye diez filas al abrirse; no crea 38.309 filas de entrada. El motor original sigue calculando sus vistas de compatibilidad, por lo que no se afirma una reducción de cálculo o memoria. Se añaden dos charts descriptivos.

Ver [CANTIDADES_VISUAL_QA_2026-10-26.md](CANTIDADES_VISUAL_QA_2026-10-26.md) para controles, equivalencia y evidencia.
