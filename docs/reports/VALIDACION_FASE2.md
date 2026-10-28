# Validación local de fase 2

Corte: 28/10/2026. Se ejecutó sobre el checkout indicado, Python 3.12.10 y Node 24.19.0. Las suites se ejecutaron secuencialmente con `python -m unittest discover -s tests/<área> -v`; frontend con `node --test --test-concurrency=1` y todos los `.cjs` de `tests/magyp_frontend/`.

| Suite | Total | Aprobadas | Fallidas | Omitidas |
| --- | ---: | ---: | ---: | ---: |
| magyp_mcba | 105 | 105 | 0 | 0 |
| mercado_central | 20 | 20 | 0 | 0 |
| magyp_common | 74 | 74 | 0 | 0 |
| sio | 13 | 13 | 0 | 0 |
| carnes | 29 | 29 | 0 | 0 |
| mayoristas | 6 | 6 | 0 | 0 |
| ci | 21 | 21 | 0 | 0 |
| Frontend | 116 | 116 | 0 | 0 |

`tests/commodities` y `tests/cantidades` contienen checks de navegador, no tests Python descubribles por unittest (0 ejecutados); Commodities tiene además cobertura en `magyp_common` y frontend, y Cantidades en frontend. No se interpretó cero tests como suite aprobada. Los resultados de construcción y su limitación de secreto están en [Pages](PAGES_BUILD.md).

En la fase 2 `actionlint` no estaba instalado y no se hizo instalación global. Los tests existentes verifican partes concretas de workflows, pero no son un validador YAML integral ni sustituyen actionlint: se completó en el cierre, como se indica más abajo. `git diff --check` no informó errores; los nuevos archivos sin agregar requieren también revisión de contenido antes del commit.

## Smoke de paquete de fase 2 (histórico)

Con Edge headless se abrió el paquete en `http://127.0.0.1:8768`: los cuatro módulos se hicieron visibles y se cambió un selector en Cantidades, Mayoristas y Carnes. El primer selector visible de Commodities no ofrecía una segunda opción; su check específico se registra por separado si termina. El CSV de cantidades, los índices de Mayoristas y Carnes y el CSV FOB respondieron HTTP 200. No se observaron excepciones `pageerror`, pero la consola informó un 404 de `/favicon.ico` (ausente en el repositorio). Por ello el requisito de consola completamente limpia no queda cumplido. El paso de descifrado de Pages tampoco se validó localmente.

El check existente `tests/commodities/browser_ui_checks.py`, ejecutado contra el paquete con Edge, terminó `PASS`; verifica selección de las seis familias y filtros. El check escucha excepciones JavaScript, no invalida el 404 de favicon observado por la captura de consola anterior.

## Medición de fase 2 (histórica)

`git ls-tree -rl HEAD`: 920 archivos, 155.425.093 bytes de blobs, `data/` 85.602.870 y `docs/` 685.370. Tras los cambios propuestos, estimando los textos nuevos y `.gitignore` con normalización LF de `core.autocrlf=true`: 932 archivos, 155.810.228 bytes, `data/` 85.602.870 y `docs/` 1.059.945. La diferencia estimada es +385.135 bytes (+0,25 %), no un ahorro. Los tamaños reales del checkout Windows difieren por finales de línea; esta estimación debe confirmarse una vez agregados los archivos a Git. No se eliminó ningún archivo.

## Cierre: actionlint y diagnóstico SIO

Se ejecutó actionlint 1.7.12 descargado temporalmente de su release oficial y verificado con SHA-256. `deploy.yml` y `magyp-mcba-pilot.yml` no produjeron diagnósticos; `magyp-commodities-review.yml`, `update-magyp-mcba.yml`, `update-mcba-monthly-central.yml` y `update-sio-commodities.yml` emitieron cada uno exclusivamente el diagnóstico conocido de `concurrency.queue`. Con `-ignore` limitado exactamente a ese diagnóstico, los seis workflows pasan sin otros errores. No se cambiaron los workflows.

`SIO_GRAIN_AUDIT.json` pesa 7.849 bytes, no 14,7 MB. El archivo de 14.688.217 bytes es `CASOS_PRECIOS_CERO_SIO.csv`. `git grep` halló productores y tests de auditoría, pero no consumidores en el frontend. Ambos se conservan en Git y `prepare_pages.py` los excluye del paquete. El flujo existente de Pages desencripta `REGISTRO 2025.csv.enc` con el secreto de Actions; la validación real de ese paso queda pendiente del build de GitHub Actions del PR, sin reproducir el secreto localmente.

## Validación de cierre

Mayoristas: 7/7; SIO: 13/13; frontend completo: 116/116. Se reutilizan los resultados de las demás suites de fase 2 porque sus áreas no cambiaron. El smoke del paquete candidato en Edge abrió los cuatro módulos, cambió un filtro en cada uno, obtuvo el favicon HTTP 200 y registró cero excepciones, errores de consola o respuestas HTTP fallidas. El favicon elimina el 404 histórico. El build de Pages de GitHub Actions debe validar el descifrado con el secreto de CI.

En el cierre el índice candidato contiene 933 archivos; su tamaño de blobs es aproximadamente 155,83 MB frente a 155,43 MB iniciales. `data/` no cambia. La cifra final exacta puede obtenerse con `git ls-tree -rl` sobre el árbol resultante; los reportes añadidos explican el aumento. Pages se midió en 64,90 MB frente a 79,20 MB en el corte anterior; ver [desglose](PAGES_BUILD.md).
