# Auditoría de duplicados actuales MCBA

Fecha: 2026-08-19. Clasificación confirmada a nivel de filas: **economic_duplicate**.
Hipótesis de archivo: source_file_duplicate por copia RF en ZIP anidado, **inferida**,
sin hash de originales XLS/ZIP disponibles en el workspace. No equivalencia binaria comprobada.

Clave literal: fecha/rubro/especie/variedad/procedencia/envase/moneda/unidades/
observaciones (atributos CAL/TAM/GRADO disponibles)/precio parseado. No se eliminan aliases.
Referencias de filas/archivos y clasificación por grupo en MCBA_CURRENT_DUPLICATE_GROUPS.csv.

```json
{
  "date": "2026-08-19",
  "classification": "economic_duplicate",
  "rows_original": 481,
  "duplicate_groups": 126,
  "excess_rows": 126,
  "rows_diagnostic_unique": 355,
  "input_sha256": "836c0945412d12e97f7acae45f28b5405ac19bf0535c4cf1b24e6d7d375acc4a",
  "source_file_hash_status": "unavailable_original_XLS_and_ZIP_not_in_workspace",
  "arithmetic_mean_original": 3155.439397089397,
  "arithmetic_mean_diagnostic_unique": 3144.8664225352113,
  "mean_method": "diagnostic_row_mean_all_products_not_economic_index",
  "source_counts": {
    "FRUTRAS_AGOSTO-26.zip/RF190826.XLS": 126,
    "FRUTAS_AGOSTO-26 (2).zip/FRUTRAS_AGOSTO-26.zip/RF190826.XLS": 126,
    "HORTALIZA_ AGOSTO_26_0.zip/RH190826.XLS": 229
  }
}
```

Los conteos por producto se inflan. El ranking por número de filas puede cambiar;
no es un ranking de volumen. Medias por producto de una copia completa idéntica de RF
no cambian por replicación uniforme, pero mezclar frutas y hortalizas aumenta el peso
relativo de frutas. La media global anterior es sólo diagnóstico, no índice publicable.
Sumas de precios/conteos se inflan; nunca inferir cantidades de estos registros.

| Producto con conteo afectado | Original | Vista diagnóstica sin repetición |
|---|---:|---:|
| Anana | 6 | 3 |
| Arandano | 6 | 3 |
| Banana | 16 | 8 |
| Ciruela | 4 | 2 |
| Coco | 4 | 2 |
| Frutilla | 12 | 6 |
| Kiwi | 12 | 6 |
| Kumquat | 6 | 3 |
| Lima | 4 | 2 |
| Limon | 14 | 7 |
| Mandarina | 22 | 11 |
| Mango | 6 | 3 |
| Manzana | 48 | 24 |
| Melon | 6 | 3 |
| Membrillo | 4 | 2 |
| Naranja | 14 | 7 |
| Nuez | 4 | 2 |
| Palta | 22 | 11 |
| Pera | 12 | 6 |
| Platano | 4 | 2 |
| Pomelo | 8 | 4 |
| Sandia | 6 | 3 |
| Uva | 12 | 6 |

No se modifica PRECIOS_MAYORISTAS_INTEGRADO.csv. La vista sin repeticiones existe sólo
en memoria para impacto; una corrección futura debe auditar originales y autorizaciones.
