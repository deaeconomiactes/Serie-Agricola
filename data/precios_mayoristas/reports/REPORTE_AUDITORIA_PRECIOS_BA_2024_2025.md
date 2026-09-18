# Auditoría de precios Mercado Central Buenos Aires 2024-2025

## Archivos revisados

| archivo | encontrado | hoja usada | filas útiles | fecha mínima | fecha máxima | rubro | mercado esperado |
|---|---:|---|---:|---|---|---|---|
| PHOR24_K.xlsx | Sí | PHOR24_K | 524 | n/d | n/d | Hortalizas | Mercado Central de Buenos Aires |
| PFRU24_K.xlsx | Sí | PFRU24_K | 707 | n/d | n/d | Frutas | Mercado Central de Buenos Aires |
| PHOR25_K.xlsx | Sí | PHOR25_K | 520 | n/d | n/d | Hortalizas | Mercado Central de Buenos Aires |
| PFRU25_K.xlsx | Sí | PFRU25_K | 743 | n/d | n/d | Frutas | Mercado Central de Buenos Aires |

Los cuatro libros carecen de una columna de fecha y de valores de fecha completos. El año no pudo validarse dentro de las celdas: se infiere del nombre del archivo y de la hoja. Las columnas mensuales K_ENER a K_DICI permiten validar los 12 meses, no el año calendario.

Ubicaciones buscadas: raíz del proyecto, `data/`, `data/precios_mayoristas/`, `data/precios_mayoristas/raw/`, la raíz externa indicada y `Precios-BS. AS/`. Los cuatro archivos se encontraron en la carpeta externa y no se copiaron al repositorio.

## Integrado actual

- Archivo detectado y usado por `app.js`: `C:\Users\acer\Oficina\Serie-Agricola\PRECIOS_MAYORISTAS_INTEGRADO.csv`.
- Filas totales: 108.331.
- Años disponibles: 2024 (208), 2025 (29.608), 2026 (78.515).
- Mercados/fuentes disponibles: Mercado Central de Buenos Aires (61.744); Mercado de Corrientes (46.587).
- Rubros disponibles: Hortalizas (74.881); Frutas (33.171); Subproductos (277); (sin informar) (2).
- Fecha mínima y máxima parseable: 2024-12-29 a 2026-12-25.
- Fechas faltantes o no parseables: 3.
- Cobertura Mercado Central de Buenos Aires: 61.744 filas; 2026 / Frutas: 26.746 filas y 43 especies; 2026 / Hortalizas: 34.998 filas y 59 especies.
- Período MCBA: 2026-01-02 a 2026-08-24; meses presentes: Enero, Febrero, Marzo, Abril, Mayo, Junio, Julio, Agosto.
- El fallback `PRECIOS_MAYORISTAS_2026_INTEGRADO.csv` es idéntico por SHA-256 al archivo principal.

## Comparación por archivo

### PHOR24_K.xlsx

- Estado: **AUSENTE**.
- Evidencia: El integrado no contiene registros de MCBA/Hortalizas/2024. No hay columna de fecha ni fechas completas; 2024 sólo se infiere del nombre del archivo/hoja. Las columnas K_ENER…K_DICI prueban cobertura mensual, no el año.
- Conteo fuente: 2.211 observaciones mensuales positivas en 524 filas útiles.
- Conteo integrado comparable: 0 filas MCBA / Hortalizas / 2024.
- Meses fuente: Enero, Febrero, Marzo, Abril, Mayo, Junio, Julio, Agosto, Septiembre, Octubre, Noviembre, Diciembre. Meses integrados comparables: ninguno.
- Especies fuente: 63; variedades informadas únicas: 65. Especies integradas comparables: 0.
- Especies principales: TOMATE, PIMIENTO, ZAPALLO, PAPA, AJO, LECHUGA, CEBOLLA, ZAPALLITO, ZANAHORIA, BATATA, REPOLLO, BERENJENA.
- Estructura: encabezado fila 1; columnas de especie ESP; variedad VAR; precio K_ENER, K_FEBR, K_MARZ, K_ABRI, K_MAYO, K_JUNI, K_JULI, K_AGOS, K_SEPT, K_OCTU, K_NOVI, K_DICI; envase/unidad ENV, KG; procedencia PROC.
- Observación metodológica: una fila útil es una presentación (C distinto de 0) con especie y al menos un precio mensual positivo. El conteo comparable usa cada celda mensual positiva como observación; no se usan las filas resumen C=0. La fuente no incluye campo de mercado: MCBA es la interpretación esperada provista para la auditoría, no un valor validable dentro del libro.

### PFRU24_K.xlsx

- Estado: **AUSENTE**.
- Evidencia: El integrado no contiene registros de MCBA/Frutas/2024. No hay columna de fecha ni fechas completas; 2024 sólo se infiere del nombre del archivo/hoja. Las columnas K_ENER…K_DICI prueban cobertura mensual, no el año.
- Conteo fuente: 1.956 observaciones mensuales positivas en 707 filas útiles.
- Conteo integrado comparable: 0 filas MCBA / Frutas / 2024.
- Meses fuente: Enero, Febrero, Marzo, Abril, Mayo, Junio, Julio, Agosto, Septiembre, Octubre, Noviembre, Diciembre. Meses integrados comparables: ninguno.
- Especies fuente: 41; variedades informadas únicas: 187. Especies integradas comparables: 0.
- Especies principales: MANZANA, DURAZNO, NARANJA, CIRUELA, PERA, UVA, BANANA, MANDARINA, LIMON, PALTA, MELON, POMELO.
- Estructura: encabezado fila 1; columnas de especie ESP; variedad VAR; precio K_ENER, K_FEBR, K_MARZ, K_ABRI, K_MAYO, K_JUNI, K_JULI, K_AGOS, K_SEPT, K_OCTU, K_NOVI, K_DICI; envase/unidad ENV, KG; procedencia PROC.
- Observación metodológica: una fila útil es una presentación (C distinto de 0) con especie y al menos un precio mensual positivo. El conteo comparable usa cada celda mensual positiva como observación; no se usan las filas resumen C=0. La fuente no incluye campo de mercado: MCBA es la interpretación esperada provista para la auditoría, no un valor validable dentro del libro.

### PHOR25_K.xlsx

- Estado: **AUSENTE**.
- Evidencia: El integrado no contiene registros de MCBA/Hortalizas/2025. No hay columna de fecha ni fechas completas; 2025 sólo se infiere del nombre del archivo/hoja. Las columnas K_ENER…K_DICI prueban cobertura mensual, no el año.
- Conteo fuente: 2.451 observaciones mensuales positivas en 520 filas útiles.
- Conteo integrado comparable: 0 filas MCBA / Hortalizas / 2025.
- Meses fuente: Enero, Febrero, Marzo, Abril, Mayo, Junio, Julio, Agosto, Septiembre, Octubre, Noviembre, Diciembre. Meses integrados comparables: ninguno.
- Especies fuente: 60; variedades informadas únicas: 68. Especies integradas comparables: 0.
- Especies principales: TOMATE, PIMIENTO, PAPA, AJO, ZAPALLO, LECHUGA, ZAPALLITO, CEBOLLA, ZANAHORIA, REPOLLO, BATATA, BERENJENA.
- Estructura: encabezado fila 1; columnas de especie ESP; variedad VAR; precio K_ENER, K_FEBR, K_MARZ, K_ABRI, K_MAYO, K_JUNI, K_JULI, K_AGOS, K_SEPT, K_OCTU, K_NOVI, K_DICI; envase/unidad ENV, KG; procedencia PROC.
- Observación metodológica: una fila útil es una presentación (C distinto de 0) con especie y al menos un precio mensual positivo. El conteo comparable usa cada celda mensual positiva como observación; no se usan las filas resumen C=0. La fuente no incluye campo de mercado: MCBA es la interpretación esperada provista para la auditoría, no un valor validable dentro del libro.

### PFRU25_K.xlsx

- Estado: **AUSENTE**.
- Evidencia: El integrado no contiene registros de MCBA/Frutas/2025. No hay columna de fecha ni fechas completas; 2025 sólo se infiere del nombre del archivo/hoja. Las columnas K_ENER…K_DICI prueban cobertura mensual, no el año.
- Conteo fuente: 2.090 observaciones mensuales positivas en 743 filas útiles.
- Conteo integrado comparable: 0 filas MCBA / Frutas / 2025.
- Meses fuente: Enero, Febrero, Marzo, Abril, Mayo, Junio, Julio, Agosto, Septiembre, Octubre, Noviembre, Diciembre. Meses integrados comparables: ninguno.
- Especies fuente: 45; variedades informadas únicas: 198. Especies integradas comparables: 0.
- Especies principales: MANZANA, DURAZNO, NARANJA, PERA, UVA, LIMON, BANANA, MANDARINA, PALTA, MELON, CIRUELA, POMELO.
- Estructura: encabezado fila 1; columnas de especie ESP; variedad VAR; precio K_ENER, K_FEBR, K_MARZ, K_ABRI, K_MAYO, K_JUNI, K_JULI, K_AGOS, K_SEPT, K_OCTU, K_NOVI, K_DICI; envase/unidad ENV, KG; procedencia PROC.
- Observación metodológica: una fila útil es una presentación (C distinto de 0) con especie y al menos un precio mensual positivo. El conteo comparable usa cada celda mensual positiva como observación; no se usan las filas resumen C=0. La fuente no incluye campo de mercado: MCBA es la interpretación esperada provista para la auditoría, no un valor validable dentro del libro.

## Control de duplicados potenciales

La clave aproximada normalizada fue fecha (o año-mes si falta), mercado, rubro, especie/producto, variedad, unidad, envase y precio efectivo (`precio_promedio`, luego `precio`, luego `precio_observado`). Es un control conservador: repeticiones legítimas sin identificador adicional pueden quedar señaladas.

- Integrado completo: 11.624 grupos, 34.767 filas afectadas y 23.143 filas excedentes sobre una por clave.
- Sólo MCBA: 4.454 grupos, 10.933 filas afectadas y 6.479 filas excedentes.
- Slices objetivo MCBA 2024-2025: 0 grupos y 0 filas, porque no contienen registros.
- No se eliminó ni modificó ninguna observación.

## Conclusión

- Incorporadas: ninguna.
- Parciales: ninguna.
- Ausentes: PHOR24_K.xlsx, PFRU24_K.xlsx, PHOR25_K.xlsx, PFRU25_K.xlsx.
- Inciertas: ninguna.

El integrado contiene Mercado Central de Buenos Aires únicamente para 2026. No hay filas comparables de MCBA para Frutas u Hortalizas en 2024 o 2025, por lo que las cuatro bases esperadas se clasifican como AUSENTES. La inferencia del año de cada fuente debe quedar explícita porque los libros no aportan fechas completas.

## Recomendación

Integrar las cuatro bases en un segundo paso, con una regla documentada que asigne el año desde el archivo/hoja y convierta cada columna mensual en observaciones fechadas sin inventar día. Antes de hacerlo, acordar la granularidad temporal (por ejemplo, año-mes) y la clave de deduplicación. Esta auditoría no ejecuta la integración ni modifica el dashboard o el integrado.
