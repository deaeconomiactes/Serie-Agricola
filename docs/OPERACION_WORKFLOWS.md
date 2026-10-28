# Operación de workflows

Inventario del checkout al 28/10/2026. Los cron están en UTC; Argentina se muestra con UTC−3. Los límites y listas exactas de publicación están en cada workflow. No se eliminan ejecuciones de Actions.

| Estado | Workflow | Trigger y horario | Runner | Fuente y salidas |
| --- | --- | --- | --- | --- |
| ACTIVE_PRODUCTIVE | Deploy Dashboard to GitHub Pages | Push a main con exclusiones; manual | Ubuntu | Construye fragmentos Mayoristas y publica el sitio Pages; requiere secreto de desencriptación. |
| ACTIVE_PRODUCTIVE | Actualizar Commodities MAGyP | Manual; días hábiles 23:00 UTC (20:00 Argentina) | Ubuntu | MAGyP: precios internos, pizarra, FAS, FOB y futuros; CSV dashboard y frescura. |
| ACTIVE_PRODUCTIVE | Actualizar commodities SIO | Manual; diario 13:30 UTC (10:30 Argentina) | Ubuntu | SIO: snapshots, CSV dashboard, auditoría y frescura. |
| ACTIVE_PRODUCTIVE | MAGyP MCBA - productivo Windows self-hosted | Manual; diario 15, 19 y 23 UTC (12, 16 y 20 Argentina) | Windows self-hosted para captura; Ubuntu para publicar | MAGyP MCBA: bundle diario validado y estado/frescura. Depende del runner Windows y de Edge; puede quedar pendiente si el runner no está disponible. |
| ACTIVE_PRODUCTIVE | Actualizar MCBA mensual derivado - Mercado Central | Manual; días hábiles 15:15 UTC (12:15 Argentina) | Ubuntu | Mercado Central: CSV mensual derivado, índice, validación, estado y frescura. |
| MANUAL_DIAGNOSTIC | MAGyP MCBA - smoke manual Chromium | Sólo manual; sin cron | Ubuntu 24.04 | Tests offline y captura oficial opcional con Chromium; guarda reportes temporales como artefacto, con permisos de lectura. Permite diagnosticar en Linux sin el runner Windows y no publica datos. |
| OBSOLETE | update MAGyP FOB | Sin archivo ni programación vigente en esta rama | — | FOB corriente forma parte de Actualizar Commodities MAGyP; no requiere workflow independiente. Ver [auditoría operativa](WORKFLOWS_AUDITORIA_OPERATIVA.md) para el registro legado en Actions. |

Los flujos pueden informar `UPDATED`, `NO_OP_ALREADY_CURRENT`, `NO_PUBLICATION`, `SOURCE_UNAVAILABLE` o `PIPELINE_ERROR` según corresponda; `HISTORICAL_ENDED` identifica una serie concluida. No todas las fuentes usan todos los estados. La cancelación o una falla previa al resumen no garantiza un estado final impreso. Una falla conserva la última salida válida según el contrato del pipeline. Los workflows que publican datos solicitan el despliegue cuando corresponde; consultar sus condiciones y listas permitidas.

La [auditoría del 27/10](WORKFLOWS_AUDITORIA_OPERATIVA.md) conserva medidas y propuestas de su corte. El archivo de workflow vigente es la autoridad para cron, condiciones y runner. El documento [automatización MCBA](MCBA_PRODUCTION_AUTOMATION.md) describe también etapas iniciales históricas: el workflow actual sí tiene programación diaria.
