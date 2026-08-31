# Auditoría de precios mayoristas 2026

## 1. Resumen ejecutivo

Se auditaron **61,744 filas** provenientes de **345 archivos de origen** en `PRECIOS_MAYORISTAS_2026_INTEGRADO.csv`. La base representa precios mayoristas diarios; no se interpretó como base de cantidades ni se cruzó con las cantidades 2024/2025.

La cobertura temporal válida va de **2026-01-02** a **2026-08-24**, con **283 series de calidad Alta** y **62 series de calidad Media** bajo la regla inicial solicitada.

Conclusión preliminar: la base puede servir para un módulo operativo de evolución de precios, pero conviene comenzar con las series de calidad Alta y mantener mercado, especie, variedad y unidad como filtros explícitos.

## 2. Bases y cobertura general

- Filas totales: 61,744
- Archivos de origen informados: 345
- Meses disponibles: 2026-01, 2026-02, 2026-03, 2026-04, 2026-05, 2026-06, 2026-07, 2026-08
- Rubros: Frutas, Hortalizas
- Especies únicas normalizadas: 102
- Variedades únicas normalizadas: 219
- Mercados informados: 0
- Fechas válidas: 100.0%
- Precios válidos (> 0): 100.0%
- Mercado informado: 0.0%
- Especie informada: 100.0%
- Variedad informada: 80.5%
- Unidades: $/Kg (61,744)

## 3. Cobertura temporal

La tabla detallada por año, mes y rubro se encuentra en `RESUMEN_COBERTURA_PRECIOS_2026.csv`.

## 4. Cobertura por mercado

La tabla completa se encuentra en `RESUMEN_MERCADOS_PRECIOS_2026.csv`. Los mercados con mejor combinación de fechas y precios válidos son:

| Mercado | Fechas | Rango | Especies | Precio promedio | Precios válidos |
|---|---:|---|---:|---:|---:|
| (sin informar) | 155 | 2026-01-02 a 2026-08-24 | 102 | 3.257,73 | 100.0% |

## 5. Cobertura por especie

La tabla completa se encuentra en `RESUMEN_ESPECIES_PRECIOS_2026.csv`. Para priorizar una evolución temporal, la cobertura de fechas y meses es más informativa que el volumen bruto de filas.

## 6. Series utilizables para evolución de precios

La tabla completa se encuentra en `RESUMEN_SERIES_UTILIZABLES_PRECIOS_2026.csv`.

Series de calidad Alta con más fechas disponibles:

| Rubro | Mercado | Especie | Variedad | Unidad | Observaciones | Fechas | Meses | CV |
|---|---|---|---|---|---:|---:|---:|---:|
| Frutas | (sin informar) | MANZANA | Red Delici | $/Kg | 1908 | 155 | 8 | 0,308 |
| Hortalizas | (sin informar) | TOMATE | Redondo | $/Kg | 1641 | 155 | 8 | 0,602 |
| Hortalizas | (sin informar) | PIMIENTO | Morron | $/Kg | 1626 | 155 | 8 | 0,525 |
| Hortalizas | (sin informar) | TOMATE | Perita | $/Kg | 1440 | 155 | 8 | 0,531 |
| Frutas | (sin informar) | PALTA | Hass | $/Kg | 1258 | 155 | 8 | 0,410 |
| Frutas | (sin informar) | MANZANA | Granny Smi | $/Kg | 1136 | 155 | 8 | 0,300 |
| Hortalizas | (sin informar) | AJO | Mdo. Chino | $/Kg | 936 | 155 | 8 | 0,502 |
| Frutas | (sin informar) | LIMON | Eureka | $/Kg | 880 | 155 | 8 | 0,561 |
| Frutas | (sin informar) | KIWI | (sin informar) | $/Kg | 879 | 155 | 8 | 0,334 |
| Hortalizas | (sin informar) | ZANAHORIA | Chantenay | $/Kg | 683 | 155 | 8 | 0,181 |

## 7. Problemas de calidad detectados

- Precios faltantes o no numéricos: **0** filas.
- Precios cero: **0** filas.
- Precios negativos: **0** filas.
- Fechas inválidas o faltantes: **0** filas.
- Mercados sin informar: **61,744** filas.
- Especies sin informar: **0** filas.
- Filas con mercado informado pero fecha inválida: **0**.
- Unidades distintas detectadas: **1**. Revisar especialmente antes de comparar precios.
- Filas marcadas como outliers por especie con Q1 -/+ 3*IQR: **1,125**. No fueron eliminadas.
- Colisiones de escritura en variedades normalizadas: **1** grupos revisables.

Los outliers se evaluaron dentro de cada especie; un precio fuera del rango no implica por sí mismo un error. Puede representar una variedad, presentación o unidad diferente.

## 8. Recomendación para incorporación al dashboard

- **Mercados:** auditar todos los mercados, pero iniciar el módulo visual con los mercados que tengan mayor cobertura de fechas y más de 80% de precios válidos.
- **Especies:** priorizar las 283 series de calidad Alta; dejar las series Media como segunda etapa y no usar las Bajas para conclusiones de evolución.
- **Rubros:** seleccionar el rubro según cobertura temporal observada en la tabla mensual; no asumir que frutas y hortalizas tienen la misma calidad.
- **Nivel de detalle:** mostrar especie + variedad cuando la variedad tenga cobertura suficiente; si no, comenzar por especie y habilitar variedad solo para series estables.
- **Filtros necesarios:** año, mercado, rubro, especie normalizada, variedad, unidad y rango de fechas.
- **Datos que no deberían usarse todavía:** filas sin fecha, precios no válidos, unidades no comparables y series Bajas.
- **Uso recomendado:** monitoreo operativo de precios mayoristas, sin inferir producción, escasez, causalidad ni relaciones precio-cantidad.

## 9. Limitaciones conceptuales

- La base de precios 2026 no debe interpretarse como base de cantidades.
- No permite estimar relaciones precio-cantidad por sí sola.
- No debe cruzarse directamente con cantidades 2024/2025 para inferir causalidad.
- Sirve para monitoreo operativo de precios mayoristas.
- La evolución de precios debe analizarse por mercado, especie, variedad y unidad cuando la cobertura lo permita.

### Notas metodológicas

Se usó `precio` como medida principal y `precio_promedio` como respaldo cuando `precio` estaba vacío. Se conservaron todas las filas y no se eliminaron outliers. Las especies y variedades se normalizaron únicamente para agrupar variantes de escritura en los resúmenes; no se modificó el CSV de entrada.

Principales especies con observaciones outlier:

- CIRUELA: 117 observaciones
- ANANA: 82 observaciones
- PELON: 80 observaciones
- DURAZNO: 72 observaciones
- NARANJA: 61 observaciones
- MANDARINA: 56 observaciones
- APIO: 56 observaciones
- PEREJIL: 52 observaciones
- NUEZ: 52 observaciones
- PERA: 51 observaciones
- JENGIBRE: 51 observaciones
- RADICCHIO: 50 observaciones
- OREGANO: 48 observaciones
- MANI: 44 observaciones
- CURCUMA: 32 observaciones
