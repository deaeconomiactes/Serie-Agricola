# Carnes — tercera iteración: análisis para decisión

23/10/2026 · local, rama `codex/ui-refresh-institucional-carnes`.
Checkout: `C:/Users/acer/Oficina/Serie-Agricola-ui-carnes`.
Sin commit/push/merge ni publicación. Se conserva la dirección visual de la
[segunda iteración](CARNES_UI_REFRESH_PILOT.md). Se añaden cálculos en el frontend
sobre los fragmentos DASHBOARD validados; no se modifican CSV publicados,
pipelines, fuentes, workflows ni observaciones originales.

## Contrato común de comparabilidad

Cada serie conserva publicación, familia, métrica, especie, tabla, tipo de
entidad, geografía, categoría, dentición, moneda, unidad, base de peso,
metodología, frecuencia, mercado e identidad/actividad de entidad.

Los archivos `magyp_slaughter_YYYY` y `magyp_slaughter_current` identifican
archivos anuales/avance de la misma publicación de faena. Sólo esa identidad
de publicación se reconoce explícitamente entre archivos; las demás dimensiones
deben coincidir. Para las demás fuentes se exige el mismo `source_id`.
SSPM 40.1 anual y 40.3 mensual siguen separados. Tampoco se empalma DNCCA con
SSPM ni peso de indicadores históricos con peso DNCCA.

Equivalencia acotada de dentición: Unicode NFC, espacios extremos/internos y
mayúsculas/minúsculas se ignoran únicamente para comparar `age_class`.
Motivo verificado: «Más de 8 dientes» en 2025 y «más de 8 dientes» en 2026.
No se modifican los campos/etiquetas originales, no se equiparan «8 dientes»
y «más de 8 dientes» y no se convierten categorías anteriores por peso/sexo.
Duplicados tras esa equivalencia invalidan el cálculo.

Una ventana mensual exige exactamente una observación válida por mes,
inicio el día 1, cierre el último día calendario y ningún faltante, duplicado
o cambio de dimensiones. Cero observado es válido; faltante nunca es cero.
Los acumulados publicados conservan su frecuencia y no se usan para rellenar
meses. Los datos provisorios mantienen esa condición en la selección y detalle.

## Métricas y visualizaciones: pregunta, fórmula y límites

En la tabla, `x[t]` es el valor de la serie seleccionada y `M` el mes de cierre.
Las condiciones del contrato común se aplican a todas las filas.

| Componente / pregunta | Fórmula o representación | Dimensiones y condiciones adicionales | Sin base válida |
|---|---|---|---|
| Nivel publicado: ¿cuánto? | `x[t]`, sin transformación | Una observación publicada de la selección; cabezas, toneladas o kg según fuente | «Sin dato publicado»; no reconstruir total |
| Variación i.a.: ¿cómo cambió? | `100 × (x[t] / x[t−12] − 1)` | Período homólogo único; base > 0; mensual completo. En anual/acumulado, misma frecuencia y mes de cierre | «Sin base comparable» |
| Acumulado calculado: ¿cuánto va en el año y cómo cambió? | `Y[y,M]=Σ(m=1..M) x[y,m]`; i.a. `100 × (Y[y,M]/Y[y−1,M]−1)` | Sólo faena/producción mensual; 1..M completos en cada año; misma entidad/ámbito. Nunca sumar medias de peso | Si falta mes actual: se omite KPI. Si sólo falta base anterior: muestra nivel derivado y «Sin base interanual comparable» |
| Media móvil: ¿cómo está el nivel frente a su tendencia reciente? | `MM12[t]=Σ(k=0..11) x[t−k]/12`, incluye mes seleccionado | 12 meses consecutivos de una misma serie. Para peso sería media temporal simple de la misma categoría, sin ponderar ni mezclar categorías | No se dibuja referencia ni diferencia; nota explícita |
| Diferencia respecto de MM12: ¿cuánto se aparta? | Absoluta `x[t]−MM12[t]`, en unidad original; relativa `100 × (x[t]/MM12[t]−1)` si MM12 > 0 | Mismo período/serie que la media. No es significancia estadística ni diagnóstico causal | Se omite el hecho |
| Ranking provincial: ¿dónde se concentra? | Barras ordenadas por valor; posición `1 + número de valores estrictamente mayores` | Sólo tabla provincial de la publicación y período seleccionados. Se muestran seis inicialmente y se permite expandir | Si no hay partición reconciliada, conserva ranking absoluto sin participación |
| Participación provincial/categoría: ¿qué peso tiene dentro del total? | `100 × valor / total nacional publicado` | Numerador y denominador del mismo período, especie, familia, métrica, frecuencia, moneda, unidad, base de peso, origen y captura. Categoría sólo nacional; no existe cruce provincia×categoría | Se omite participación/KPI; no usar suma provincial como denominador |
| Top 3: ¿cuánto concentran los principales territorios? | `100 × Σ(valores de las tres provincias mayores) / total nacional publicado` | ≥3 provincias; partición completa reconciliada, sin duplicados geográficos. Empates de concentración se resuelven con orden alfabético estable; las posiciones conservan empates | Se omite KPI |
| Categoría principal: ¿en qué categoría se concentra? | Categoría/dentición con mayor participación publicada derivada del total nacional | Mismo universo/clasificación seleccionada; todos los componentes observados y suma reconciliada | Se omite el hecho |
| Composición y cambio: ¿cómo cambió la mezcla? | Barras agrupadas de participaciones; `Δpp = share[y,m] − share[y−1,m]` | Ambas particiones completas y reconciliadas; identidad de los componentes uno a uno; mismo mes del año anterior, especie y clasificación | Sólo composición actual si válida. Si no se reconcilia: valores absolutos publicados, sin shares ni pp |
| Comparación de peso: ¿cuánto publica cada categoría compatible? | Barras de kg publicados por categoría/dentición | Un período, una publicación, unidad/base y metodología. No son participaciones y nunca se suman ni promedian para fabricar peso total | Faltantes permanecen ausentes |
| Rango reciente: ¿dentro o fuera de sus niveles recientes? | `min/max{x[t−36],...,x[t−1]}` y comparación de `x[t]` con esos extremos | 36 meses consecutivos previos; excluye el seleccionado. Fechas y unidad visibles. Sin ajuste estacional: no es banda de confianza ni prueba de anomalía | Se indica ausencia de 36 meses comparables |
| Estacionalidad: ¿patrón mensual o diferencia respecto del patrón? | Media aritmética de cada mes sobre años completos anteriores; curva del año seleccionado. Tooltip muestra min/max del mes histórico | Últimos cinco años calendario previos, excluyendo seleccionado; al menos tres completos y homogéneos. No se interpolan meses ni se mezclan especies | Se omite gráfico; se informa cuántos años completos hay |
| Heatmap: ¿qué años/meses tuvieron niveles altos/bajos? | Valores originales; escala secuencial única entre min/max de celdas observadas | Mismos años completos elegibles y año seleccionado. Cero tiene color válido; sin dato tiene guion y tooltip explícito. No se atribuye valor al futuro/faltante | Sin tres años previos completos, se omite matriz |
| Cambios destacados: ¿qué hechos merecen atención? | Hasta cuatro hechos derivados: diferencia de MM12, territorio líder, categoría principal y mayor cambio absoluto de composición | Sólo resultados disponibles de las métricas anteriores. El cambio mayor conserva signo. Sin lenguaje causal ni scores | No se crea panel vacío |

Reconciliación: suma de componentes contra el total **publicado**, tolerancia
`max(0,000001; abs(total) × 10⁻¹⁰)` exclusivamente para aritmética de coma flotante.
No permite completar una partición con observaciones faltantes. El total de
faena mensual procede de `slaughter/category_age/Total general`, no del total
provincial sin valor cacheado. Las comparaciones por peso no usan este mecanismo
aditivo. Ningún KPI representa metas, umbrales de alarma o índice sintético.

## Aplicación a los datos disponibles

- **Faena DNCCA, septiembre 2026:** nivel **1.045.293** cabezas; i.a.
  **−11,0030297316%**. Acumulado mensual derivado enero–septiembre
  **9.176.312,75** frente a **10.197.221,75**: **−10,0116387093%**.
- MM12 del mismo total: **1.047.218,125** cabezas; diferencia **−1.925,125**.
  Top 3 provincial: **76,2186056924%**. Las 23 provincias y las 15 categorías
  reconciliadas suman separadamente **1.045.293**, sin sumar ambas tablas.
- Categoría principal: Novillito / 2 dientes, **33,8398420347%**.
  Mayor cambio de mezcla: Vaquillona / 2 dientes, **−3,8411869253 p.p.**
  respecto de septiembre 2025. Se comparan las 15 categorías, sin descartar
  las tres denticiones cuya única diferencia era capitalización.
- **Límite DNCCA histórico:** 2021–2023 incluyen bovinos y bubalinos;
  2024–2026 identifican bovinos. Para selección 2026 hay sólo dos años previos
  completos homogéneos (2024/25). No se presenta rango de 36 meses, estacionalidad
  ni heatmap a partir de ese cruce de coberturas.
- **SSPM faena mensual:** cinco años previos homogéneos (2021–2025) habilitan
  el historial. Agosto 2026 se compara con el rango anterior de 36 meses
  **926.614–1.282.667,25 cabezas**. No se mezcla con la vista DNCCA.
- **Producción DNCCA:** nueve meses de 2026 permiten acumulado derivado actual;
  no interanual comparable, MM12, rango ni estacionalidad. SSPM producción
  mantiene sus propias toneladas con base de peso no identificada y puede usar
  referencias dentro de su historia independiente.
- **Peso DNCCA:** nueve medias mensuales por categoría. Se mantiene el valor
  publicado y la comparación entre categorías; sin reconstrucción de media
  nacional, YTD, interanual, MM12 ni rango histórico inventado. El archivo histórico
  de indicadores sigue siendo otra publicación, con su estado finalizado.

Los valores en pantalla se formatean a dos decimales, sin redondear los cálculos
intermedios. Los períodos y las unidades originales se conservan en el detalle.

Fuentes locales revisadas: [índice de fragmentos](../data/carnes/dashboard/index.json),
[estado de actualización](../data/carnes/reports/CARNES_UPDATE_STATUS.json),
[guía de la plataforma](CARNES_DATA_PLATFORM.md) y los CSV.gz identificados por
ese índice. Los modelos derivados conservan las filas originales utilizadas,
incluida la observación del año anterior para cada cambio de composición, con
`source_url`, período, captura, localizador y hash. No se consultaron fuentes nuevas.

## Interacción, eliminaciones y carga

El ranking completo de 23 barras deja paso a seis barras con posición, valor y
participación; la expansión conserva todas las provincias. La tarjeta de categoría
principal se sustituye por concentración/participación contextual; el dato de
categoría principal pasa al panel factual. No se añade un gráfico separado para
la media móvil: se superpone a la evolución. Composición absoluta pasa a
participaciones y comparación sólo cuando sus denominadores son válidos.

La tabla continúa cerrada; se elimina la expansión acumulativa «Ver 10 más».
Ahora dispone de páginas de diez filas, búsqueda por período, ámbito, categoría,
fuente, valor y unidad, y CSV de toda la selección, independiente de búsqueda
y página. Datos técnicos permanecen en detalle lateral. Cerrar con Escape
devuelve foco al origen; ranking expandible conserva foco en su control.

Referencias históricas se cargan sólo al abrir su sección: hasta cinco años
anteriores y seleccionado, mismo grupo/familia/mensual, caché por hash existente.
No se consulta RAW ni una API. Cambiar selección limpia las referencias visibles;
una respuesta atrasada o una sección cerrada no publica resultados antiguos.
La apertura conserva **177.440 bytes / cuatro solicitudes de datos**. El recorrido
de aceptación que abre referencias DNCCA y luego SSPM acumula **398.667 bytes**;
ese total incluye las dos selecciones, no es el costo de una apertura inicial.

## Validación y evidencias

Evidencia fuera de Git: `C:/Users/acer/Oficina/carnes-ui-evidence/iteration3/`.

- `*-analytical-1440.png`: captura completa inicial a 1440 px.
- `*-references-1440.png`: SSPM con estacionalidad, rango y matriz abiertos.
- `*-references-{1000|900|640}.png`: verificación responsive, sin overflow de página.
- `*-analytics-report.json`: contraste independiente contra CSV con aritmética
  Python para YTD, base, MM12, Top 3, medias estacionales y rango de 36 meses;
  control de errores JS y prueba de respuesta histórica demorada tras cambiar
  de familia. Incluye teclado, faltante de la matriz y detalle trazable.
- `iteration3-independent.json` y `audit_iteration3.py`, en la carpeta superior:
  auditoría adicional de las 15 participaciones/cambios de composición.

Pruebas: suite frontend **110**; Carnes específicas **27**, incluidas **11** nuevas
analíticas; Python Carnes **29**. Browser UI y Browser Analytics en Edge y Chrome.
Comandos reproducibles:

```powershell
node --test tests/magyp_frontend/*.cjs
python -m unittest discover -s tests/carnes -v
python tests/carnes/browser_ui_checks.py --channel msedge --output RUTA
python tests/carnes/browser_ui_checks.py --channel chrome --output RUTA
python tests/carnes/browser_analytics_checks.py --channel msedge --output RUTA
python tests/carnes/browser_analytics_checks.py --channel chrome --output RUTA
git diff --check
```

La fixture comprimida `analytics-composition-september.json.gz` congela las
32 observaciones reales de las dos clasificaciones de septiembre. Otros tests
cubren meses ausentes, duplicados, cierres parciales, ceros, drift de dimensiones,
fuentes, unidades y especies, particiones incompletas y series de peso cortas.
Revisión independiente de sólo lectura: cálculos y reglas contrastados contra CSV;
corregidos filtro de dentición y texto de período. Sin hallazgos materiales
pendientes en los cálculos revisados.

Límites: no auditoría formal con lector de pantalla ni pruebas Safari/Firefox;
el rango no elimina estacionalidad y no declara anomalías estadísticas. No se
atribuyen causas a diferencias. La aprobación visual corresponde al usuario.

## Patrones transferibles, sujetos a la definición de cada módulo

| Módulo | Patrones útiles | Condición antes de trasladar |
|---|---|---|
| Cantidades | YTD al mismo cierre; ranking/concentración; estacionalidad y matriz | Misma unidad, especie/producto, origen/destino y frecuencia; cantidades aditivas; cobertura mensual completa |
| Mayoristas | Referencia temporal, comparación homóloga, rango y búsqueda paginada | Misma especie, variedad/calidad, unidad, moneda, mercado y metodología. No sumar precios ni convertir medias en volumen |
| Commodities | Panel factual, evolución con referencia de la misma serie, ranking cuando haya dimensión válida y detalle trazable | Separar SIO, internos, BCR, FOB/FAS, índices y referencias internacionales. Mantener moneda, unidad, plazo/entrega, mercado y condiciones; no promedio global ni YTD sumado de precios |

No se trasladan datos ni fórmulas automáticamente a otros módulos. La definición
económica de cada serie gobierna qué patrones son válidos.
