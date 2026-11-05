# Exploración descriptiva de precios mayoristas

La vista mensual requiere un producto y una procedencia. Agrupa por mercado y mes exclusivamente registros con moneda ARS identificada, precio positivo por kilogramo, conversión validada y confianza alta o media. Se conservan los filtros de presentación cuando se aplican. No se mezclan mercados, productos ni procedencias.

- **Registros diarios**, incluidos los de Corrientes: mediana de precios de cada fecha; después, mediana de esas medianas diarias del mes. Cada día observado tiene el mismo peso, independientemente de su cantidad de registros.
- **Registros mensuales**, incluidos los agregados derivados de Mercado Central y registros históricos: mediana de los valores mensuales por serie publicados en ese mes. Cada fila mensual cuenta una vez; no se presupone la cantidad de operaciones ni se reconstruyen observaciones diarias. El resultado resume registros, no el conjunto de operaciones ni días subyacentes.
- Un mercado/mes con más de una fuente o granularidad se excluye de la serie exploratoria. La cobertura indica registros y, cuando corresponde, días observados; el tooltip conserva fuente, granularidad, método y confianza de conversión.
- La diferencia es `(Corrientes / Buenos Aires - 1) × 100`, exclusivamente en el último mes común con ARS/kg válido. Las variaciones se calculan entre meses calendario consecutivos y no rellenan huecos. La composición puede cambiar por mes y entre mercados. Son descripciones sin ponderadores de volumen, no cotizaciones oficiales homogéneas ni índices.

La comparación estricta, los filtros comerciales, fuentes, frescura y series individuales continúan en Análisis avanzado. Las frecuencias diaria y anual siguen disponibles allí; la vista descriptiva principal actualmente requiere mensual. Las opciones con moneda o unidad no verificadas permanecen consultables en detalle avanzado y no se incluyen en estas medianas.
