# Auditoría de unidades y precios mayoristas

Archivo auditado: `PRECIOS_MAYORISTAS_INTEGRADO.csv`. Filas: **108,331**. Años detectados: 2024, 2025, 2026.

## Resumen de comparabilidad

- Registros con precio observado válido (> 0): **108,275 (99.95%)**.
- Registros con precio por kg estimado válido: **108,271 (99.94%)**.
- Registros no comparables por kg: **4 (0.0%)**.
- Fechas válidas: **108,328**; rango: **2024-12-29** a **2026-12-25**.

`precio_observado` conserva el valor original. `precio_kg_estimado` sólo se calcula cuando la fuente permite identificar una unidad por kg o convertir una presentación con `kg_bulto` válido. No se borran ni imputan registros.

## Diagnóstico específico 2024

- ¿Existen registros 2024?: **Sí**, con **208 filas**.
- Archivos origen: MARTIN MICELLI 26-08-2026.xlsx.
- Mercados: Mercado de Corrientes.
- Meses cubiertos: 12.
- Especies únicas: **160**; variedades únicas: **0**.
- Precio observado válido: **154**; precio por kg estimado válido: **154**.
- Registros no comparables: **0**.
- Primer y último registro válido: **2024-12-29** a **2024-12-30**.

La cobertura 2024 debe interpretarse como parcial si sólo comprende los archivos, meses o especies detallados en `DIAGNOSTICO_PRECIOS_2024.csv`. No se completan meses faltantes ni se extrapolan precios. Si 2024 aparece únicamente en Martin Micelli, la columna `archivo_origen` lo deja identificado.

## Archivos generados

- `RESUMEN_UNIDADES_PRECIOS.csv`: distribución por unidad observada y conversión posible.
- `RESUMEN_ENVASES_PRECIOS.csv`: envases, kilos por bulto y porcentaje convertible.
- `RESUMEN_PRODUCTO_ENVASE_PRECIOS.csv`: detalle por especie, variedad, envase y kilos por bulto.
- `CASOS_NO_COMPARABLES_PRECIOS.csv`: observaciones que no pueden expresarse por kg con la información disponible.
- `CASOS_SOSPECHOSOS_PRECIO_KG.csv`: valores que requieren revisión.
- `DIAGNOSTICO_PRECIOS_2024.csv`: cobertura detallada de 2024 por fuente, mercado y producto.

La base de precios permanece separada de las cantidades. Esta auditoría no calcula relaciones precio-cantidad, causalidad ni escasez.
