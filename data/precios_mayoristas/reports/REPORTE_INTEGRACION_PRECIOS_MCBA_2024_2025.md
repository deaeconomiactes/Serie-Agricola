# Integración de precios MCBA 2024-2025

## Archivos integrados

| archivo | rubro | año | filas fuente | filas útiles | filas integradas | filas excluidas | motivo de exclusión principal | período mínimo | período máximo |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| PHOR24_K.xlsx | Hortalizas | 2024 | 587 | 524 | 2.211 | 63 | resumen C=0 (63) | 2024-01 | 2024-12 |
| PFRU24_K.xlsx | Frutas | 2024 | 748 | 707 | 1.956 | 41 | resumen C=0 (41) | 2024-01 | 2024-12 |
| PHOR25_K.xlsx | Hortalizas | 2025 | 580 | 520 | 2.451 | 60 | resumen C=0 (60) | 2025-01 | 2025-12 |
| PFRU25_K.xlsx | Frutas | 2025 | 788 | 743 | 2.090 | 45 | resumen C=0 (45) | 2025-01 | 2025-12 |

## Integrado actualizado

- Filas antes (base sin las cuatro fuentes administradas): 108.331.
- Filas nuevas normalizadas: 8.708.
- Filas después: 117.039.
- Cobertura por año:
  - 2024: 4.375
  - 2025: 34.149
  - 2026: 78.515
- Cobertura por mercado:
  - Mercado Central de Buenos Aires: 70.452
  - Mercado de Corrientes: 46.587
- Cobertura por rubro:
  - (sin informar): 2
  - Frutas: 37.217
  - Hortalizas: 79.543
  - Subproductos: 277
- Cobertura MCBA 2024: 4.167 filas.
- Cobertura MCBA 2025: 4.541 filas.
- Cobertura MCBA 2026: 61.744 filas.

## Duplicados

- Coincidencias contra la base previa con la clave aproximada solicitada: 0.
- Duplicados potenciales dentro de las fuentes con la clave aproximada: 28.
- Duplicados exactos omitidos: 0.
- Los potenciales se conservaron porque difieren en procedencia y/o CAL/TAM/GRADO; eliminarlos con la clave corta perdería observaciones legítimas.
- En una reejecución se reemplazan sólo las filas de los cuatro `archivo_origen`; no se acumulan copias.

## Metodología

- Mercado y fuente: `Mercado Central de Buenos Aires`. Provincia del mercado: Buenos Aires. País: Argentina.
- Período: el año se toma del archivo/hoja y el mes de `K_ENER` a `K_DICI`. `fecha` usa el primer día del mes, `fecha_precision=mensual` y `periodo=YYYY-MM`. La fecha es un ancla técnica mensual, no una observación diaria.
- Precio: las columnas `K_mes` se interpretan como precio informado por kg. Se conserva `KG` como peso del bulto, pero el precio no se divide nuevamente por ese valor.
- Moneda: ARS, interpretada por tratarse de listas locales MCBA; la fuente no contiene un campo monetario explícito.
- Unidad: `$/kg`, siguiendo la convención del integrado y de MCBA 2026.
- Procedencia: se conserva `PROC` cuando existe. No se confunde con el mercado ni se imputa cuando está vacía.
- Exclusiones: filas vacías, resúmenes `C=0`, filas sin especie y celdas mensuales sin precio numérico positivo.
- Trazabilidad: se preservan archivo, hoja, período, precisión temporal y atributos CAL/TAM/GRADO en observaciones.
- Dashboard: las observaciones con `fecha_precision=mensual` se excluyen de la frecuencia diaria; la fecha ancla no se presenta como cotización diaria.

## Conclusión

Las cuatro bases quedaron incorporadas como series mensuales MCBA 2024-2025. El proceso conserva MCBA 2026 y Mercado de Corrientes, y es idempotente por reemplazo controlado según `archivo_origen`.
