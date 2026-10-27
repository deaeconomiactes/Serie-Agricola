# Auditoría operativa de workflows

Corte: 27 de octubre de 2026. Base: `main` bd85af0. Los cambios descritos son locales y todavía no están publicados. Los horarios corresponden a Argentina (UTC−3); GitHub puede demorar el inicio.

## Inventario

Las duraciones son muestras de tres trabajos terminados, medidas desde el inicio del job, no garantías ni tiempos de espera. Todos admiten ejecución manual. Los escritores programados sólo publican en `main`; el deploy manual permanece disponible para recuperación.

| Workflow | Inicio y runner | Muestra de duración | Concurrencia y salida |
| --- | --- | --- | --- |
| MCBA Windows | Diario 12, 16 y 20 h; Windows self-hosted, Edge autoritativo | 6:41–10:16; una muestra falló | Adquisición con grupo propio y publicación en Ubuntu con `serie-agricola-data-writer`. Hasta 15 min de job, 8 min de captura y 5 min de publicación. Publica los cuatro CSV MCBA, `_SUCCESS`, estado MCBA y frescura, únicamente tras validar el candidato. |
| MCBA mensual derivado | Días hábiles 12:15; Ubuntu | 0:57–2:24; dos muestras fallaron | Grupo escritor compartido; límite 15 min. Publica CSV mensual, marcador, índice, estado, validación y frescura si cambian. |
| Commodities MAGyP | Días hábiles 20 h; Ubuntu | 0:59–1:17; una muestra falló | Grupo escritor compartido; límite 10 min. Publica series dashboard de precios internos, pizarra, FAS, FOB y futuros, más estados/frescura. |
| Commodities SIO | Diario 10:30; Ubuntu | 0:12–0:18 | Grupo escritor compartido; límite 10 min y 2 min de captura. Publica CSV dashboard, auditoría y frescura permitidos. |
| update MAGyP FOB | Sin workflow vigente en `main` | Último run legado localizado: 5 de octubre, fallido | El archivo independiente ya no está en `main`; el registro histórico de Actions figura activo. FOB corriente se actualiza como familia de Commodities MAGyP. No se crea una programación adicional. |
| Deploy Dashboard to GitHub Pages | Push a `main` y ejecución manual; Ubuntu | 1:15–1:57 | Grupo `pages`; límite 15 min. Construye y publica Pages; no escribe los datos fuente en Git. Se excluyen cambios de documentación, pruebas y configuración auxiliar sin impacto en el sitio. |

Las rutas exactas de publicación son las listas permitidas en cada workflow. Un cambio observado se confirma en Git sólo si está dentro de esa lista; las publicaciones se solicitan tras un push exitoso y un cambio con efecto productivo. El push de un workflow con `GITHUB_TOKEN` no dispara otro workflow: la actualización necesaria de Pages se solicita explícitamente. La ejecución manual de Pages sigue disponible.

## Hallazgos y medidas

1. [MCBA 40435273994](https://github.com/deaeconomiactes/Serie-Agricola/actions/runs/40435273994) esperó aproximadamente 9 h 17 min antes de iniciar y luego ejecutó 6 min 41 s. Edge agotó el tiempo ante la fuente y se clasificó `SOURCE_UNAVAILABLE`; el fallo final fue un conflicto al publicar metadata. La espera no demuestra por sí sola si la causa fue disponibilidad del runner o concurrencia.
2. La captura Windows retenía el grupo compartido mientras esperaba un runner. El flujo propuesto separa captura y publicación, valida hashes, estado y base del candidato y reconstruye frescura sobre el `main` actual. Ante una base MCBA cambiada rechaza el candidato en vez de sobrescribirla. No cancela una captura en curso.
3. Se observaron ejecuciones de [mensual](https://github.com/deaeconomiactes/Serie-Agricola/actions/runs/40395779500) y [Commodities](https://github.com/deaeconomiactes/Serie-Agricola/actions/runs/40434681162) canceladas sin job. El grupo compartido configurado por defecto conserva sólo un pendiente. Se propone `queue: max` para los cuatro escritores: serializa escrituras y admite hasta 100 pendientes; superado ese límite GitHub cancela los adicionales. El grupo propio de captura MCBA conserva sólo el pendiente más reciente y no interrumpe el trabajo activo. Véase la [documentación de concurrencia de GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).
4. SIO podía ocultar un error en la captura por el uso de `tee` sin `pipefail`; se corrige. Su push sigue sin forzar y falla de forma segura ante una carrera con un push humano. Un reintento automático seguro requiere publicar desde una copia limpia: queda pendiente.
5. Se distinguen cambios de datos o estado visible de cambios exclusivos en marcas de intento y diagnósticos. Estos últimos pueden guardarse en Git sin desplegar: Pages puede mostrar la fecha del intento anterior hasta el siguiente despliegue, aunque se conserve correctamente la última captura válida y el estado visible no haya cambiado. Un cambio real de estado sí requiere despliegue.
6. El estado mensual observado fue `PIPELINE_ERROR` con `InvalidSource`; no hay evidencia suficiente para atribuirlo a una caída externa. Se conserva el último conjunto válido. No se alteró la fuente ni se intentó corregir ese estado desde esta auditoría.

## Estados y observabilidad

`UPDATED`: salida válida nueva; `NO_OP_ALREADY_CURRENT`: ya estaba vigente; `NO_PUBLICATION`: no hay publicación nueva; `SOURCE_UNAVAILABLE`: fuente inaccesible; `PIPELINE_ERROR`: falla de procesamiento o publicación. Cada integración puede emitir sólo el subconjunto que corresponde a sus mecanismos; no se debe inferir indisponibilidad de una fuente a partir de cualquier excepción.

La frescura distingue fecha de observación (`last_observation_date`), última captura exitosa (`last_successful_update`), último intento (`attempted_at`) y estado actual (`status`). Un fallo no reemplaza la última captura exitosa. Los resúmenes operativos imprimen `FINAL_STATUS`, `SOURCE`, `REQUESTED_DATE`, `LAST_OBSERVATION`, `OUTPUT_CHANGED` y `DEPLOY_REQUIRED` cuando el job alcanza el paso de resumen; una cancelación o falla anterior a su inicio no puede imprimirlo.

## Runner y riesgos

El runner consultado estaba online e inactivo, con etiquetas Windows/self-hosted/serie-agricola, Edge 156, PowerShell 7 y directorio `_work`; no se detectó servicio de Actions. El workflow prepara sus herramientas y usa token temporal; no se instaló ni registró nada. Considerar servicio con la misma cuenta y permisos tras validar acceso al escritorio, red y limpieza. Un job puede permanecer pendiente si el runner está desconectado: el timeout del job comienza sólo cuando inicia.

La cola máxima evita reemplazos entre fuentes pero puede acumular trabajo durante incidentes; vigilar su profundidad. El timeout acota trabajos iniciados, no la espera de infraestructura. La validación local no equivale a una ejecución real de GitHub Actions: confirmar el primer ciclo controlado tras integrar. `actionlint` 1.7.12 aún no reconoce la propiedad oficial `queue`; se filtra exclusivamente ese diagnóstico y se mantienen las demás comprobaciones.
