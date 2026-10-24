# Integración del piloto visual — 24/10/2026

Rama: `codex/ui-refresh-institucional-carnes`.

## Sincronización y alcance

Se incorporaron por fast-forward los cinco commits de main hasta `ddb9f5b8415b8ecfc7b7a44dcffa13dc85fc2cd5`, sin conflictos. Se conservaron las actualizaciones de Commodities MAGyP, SIO, snapshots y estados productivos. La integración no añadió modificaciones a cálculos, loaders, shards, pipelines, workflows ni metadata.

El diff de `data/`, `scripts/` y `.github/` contra main está vacío. El cambio completo conserva las visualizaciones y métricas de Carnes previamente aprobadas; en `app.js` sólo cambia la versión de caché del módulo Carnes. La presentación Mayoristas reside en HTML y archivos CSS/JS propios, sin alterar su lógica económica.

## Controles posteriores a la sincronización

- Frontend completo: 110 pruebas correctas.
- Carnes Python: 29 pruebas correctas; smokes funcional y analítico Edge correctos.
- Referencias Commodities: 28 pruebas correctas; publicación: 3 pruebas correctas; validación de cinco CSV correcta.
- Mayoristas Edge y Chrome: 20.373 filas mensuales 2026; tres solicitudes iniciales, 849.526 bytes; retorno al año en caché sin descargar; errores/corrupción conservan última vista y controles válidos; respuestas tardías no reemplazan la selección vigente.
- Comparación exacta con el cierre visual aprobado: filtros, filas completas, ocho valores KPI, etiquetas/datasets de gráficos y tabla iguales.
- KPIs de control: fecha 01/10/2026; 193 especies; 229 variedades; promedio $ 2.054,4; mayor suba 74,4%; mayor baja −16,5%; mínimo $ 3; máximo $ 110.000.
- Responsive Mayoristas: sin desborde horizontal en 1440/1000/900/640; revisión visual Chrome también a 375. Más filtros, navegación contextual, búsqueda y detalle paginado correctos.
- Compilación de fragmentos y validación de hashes/esquema/cobertura ejecutadas sobre copias aisladas de las entradas; empaquetado Pages fuera del checkout, con los nuevos CSS/JS/assets presentes. No se regeneraron salidas productivas del repositorio.
- Sintaxis JS y `git diff --check` correctos.

## Estado MCBA y límites

Se comprobó en el navegador, sin interceptar respuestas, que el aviso de **Error de actualización · se conserva última versión válida** permanece visible. La metadata de main conserva último dato 19/10/2026 y última actualización exitosa 20/10/2026. No se intentó corregir ese incidente desde esta rama.

Los workflows actuales no tienen disparador `pull_request`; los controles pertinentes se ejecutaron localmente. No se disparó el deploy de producción. El PR requiere revisión y merge manual.

Evidencia local reproducible: `C:/Users/acer/Oficina/carnes-ui-evidence/integracion-20261024/` (logs, snapshots, capturas, equivalencia y paquete Pages).
