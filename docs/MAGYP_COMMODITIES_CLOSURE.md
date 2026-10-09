# Cierre técnico de Commodities MAGyP — 2026-10-09

Estado: **PENDING_GITHUB_ACTIONS_VALIDATION**. La integración aceptada está validada localmente; todavía no cumple el requisito de ejecución Linux para `READY_FOR_PRODUCTION_AUTOMATION`.

## Workflow manual

Se intentó despachar `magyp-commodities-review.yml` mediante la API autenticada de GitHub, sobre `codex/magyp-data-platform-mcba`, con `date=2026-10-08` y `source=all`. GitHub respondió HTTP 404 y no creó una ejecución. La lectura autenticada de workflows funcionó (HTTP 200); el archivo existe en la rama de trabajo (HTTP 200) y falta en la rama predeterminada `main` (HTTP 404).

GitHub exige que el archivo con `workflow_dispatch` exista en la rama predeterminada antes de permitir el despacho: [documentación oficial](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow). No se hizo merge, commit, push ni deploy para resolver este bloqueo. WSL/Linux y Docker no están disponibles en el entorno local.

El workflow usa Ubuntu, Python 3.12 y Node 22; los cuatro tags de acciones v7 fueron comprobados en GitHub. Ejecuta pruebas offline, prepara la familia seleccionada y valida las salidas después de generarlas. Conserva permisos de sólo lectura, ejecución manual y artefactos de revisión; no tiene cron ni publicación automática.

## Verificación local

- 18 pruebas Python y 20 pruebas Node pasaron, incluidas las regresiones de MCBA, Corrientes, cantidades y comportamiento legacy. La suite Commodities modificada volvió a pasar sus siete pruebas.
- Se corrigió una fecha fija en la prueba del último precio diario: ahora compara cada serie con su última observación positiva real, permitiendo futuras actualizaciones válidas.
- En un directorio temporal se reprodujo RAW → NORMALIZED → ANALYTICAL → DASHBOARD para cada familia, sin nuevas consultas de mercado. Los cinco CSV reprodujeron exactamente sus hashes SHA-256 aceptados.
- Navegador Chromium: siete fuentes seleccionables, filtros, KPIs, evolución, rankings, gráficos, semáforo y tablas. Se comprobaron condición/posición, precios diarios, enlaces de fuente y actualización UTC. Sin errores de página ni requests MAGyP desde el frontend.
- Se comprobó el bloqueo de gráficos al seleccionar monedas/unidades incompatibles. FOB conserva `Sin identificar` en moneda y unidad; no se asignaron etiquetas económicas sin diccionario validado.
- Todos los archivos previamente versionados fueron comparados por SHA-256. Sólo cambian el workflow y su prueba; el dashboard, los CSV aceptados y los módulos protegidos permanecen idénticos.

## Salidas aceptadas, reproducidas independientemente

| Archivo | Observaciones positivas | Período de observación |
| --- | ---: | --- |
| `internal.csv` | 56 | Enero–septiembre 2026, mensual |
| `board.csv` | 4 | 2026-10-07 |
| `fas.csv` | 162 | D.E.C.: 2026-09-28–2026-10-08; D.E.R.: octubre 2025 |
| `fob.csv` | 134 | 2026-10-08 |
| `futures.csv` | 104 | 2026-10-07–2026-10-08, externos |

Cada archivo está en `data/magyp/dashboard/commodities/`. FAS D.E.R. permanece como histórico separado por régimen; futuros locales quedan excluidos; SIO continúa como circuito transaccional y el histórico mensual legacy sigue disponible. Los conteos describen capturas aceptadas, no una descarga nueva ni una actualización de actualidad.

## Puerta pendiente para producción

Después de la revisión del usuario y del registro normal del workflow en `main`, ejecutar manualmente el workflow sobre la rama revisada, con una fecha FOB publicada. Exigir éxito en Ubuntu, en generación de las cinco familias y en las pruebas posteriores antes de cambiar la clasificación a `READY_FOR_PRODUCTION_AUTOMATION`.

Los artefactos de Actions tienen retención de 30 días: no sustituyen un almacenamiento RAW duradero. Confirmar esa política antes de activar automatización desatendida. No se activó cron.

Evidencia detallada: `data/magyp/reports/COMMODITIES_CLOSURE_CHECK.json`. Arquitectura y contratos: `docs/MAGYP_COMMODITIES.md`.
