# Cierre de entrega: actualización y estado de precios

Summary: Consolidar actualización y estado de todas las fuentes de precios

## Alcance aprobado

Se conserva la implementación previamente registrada en `59dc227`.
La entrega incluye actualización de referencias MAGyP y SIO, preservación del último
MCBA diario válido, reporte único PRICE_FRESHNESS_STATUS.json, indicadores compactos,
metadata de fuentes legacy y publicación/deploy explícitos preparados en los workflows.
No se incorporan balance, producción, exportaciones, DJVE, carnes ni nuevas variables.

Los estados de disponibilidad no garantizan respuesta de MAGyP. Las últimas pruebas
reales y las fechas por fuente están en el reporte de frescura y en PRICE_FRESHNESS.md.

## Validación de cierre

- Python común: 48 tests.
- MCBA: 105 tests.
- Frontend: 42 tests.
- CI/publicación Git: 6 tests.
- actionlint sobre los tres workflows productivos modificados.
- git diff --check tanto del trabajo local como de la diferencia con main.

El diff de entrega no contiene RAW, temporales, artifacts locales, perfiles browser,
cookies, tokens ni credenciales. Los CSV publicados son livianos; el mayor archivo
del diff anterior al acta tiene 697592 bytes. Los logs de prueba quedan fuera del repo.

## Separación de etapas

NEXT_STAGE_READY = MCBA_MONTHLY_MAGYP

La implementación mensual oficial NO forma parte de este PR.
Sólo puede empezar después del merge de esta entrega a main y de actualizar main.
Su rama será `codex/magyp-mcba-monthly-official`.
Debe partir de la publicación mensual oficial, nunca de promediar el diario.
Este cierre no autoriza merge automático ni inicia la etapa B.
