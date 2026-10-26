# Commodities — validación visual y funcional

## Alcance

Rama nueva `codex/ui-refresh-institucional-commodities`, base main `193b291`. Implementación local sin commit, push ni merge. Sistema y criterios: [COMMODITIES_UI_DESIGN_SYSTEM.md](COMMODITIES_UI_DESIGN_SYSTEM.md).

Cambios productivos limitados a `index.html` (inclusión de CSS/JS y footer), `commodities-ui.css` y `commodities-ui.js`. Se conservaron íntegros `app.js`, loaders, fuentes, datos, cálculos, metodología, estados, granularidad SIO, pipelines, shards y workflows. El smoke SIO sólo adapta el acceso a los nuevos disclosures; sus controles económicos permanecen.

## Revisión visual

Antes predominaban una gran grilla de filtros, siete cards, gráficos sucesivos y tablas extensas en la lectura principal. Ahora la identidad de la referencia organiza la lectura: seis familias en sidebar, header dinámico, filtros primarios en barra, dimensiones específicas bajo demanda, hasta cuatro KPIs y evolución con ranking lateral. Los conteos pasan a metadata; varias series muestran una única invitación a seleccionar, sin inventar un precio global.

Se reutilizan el shell, tokens slate/menta, jerarquía tipográfica, controles, estados y disclosures aprobados. La composición se adapta a precios: no incorpora métricas físicas de Carnes, hero fotográfico ni paneles administrativos. Se verificaron correcciones de altura de canvas al alternar viewports y etiquetas del ranking legibles en el ancho lateral; no se alteraron datasets.

El estado de adquisición original y el mensaje de carga/error permanecen visibles en el header. La fecha de observación y el vencimiento se distinguen en futuros. FOB muestra la separación SSPM/API; SIO conserva entrega, procedencia y condiciones como dimensiones independientes.

## Equivalencia

Comparación por navegador de doce contextos: selección general y selección válida de producto/plaza en Internos, Pizarra, FAS, FOB, Futuros y SIO. Igualdad exacta de:

- filtros, opciones, selección, frecuencia y año;
- filas filtradas y últimos valores por serie;
- siete valores KPI originales, aunque algunos pasan a metadata o detalle;
- labels y datasets de evolución, ranking y actividad/volumen;
- todas las celdas y estados del semáforo;
- tabla original (se excluye sólo el atributo de visibilidad de paginación);
- metadata, metodología y estados originales.

La curva nueva se valida independientemente contra registros publicados de una sola observación: nueve vencimientos para HARINA DE SOJA / CHICAGO el 23/10/2026. Cada punto coincide exactamente con `precio_mediana` del registro correspondiente. No se altera el gráfico temporal existente, no se crea roll ni se reconstruye precio alguno.

## Tests y navegación

- Frontend completo: **110/110**.
- Commodities/histórico/estados/SIO específicos: **42/42**.
- Python comunes: **74/74**.
- Python SIO: **13/13**.
- Smoke institucional Edge/Chrome: familias, selección activa, Más filtros/Escape, estados, detalle, búsqueda, paginación, CSV completo, curva publicada y cambio de títulos entre módulos.
- Smoke SIO Edge/Chrome: mismo control económico **195**, una serie con entrega/condición/procedencia explícitas, detalle y capturas conservados, vuelta al mensual e Internos.
- Responsive: **1440, 1000, 900, 640 y 375 px**, sin desborde horizontal global. Sidebar como disclosure móvil, foco visible y tablas con scroll propio.
- Sintaxis JS y `git diff --check`: correctos.

Durante la implementación se corrigieron incidencias de la capa visual y se repitieron sus smokes. No se cambiaron pipelines ni datos para resolverlas. Los tests de navegador esperan la inicialización efectiva antes de pulsar la navegación, además de comprobar el overlay.

## Performance

Mismas **24 solicitudes de datos / 9.244.096 bytes** en la apertura de Commodities antes/después. Se verificaron rutas, estados HTTP y tamaños exactos. El adaptador no incorpora fetch ni consultas de API. CSS/JS nuevos: aproximadamente **36 KB**, más los pequeños iconos existentes.

La medición local aislada fue 13,945 s antes y 10,959 s después; es orientativa y no demuestra una mejora de velocidad, por variabilidad de máquina/caché. El coste de adquisición y preparación de las vistas permanece en el loader actual. Colapsar tablas no elimina la construcción original de filas ni reduce por sí solo el consumo de memoria.

## Límites y entrega

- El estado operativo de cada fuente sigue siendo el publicado por main; este piloto no corrige incidentes de actualización.
- FOB API conserva moneda/unidad sin identificar cuando así están publicadas. No se calcula spread con SSPM.
- No se incorporan spreads, bandas, estacionalidad ni heatmap estadístico nuevos: no están autorizados cambios de cálculo/metodología. Se conserva el semáforo mensual original.
- La curva se omite si faltan vencimientos inequívocos, hay duplicados o no puede aislarse una combinación compatible.
- CSV: últimos valores por serie filtrada, todas sus filas; no se presenta como histórico completo.

Evidencia local: `C:/Users/acer/Oficina/commodities-ui-evidence/20261026/`. `revision.html` contiene comparaciones de las seis familias a 1440/900/375; `equivalence.json`, `load-equivalence.json`, snapshots y logs permiten auditar el resultado. Preview: `http://127.0.0.1:8770/`.

Lista para revisión visual del usuario. No constituye autorización de merge o publicación.

## Ajuste posterior: etiquetas compactas

Se abreviaron encabezados, labels KPI, opciones extensas, leyendas, ejes y nombres de series del semáforo. Los códigos E/R/A/M identifican únicamente referencias de la vista; «Ver etiquetas completas» conserva la correspondencia original y la selección completa de filtros. Destino/origen se abrevian sólo cuando el sufijo literal lo informa. Tooltips, valores de selectores, datasets, descarga y trazabilidad mantienen su información original.

Validación focal: Edge funcional correcto; Chrome verifica SIO y Futuros, igualdad exacta de filas/últimos valores/datasets, celdas y labels originales del semáforo, valores/opciones de filtros aplicables y acceso a textos completos. Capturas a 1440/900/375 en `compact-labels/`. Sintaxis JS y diff correctos. No se repitieron suites económicas sin cambios de lógica.

## Publicación autorizada por PR

Posteriormente al cierre local, el usuario autorizó commit, push y PR, sin merge automático. Se incorporó main `8530b7e` por fast-forward, sin conflictos, preservando sus actualizaciones de estados MCBA y frescura. El diff de datos, app.js, loaders, scripts y workflows frente a esa base permanece vacío.

Se repitieron frontend completo (110/110, incluidos Commodities y SIO), Python comunes (74/74), Python SIO (13/13), smokes institucionales y SIO en Edge/Chrome, equivalencia de etiquetas compactas y `git diff --check`. Edge agotó el tiempo de arranque en el primer intento; la repetición aislada y el smoke SIO terminaron correctamente. No se modificó el arranque ni un loader para resolverlo. Control SIO: 195 en ambos navegadores.

Se publica únicamente UI, estilos, tests y estos documentos; la excepción de `.gitignore` permite incluir los tests Python de Commodities. Baselines, capturas, logs y auxiliares permanecen fuera de Git, en `publicacion/` dentro de la carpeta de evidencia local. Los workflows existentes no tienen disparador de PR; no se lanzó el deploy de producción.
