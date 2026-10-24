# Precios mayoristas · cierre visual y funcional

Fecha: 24/10/2026. Rama: `codex/ui-refresh-institucional-carnes`.

**Estado: APROBADO visual y funcionalmente para integración manual del cambio.**

**Recomendación: merge manual, conservando las actualizaciones de datos/estados de main y pasando el CI del PR.** No se ejecutaron commit, push, merge, rebase ni despliegue. La aprobación no certifica que las fuentes estén actualizadas hoy.

## 1. Flujo revisado

1. Abrir el preview local y entrar a Precios mayoristas.
2. Revisar metadata, filtros principales y Más filtros, multiselección y Escape.
3. Contrastar los KPIs, la evolución, los rankings y los extremos con la versión anterior.
4. Abrir Detalle mensual desde la sidebar: comprobar foco, búsqueda, páginas 1/2 y 2/2 y cierre.
5. Comprobar años 2024–2026, frecuencia diaria MCBA, selección rápida y conservación de la última vista válida ante corrupción.
6. Revisar desktop y responsive, además de la compatibilidad con la metadata más reciente de main.

El preview se abrió e inspeccionó en el navegador integrado. Se complementó con pruebas Edge y Chrome y capturas nuevas de esta revisión.

## 2. Revisión visual concreta

| Antes | Después / mejora |
|---|---|
| Cabecera frutihortícola y navegación con mucho peso vertical | Marca Serie Agrícola compacta y cabecera específica de Mayoristas |
| Diez filtros expuestos junto a secundarios | Año, frecuencia, especie y mercado como primer nivel; demás dimensiones bajo Más filtros |
| Ocho cards con protagonismo similar | Tres KPIs principales; mínimo/máximo en bloque de extremos; fecha/cobertura en metadata |
| Evolución, rankings y mercados en una secuencia larga | Evolución y ranking juntos; variación y mercados como segundo bloque |
| Matriz mensual abierta en el recorrido normal | Detalle cerrado, búsqueda y paginación de 10 filas sobre la misma matriz |
| Subas/bajas ampliadas siempre en el recorrido | Consulta bajo demanda; se oculta cuando sus dos charts ya están ocultos |

Se reutilizan navegación global, sidebar contextual, paneles slate, menta de selección/foco, símbolos de KPI, geometría de controles/cards, escala tipográfica, gutters, disclosures, estados y comportamiento responsive del sistema aprobado. Se adaptan el contenido, la jerarquía y las proporciones a precio/cambio/rango/mercados. No se copian cabezas, YTD físico ni concentración provincial.

A 1440 px, la vista mensual inicial pasa de **5152 a 1719 px de altura**. A 900, de **4889 a 2653 px**. Es reducción del recorrido por composición y detalle cerrado, no una reducción de datos ni una medida de velocidad.

La matriz anterior tiene 20 productos y 12 meses, más columnas auxiliares. Se conserva completa; sólo se muestran 10 filas por página al solicitarla. No se afirma que la búsqueda incluya observaciones ajenas a la matriz calculada, cuyo límite original sigue intacto.

## 3. Ajustes de este cierre

- Título del documento contextual: `Precios mayoristas · Serie Agrícola` al activar el módulo. Al salir se restaura el título anterior. Se corrige la identidad de la pestaña sin cambiar las otras vistas.
- Nota con tono institucional: el promedio resume la selección y no representa una canasta ponderada ni un índice de mercado.
- Metadata de fuente/selección alineada a la izquierda para facilitar lectura de referencias largas.
- Versiones de caché de los dos recursos de presentación actualizadas a v2.
- Prueba visual ampliada a 375 px y verificación del título/restauración.

Los ajustes sólo afectan presentación y copy. No se modificó ninguna fórmula, agregación, filtro económico, loader o pipeline.

## 4. Confirmaciones funcionales

| Componente | Resultado y evidencia |
|---|---|
| Filtros | Aprobado: año, mes, mercado, frecuencia; multiselección y desplegable de especie; Más filtros/Escape; conservación de selección ante error |
| KPIs | Aprobado: ocho valores antes/después idénticos; tres principales con contexto, extremos y cobertura conservados |
| Evolución | Aprobado: labels y datasets idénticos; diaria/mensual y cambios de año; sin interpolación o agregación nueva |
| Rankings | Aprobado: datasets/compuertas conservados; no se expone un disclosure vacío en diaria; charts se redimensionan al abrir paneles |
| Tabla bajo demanda | Aprobado: cerrada al iniciar, foco desde sidebar, búsqueda sobre filas calculadas, 10 visibles, navegación 1/2 ↔ 2/2 |
| Responsive | Aprobado localmente: 1440, 1000, 900, 640 y 375 px, sin desborde horizontal global; tabla con scroll local |
| Carga/performance | 3 solicitudes de datos y 849526 bytes al abrir Mayoristas; 20373 filas. Apertura medida en Chrome: 2,77 s local. Al volver a 2026: 0 bytes nuevos por caché. No es un benchmark ni una promesa de tiempo en producción |
| Integridad | Snapshot mensual idéntico: 20373 filas filtradas, 8 KPIs, todos los datasets y 20 productos de matriz |
| Estados | Error/carga/unidad y última vista válida preservados. Avisos problemáticos de fuente quedan fuera de metadata cerrada |
| Regresión Carnes | Archivos aprobados sin cambios; 27 tests de Carnes aprobados |

**Pruebas nuevas ejecutadas:** 18 tests Node focales de Mayoristas/MCBA/frescura, 27 tests Node de Carnes, browser visual Edge y Chrome y browser delivery Chrome. Todos aprobados, sin errores JavaScript en los flujos automatizados. La revisión de teclado cubre los controles probados; no constituye una auditoría integral de accesibilidad.

`app.js`, `carnes.js` y `styles.css` siguen byte idénticos al respaldo anterior a la adopción de Mayoristas. Sintaxis JS y `git diff --check` aprobados.

## 5. Integración y riesgos pendientes

### Actualizaciones en main

La rama está cinco commits detrás de main al cerrar esta revisión. Esos commits modifican snapshots de Commodities/SIO y estados de fuente; no modifican código frontend ni pipelines. Deben conservarse al integrar. No se sincronizó la rama porque no está autorizado un merge/rebase automático.

Se realizó una prueba aislada de navegador leyendo con `git show` los tres JSON de estado vigentes en main y suministrándolos sólo al contexto de prueba, sin escribir datos en el checkout. Resultado: 20373 filas, KPIs idénticos y cero errores JS. El aviso de MCBA se muestra correctamente.

### Fuente MCBA

La metadata actual de main informa: **MCBA mensual · Error de actualización · Se conserva la última versión válida**, con último dato 19/10/2026 y actualización exitosa 20/10/2026 09:49. Es un riesgo operativo de frescura preexistente, no una regresión visual. La UI no lo oculta ni lo transforma en “Actualizado”. Su resolución corresponde al flujo de actualización de datos, que no se tocó.

### Rótulos y alcance

Existen grafías heredadas como `Casta¥a`, presentes de igual modo antes y después. Se conserva el valor de origen; normalizarlas requiere un cambio de datos separado y trazable. No afecta la equivalencia de cálculos de esta modificación.

El promedio sigue siendo simple; los extremos pueden pertenecer a productos distintos. La matriz mensual no es una estimación de estacionalidad histórica. Estas limitaciones se mantienen explícitas.

La validación fue local en Edge/Chrome. No se publicó un sitio ni se ejecutó el deploy real; el CI y un smoke del artefacto final siguen siendo la puerta de publicación. La revisión del empaquetador confirma que copia los nuevos JS/CSS/assets; no hubo cambios en el workflow.

## 6. Evidencia comparativa

Carpeta: `C:/Users/acer/Oficina/carnes-ui-evidence/mayoristas-close-20261024/`.

- `revision.html`: galería de capturas completas antes/después a 1440/900, Más filtros, detalle y 375 px.
- `viewport-comparison-1440.png`, `viewport-comparison-900.png`: comparación al mismo tamaño de viewport.
- `comparison-1440.png`, `comparison-900.png`: recorridos completos.
- `before/`: capturas nuevas del layout anterior reconstruido con el HTML/CSS/JS respaldado al iniciar la adopción, usando las mismas fuentes actuales.
- `after/`: capturas y snapshots nuevos de Edge y Chrome.
- `delivery-chrome/chrome.json`: medición de carga, caché, años, diaria, corrupción y responsive.
- `main-metadata-check.json`, `main-metadata-preview.png`: compatibilidad y visibilidad de avisos con los estados actuales de main.

Las comparaciones de esta revisión se abrieron e inspeccionaron en conjunto. No se usan mockups ni capturas antiguas como prueba del estado final.

## Dictamen

**Sin bloqueantes visuales o funcionales introducidos por la modificación. Recomiendo merge manual del cambio revisado, preservando los datos vigentes de main y ejecutando el CI normal antes de publicar.** El incidente de actualización MCBA debe seguir identificado y atenderse por separado; no se declara resuelto por este cierre visual.
