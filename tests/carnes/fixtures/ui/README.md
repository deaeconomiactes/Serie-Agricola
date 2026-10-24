# Fixtures frontend Carnes

Fragmentos DASHBOARD livianos congelados de la captura oficial del 22/10/2026.
Preservan los valores, URLs y hashes RAW originales; no contienen RAW, XLSX,
NORMALIZED completos ni establecimientos/usuarios. El índice recorta la selección
de fragmentos a las familias/períodos necesarios para los tests; `status.json`
es metadata sintética del test. No usar estos archivos en el frontend productivo.

Las pruebas Node usan este snapshot para no fallar ante una actualización legítima
del avance corriente. Las pruebas browser opt-in verifican los outputs productivos
reales del checkout servido. No descargar fuentes externas al ejecutar tests.

# Analítica de la tercera iteración

`analytics-composition-september.json.gz` congela las 32 filas de
`slaughter/category_age` de septiembre 2025/2026 extraídas de los fragmentos
DASHBOARD ya versionados (MAGyP faena 2025/avance 2026). Conserva los campos
originales, hashes, localizadores y capturas. Comprueba la diferencia publicada
«Más de 8 dientes»/«más de 8 dientes» y la equivalencia de comparación acotada
a mayúsculas y espacios de dentición, sin alterar etiquetas originales.
