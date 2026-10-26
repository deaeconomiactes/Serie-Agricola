# Commodities — adopción visual institucional

Trabajo local en `codex/ui-refresh-institucional-commodities`, creado desde main `193b29131fc9ea3263b3ae9652c6874f519f2074` el 26/10/2026. Referencia: [design system institucional](SERIE_AGRICOLA_DESIGN_SYSTEM.md). No se reutilizó la rama de Carnes.

## Composición y componentes

La pantalla se organiza por identidad de referencia: sidebar de seis familias, encabezado dinámico con producto/plaza/moneda/unidad/frecuencia, estado original visible, filtros compactos, nivel y cambios de una serie, evolución dominante y ranking lateral. Los conteos de cobertura se muestran como metadata. No hay hero fotográfico ni indicadores físicos de Carnes trasladados a precios.

Se reutilizan tokens slate/menta, navegación global compacta, rail contextual, labels visibles, controles de 34 px, superficies discretas, radios de 4–6 px, escala de spacing, jerarquía tipográfica y disclosures accesibles. Los iconos existentes de la biblioteca Phosphor conservan su licencia.

El adaptador `commodities-ui.js` mueve nodos existentes sin reemplazar sus IDs o eventos. `commodities-ui.css` sólo afecta Commodities. `app.js`, `commodity-history.js`, datos, fuentes, estados, pipelines, shards y workflows permanecen intactos.

Las leyendas extensas y los rótulos laterales se abrevian sólo para dibujarlos dentro del panel. Los labels originales de datasets y sus tooltips permanecen completos. No se eliminan dimensiones de identidad para abreviar una leyenda SIO.

Las etiquetas extensas usan códigos locales E (evolución), R (ranking) y A (actividad), junto a producto/plaza o vencimiento. «Ver etiquetas completas» vincula cada código con su texto original y expone también la selección completa de filtros abreviados. Son identificadores de presentación de la selección vigente, no scores ni nuevos IDs económicos. Las opciones mantienen su valor original, `data-full-label`, título y nombre accesible completos. Los títulos/KPI abreviados conservan los nodos originales y el texto completo como tooltip.

## Reglas específicas

- **Precio interno, Pizarra y FAS:** evolución/ranking originales y valores comparables por serie. Fecha y cobertura quedan en el encabezado; no se cambia la definición de mensual publicado o derivado.
- **FOB:** advertencia visible sobre contextos SSPM histórico/API corriente. Se preservan sus identidades, tipos, moneda/unidad y compuertas existentes; no se une una serie a otra ni se infiere equivalencia entre posición y producto. Año, tipo y moneda siguen determinando el contexto original.
- **Futuros:** fecha de observación y vencimiento se explican por separado. La selección del contrato permanece en Más filtros. La curva adicional es una proyección de registros publicados de una misma fecha, sin roll, promedio ni interpolación.
- **SIO:** se conserva `sio-transactions-v2`, lugar de entrega, procedencia y condición separados; se habla de operaciones/eventos informados, no de precio spot o de plaza. Mediana, operaciones y último período son principales; variaciones permanecen disponibles por serie en el detalle. El volumen informado sigue en su gráfico original bajo demanda.
- **Varias series:** se muestra una sola invitación «Seleccioná una serie»; no se inventa un KPI global. Los nodos/valores originales permanecen disponibles para comparación automatizada y la tabla conserva los valores individuales.

## Visualizaciones y métricas

| Componente | Pregunta | Regla / fórmula | Dimensiones y comparabilidad | Sin base |
|---|---|---|---|---|
| Valor de referencia o mediana de eventos | ¿Cuál es el valor de mi serie? | Valor original de `updateCommodityKpis`; no se recalcula en el adaptador | Identidad completa de serie; moneda/unidad separadas | «Seleccioná una serie» o estado vacío original |
| Variación corta y larga | ¿Cómo cambió? | Porcentajes ya calculados por el módulo: mensual/interanual o 7/30 días, con sus labels originales | Misma serie y base admitida por main | «Sin dato comparable» original; no se rellena |
| Último período / cobertura | ¿De cuándo es el dato? | Fechas originales de selección y resumen, sin sustituir por captura o vencimiento | Observación y actualización separadas | Texto original sin datos |
| Operaciones / observaciones | ¿Cuántos eventos o publicaciones? | Conteo original de operaciones de la selección | Se conserva definición de cada familia; no son contratos vigentes | Estado original |
| Evolución | ¿Cómo evolucionó? | Mismos labels, datasets y tooltips de main | Todas las separaciones originales de producto, plaza, fuente, tipo, moneda, unidad y posición | Compuerta/mensaje original |
| Ranking lateral | ¿Qué referencias estoy comparando? | Ranking original de últimos valores por serie, sin reordenar ni recalcular datos | Fechas y condiciones en tooltip/detalle; comparación descriptiva | Estado original |
| Curva por vencimiento | ¿Cómo difieren contratos a una misma fecha? | Para la fecha elegida: `vencimiento → precio_mediana` publicado, sin agregación | Diario, un producto/mercado/moneda/unidad/tipo; fechas explícitas; al menos dos vencimientos únicos | Se omite ante selección múltiple, unidad desconocida, vencimiento ambiguo o duplicado |
| Actividad / volumen | ¿Qué actividad informa la fuente? | Dataset original de observaciones o volumen informado | Se conserva denominación y alcance existentes | Mensaje original |
| Semáforo mensual | ¿Qué cambios mensuales registra cada serie? | Valores, porcentajes y estados originales sin cambiar umbrales | Mismas series y meses que main | Celdas/estados originales |

La normalización visual del orden de vencimientos acepta ISO año-mes/fecha y abreviaturas españolas con año explícito (incluidos SEP/SET). No calcula días al vencimiento ni completa un día ausente. El eje conserva las etiquetas originales.

No se añaden spreads entre referencias, estacionalidad, bandas históricas, dispersión global ni un nuevo heatmap: exigirían nuevos cálculos o garantías metodológicas adicionales. La matriz conservada se denomina semáforo mensual, no patrón estacional histórico.

## Tablas, descargas y trazabilidad

Últimos valores y matriz mensual se abren a pedido, con búsqueda y páginas de diez series. La búsqueda y paginación sólo cambian visibilidad de filas, sin filtrarlas del análisis. Se conserva scroll horizontal local y encabezados de unidades, períodos y condiciones.

La descarga CSV exporta todas las filas del detalle de últimos valores por serie, con encabezados y campos visibles originales; no sólo la página o búsqueda actual. Se informa expresamente que no exporta el histórico completo. IDs, source_url, capture, flags, hashes y campos de origen disponibles se consultan en un disclosure técnico, construido al abrirlo. Los datos que la fuente no publica no se inventan.

## Responsive y teclado

1440 px: rail + evolución dominante + ranking lateral. Hasta 1100: filtros en varias filas y visualizaciones apiladas. Hasta 700: rail como disclosure, controles en dos columnas y paneles apilados. A 375: KPIs en una columna. Foco visible menta, labels conservados y Escape para cerrar disclosures. Tablas con scroll local; sin desborde global.

## Verificación y evidencia

Snapshots antes/después de seis familias, con selección general y selección de producto/plaza, comparan filtros, filas, últimos valores, KPIs, datasets, ranking, semáforo, estados y metadata. Capturas a 1440/900/375; aceptación funcional adicional a 1000/640, en Edge y Chrome.

Evidencia fuera de Git: `C:/Users/acer/Oficina/commodities-ui-evidence/20261026/`.

El smoke `tests/commodities/browser_ui_checks.py` prueba navegación contextual, filtros/Escape, detalle, paginación, búsqueda, CSV completo, responsive, títulos entre módulos y curva frente a los registros originales. El smoke SIO existente conserva sus comprobaciones económicas y sólo adapta los accesos a disclosures.

No se realizaron commit, push ni merge. Los estados operativos de las fuentes son los que publica main y no se corrigen desde este piloto visual.
