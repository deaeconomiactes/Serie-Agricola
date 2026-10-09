# Integración local MCBA MAGyP — resultado

Rama `codex/magyp-data-platform-mcba`, HEAD `5fb5987`. Cambios de la fase anterior conservados. No se hizo commit, push, merge ni deploy.

1. **Diaria integrada:** consulta MAGyP MCBA `frutas.precios.aspx`, vía adaptador Playwright/Chromium existente; sólo `detail` alimenta análisis comerciales.
2. **Mensual:** no está automatizado el mensual oficial. Se mantiene legacy identificado. GET mensual: TimeoutError; portal: HTTP 200 HTML; no se confirmó un contrato estructurado. No se inventó un mensual con promedios diarios.
3. **Período disponible:** observaciones entre 02/10/2024 y 05/10/2026, en **28 días**. Es una colección de ventanas verificadas, no una historia diaria continua.
4. **Última observación:** 05/10/2026. El intento controlado del 06/10/2026 falló en `initial_get` por TimeoutError; no se reintentó y el conjunto publicado permaneció intacto. Estado actual: `MAGYP_LAST_VALID`. Última captura del conjunto: 06/10/2026 13:34:47.388718 UTC.
5. **Filas:** DAILY 10.380; detalle utilizado 8.126; resúmenes separados 2.254. Octubre 2025: 6.169 detail en 21 días.
6. **Productos detail:** 91 etiquetas normalizadas distintas.
7. **Variedades detail:** 129 etiquetas no vacías; Prom.Esp. excluido del análisis comercial.
8. **Procedencias detail:** 30 etiquetas no vacías.
9. **Otras dimensiones detail:** 10 envases, 5 calidades, 63 tamaños y 15 grados. Se conservan campos raw, SHA, captura y IDs. Kg no se usa como volumen ni ponderador.
10. **Archivos:** DAILY (5,34 MB), DETAIL (4,17 MB), LATEST (379 KB), SUMMARY (443 bytes), _SUCCESS y UPDATE_STATUS. MONTHLY continúa como diagnóstico no oficial y no lo carga el frontend. No existe MONTHLY_OFFICIAL operativo.
11. **app.js:** carga adicional de MAGyP, selección por frecuencia y cobertura diaria, metadatos visibles, filtros dependientes y consulta mensual independiente para semáforo. Se corrigió la clasificación de precisión mensual MCBA que podía mezclar legacy mensual en la vista diaria. Adaptador separado `mcba-prices.js`.
12. **Filtros:** preservados año/mes/rubro/especie/variedad/mercado/procedencia/unidad/frecuencia. Filtros nuevos de presentación expandibles. Se conserva el año al cambiar frecuencia. Banana → Cavendish → Ecuador: 168 → 84 → 42 observaciones MAGyP en octubre 2025.
13. **KPIs:** mantienen promedios simples/extremos/conteos/fecha/variaciones. General diario octubre 2025: ARS 2.396,8/kg; Banana: 1.560,5; Cavendish: 1.791,1; Cavendish Ecuador: 1.890,5. No hay medias ponderadas por Kg.
14. **Rankings:** siguen especies, variedades y procedencias según nivel. Cuando coexisten fechas MAGyP y legacy, evolución y ranking separan y rotulan la fuente; no conectan ambas en una única serie indistinguible.
15. **Semáforo:** mensual legacy MCBA, identificado también en la vista diaria. Caso general y filtros específicos renderizan; Corrientes conserva 20 filas visibles en la prueba.
16. **Fallback:** última salida validada en disco y copia validada del navegador. Legacy sólo para fechas sin cobertura comprobada o frecuencias no operativas. No se rellenan dimensiones ausentes; cobertura desconocida sin caché bloquea la sustitución diaria.
17. **Corrientes:** sin migración. Comparación independiente contra app.js comprometido: mismos registros, evolución, ranking y semáforo para selección Corrientes 2025. Bases CSV/Excel permanecen intactas; duplicación RF legacy sólo documentada.
18. **Workflow:** update-magyp-mcba.yml manual, Chromium, pipeline completo incremental y validaciones, candidatos como artefactos para revisión; RAW separado 90 días. Sin cron/commit/deploy. GitHub/Linux aún no ejecutado.
19. **Tests:** 13 comunes + 67 MCBA y 13 frontend (93 en total); fixtures sintéticos, integridad del bundle, preservación ante descarga inválida, revisión completa, idempotencia, prioridad diaria/mensual, copia válida, separación de fuentes en evolución/rankings y regresión de Corrientes/Cantidades/Commodities. Pruebas navegador A–K documentadas en MCBA_DASHBOARD_BROWSER_VALIDATION.json; además pasó la prueba real de caché frente a CSV corrupto y filtros secundarios Caja/Elegido (1.254 filas).
20. **Bloqueos reales:** conectividad intermitente del servicio, mensual oficial sin contrato reproducible, archivo RAW permanente y validación del workflow Linux pendientes. Sin calendario oficial, sin semántica de Kg y sin certificación económica de completitud del export.

Documentación operativa: `docs/MCBA_DASHBOARD_INTEGRATION.md`. Métricas: `MCBA_INTEGRATION_METRICS.json`. Investigación mensual: `MCBA_MONTHLY_OFFICIAL_SOURCE_CHECK.json`.
