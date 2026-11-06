# Diferencia MCBA mensual y criterio de validación

Corte de la comprobación: 6 de noviembre de 2026. El índice versionado en Git identifica el CSV MCBA de 4.055 filas con SHA-256 `b16df72e35e9a8773674b8ed7fe48e019fb03611edcac2ce7332ff8e781ed2ea`. La publicación fuente vigente tiene 4.058 filas, SHA-256 `b90a614e9872d564436b08921964e6d5ebe9f58b5ebe8c1f2e44db717bdef244`, coincidente con `_SUCCESS.json`. Son 4.055 y 4.058 claves económicas únicas, sin duplicados por período, rubro, producto, variedad, procedencia, envase, peso, calidad, tamaño y grado. No se eliminaron claves; hay tres nuevas y los precios de 153 claves existentes cambiaron con la incorporación de días observados.

Las tres claves nuevas son agregados mensuales de noviembre basados en una observación del **5 de noviembre**. Se descargaron los ZIP oficiales y sus SHA-256 coincidieron con los registrados en las filas; `ZipFile.testzip()` no informó errores. Se abrieron las planillas BIFF y se cotejó la columna modal por kg (MOPK):

| Producto y procedencia | Presentación / calidad | Precio ARS/kg | Planilla oficial |
|---|---|---:|---|
| Tomate Perita, Brasil | Caja 18 kg, Primera, Mediano, PIN | 2.944,44 | `RH051126.XLS`, fila 184, [ZIP hortalizas](https://mercadocentral.gob.ar/sites/default/files/precios_mayoristas/HORTALIZA_NOVIEMBRE-26_0.zip) |
| Melón Rocío Miel, Santiago del Estero | Perdido 12 kg, Elegido, 008/012 | 2.666,67 | `RF051126.XLS`, fila 95, [ZIP frutas](https://mercadocentral.gob.ar/sites/default/files/precios_mayoristas/FRUTAS_NOVIEMBRE-26_0.zip) |
| Naranja Valencia Late, Entre Ríos | Torito 18 kg, Elegido, 080/100 | 777,78 | `RF051126.XLS`, fila 104, [ZIP frutas](https://mercadocentral.gob.ar/sites/default/files/precios_mayoristas/FRUTAS_NOVIEMBRE-26_0.zip) |

El workflow productivo MCBA del 5 de noviembre terminó correctamente y el despliegue de Pages del 6 de noviembre (`42208683941`) reconstruyó el índice y los fragmentos desde la fuente vigente. La consulta al índice del sitio publicado confirmó **4.058 filas** y el hash vigente. El índice versionado en Git permanece con la fotografía anterior; no se modificaron las fuentes ni los datos RAW en esta rama.

La validación distingue dos cuestiones:

1. **Equivalencia:** los once controles comparan el shard y sus resultados con los insumos exactos cuyos hashes figuran en su índice. Si un insumo local cambió, la prueba busca en el historial Git la versión que coincide con ese SHA-256, la copia a un directorio temporal y no toca el archivo actual. Si la fotografía no está disponible, informa `SOURCE_SNAPSHOT_UNAVAILABLE`; no la reemplaza por una fuente distinta.
2. **Actualidad:** se informa `SOURCE_CHANGED` cuando la fuente actual difiere del índice y se verifica por separado el CSV mensual actual contra su marcador de integridad. Una diferencia de hash no se denomina corrupción ni acredita por sí sola que la nueva fuente sea posterior. Con ambos marcadores validados, se comparan las últimas fechas observadas y se informa `SOURCE_NEWER`, `SOURCE_CHANGED_SAME_COVERAGE` o `SOURCE_OLDER`. En este caso la cobertura avanza del 4 al 5 de noviembre. Las candidatas explícitas siguen exigiendo coincidencia con los insumos actuales, de modo que una candidata desactualizada falle y deba reconstruirse.
