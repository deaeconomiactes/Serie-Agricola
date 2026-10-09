# FOB: respuesta vacía oficial — 2026-10-09

Se comparó el parser con dos consultas controladas al endpoint oficial. La primera consulta usó por error el día 8; la segunda, autorizada expresamente, reprodujo la fecha del workflow fallido.

| Consulta `Fecha` | HTTP | Content-Type | Respuesta |
| --- | --- | --- | --- |
| `08/10/2026` | 200 | `text/html; charset=UTF-8` | Objeto `{"posts":[...]}` con 134 filas |
| `09/10/2026` | 200 | `text/html; charset=UTF-8` | Exactamente `[]`, dos bytes |

La consulta del día 9 se realizó a las `2026-10-09T12:25:54.928612Z`. SHA-256 de su cuerpo: `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.

En la respuesta no vacía no cambió ningún campo: `fecha`, `circular`, `posicion` siguen siendo strings; `precio`, `mesDesde`, `añoDesde`, `mesHasta`, `añoHasta` siguen siendo enteros. No hay campos agregados o eliminados ni cambios de nesting para los registros. La diferencia observada es la representación vacía: array raíz sin registros, en lugar del objeto con `posts`. No prueba un cambio del schema de precios ni permite concluir que el día 9 nunca tendrá publicación.

## Corrección acotada

`project()` reconoce únicamente un array raíz vacío como representación FOB conocida y lo conserva, sin convertirlo ni aceptar arrays con registros. La validación exacta de los ocho campos y del objeto raíz `posts` permanece intacta para respuestas no vacías.

`parse_fob()` distingue la ausencia de registros del schema desconocido. Tanto `[]` como `{"posts":[]}` generan `FOB sin publicación para la fecha solicitada; respuesta vacía no publicable`. En día hábil el proceso sigue fallando con código 1 y preserva el último CSV válido. La excepción existente de fin de semana se aplica ahora a ambas representaciones; no publica ni sobrescribe nada. No se agregó calendario de feriados ni backfill automático de otra fecha.

Un schema desconocido sigue produciendo error, conserva la última salida y deja el workflow con código 1. La ejecución `--source all` continúa con las otras familias aunque FOB falle, conservando el resultado global fallido. Ningún parser de las otras familias, workflow, CSV ni archivo del dashboard se modificó.

## Pruebas

Cuatro fixtures livianos: schema legacy sintético, una fila publicada del día 8, array vacío observado el día 9 y schema desconocido sintético. No se versionó la respuesta completa ni capturas RAW.

Cinco pruebas nuevas verifican compatibilidad y valores originales, representación vacía, rechazo de schemas desconocidos, conservación del último FOB en fin de semana y, con vacíos/schema desconocido en día hábil, publicación independiente de las otras cuatro familias con código global 1. Se mantienen las pruebas existentes de fechas, precios, duplicados y publicación atómica.

Moneda y unidad continúan como `Sin identificar`; no se agregaron producto, NCM ni equivalencias de posición.

Validación final: 23 tests Python de referencias y 20 tests frontend; `git diff --check`. Para verificar publicación real en Linux debe usarse una fecha con datos publicados; un vacío en día hábil continuará fallando de forma explícita.
