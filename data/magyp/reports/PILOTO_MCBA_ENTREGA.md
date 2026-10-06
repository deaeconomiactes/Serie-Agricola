# Entrega del piloto canónico MAGyP + MCBA

Clasificación: **COMPLEMENT_ONLY**. Arquitectura y procesamiento verificables; adquisición GeneXus autónoma pendiente.

| Punto solicitado | Resultado |
|---|---|
| 1. Rama | codex/magyp-data-platform-mcba |
| 2. Base | main actualizado e18350e93d4aabf0f7ea46b92da98af69c40ab7d, worktree aislado |
| 3. Endpoint | https://ssma.magyp.gob.ar/frutas.precios.aspx; POST GeneXus DOEXPORT → XLSX |
| 4. Requests | 8 HTTP explícitas de investigación; POST directo 403. Navegador: una navegación, 3 filtros de un día y 3 exports; assets/requests internos no contabilizados. Un intento gráfico sin seleccionar producto no produjo datos. Un intento adicional de apertura por herramienta web no fue accesible. Ninguna descarga masiva. Ver MCBA_DISCOVERY_REQUESTS.csv |
| 5. Períodos | 2024-10-02 (356), 2025-10-02 (363), 2026-08-24 (359). Son 3 días aislados, no rango continuo |
| 6. RAW | 3 XLSX originales + manifests, 1.078 filas de datos, excluidos de Git |
| 7. NORMALIZED | 1.078 filas, 51 campos por observación/captura |
| 8. ANALYTICAL | 1.078 filas, mismo grano + valid_for_price_series/reason; 1.078 válidas según reglas piloto |
| 9. Dimensiones | Todos los 11 campos XLSX: fecha/tipo/especie/variedad/procedencia/envase/calidad/tamaño/grado/Kg/promedio x Kg; más trazabilidad. 5 calidades, 58 tamaños, 14 grados. IDs internos de grilla no exportados |
| 10. Productos | 89 distintos, etiqueta original; 81 en solapamiento diario 2026 |
| 11. Variedades | 113 etiquetas no nulas distintas, incluyendo Prom.Esp.; 842 detail + 236 species_summary |
| 12. Procedencias | 30 no nulas; 236 nulas corresponden a Prom.Esp. |
| 13. Envases | 10 no nulos |
| 14. Unidades | ARS/kg contextual. Kg=0 en 1.078 filas, semántica no validada, volumen null |
| 15. Monedas | ARS contextual a pesos locales, evidencia oficial de frutas; transferencia a Hortalizas con warning, ratificar antes de producción. No viene como campo del XLSX |
| 16. Precio cero/nulo/negativo | 0 / 0 / 0; no se eliminan en parser cuando aparecen |
| 17. Duplicados/extremos | 0 candidatos de cada tipo en piloto; cobertura de ambos en fixtures |
| 18. Comparación | Base total MCBA 70.452 filas. Solapamiento diario: 361 actuales vs 359 MAGyP; 81 exactas en dimensiones disponibles + 274 probables; 4 sólo MAGyP y 6 sólo actuales. Mensuales: 782 actuales frente a 719 diarias MAGyP no equiparables |
| 19. Diferencias | 274 aliases/textos en coincidencias probables; 0 diferencias numéricas/unidad en filas emparejadas (contexto $/kg→ARS/kg). ¥ publicado versus ñ en etiquetas; 14 observaciones con carácter sospechoso en el conjunto. Calidad/tamaño/grado ausentes como columnas estructuradas en base diaria actual. Frutilla y Zanahoria adicionales en base actual |
| 20. Cobertura | Actual 2024-01-01–2026-08-24: 8.708 mensuales/61.744 diarias. Piloto sólo 3 días. No inferir continuidad ni equivalencia mensual |
| 21. Tests | 36 offline: 13 comunes + 23 MCBA; comandos requeridos y diff --check documentados |
| 22. Archivos | Lista abajo; único archivo existente modificado .gitignore |
| 23. Decisión | COMPLEMENT_ONLY; no READY_TO_REPLACE ni producción autónoma |
| 24. Próxima fase | MCBA: export autónomo, diccionarios, Kg/Prom.Esp., mensual 2024–2025 y revisión diferencias; SIO queda pausado y espera validación de grilla/export/eventos |

## Capturas auditables

Las exportaciones nuevas se obtuvieron del navegador oficial con filtros Desde=Hasta del día indicado. HTTP/content-type de la descarga no observados: null en manifest. Los archivos se importaron a RAW, sin inventar metadata HTTP.

| Día solicitado | Filas | Bytes | SHA-256 | Captura UTC |
|---|---:|---:|---|---|
| 2026-08-24 | 359 | 19111 | 772d829a7107696889aff0ebeafed530064866f7b4b1fdd62e15d030ad31bcec | 2026-10-06T12:10:56.106249Z |
| 2024-10-02 | 356 | 18920 | b06369128521e4415047421a58a8f406809f431ab6b19c4c63d194a24026e92c | 2026-10-06T12:18:11.346124Z |
| 2025-10-02 | 363 | 19284 | 1ddbef8b2097e947b8c0e1bdf4275bef8f085a4d963ecc5b7ccf51a5486bb0d9 | 2026-10-06T12:20:50.197055Z |

## Salidas piloto

| Archivo | Filas | Bytes |
|---|---:|---:|
| MCBA_MAGYP_DAILY.csv | 1078 | 264037 |
| MCBA_MAGYP_LATEST.csv | 625 | 152987 |
| MCBA_MAGYP_MONTHLY.csv | 1078 | 238870 |
| MCBA_MAGYP_SUMMARY.csv | 1 | 276 |

Monthly tiene sólo un día observado por mes: no acredita promedios mensuales oficiales. LATEST selecciona por combinación completa, no sólo especie.

## Esquemas y controles

RAW exacto XLSX y manifest (21 campos), hashes e inmutabilidad. NORMALIZED JSONL con valores originales y 51 campos. ANALYTICAL añade dos campos, mantiene versiones previas en RAW/NORMALIZED. DASHBOARD CSV separado con dimensiones, fuente y actualización.
Ver docs/MAGYP_SCHEMA_DICTIONARY.md para tipos, nulabilidad, significado y mapeo de cada campo; docs/MAGYP_DATA_ARCHITECTURE.md para límites, ejecución y contratos.

HTTP/HTML/schema/vacío/ventana distinta/SHA/tamaño/versiones/fecha/precio/duplicados/nulos/cero/extremos/proveniencia: controles implementados. No se guarda formulario HTML con tokens. Falla antes de reemplazar salidas; rollback multiarchivo ante excepción, marcador con hashes detecta generación incompleta ante caída de proceso.

## Archivos creados/modificados

- data/magyp/reports/PILOTO_MCBA_ENTREGA.md (este informe)
- .gitignore (exclusión RAW/bases completas y allowlist scripts/tests/CSV piloto)
- scripts/magyp/common/__init__.py
- scripts/magyp/common/platform.py
- scripts/magyp/grains/.gitkeep
- scripts/magyp/mcba/build_analytical_mcba.py
- scripts/magyp/mcba/build_dashboard_mcba.py
- scripts/magyp/mcba/compare_mcba_current_vs_magyp.py
- scripts/magyp/mcba/fetch_mcba.py
- scripts/magyp/mcba/model.py
- scripts/magyp/mcba/normalize_mcba.py
- scripts/magyp/meats/.gitkeep
- scripts/magyp/requirements.txt
- scripts/magyp/sio/.gitkeep
- tests/magyp_common/test_platform.py
- tests/magyp_mcba/test_mcba.py
- config/magyp_sources.json
- docs/MAGYP_DATA_ARCHITECTURE.md
- docs/MAGYP_SCHEMA_DICTIONARY.md
- data/magyp/dashboard/mcba/.gitkeep
- data/magyp/dashboard/mcba/_SUCCESS.json
- data/magyp/dashboard/mcba/MCBA_MAGYP_DAILY.csv
- data/magyp/dashboard/mcba/MCBA_MAGYP_LATEST.csv
- data/magyp/dashboard/mcba/MCBA_MAGYP_MONTHLY.csv
- data/magyp/dashboard/mcba/MCBA_MAGYP_SUMMARY.csv
- data/magyp/reports/.gitkeep
- data/magyp/reports/MCBA_CURRENT_VS_MAGYP.csv
- data/magyp/reports/MCBA_CURRENT_VS_MAGYP.md
- data/magyp/reports/MCBA_DISCOVERY_REQUESTS.csv
- data/magyp/reports/MCBA_PILOT_METRICS.json

Directorios reservados grains/sio/meats y raw/normalized/analytical/dashboard/reports con .gitkeep. RAW completo y bases JSONL están locales: respaldar antes de archivar el worktree.

## Referencias y cambios excluidos

Código nuevo; relevamiento previo usado sólo como referencia y reconfirmado con tres exports nuevos. Sin merge de ramas anteriores ni copia de pipelines SIO/FOB. SourceFetcher/Normalizer/RawManifest/ValidationResult/PublishResult preparados.
No se implementó generación autónoma GeneXus ni fuentes adicionales. Sin workflow, cron, integración de frontend o migración productiva. app.js/index.html/styles.css, series históricas, base integrada, Excel MCBA, Corrientes, Cantidades y pipelines SIO/FOB preservados. Sin commit/push/merge/deploy.

## Comprobaciones ejecutadas

```text
python -m unittest discover -s tests/magyp_common -v
python -m unittest discover -s tests/magyp_mcba -v
python scripts/magyp/mcba/fetch_mcba.py --dry-run
python scripts/magyp/mcba/normalize_mcba.py
python scripts/magyp/mcba/build_analytical_mcba.py
python scripts/magyp/mcba/build_dashboard_mcba.py
python scripts/magyp/mcba/compare_mcba_current_vs_magyp.py
git diff --check
git status --short
```
