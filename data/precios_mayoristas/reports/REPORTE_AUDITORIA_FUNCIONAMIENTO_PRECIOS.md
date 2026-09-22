# Auditoría de funcionamiento del módulo Precios Mayoristas

## Objetivo

Auditar integralmente el módulo **Precios Mayoristas** después de la incorporación de las bases mensuales del Mercado Central de Buenos Aires (MCBA) 2024-2025, verificando cobertura, fechas, frecuencia, precios, duplicados, filtros, visualizaciones, publicación en GitHub Pages y ausencia de regresiones en los demás módulos.

La auditoría se realizó el 22/09/2026 sobre la rama `codex/auditar-actualizacion-precios-dashboard`, creada desde `main` actualizado en el commit `59ab62a`. No se modificaron bases, scripts ni archivos funcionales.

## Archivos revisados

- `PRECIOS_MAYORISTAS_INTEGRADO.csv`: archivo principal consumido por `app.js`.
- `PRECIOS_MAYORISTAS_2026_INTEGRADO.csv`: fallback ante error de carga del principal. Ambos son el mismo blob Git y contienen la misma información.
- `app.js`, `index.html` y `.github/workflows/deploy.yml`.
- `integrar_precios_mcba_2024_2025.py` y `auditar_precios_ba_2024_2025.py`.
- Reportes existentes en `data/precios_mayoristas/reports/`.
- Archivos de dashboard SIO y del histórico local mensual, únicamente para control de no regresión.

`app.js` carga primero `PRECIOS_MAYORISTAS_INTEGRADO.csv` y sólo usa `PRECIOS_MAYORISTAS_2026_INTEGRADO.csv` si falla la carga. El integrado tiene 117.039 filas y 36 columnas. El navegador acepta 116.868 filas: excluye 56 precios inválidos o cero y 115 registros con fecha posterior al día de auditoría.

Columnas disponibles: `fecha`, `año`, `mes`, `rubro`, `especie`, `variedad`, `mercado`, `procedencia`, `localidad_corrientes`, `envase`, `kg_bulto`, `total_kilos`, `unidad`, `precio_observado`, `unidad_precio_observado`, `precio_kg_estimado`, `metodo_conversion_precio`, `confianza_conversion_precio`, `precio`, `precio_min`, `precio_max`, `precio_promedio`, `archivo_origen`, `especie_normalizada`, `fuente`, `mercado_fuente`, `provincia_mercado`, `pais`, `origen`, `procedencia_informada`, `moneda`, `hoja_origen`, `fecha_precision`, `periodo`, `precio_cero_flag` y `observaciones`.

## Cobertura del integrado

- Años: 2024, 2025 y 2026.
- Mercados: Mercado Central de Buenos Aires y Mercado de Corrientes.
- Rubros: Frutas, Hortalizas, Subproductos y 2 filas sin rubro.
- Fecha mínima y máxima informada: 01/01/2024 a 25/12/2026. La fecha máxima corresponde a 115 filas futuras respecto del 22/09/2026; el dashboard las excluye.
- Frecuencia declarada: 8.708 filas MCBA 2024-2025 con `fecha_precision=mensual`. Las 108.331 filas históricas restantes no tienen precisión explícita.
- Fuentes integradas nuevas: `PHOR24_K.xlsx` (2.211), `PFRU24_K.xlsx` (1.956), `PHOR25_K.xlsx` (2.451) y `PFRU25_K.xlsx` (2.090).

### A. Año × mercado/fuente

| Año | Mercado/Fuente | Filas |
|---:|---|---:|
| 2024 | Mercado Central de Buenos Aires | 4.167 |
| 2024 | Mercado de Corrientes | 208 |
| 2025 | Mercado Central de Buenos Aires | 4.541 |
| 2025 | Mercado de Corrientes | 29.608 |
| 2026 | Mercado Central de Buenos Aires | 61.744 |
| 2026 | Mercado de Corrientes | 16.771 |

## Cobertura por año, mercado y rubro

La tabla combina los controles B (filas) y D (cantidad de especies normalizadas distintas). Para las 108.331 filas históricas sin `especie_normalizada`, se usa `especie` como equivalente operativo, igual que la normalización del dashboard.

| Año | Mercado/Fuente | Rubro | Filas | Especies distintas |
|---:|---|---|---:|---:|
| 2024 | MCBA | Frutas | 1.956 | 41 |
| 2024 | MCBA | Hortalizas | 2.211 | 63 |
| 2024 | Corrientes | Frutas | 68 | 53 |
| 2024 | Corrientes | Hortalizas | 87 | 56 |
| 2024 | Corrientes | Subproductos | 53 | 51 |
| 2025 | MCBA | Frutas | 2.090 | 45 |
| 2025 | MCBA | Hortalizas | 2.451 | 60 |
| 2025 | Corrientes | Frutas | 3.836 | 66 |
| 2025 | Corrientes | Hortalizas | 25.614 | 62 |
| 2025 | Corrientes | Subproductos | 157 | 8 |
| 2025 | Corrientes | Sin rubro | 1 | 1 |
| 2026 | MCBA | Frutas | 26.746 | 43 |
| 2026 | MCBA | Hortalizas | 34.998 | 59 |
| 2026 | Corrientes | Frutas | 2.521 | 60 |
| 2026 | Corrientes | Hortalizas | 14.182 | 59 |
| 2026 | Corrientes | Subproductos | 67 | 7 |
| 2026 | Corrientes | Sin rubro | 1 | 1 |

### C. Año × mercado/fuente × rubro × mes

| Año | Mercado | Rubro | Ene | Feb | Mar | Abr | May | Jun | Jul | Ago | Sep | Oct | Nov | Dic | Sin mes |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2024 | MCBA | Frutas | 191 | 218 | 213 | 141 | 139 | 133 | 137 | 126 | 129 | 178 | 169 | 182 | 0 |
| 2024 | MCBA | Hortalizas | 166 | 151 | 161 | 159 | 192 | 177 | 211 | 205 | 208 | 232 | 195 | 154 | 0 |
| 2024 | Corrientes | Frutas | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 68 | 0 |
| 2024 | Corrientes | Hortalizas | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 87 | 0 |
| 2024 | Corrientes | Subproductos | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 53 | 0 |
| 2025 | MCBA | Frutas | 208 | 206 | 239 | 175 | 165 | 148 | 142 | 136 | 139 | 149 | 193 | 190 | 0 |
| 2025 | MCBA | Hortalizas | 150 | 183 | 182 | 213 | 238 | 227 | 209 | 217 | 214 | 223 | 218 | 177 | 0 |
| 2025 | Corrientes | Frutas | 290 | 372 | 345 | 384 | 446 | 497 | 320 | 172 | 238 | 223 | 307 | 242 | 0 |
| 2025 | Corrientes | Hortalizas | 429 | 935 | 2.148 | 2.494 | 3.046 | 3.106 | 2.892 | 2.303 | 2.185 | 2.314 | 1.879 | 1.883 | 0 |
| 2025 | Corrientes | Subproductos | 9 | 4 | 17 | 28 | 26 | 19 | 10 | 15 | 9 | 9 | 7 | 4 | 0 |
| 2025 | Corrientes | Sin rubro | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026 | MCBA | Frutas | 3.497 | 2.909 | 3.390 | 2.970 | 2.682 | 3.100 | 2.895 | 5.303 | 0 | 0 | 0 | 0 | 0 |
| 2026 | MCBA | Hortalizas | 4.109 | 3.442 | 4.002 | 4.155 | 4.452 | 6.138 | 4.977 | 3.723 | 0 | 0 | 0 | 0 | 0 |
| 2026 | Corrientes | Frutas | 271 | 239 | 364 | 205 | 347 | 334 | 431 | 321 | 0 | 0 | 0 | 9 | 0 |
| 2026 | Corrientes | Hortalizas | 1.511 | 1.469 | 2.036 | 1.504 | 1.540 | 1.897 | 2.336 | 1.781 | 0 | 0 | 0 | 105 | 3 |
| 2026 | Corrientes | Subproductos | 0 | 3 | 11 | 10 | 10 | 6 | 14 | 12 | 0 | 0 | 0 | 1 | 0 |
| 2026 | Corrientes | Sin rubro | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |

Los registros Corrientes de diciembre de 2026 son futuros al corte y no aparecen en el dashboard. MCBA 2026 termina el 24/08/2026; no debe interpretarse como año cerrado.

### E y F. Año × frecuencia y año × mercado/fuente × frecuencia

| Año | Mercado/Fuente | Precisión/frecuencia original | Filas |
|---:|---|---|---:|
| 2024 | MCBA | mensual | 4.167 |
| 2024 | Corrientes | no declarada | 208 |
| 2025 | MCBA | mensual | 4.541 |
| 2025 | Corrientes | no declarada | 29.608 |
| 2026 | MCBA | no declarada | 61.744 |
| 2026 | Corrientes | no declarada | 16.771 |

## Validación MCBA 2024-2025

Los cuatro conjuntos esperados están presentes y completos según los conteos de aceptación del integrador. Los 24 períodos mensuales usan `fecha=YYYY-MM-01`, `fecha_precision=mensual` y `periodo=YYYY-MM`; no hay inconsistencias entre fecha, año, mes y período. No se detectaron duplicados exactos en estas 8.708 filas.

El año se infiere del nombre de archivo/hoja y la integración asume que las columnas `K_ENER` a `K_DICI` son precios en ARS por kg. Esta decisión está documentada, pero no surge de un campo monetario/temporal explícito de los libros fuente.

## Validación MCBA 2026

Se conservaron 61.744 filas, 26.746 de Frutas y 34.998 de Hortalizas, con cobertura del 02/01/2026 al 24/08/2026. Mantienen su granularidad histórica original y no fueron reescritas por la integración 2024-2025. `fecha_precision` permanece vacía, por lo que la base permite detalle diario en el dashboard cuando se elige una especie específica.

## Validación Mercado de Corrientes

Se conservaron 46.587 filas: 208 en 2024, 29.608 en 2025 y 16.771 en 2026. La fuente usa precios por bulto y conversión estimada por kg con confianza Media. Hay 3 fechas vacías, 4 registros no comparables por ausencia de `kg_bulto`, 54 precios cero y 2 precios faltantes. No se modificaron estos registros.

## Validación de frecuencia y fechas

- La vista diaria de `app.js` excluye explícitamente las filas con `fecha_precision=mensual`.
- La frecuencia diaria queda deshabilitada cuando el filtro sólo contiene MCBA 2024-2025, incluso al seleccionar una especie.
- La vista mensual incluye correctamente los cuatro conjuntos MCBA 2024-2025.
- Una serie diaria real de Corrientes 2026 (Tomate Perita) habilitó la frecuencia diaria y mostró 688 observaciones hasta el 25/08/2026.
- La precisión vacía de las 108.331 filas históricas significa “no declarada”, no una certificación metodológica de frecuencia diaria. El dashboard infiere su disponibilidad temporal por las fechas observadas.
- El navegador excluye 115 filas con fecha futura respecto del 22/09/2026.

## Validación de precios

- `precio_observado`/`precio`: 2 vacíos, 54 ceros, 0 negativos y 0 valores no numéricos.
- Precio efectivo positivo: 116.983 filas; percentil 1 = 333,33; mediana = 3.000; percentil 99 = 44.000; máximo = 400.000.
- Se detectaron 14 valores superiores a 100.000. Casos Corrientes a revisar: Banana Ecuatoriana 400.000 (06/04/2026), Pepino 300.000 (20/07/2026), Pepino 220.000 (23/06/2025) y Repollo Blanco 220.000 (11/06/2025). No se concluye que sean errores ni se eliminaron.
- MCBA usa `$/kg`; Corrientes usa `$/bulto` y el dashboard compara mercados sólo mediante `precio_kg_estimado` cuando la conversión tiene confianza Alta o Media.
- `kg_bulto`: 4 vacíos, 14.880 ceros y 0 negativos. Los ceros están en MCBA y no se usan como divisor para las filas ya expresadas en $/kg.
- `moneda=ARS` está poblada en las 8.708 filas MCBA nuevas; permanece vacía en las 108.331 históricas. Es una limitación de trazabilidad, aunque la unidad contiene el símbolo `$`.

Resumen por mercado/unidad: MCBA tiene 70.452 filas en `$/kg`; Corrientes tiene 46.587 filas en `$/bulto`. Las unidades, envases, pesos de bulto y métodos de conversión no fueron alterados.

## Duplicados y posibles inconsistencias

- Duplicados exactos en las 36 columnas: 2.873 grupos, 6.511 filas afectadas y 3.638 excedentes (3,11% del total). Se concentran en Corrientes 2025 (2.298 excedentes), Corrientes 2026 (1.239), MCBA 2026 (98) y Corrientes 2024 (3). No hay duplicados exactos en MCBA mensual 2024-2025.
- Clave aproximada `fecha + mercado + rubro + especie_normalizada/especie + variedad + unidad + envase + precio + procedencia/origen`: 11.651 grupos, 34.822 filas afectadas y 23.171 excedentes. Parte de estas repeticiones puede ser metodológicamente aceptable porque la clave no incorpora todos los atributos de la observación.
- Los duplicados exactos no tienen ningún campo que permita distinguir observaciones y pueden sesgar promedios simples. Se clasifican como anomalía de datos de severidad alta y requieren revisión de fuente antes de cualquier deduplicación.
- Los reportes legacy `REPORTE_AUDITORIA_PRECIOS.md`, `REPORTE_AUDITORIA_PRECIOS_2026.md` y `REPORTE_AUDITORIA_PRECIOS_BA_2024_2025.md` quedaron obsoletos: todavía informan 108.331 filas y ausencia de MCBA 2024-2025. El reporte de integración más reciente sí informa correctamente 117.039 filas. No se sobrescribieron para conservar trazabilidad histórica.

## Pruebas funcionales en dashboard local

Se ejecutó `python -m http.server 8000` y se automatizó Chromium sobre `http://localhost:8000`.

| Caso | Filas visibles | KPI promedio | Último dato | Resultado |
|---|---:|---:|---|---|
| 2024 · MCBA · Frutas · Mensual | 1.956 | $ 2.087,7/kg | 01/12/2024 | OK |
| 2024 · MCBA · Hortalizas · Mensual | 2.211 | $ 1.714/kg | 01/12/2024 | OK |
| 2025 · MCBA · Frutas · Mensual | 2.090 | $ 2.949,7/kg | 01/12/2025 | OK |
| 2025 · MCBA · Hortalizas · Mensual | 2.451 | $ 1.987,8/kg | 01/12/2025 | OK |
| 2026 · MCBA · Mensual | 61.744 | $ 3.257,7/kg | 24/08/2026 | OK |
| Mercado de Corrientes · Mensual | 46.412 válidas para KPI | $ 1.638,9/kg estimado | 25/08/2026 | OK |

En los seis casos se visualizaron KPIs, evolución temporal, rankings y 20 filas de semáforo cuando correspondía. No hubo errores críticos de página; la consola sólo mostró advertencias esperadas por precios inválidos/cero, fechas futuras y variaciones extremas excluidas.

Los filtros de año, mes, rubro, especie, variedad, mercado, procedencia, unidad, comparabilidad y frecuencia están conectados a columnas disponibles. Los años 2024, 2025 y 2026, ambos mercados y ambos rubros principales aparecen. Variedad se actualiza en función de especie; los demás catálogos no son filtros encadenados y se validan al aplicar la selección.

Observación metodológica: el semáforo agrupa por número de mes sin incluir el año. Con “Todos los años” mezcla enero de 2024, 2025 y 2026 en una sola celda y la variación Ene→Dic deja de ser estrictamente cronológica. No se corrigió porque cambia la metodología de presentación; debe usarse con un año seleccionado hasta resolverlo.

## Comparación con GitHub Pages

- URL verificada: `https://deaeconomiactes.github.io/Serie-Agricola/`.
- Último deploy de Pages visible: ejecución #26, estado exitoso, 18/09/2026 19:39, commit `8a29463`, duración 18 segundos.
- `main` avanzó después hasta `59ab62a` por actualizaciones SIO, pero `app.js`, `index.html`, estilos y ambos CSV de precios no cambiaron entre esos commits.
- Pages cargó 117.039 filas crudas/116.868 válidas y ofreció años 2024-2026, MCBA y Corrientes.
- Los seis casos funcionales devolvieron los mismos conteos, KPIs y fechas que localhost.
- El archivo publicado usa finales de línea LF y el checkout Windows usa CRLF; la diferencia binaria es exactamente un byte por cada una de las 117.040 líneas. No representa una diferencia de datos.

Conclusión de publicación: GitHub Pages consume la misma versión lógica de los archivos de Precios Mayoristas que `main`. El workflow publica todo el repositorio y desencripta únicamente el CSV de cantidades. No se modificaron URLs ni configuración.

## No regresión en otros módulos

### Cantidades transadas

- El módulo cargó sin estado de error.
- Se visualizaron 6 KPIs con valores y 7 gráficos.
- Los filtros principales y la tabla de estacionalidad permanecen operativos.

### Commodities agrícolas

- SIO cargó con fuente, moneda ARS, unidad TN, tipo Precio Hecho, tabla de últimos precios y semáforo.
- El histórico local mensual cargó de forma separada con período Ago 2026, 5 series y 343 observaciones.
- Al cambiar de fuente se actualizan subtítulo, filtros y KPIs; no se mezclan SIO e histórico local.
- No se modificaron archivos de Commodities, SIO ni Cantidades.

## Conclusión

La integración MCBA 2024-2025 funciona correctamente en los filtros, KPIs y visualizaciones mensuales tanto en localhost como en GitHub Pages. MCBA 2026 y Mercado de Corrientes siguen disponibles y no se detectó regresión en Cantidades ni Commodities. Las anclas `YYYY-MM-01` de MCBA 2024-2025 están marcadas como mensuales y no contaminan la vista diaria.

Quedan observaciones que requieren tratamiento posterior, sin corrección automática en esta auditoría:

1. Revisar 3.638 filas excedentes por duplicación exacta antes de deduplicar.
2. Evitar el semáforo con “Todos los años” o redefinir su clave para separar año y mes.
3. Completar gradualmente `fecha_precision`, `moneda` y trazabilidad de las 108.331 filas históricas.
4. Revisar valores extremos, precios cero/faltantes, fechas vacías/futuras y reportes legacy obsoletos.

**Estado general: OK con observaciones.**
