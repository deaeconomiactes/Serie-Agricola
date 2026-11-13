# Carnes — primera UI productiva

Para las métricas y comparaciones añadidas en el piloto posterior, consultar
[Carnes: tercera iteración analítica](CARNES_ANALYTICS_PILOT.md). Esta guía
describe la primera implementación productiva.

Interfaz implementada el 22/10/2026 y ampliada para precios MAG y exploración
multianual. La revisión de fuentes y conversión BCRA está en
[CARNES_REVISION_FUENTES_2026-11-13.md](CARNES_REVISION_FUENTES_2026-11-13.md).
Los módulos existentes conservan sus controles y lógica; sus KPIs globales de
Cantidades se ocultan únicamente mientras Carnes está activo, para no atribuirlos
a las nuevas familias.

## Superficie y archivos

- `index.html`: pestaña y contenedor Carnes; ningún CSV Carnes se carga al inicio.
- `app.js`: registro de la pestaña y carga de `carnes.js` al primer acceso.
- `carnes.js`: loader validado, estado, filtros, KPIs, gráficos, tablas y descarga
  de selección. Carga fragmentos publicados y no consulta APIs externas.
- `styles.css`: extensiones acotadas a Carnes que reutilizan los componentes
  institucionales; no cambia las reglas de los otros módulos.
- `scripts/carnes/mag_prices.py`: captura pública de MAG, evidencia RAW inmutable,
  validación y bundle de dashboard.
- `.github/workflows/update-carnes-mag.yml`: actualización diaria hábil del módulo;
  la ejecución productiva se habilita cuando el PR se integre.
- `.gitignore`: permite versionar el nuevo módulo JavaScript.

## Familias, filtros y métricas

La sección principal es **Precios ganaderos**. Faena bovina, producción bovina y
peso medio conservan sus vistas anteriores. Año, mes, fuente y
frecuencia dependen de los fragmentos existentes. Provincia sólo aparece para la
tabla provincial de faena. Categoría/dentición sólo aparecen si existen; elegir
provincia restablece categoría/dentición, que quedan deshabilitadas. Explorar una
categoría tiene ámbito nacional. La especie se muestra como atributo de la
publicación: bovinos o bovinos+bubalinos no separables; no se ofrece un desglose falso.

Las clasificaciones de 2019 se seleccionan separadamente. No se combinan
categorías antiguas de peso/sexo con categorías nuevas por dentición.

| Familia | KPIs | Gráficos |
|---|---|---|
| Precios ganaderos | Último promedio publicado por categoría, fecha y estado de actualización | Evolución diaria MAG desde 17/05/2022; tabla descargable de estadísticas por clasificación; I.N.M.A.G. en tarjeta separada |
| Faena | Cabezas, interanual compatible, participación provincial, categoría/dentición principal cuando aplica | Evolución del año, ranking provincial, composición nacional |
| Producción | Toneladas publicadas e interanual compatible | Evolución; sin mapa o distribución provincial inventada |
| Peso | Media publicada por categoría e interanual compatible | Evolución y comparación de categorías |

El mes determina los indicadores de nivel y desgloses. La exploración mensual
personalizada carga los años de la fuente elegida, ofrece sólo meses observados y
actualiza el gráfico principal, tabla y descarga al rango elegido. Su acumulado
calculado se muestra sólo para faena o producción con meses completos y la misma
serie; su comparación exige el mismo rango completo del año anterior. No se suma
el peso medio. Las opciones anuales y los acumulados publicados siguen separados.
Las tablas conservan unidades, condición provisoria, fuente, captura, localizador,
hash RAW y flags; se puede descargar la selección completa aunque la tabla pagine.
Las URLs completas permanecen en los enlaces, no en los tooltips.

### Totales y límites reales

- Los totales de provincia, establecimiento y usuario son redundantes. No se suman.
  En mensual, el total nacional de faena usa el `Total general` publicado de
  `slaughter/category_age`: el total de la hoja provincial no tiene resultado
  cacheado en el avance actual. No se calcula el total desde las provincias.
- La participación provincial mensual usa ese mismo total nacional publicado y
  el numerador provincial de igual período/especie/unidad. Control offline:
  los nueve meses enero–septiembre 2026 coinciden con la suma de las celdas
  provinciales. La UI no realiza esa suma para producir su denominador.
- Anual y acumulado de faena usan el total publicado de la tabla provincial;
  si falta su valor, se muestra «Sin dato publicado», sin fabricar resultado.
- Para los acumulados de categorías se usa una sola tabla por dentición:
  `TOTAL POR EDAD`, o `PESO MEDIO DE LA RES POR DENTICION (KG)`. No se mezcla con
  totales por categoría ni participaciones redundantes.
- El avance de peso no trae resultados cacheados para el total nacional.
  La vista inicial de peso selecciona explícitamente Novillito / 2 dientes,
  que sí tiene medias publicadas. Seleccionar el total muestra el faltante y
  una explicación; nunca se promedian categorías para reconstruirlo.
- Producción SSPM conserva «Toneladas» y base de peso no identificada; no se
  rotula RCH. La producción DNCCA sí conserva toneladas res con hueso declaradas.
- La interanual exige período equivalente, misma familia, métrica, especie,
  tabla, entidad, geografía, categoría, dentición, moneda, unidad, base de peso,
  metodología y frecuencia. Los archivos anuales/avance de la misma publicación
  pueden compararse cuando coinciden esas dimensiones; no se empalma SSPM con DNCCA.
  Si falta denominador positivo comparable, se muestra «Sin base comparable».
- Producción/peso detallados sólo tienen 2026 integrado: no se inventa su
  interanual con otra publicación. Los acumulados requieren igual mes de cierre;
  enero–septiembre no se compara con enero–diciembre.
- Mensual/anual/acumulado permanecen separados. Un acumulado muestra su cierre
  explícito, por ejemplo «Acumulado enero–septiembre 2026». Las observaciones
  provisorias llevan esa condición en la nota y tabla.

## Históricos y metadata

«Series históricas finalizadas» abre una sección secundaria, con carga diferida,
para Liniers 1998–2019 y exportaciones 1998–2019. No modifica la familia principal.
Precios ARS y USD tienen selectores de magnitud separados; las exportaciones
distinguen volumen RCH, valor en miles USD y valor unitario USD/t RCH.
No hay empalme de Liniers con Cañuelas ni conversión de kg producto a RCH. La
vista corriente de MAG ofrece una conversión explícita a USD con BCRA A3500; no
altera los datos originales ni convierte I.N.M.A.G.

La vista de precios corrientes usa seis categorías del gráfico diario oficial MAG:
Novillos, Novillitos, Vaquillonas, Terneros, Vacas y Toros. El servicio también
devuelve etiquetas anteriores a la apertura del mercado en Cañuelas; el pipeline
empieza el 17/05/2022 y descarta las fechas anteriores para que el historial de
Liniers no aparezca como MAG Cañuelas. El promedio gráfico y los estadísticos del
informe diario detallado tienen `methodology` distintos. La tabla muestra la
última fecha disponible y distingue precios provisorios de definitivos por el
encabezado original; se descarga junto con categoría/clasificación, captura y
hash RAW.

La consulta de totales publica cabezas, importe e I.N.M.A.G. El índice se visualiza
por separado en puntos; no se deriva de los promedios por categoría. `Falta Cerrar`
y `- *` permanecen como valores faltantes con el texto original. El I.N.M.A.G. puede
quedar sin valor cerrado aunque los totales diarios ya estén publicados.

La tabla de precios MAG no imprime unidad. La UI muestra ARS/kg vivo porque el
tablero sectorial SAGyP oficial identifica los precios MAG con esa unidad; el
catálogo y cada fila marcan esta asignación como inferencia documentada. `unit_raw`
queda vacío para el precio cuando MAG no imprime unidad; la exportación descarga
por separado unidades originales/normalizadas y flags de calidad. La publicación
MAG no declara licencia de redistribución; el acceso público no confirma términos
de uso.

El estado visual proviene de `CARNES_UPDATE_STATUS.json` y `source_lifecycle` del
índice: UPDATED (incluye NO_OP_ALREADY_CURRENT), HISTORICAL_ENDED,
SOURCE_UNAVAILABLE, NO_PUBLICATION y PIPELINE_ERROR. Un archivo histórico
finalizado no genera error por antigüedad. Una incidencia no elimina la etiqueta
histórica. Si la metadata de estado no se puede leer, se indica su ausencia.

Fuente, cobertura de archivos, último dato de la selección, captura UTC y unidad
se muestran de forma compacta. «Cobertura de archivos» no implica que cada
métrica tenga valores en todos sus años: los faltantes permanecen explícitos.

## Carga y performance

El frontend solicita el índice, metadata y fragmentos DASHBOARD necesarios para
la selección. Al explorar un rango mensual carga los años disponibles de la fuente;
al entrar en una familia revisa la última observación válida de fuentes candidatas.
La serie BCRA se carga sólo cuando se selecciona USD.
No solicita RAW/NORMALIZED/ANALYTICAL ni detalle de establecimientos/usuarios.

Cada fragmento se valida por SHA-256, tamaño, schema, conteo, origen y grano.
La descompresión CSV.gz usa `DecompressionStream`, comprobado en Edge/Chrome.
El parser conserva campos con comillas/saltos. Cero y faltante son distintos.
Cache por hash; un fragmento fallido no queda cacheado como válido. Las respuestas
de selecciones anteriores se ignoran mediante revisión de estado; no reemplazan
la selección más reciente. Si falla una nueva carga se conserva la última vista,
con una advertencia explícita sobre la selección fallida.

Medición local de apertura inicial, en Edge y Chrome:

| Recurso | Bytes |
|---|---:|
| Índice | 88.543 |
| Metadata de estado | 1.875 |
| Faena mensual 2026 | 38.312 |
| Faena mensual 2025 (base interanual) | 48.710 |
| Total datos, 4 solicitudes | **177.440** |

El script diferido `carnes.js` se transfiere además de esos datos. CSS y Chart.js
ya pertenecen al dashboard existente. La medición representa cuerpos recibidos
en servidor local, no overhead HTTP ni compresión adicional del hosting. No se
descarga el histórico completo ni las series históricas al abrir Carnes.
Se verificó también el fragmento corriente publicado en GitHub Pages: HTTP 200,
`Content-Type: application/gzip`, sin `Content-Encoding`, tamaño 38.312 bytes.
La descompresión explícita del módulo es compatible con esa entrega del hosting.
El script medido ocupa 37.682 bytes: incremento inicial total de datos + módulo
de 215.122 bytes, sin contar recursos institucionales previamente cargados.

## Validación reproducible

```powershell
node --test tests/magyp_frontend/carnes.test.cjs
node --test tests/magyp_frontend/*.cjs
python -m unittest discover -s tests/carnes -v
python -m unittest discover -s tests/magyp_common -v
python scripts/carnes/validate.py
git diff --check
```

Pruebas visuales/funcionales opt-in, con Playwright y Edge/Chrome instalados;
no forman parte de los requisitos de adquisición de Carnes:

```powershell
python -m http.server 8767 --bind 127.0.0.1
# En otra terminal, apuntando a ese checkout:
python tests/carnes/browser_ui_checks.py --channel msedge --output "$env:TEMP/carnes-ui-validation"
python tests/carnes/browser_ui_checks.py --channel chrome --output "$env:TEMP/carnes-ui-validation"
```

El script valida lazy loading, filtros, provincia/categoría, transición 2019,
anual/acumulado parcial, provisorios, total de peso ausente, selección rápida,
estados, históricos y regreso a pestañas existentes. Genera screenshots en
1440 px y 900 px, reportes de payload y errores JS fuera de Git. Las pruebas
Node verifican además hashes/schema, duplicados, cero/faltante, no agregación
de tablas redundantes y base interanual. No consulta fuentes nuevas.
Usan fragmentos DASHBOARD congelados en `tests/carnes/fixtures/ui/`, evitando que
una actualización legítima del avance corriente rompa el test. Las pruebas browser
sí inspeccionan los outputs productivos del checkout. Requieren Node 20 o posterior
para WebCrypto, Blob y descompresión nativa en la suite Node.

### Verificación de la actualización MAG · 11/11/2026

- Python Carnes: 41 pruebas aprobadas, incluidas captura RAW, decimales argentinos,
  fechas, clasificaciones, provisorios/definitivos, `NO_PUBLICATION`, caída de
  fuente y protección del último bundle válido. Empaquetado Pages: 1 prueba aprobada.
- Suite frontend del repositorio: 152 pruebas aprobadas.
- Edge sobre el paquete preparado para Pages: recorrido completo aprobado, 466.840
  bytes iniciales de Carnes en 24 solicitudes, sin errores JavaScript ni overflow
  horizontal en 1440, 1000, 900 y 640 px. Capturas y reportes quedan fuera de Git.
- El paquete Pages valida 21.832 observaciones y excluye `raw`, `normalized` y
  `analytical`. El bundle MAG comprimido de esta captura ocupa 1.056.109 bytes.
- La captura oficial del 11/11 registró datos definitivos para cinco categorías;
  Terneros conserva 09/01/2026 como último promedio gráfico (`NO_PUBLICATION`). El
  I.N.M.A.G. del 11/11 fue publicado como `- *`, distinto de un valor cerrado.
- La ejecución productiva de GitHub Actions y la URL final de Pages quedan para
  después de integrar el PR y recibir autorización del usuario.
