# Mayoristas · adopción del sistema visual de Serie Agrícola

Referencia: [sistema de diseño](SERIE_AGRICOLA_DESIGN_SYSTEM.md), extraído del piloto Carnes aprobado. Rama local `codex/ui-refresh-institucional-carnes`; sin commit, push, merge ni publicación.

## Presentación implementada

- Navegación global compacta y marca institucional sólo mientras Mayoristas está activo.
- Sidebar de secciones: evolución, productos, mercados/fuentes, detalle mensual, actualización y metodología. No copia las familias Faena/Producción/Peso.
- Header con fecha del último dato y cobertura de especies/variedades existentes. No se añade una imagen por obligación.
- Barra principal: año, frecuencia, especie y mercado. Más filtros conserva mes, rubro, variedad, procedencia, unidades/modo comparable y atributos MCBA, con sus IDs, opciones, eventos y multiselección originales.
- Tres indicadores principales: promedio y extremos de variación de la serie según la definición existente. El promedio se identifica como resumen simple de la selección, no como índice de mercado ni canasta ponderada.
- Mínimo/máximo en un bloque separado de extremos observados. Pueden pertenecer a diferentes productos: no se presentan como intervalo estadístico ni como dispersión de una serie única.
- Evolución y ranking contextual en primera fila; variaciones y mercados en segunda. Las compuertas de disponibilidad del módulo siguen vigentes. Con un solo mercado, se conserva el mensaje existente.
- Rankings ampliados de subas/bajas bajo demanda. El disclosure se oculta si las dos cards están ocultas por la lógica existente, por ejemplo en vista diaria.
- Matriz mensual bajo demanda, búsqueda y paginación de 10 filas. Su cálculo, valores, colores/umbrales, definición y máximo de productos permanecen intactos. No se presenta como estacionalidad histórica: ese gráfico no existe en el módulo y añadirlo requeriría un cálculo nuevo, fuera del alcance autorizado.
- Estados problemáticos de fuente, integridad, unidad y carga permanecen visibles. Se replican los avisos de fuente warning/error fuera de la metadata cerrada, sin inferir ni modificar su estado.

## Separación de responsabilidades

`mayoristas-ui.css` aplica estilos a Mayoristas. Los tokens de referencia no sustituyen los estilos de Carnes.

`mayoristas-ui.js` sólo gestiona navegación/foco, disclosures, resize de Chart.js al abrirlos, réplica de avisos ya calculados y búsqueda/paginación sobre filas renderizadas. No accede a observaciones, no calcula precios o variaciones, no dispara filtros, no hace fetch y no altera datasets.

`index.html` reorganiza nodos conservando todos los IDs anteriores sin duplicarlos. `tests/mayoristas/browser_delivery.py` abre Más filtros para seguir probando el mismo control Mes y comprueba que la vista diaria no exponga un disclosure vacío. `tests/mayoristas/browser_visual.py` verifica interacciones nuevas, snapshots y responsive.

Comparados con el respaldo de inicio de esta adopción, `app.js`, `carnes.js` y `styles.css` son byte idénticos. No se modificaron datos, cálculos, loaders, fragmentos, fuentes ni pipelines. Los cambios anteriores del piloto que ya estaban en la rama se conservan.

## Validación

- 18 tests focales Node: entrega fragmentada, equivalencia económica exacta de 11 selecciones, MCBA, frescura, errores e integridad. Aprobados.
- Snapshot mensual antes/después idéntico en Edge y Chrome: filtros, frecuencia, todas las filas filtradas, los ocho valores de KPI, labels/datasets de todos los charts y HTML de la matriz (sin el atributo visual de paginación).
- Browser delivery Edge/Chrome: particiones 2024–2026, cambio a diario MCBA, selección rápida, corrupción con última vista válida, exclusión de publicaciones completas y responsive.
- Browser visual Edge/Chrome: Más filtros/Escape, dropdown de especie por encima del contenido, apertura de metodología y detalle con foco, búsqueda, paginación y ausencia de desborde global a 1440/1000/900/640 px.
- Entrada Mayoristas: 3 solicitudes de datos y 849.526 bytes, sin cambios.
- Regresión Carnes: `carnes.js` y estilos aprobados sin cambios; captura de Faena 1440 idéntica píxel a píxel. En 900 sólo difiere un área de 3 × 4 px del antialiasing del símbolo global; layout y contenido sin cambios. Capturas de las tres familias conservadas.
- Revisión independiente de interpretación económica y accesibilidad: sin bloqueantes. Se corrigió el único hallazgo menor, el disclosure vacío.
- Sintaxis JS y `git diff --check` aprobados.

Evidencia fuera de Git: `C:/Users/acer/Oficina/carnes-ui-evidence/mayoristas-before/`, `mayoristas-after/` y `mayoristas-review.html`. Incluye antes/después completos a 1440/900 y estados de filtros/detalle. La comparación usa el estado inmediatamente anterior de Mayoristas y el lenguaje aprobado de Carnes; no busca duplicar sus gráficos.

## Comandos de verificación

```text
node --test tests/magyp_frontend/mayoristas-delivery.test.cjs tests/magyp_frontend/mcba.test.cjs tests/magyp_frontend/price-freshness.test.cjs
python tests/mayoristas/browser_delivery.py --url http://127.0.0.1:8767 --channel msedge --output <carpeta-fuera-de-Git>
python tests/mayoristas/browser_visual.py --url http://127.0.0.1:8767 --channel chrome --output <carpeta-fuera-de-Git>
```
