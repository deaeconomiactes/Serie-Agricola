# Política MCBA propuesta — fase 3

**Actualización posterior:** el usuario autorizó integrar el detalle diario en el
módulo existente, conservando legacy y sin publicar automáticamente. La integración
local se documenta en `MCBA_DASHBOARD_INTEGRATION.md`; mantiene los criterios de
integridad de esta política. Las restricciones de frontend de la fase 3 son históricas.

Estado: propuesta validada offline; no implica autorización de migración. Arquitectura
congelada: MAGyP → RAW → NORMALIZED → ANALYTICAL → DASHBOARD PILOTO.

## Nivel de observación

`detail` alimenta visualización desagregada, preservando fecha, especie, variedad,
procedencia, envase, calidad, tamaño y grado. Export preferido:
`data/magyp/dashboard/mcba/MCBA_MAGYP_DETAIL.csv`, exclusivo detail.
DAILY mantiene todas las observaciones válidas con observation_level explícito.

`species_summary` es observación oficial separada. Prom.Esp. se conserva como etiqueta
original, nunca como variedad comercial ni como una observación adicional en el
promedio de detail. MONTHLY y LATEST separan por nivel y todas las dimensiones.
No se intenta replicar la fórmula del resumen sin metodología oficial. Unknown no
puede alimentar una serie desagregada; producto/fecha/precio inválidos bloquean uso.

## Kg y precios

kg_raw preserva exactamente el valor publicado. Con kg_semantics_status=unknown,
volume=null y volume_unit=null, incluso si Kg es cero o positivo. La validación
rechaza contaminación con volumen cero o unidad inferida. No se pondera por Kg ni
se calcula actividad comercial. Esto por sí solo no bloquea migrar series de precios.

Nuevos manifests: currency=ARS, price_unit=kg, currency_evidence=documented, según
encabezados oficiales para [frutas](https://ssma.magyp.gob.ar/frutas.preciospromediof.aspx)
y [hortalizas](https://ssma.magyp.gob.ar/frutas.preciospromedioh.aspx). El precio está
expresado en pesos por kg. No hay conversión numérica; moneda y denominador se
separan. ISO ARS es regla explícita para pesos locales, no código entregado por XLSX.
RAW históricos no se modifican; NORMALIZED conserva su evidencia/unidad original.
Matching/diagnóstico reconoce kg + ARS, ARS/kg y $/kg en contexto exclusivo MCBA,
con moneda incompatible excluida. Agregados rechazan unidades/monedas desconocidas.

## Aliases y encoding

Sólo validated puede aplicarse automáticamente. En el diccionario actual son
equivalencias de Unicode/mayúsculas/espacios, no recodificaciones semánticas nuevas.
Observed participa sólo en matching probable/diagnóstico. Manual_review nunca se
aplica. Las tres propuestas previas ¥→Ñ y dos adicionales del mes siguen pendientes
de evidencia sobre cada valor y causa;
se documentan como encoding_anomaly. No hay replace global ni eliminación de tildes.
Casos marginales no son veto automático si están acotados, identificados y trazables.

## Duplicados actuales

La base actual se conserva íntegra. Economic_duplicate se reporta con clave,
referencias y procedencia; source_file_duplicate requiere evidencia de originales
para confirmación binaria. Los XLS/ZIP del caso auditado no están disponibles aquí.
No se hace deduplicación automática ni matching arbitrario uno a uno; las múltiples
alternativas son ambiguous. Una vista sin repetición sólo puede usarse para auditar
impacto y debe quedar claramente separada de un dataset productivo.

## Mes solicitado y equivalencia

complete_requested_window significa que los días calendario del mes están cubiertos
por ventanas con XLSX válido. No significa que se conozcan todos los días de
publicación esperados ni que cada día deba tener registros. Observed_rows=0 se registra
con calendar_status=unknown; un fallo es rows=null, nunca día sin publicación.
coverage_ratio_requested = días en ventanas validadas / días únicos solicitados.
Sin calendario oficial no hay expected_days ni razón de cobertura de publicación.

El dashboard MONTHLY conserva mediana de precios observados por combinación y
aggregation_status=partial_period. El reporte de validación calcula aparte media de
medias diarias, por la misma combinación, sólo detail y días observados; no es mensual
oficial. Comparaciones A (diario), B (agregados de días compartidos) y C (histórico
mensual K_mes) son independientes. C tiene equivalencia metodológica no verificada:
sus diferencias son descriptivas y no prueban error o consistencia económica.

## Adquisición reproducible y smoke CI

Python 3.12; instalar `scripts/magyp/requirements-browser.txt` en venv nuevo y luego
`python -m playwright install chromium` (Linux: `install --with-deps chromium`).
Versiones directas y transitivas fijadas. Playwright selecciona su revisión Chromium
compatible. Consultar [instalación CI oficial](https://playwright.dev/python/docs/ci).
Headless, contextos efímeros, allowlist HTTPS, máximo 80 requests por sesión y 2 MB
por export; timeout 40 s por operación para validación. No captura de estados/HAR.

```powershell
python scripts/magyp/mcba/validate_acquisition_mcba.py --date-from 2025-10-02 --purpose validation_2025 --browser-channel chromium --timeout 40 --max-requests 80 --allow-web
python scripts/magyp/mcba/validate_readiness_mcba.py --month 2025-10
```

Cada invocación hace un solo intento. Una segunda sesión es explícita, no retry
automático. Los diagnósticos públicos guardan resultado, etapa, duración, requests,
filas, validación XLSX, error_category y runtime. Fallo no escribe RAW ni publica.

`.github/workflows/magyp-mcba-pilot.yml`: workflow_dispatch, allow_web=false por
defecto; Linux/Python/Chromium, tests offline y como máximo una captura en runner.temp.
Permisos de lectura, sin commit ni schedule. Artifact sólo tests/diagnósticos públicos
livianos seleccionados; sin RAW, perfiles, cookies, tokens, capturas visuales o traces.
Workflow preparado no equivale a ejecución CI satisfactoria: cloud debe probarse
manualmente después de revisión y disponibilidad del archivo en GitHub.

## Decisión

Readiness requiere autonomía estable en Chromium/CI y 2025, mes solicitado validado,
comparación satisfactoria o discrepancias acotadas, grano preservado, fallbacks,
idempotencia y RAW recuperable. Kg excluido y aliases marginales pendientes son
observaciones admisibles, no bloqueos automáticos. No promover clasificación por
éxito de mocks ni por una muestra antigua. El reporte de fase 3 registra evidencia
positiva, negativa y pendiente de cada criterio.
