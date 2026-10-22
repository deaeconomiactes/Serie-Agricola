# Fixtures frontend Carnes

Fragmentos DASHBOARD livianos congelados de la captura oficial del 22/10/2026.
Preservan los valores, URLs y hashes RAW originales; no contienen RAW, XLSX,
NORMALIZED completos ni establecimientos/usuarios. El índice recorta la selección
de fragmentos a las familias/períodos necesarios para los tests; `status.json`
es metadata sintética del test. No usar estos archivos en el frontend productivo.

Las pruebas Node usan este snapshot para no fallar ante una actualización legítima
del avance corriente. Las pruebas browser opt-in verifican los outputs productivos
reales del checkout servido. No descargar fuentes externas al ejecutar tests.
