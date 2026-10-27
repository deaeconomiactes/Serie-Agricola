# Cantidades — validación del piloto local

## Alcance

Base main `4eb8e29`, rama `codex/ui-refresh-institucional-cantidades`. Nuevos CSS/JS de presentación y analítica descriptiva, inclusiones en HTML, tests y documentación. Sin cambios en `app.js`, datos, unidades, loaders, fuentes, metodología de origen, pipelines o workflows. Diseño aprobado para publicar en PR; sin merge automático.

## Control de datos y equivalencia

- Base interpretada: **49.494 registros** (2024: 11.185; 2025: 38.309).
- Selección inicial 2025: **38.309 registros**, **1.343.289,23 TN**; el total flotante de main es 1343289.2300000011, preservado exactamente.
- El smoke realiza un control independiente con CSV/Decimal; cuenta filas elegibles y suma sus pesos publicados, sin usar el nuevo helper para determinar el resultado esperado.
- 2024: 1.410.775,70 TN. Ambos años contienen registros de doce meses; esto no acredita igual completitud ni autoriza por sí solo una variación interanual.
- Indicadores descriptivos de 2025: producto principal Papa, 318.136,5 TN y 23,7%; Top 5: 52,9%; 223 productos y 45 categorías de procedencia (incluye no informadas).

Snapshots antes/después en Edge y Chrome comparan **siete contextos**: inicial, 2024, todos los años, 2025, procedencia Corrientes, una especie disponible en esa selección y frecuencia diaria. Coinciden exactamente filas, cantidad de registros, volumen, unidad, filtros/opciones, períodos, once valores/textos KPI originales, todos los labels/datasets originales, heatmap y matriz tabular original.

Los nuevos descriptores no reemplazan esos valores. Top 5 mantiene el total completo como denominador, las unidades mixtas/inválidas se rechazan y los meses sin observación quedan como huecos en la composición.

## Revisión visual y funcional

El filtro de ocho dimensiones y seis cards deja lugar a una barra compacta, tres KPIs y un gráfico dominante con ranking lateral. Procedencias dispone de un ranking propio; composición usa barras 100% apiladas. El heatmap se presenta como patrón observado, con scroll local. Donuts y matriz extensa salen de la lectura principal.

El detalle tiene diez filas, búsqueda, navegación de páginas, CSV completo y metadatos bajo demanda. La descarga se valida por conteo y suma Decimal contra el CSV fuente. Se verifican filtros/cascadas, año, diaria, teclado/Escape, navegación contextual, títulos entre módulos y responsive 1440/1000/900/640/375. No hay scroll horizontal global.

Las capturas «antes» de Procedencias muestran los controles anteriores: no había ranking propio. El detalle anterior era una matriz mensual, no una tabla completa de registros; la comparación visual indica esa diferencia de función.

## Tests

- Frontend completo repetido al consolidar: **116/116**, incluidas las seis pruebas nuevas de Cantidades.
- Nuevas pruebas Cantidades: **6/6** (denominador, categorías repetidas, Top 5, unidades/valores inválidos, ausencia de base y composición sin interpolar).
- Smoke Edge y Chrome correcto, con control independiente del CSV, CSV descargado, detalle y responsive.
- `node --check` de los nuevos JS y `git diff --check` correctos.

## Carga y límites

Mismas **dos solicitudes de datos / 3.949.561 bytes**: CSV 3.931.671 y metadata común 17.890. Sin APIs o datos nuevos. Medición local orientativa: 22,643 s antes y 23,181 s después; no es un benchmark ni una promesa de mejora. Se conserva el coste del motor existente, más descriptores y dos charts adicionales.

La fuente es estática y no tiene actualización/captura acreditada. No se calcula i.a., pp i.a. ni estacionalidad estructural. Se conserva año/frecuencia, sin agregar filtro de mes. Las categorías de origen no se homologan geográficamente. No se corrigen vacíos o diferencias de cobertura desde esta rama.

Evidencia fuera de Git: `C:/Users/acer/Oficina/cantidades-ui-evidence/20261026/`: `revision.html`, comparaciones de Resumen/Productos/Procedencias/Patrón mensual/Detalle a 1440/900/375, snapshots, `equivalence.json`, `load-equivalence.json` y reportes de smokes.

Preview local: `http://127.0.0.1:8771/`. Listo para revisión del usuario; no implica aprobación de publicación.
