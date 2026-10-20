# Mercado Central de Buenos Aires — precios

Fuente independiente de MAGyP. Los ZIP publicados por Mercado Central contienen
planillas **diarias**. El CSV mensual de esta carpeta es una **vista derivada**;
no representa un promedio mensual oficial publicado por MAGyP.

## Organización

| Ruta | Contenido | Git |
|---|---|---|
| `raw/mcba/<capture_id>/` | ZIP original inmutable y manifest SHA-256 | Ignorado |
| `normalized/mcba/<capture_id>/` | Observaciones con campos originales y trazabilidad | Ignorado |
| `analytical/mcba/` | Detalle diario y agregación mensual reproducible | Ignorado |
| `dashboard/mcba/` | CSV publicado, checksum, índice de fuentes y estado | Versionable |
| `reports/` | Cobertura y comparación verificable | Versionable |

El código está en `scripts/mercado_central/`, los códigos oficiales en
`config/mercado_central_codes.json` y las pruebas en `tests/mercado_central/`.
La integración de lectura del navegador está en `mcba-monthly.js`.

Guía completa: [MCBA_MERCADO_CENTRAL_MONTHLY.md](../../docs/MCBA_MERCADO_CENTRAL_MONTHLY.md).

Histórico y cutover: [MCBA_HISTORICAL_COVERAGE.md](../../docs/MCBA_HISTORICAL_COVERAGE.md).
`reports/MCBA_HISTORY_DISCOVERY.json` conserva evidencia de índices oficiales y
`reports/MCBA_HISTORY_INVENTORY.json`/`.csv` comparan cobertura por año. El candidato
2017–2018 en USD se archiva en `raw/history/` y `normalized/history/`, excluidos de
Git y del runtime ARS. Los scripts `discover_history.py` y `audit_history.py` están
en el mismo directorio de scripts de la fuente. No se retira el archivo mensual
de 2024–2025: falta un reemplazo suficiente y comparable.

No guardar aquí copias manuales, temporales, credenciales ni archivos extraídos
que no pertenezcan a las planillas de precios autorizadas.
