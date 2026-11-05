# Validación de cobertura exploratoria

Corte aplicado: 2026-11-05. Datos y mediciones corresponden a los shards del índice actualizado de este cambio.

## Inventario y controles por lotes

El script `node --expose-gc --max-old-space-size=1024 scripts/mayoristas/validar_cobertura_exploratoria.cjs`, con `MAYORISTAS_AS_OF=2026-11-05`, recorre secuencialmente año, frecuencia y mercado mediante el loader productivo. La [matriz CSV comprimida](COBERTURA_EXPLORATORIA_MATRIZ.csv.gz) contiene 30,858 combinaciones presentes de mercado, fuente, producto, año, mes, frecuencia de vista, procedencia, variedad y granularidad, con recuentos de fechas futuras. Los [resultados JSON](COBERTURA_EXPLORATORIA_RESULTADOS.json) contienen catálogos y totales. El inventario no inventa combinaciones ausentes.

En la vista mensual, excluyendo fechas posteriores al corte, se observaron 217 productos y 46 procedencias, en 3 años y dos mercados. Se contrastó cada mediana mensual con un cálculo independiente por producto, procedencia, mercado y mes, incluida la cantidad de registros. NO_DATA cuenta producto/procedencia/mes presentes en un mercado y ausentes en el otro; NOT_COMPARABLE cuenta grupos mensuales presentes sin observaciones aptas o con mezcla de fuentes o granularidades. Los contadores usan universos distintos y no se suman como un total de pruebas.

| Año | Productos | Mercados | Meses observados | PASS mediana | NO_DATA entre mercados | NOT_COMPARABLE mensual | FAIL mediana |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2024 | 189 | 2 | 12 | 2017 | 2013 | 14 | 0 |
| 2025 | 175 | 2 | 12 | 3871 | 3340 | 167 | 0 |
| 2026 | 163 | 2 | 11 | 2837 | 2574 | 105 | 0 |

Los 8,725 grupos con mediana válida coinciden con la referencia (100 % de esos cálculos). Se identificaron 286 grupos mensuales no comparables, 7,927 períodos sin observaciones en el otro mercado y 500 períodos comunes con ambos precios válidos. Hay 42 casos adicionales con datos en ambos mercados pero al menos un precio no comparable. Las 115 filas posteriores al corte en los shards mensuales quedan en el inventario y fuera de las medianas. El recorrido por lotes comprueba las medianas; la interfaz se verifica mediante la muestra descrita abajo, no con cada una de las combinaciones.

## Equivalencia económica e integridad

Los 11 controles originales pasaron en procesos independientes, manteniendo la igualdad exacta de filas, KPI, evolución, rankings, variaciones y tabla. La preparación conserva el catálogo completo para normalizar, pero materializa sólo el mercado, año y frecuencia del control. Cada proceso libera su memoria al terminar. La validación de integridad de los 19 shards, esquemas, hashes y recuentos pasó.

El índice anterior referenciaba el derivado mensual MCBA del 30 de octubre, mientras que el CSV y su marcador fueron actualizados el 4 de noviembre: 3.766 frente a 4.055 filas. La aserción de igualdad intentaba generar un diff voluminoso y agotaba memoria; el mismo fallo se reprodujo en `origin/main`. El test ahora detecta diferencias de manera acotada antes de conservar la aserción completa. Se reconstruyó una candidata con el pipeline existente, se verificaron sus 11 controles y se activaron únicamente el índice y el shard mensual MCBA 2026 nuevos. Los otros 18 shards son idénticos; el shard anterior permanece en disco. No se modificaron las fuentes originales.

## Frontend y rendimiento

Pasaron 26 pruebas frontend secuenciales y 15 pruebas Python del pipeline, incluida la regresión de reconstrucción ante una publicación cambiada. En Edge headless se probaron Tomate para 2024, 2025, 2026 y Todos los años; otro producto; un mercado y dos; ausencia de mes común; un mes sin observaciones; limpieza; y gráficos avanzados diario y anual. La prueba contrastó los KPI, puntos, barras de variación y celdas de tabla para las selecciones históricas, y la comparación estricta y su selector. No se registraron errores JavaScript. La validación visual es una muestra representativa, no una revisión manual de todas las combinaciones.

El máximo RSS de un control económico fue aproximadamente 1111 MiB; el barrido histórico registró 384 MiB de RSS máximo. La carga inicial medida localmente fue de 963.172 bytes en tres solicitudes y 1,75 s, con aproximadamente 71 MB de heap reportado por el navegador. La referencia histórica del repositorio era 849.526 bytes y 1,73 s; no es una medición controlada idéntica. El dato mensual vigente de noviembre de 2026 se identifica como mes en curso.

## Estado

PASS: controles económicos, integridad, pruebas frontend y de pipeline y muestra visual descrita. Sin fallos económicos conocidos en el estado validado. La cobertura de interfaz sigue siendo una muestra y no debe interpretarse como revisión visual individual de cada selección.
