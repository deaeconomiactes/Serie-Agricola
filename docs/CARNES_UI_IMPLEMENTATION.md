# Carnes — primera UI productiva

Para las métricas y comparaciones añadidas en el piloto posterior, consultar
[Carnes: tercera iteración analítica](CARNES_ANALYTICS_PILOT.md). Esta guía
describe la primera implementación productiva.

Implementación del 22/10/2026 basada en `CARNES_UI_PLAN.md` (nombre real de la
propuesta aprobada en main; el adjunto la menciona como `CARNES_UI_PROPOSAL.md`).
No cambia datos ni pipelines. No activa cron. Los módulos existentes conservan
sus controles y lógica; sus KPIs globales de Cantidades se ocultan únicamente
mientras Carnes está activo, para no atribuirlos a las nuevas familias.

## Superficie y archivos

- `index.html`: pestaña y contenedor Carnes; ningún CSV Carnes se carga al inicio.
- `app.js`: registro de la pestaña y carga de `carnes.js` al primer acceso.
- `carnes.js`: loader validado, estado, filtros, KPIs, gráficos, tablas y descarga
  de selección. Sin dependencias de adquisición ni consultas a APIs externas.
- `styles.css`: extensiones acotadas a Carnes que reutilizan los componentes
  institucionales; no cambia las reglas de los otros módulos.
- `.gitignore`: permite versionar el nuevo módulo JavaScript.

## Familias, filtros y métricas

Principales: faena bovina, producción bovina y peso medio. Año, mes, fuente y
frecuencia dependen de los fragmentos existentes. Provincia sólo aparece para la
tabla provincial de faena. Categoría/dentición sólo aparecen si existen; elegir
provincia restablece categoría/dentición, que quedan deshabilitadas. Explorar una
categoría tiene ámbito nacional. La especie se muestra como atributo de la
publicación: bovinos o bovinos+bubalinos no separables; no se ofrece un desglose falso.

Las clasificaciones de 2019 se seleccionan separadamente. No se combinan
categorías antiguas de peso/sexo con categorías nuevas por dentición.

| Familia | KPIs | Gráficos |
|---|---|---|
| Faena | Cabezas, interanual compatible, participación provincial, categoría/dentición principal cuando aplica | Evolución del año, ranking provincial, composición nacional |
| Producción | Toneladas publicadas e interanual compatible | Evolución; sin mapa o distribución provincial inventada |
| Peso | Media publicada por categoría e interanual compatible | Evolución y comparación de categorías |

El mes determina KPIs/desgloses; la evolución y tabla muestran la serie del año
seleccionado, con ese alcance indicado en el gráfico y título de tabla.
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
No hay empalme con Cañuelas, conversión de moneda ni de kg producto a RCH.

El estado visual proviene de `CARNES_UPDATE_STATUS.json` y `source_lifecycle` del
índice: UPDATED (incluye NO_OP_ALREADY_CURRENT), HISTORICAL_ENDED,
SOURCE_UNAVAILABLE, NO_PUBLICATION y PIPELINE_ERROR. Un archivo histórico
finalizado no genera error por antigüedad. Una incidencia no elimina la etiqueta
histórica. Si la metadata de estado no se puede leer, se indica su ausencia.

Fuente, cobertura de archivos, último dato de la selección, captura UTC y unidad
se muestran de forma compacta. «Cobertura de archivos» no implica que cada
métrica tenga valores en todos sus años: los faltantes permanecen explícitos.

## Carga y performance

El frontend sólo solicita el índice, metadata de estado y fragmentos DASHBOARD
por familia/frecuencia/año. El año anterior se solicita únicamente para la
comparación interanual dentro de la misma publicación y si el índice lo contiene.
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

### Resultado ejecutado

- Suite frontend: 79 aprobadas, incluyendo 16 de Carnes.
- Python Carnes: 29 aprobadas; Python común: 74 aprobadas.
- Edge y Chrome: recorridos completos aprobados, sin errores JavaScript ni
  overflow horizontal a 900 px. Screenshots desktop 1440 px y ancho intermedio
  900 px inspeccionados; las imágenes y reportes quedan fuera de Git.
- La carga de un fragmento sintético corrupto conserva la vista válida y muestra
  una advertencia; cambios rápidos no publican una selección anterior.
- actionlint y `git diff --check` sin errores. Workflows, adquisición y datasets
  oficiales permanecen sin modificaciones.
