# Política de fuentes de datos

Política confirmada por el usuario el 20/10/2026. Aplica al sistema; esta etapa
implementa únicamente verificaciones MCBA. No autoriza migraciones de otros módulos.

## Cobertura y prioridad

Maximizar la cobertura histórica reproducible, sin restringirla artificialmente
a los últimos años. Descubrir archivos por índices, catálogos y enlaces oficiales.
No enumerar URLs inventadas, evadir bloqueos ni generar tráfico agresivo.

Priorizar fuentes oficiales, robustas, trazables y automatizables. Cuando una
fuente oficial sustituye suficientemente una carga manual, pasa a producción y
la carga manual deja de participar en cálculos, filtros y gráficos del ámbito
reemplazado. No mantener datasets estáticos activos por costumbre.

Para MCBA: Mercado Central oficial tiene prioridad donde frecuencia y metodología
son compatibles; MAGyP cubre su circuito y frecuencia documentados; los archivos
manuales sólo cubren huecos reales. Autoridad institucional no implica igualdad
entre un modal, un promedio publicado, un precio acordado y una media derivada.

## Condiciones de cutover

Antes de reemplazar un período, rubro o serie, exigir y registrar:

1. Cobertura suficiente: períodos, días observados y dimensiones comparados con
   la fuente anterior. Un único archivo o mes no demuestra cobertura histórica.
2. Semántica compatible: concepto del precio, frecuencia, población y método.
   La agregación de modales diarios se identifica siempre como mensual derivada.
3. Moneda y unidad entendidas, con evidencia de cualquier mapeo. USD/kg no
   reemplaza ARS/kg ni se convierte sin una metodología autorizada y explícita.
4. Calidad: schema, fechas, precios, duplicados, faltantes, archivos parciales,
   revisiones y exclusiones documentadas. No inventar observaciones.
5. Comparación de solapamiento a grano comparable, identificando ambigüedades.
   La ausencia de solapamiento se informa como tal, no como igualdad validada.
6. Tests, trazabilidad y regresiones aprobados; publicación atómica con última
   salida válida preservada ante fallos.

La exclusión se aplica antes de filtros de productos y de cálculos. Una selección
vacía dentro de un período cubierto no habilita rellenarlo silenciosamente desde
otra metodología. Si no se cumplen las condiciones, se conserva la fuente previa
para el hueco y se explica el bloqueo real.

## Retiro de fuentes manuales

Retirar MCBA manual del runtime sólo después de confirmar que todo el rango y las
frecuencias todavía necesarias tienen sustituto suficiente, con evidencia por
año. El retiro comprende cargas, outputs/bundles y ramas técnicas exclusivas.
No retirar un archivo compartido si contiene otras fuentes que siguen vigentes.

No borrar originales manuales antes del cutover final confirmado. Una vez
confirmado, conservar sólo documentación y evidencia de auditoría necesarias;
los originales que deban retenerse quedan archivados fuera del runtime.

## Trazabilidad y comunicación

RAW inmutable, SHA-256, URL, captura UTC, archivo/miembro/fila y versión de parser.
NORMALIZED conserva valores originales y campos normalizados. ANALYTICAL declara
cada regla. DASHBOARD utiliza sólo salidas validadas y metadata real de frescura.
No guardar cookies, tokens, perfiles ni sesiones. No versionar RAW pesado.

Mantener fuentes y metodologías identificables; nunca mezclarlas silenciosamente,
interpolar días sin publicación o promediar monedas/unidades incompatibles.
Una serie gráfica sólo es homogénea si también lo son su grano y metodología.

La UI muestra fuente institucional, cobertura, último período y estado. No ofrece
al usuario opciones técnicas como legacy, fallback o pipeline. La metodología y
las diferencias entre publicaciones siguen disponibles en la documentación.
