# Dependencias y límites del inventario

Inventario de esta rama, 28/10/2026. No se retiraron ni actualizaron dependencias. Los archivos requirements fijan entornos distintos, no un único entorno global.

| Archivo | Dependencias y uso |
| --- | --- |
| `scripts/magyp/requirements.txt` | `openpyxl==3.1.5`: lectura de XLSX MCBA e históricos de granos (`scripts/magyp/mcba/model.py`, `scripts/magyp/grains/history_model.py`) y tests. |
| `scripts/magyp/requirements-browser.txt` | Incluye el anterior; `playwright==1.58.0` para captura MCBA y comprobaciones de navegador; `et-xmlfile`, `pyee`, `greenlet` y `typing-extensions` son dependencias transitivas fijadas para reproducibilidad. El piloto instala Chromium con la CLI Playwright. |
| `scripts/magyp/grains/requirements-history.txt` | Incluye requirements MAGyP y fija `et-xmlfile` para openpyxl; la adquisición FAS con navegador necesita además requirements-browser. |
| `scripts/mercado_central/requirements.txt` | Incluye requirements MAGyP, fija `et-xmlfile` y usa `xlrd==2.0.2` para XLS BIFF (`scripts/mercado_central/update_mcba_monthly.py`). |
| `scripts/carnes/requirements.txt` | `openpyxl` y su dependencia `et-xmlfile`, para libros oficiales (`scripts/carnes/magyp_workbooks.py`) y sus tests. |

No hay `package.json` ni lockfile Node versionado. El builder y las pruebas usan módulos incorporados (`node:test`, `fs`, `crypto`, `zlib`, `vm`); Playwright de los browser checks es Python. El frontend carga Chart.js y su plugin desde CDN en `index.html`. No se agregaron paquetes npm.

## Inventario reproducible

`python scripts/ci/inventory_repository.py` consulta `git ls-files`, mide los archivos presentes, calcula SHA-256 y busca referencias literales en archivos de código y documentación de hasta 2 MB. Produce [inventario CSV](reports/REPO_INVENTORY.csv), [50 mayores](reports/REPO_LARGEST_50.json) y [duplicados](reports/REPO_DUPLICATES.json). Cuenta archivos que contienen la referencia, no ocurrencias. Para nombres duplicados exige ruta completa. No resuelve rutas dinámicas, imports indirectos, archivos no versionados ni consumidores externos: cero coincidencias no acredita ausencia de uso y la clasificación automática conservadora requiere revisión. Se debe regenerar después de incorporar archivos al índice de Git. Los tres reportes generados no se hashean a sí mismos para evitar una dependencia circular; sus campos SHA se indican como GENERATED_REPORT.

Los directorios RAW de las fuentes tienen reglas específicas; `.gitignore` conserva excepciones para salidas dashboard y fixtures. Se agregaron exclusiones de entornos, cachés, reportes de navegador y carpetas locales de evidencia en la raíz. No se ignoran globalmente imágenes ni PDF para no ocultar activos o documentación válidos.
