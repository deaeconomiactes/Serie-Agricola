# Carnes: revisión inicial de fuentes

La documentación de cobertura y metodología existente está en
[CARNES_DATA_PLATFORM.md](CARNES_DATA_PLATFORM.md). Las coberturas de los
archivos disponibles no garantizan observaciones para cada categoría o mes.

## Cabezas fraccionarias: Corrientes

El avance de faena de [MAGyP/DNCCA](https://www.magyp.gob.ar/sitio/areas/gestion/bovinos.php?accion=imp)
contiene valores numéricos literales en la hoja `POR PROVINCIA`, fila 15:
febrero de 2026, C15 = 9114,5; marzo, D15 = 9887,25; mayo, F15 = 10171,25;
septiembre, J15 = 9824,5. No son fórmulas en el archivo consultado el 13/11/2026.
El XLSX consultado tenía SHA-256
`ad7a79abbfb0a662a4dc5f1bcd5f4860fb353145d27715dfa285ff1e2e971fc3`.
La captura previamente integrada, de hash
`58a9079b5062fcdfa77013bb5dbf06254b951bb87f73a405ae7ab57c0cab4631`,
conserva esos mismos valores y localizadores en el CSV publicado. Los archivos
son distintos: esta comparación no reemplaza la evidencia RAW de la captura anterior.

El extractor lee el número de la celda sin agregar ni redondear y marca
`fractional_published_value`; existe una prueba de regresión para conservar valores
fraccionarios y su localizador. No se encontró una explicación metodológica
oficial que permita atribuirlos a estimaciones u otra causa. No debe suponerse que
una fracción representa un animal individual ni corregirse sin evidencia adicional.
La conciliación provincial con el total publicado no demuestra por sí sola que el
origen haya calculado correctamente las cifras.

## Peso y exportaciones

El [informe sectorial oficial](https://www.magyp.gob.ar/sitio/areas/bovinos/informacion_interes/informes/index.php)
describe una serie mensual reciente de faena y producción y una clasificación
anterior a la Resolución 32/2018. No se deben empalmar las clasificaciones sin
validar sus conceptos. La fuente detallada de peso disponible en el dashboard
publica kg de res con hueso por categoría y dentición, sin total nacional cacheado;
la serie histórica finalizada tiene otra cobertura. La disponibilidad de archivos
no garantiza un total publicado ni la comparabilidad de categorías.

La página de [información sectorial bovina](https://www.magyp.gob.ar/sitio/areas/bovinos/informacion_sectorial/)
enlaza un [tablero de exportaciones en PDF](https://www.magyp.gob.ar/sitio/areas/bovinos/informacion_sectorial/_archivos/000019_Tablero%20de%20exportaciones/000003_Tablero_exportacion_carne_bovina.pdf),
cuya página indica actualización a septiembre de 2026. El documento consultado
tiene SHA-256 `e48a97a0bea0803591433f566fa44acdb7abe346372fede68843b02713081197`;
presenta totales acumulados en toneladas equivalentes res con hueso y miles de USD,
y gráficos de destinos en toneladas peso producto. Las cifras gráficas no
constituyen una tabla mensual de datos apta para extraer sin validación adicional.
No se incorporó una serie automática a partir de esas imágenes.

El [BCRA](https://www.bcra.gob.ar/tipo-cambio-referencia-comunicacion-a-3500-tcnpm/)
publica la planilla histórica A 3500. La descarga respondió inicialmente HTTP 403,
pero el 13/11/2026 se obtuvo con una identificación de cliente HTTP. La captura
tiene SHA-256 `b57e4284bb6160ae35a70a1890a6db933b955f108db0f2528022d1a6488ce50c`
y cubre el período MAG hasta el 12/11/2026. La hoja diaria es distinta de la hoja
de promedios mensuales. El dashboard divide ARS/kg vivo por ARS/USD; usa la última
referencia anterior dentro de siete días corridos, solamente entre el primer y el
último día observado de BCRA. No extrapola más allá de la cobertura ni convierte
el índice INMAG. El CSV conserva precio original, tipo de cambio, fecha, fuente,
captura y hash. El cambio de metodología A3500 anunciado para 2026 se conserva
como parte de la serie oficial y debe tenerse en cuenta en comparaciones largas.

La actualización `scripts/carnes/bcra_rates.py --allow-web` conserva la respuesta
original en RAW, verifica estructura, valores, orden y cobertura antes de reemplazar
el archivo liviano. Los estados son `UPDATED`, `NO_PUBLICATION`,
`SOURCE_UNAVAILABLE` y `PIPELINE_ERROR`; ante un error conserva la última salida.
El workflow `update-carnes-bcra.yml` guarda el RAW como artefacto y publica sólo
la salida y estado livianos cuando se ejecute en `main`.

## Consulta COMEX INDEC

El sistema [COMEX INDEC](https://comex.indec.gob.ar/) admite consultas mensuales
por NCM de ocho dígitos y país; su interfaz identifica peso neto en kg y valor
FOB en USD, y señala celdas protegidas por secreto estadístico. El 13/11/2026 se
consultaron las diez posiciones vigentes que comienzan con 0201 o 0202 para 2026
mediante el servicio público usado por esa interfaz. La respuesta guardada en RAW
tiene SHA-256 `9dc46f12e03a702b7676903fd2bcc6a6ff0f15c940e301a5e8a2b07b2077c7e3`:
54 filas para enero–septiembre, nueve confidenciales. En esas filas el cero del
servicio **no** es un valor publicado y no debe tratarse como tal.

Las 45 filas no confidenciales suman USD 3.791.180.152,09 y 549.616.926 kg;
es una suma parcial de posiciones disponibles, no un total validado. El tablero
MAGyP consultado declara USD 3.656.454 miles y 675.192 toneladas equivalentes res
con hueso para enero–septiembre. El peso producto no equivale a RCH, y las cifras
de valor tampoco coinciden directamente. No se confirmó la causa: pueden influir
el alcance de productos, fechas de revisión u otras diferencias de compilación.
No se publica una serie de exportaciones hasta resolver cobertura, secreto y
conciliación; no se distribuye un parcial como total ni se infieren faltantes.
