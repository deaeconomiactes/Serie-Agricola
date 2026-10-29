# Auditoría de comparación mayorista: tomate 2026

**Instantánea anterior a la normalización productiva.** El texto describe el comportamiento previo. La matriz regenerada usa el índice activo y muestra las dimensiones actuales; para el estado posterior consultar `NORMALIZACION_PRODUCTIVA.md`.

Revisión de los fragmentos mensuales activos del índice `data/mayoristas/dashboard/index.json`, con corte operativo 29/10/2026. La matriz `TOMATE_2026_MATRIZ.csv` contiene todas las 1.665 filas con tomate, incluidos todos los orígenes y las fechas futuras. Se genera con `python scripts/mayoristas/auditar_tomate_2026.py`. Una fila mensual MCBA puede resumir varias observaciones diarias; no debe sumarse con las filas diarias Corrientes como si tuvieran la misma frecuencia.

## Origen Corrientes

| Mercado | Filas publicadas | Fecha / meses | Producto y variedad en la interfaz actual | Unidad |
|---|---:|---|---|---|
| Central de Buenos Aires | 55 mensuales | marzo–octubre | Tomate: 27 Redondo, 19 Cherry, 5 Perita, 4 Larga Vida | ARS/kg directo |
| Corrientes | 970 diarias | enero–agosto y tres filas en diciembre | 474 Tomate Perita, 339 Tomate Redondo, 157 Tomate Cherry; variedad vacía | $/bulto, moneda no identificada en el integrado; estimación por kg de confianza media |

Las tres filas de diciembre se excluyen de la vista al corte indicado: 967 filas de Corrientes son anteriores o iguales al corte. Los meses comunes al corte son marzo–agosto. La matriz contiene precios, fechas, envases, pesos y conversiones individuales; las 55 filas MCBA conservan además `origin_raw`, producto y variedad originales en el fragmento. Para Corrientes, el integrado ya es un derivado: los valores disponibles no demuestran los textos originales del libro y se identifican como `raw_disponible`, no como captura primaria. El integrado señala el archivo `MARTIN MICELLI 26-08-2026.xlsx`; el libro no se verificó en esta auditoría.

## Causa reproducible

El fragmento MCBA sí se carga. Sus 55 filas dicen `procedencia = Ctes.`; el de Corrientes dice `Corrientes`. `matchesPriceFilter` compara los valores de filtro sin aplicar `normalizeLocation`: seleccionar Corrientes excluye las 55 filas MCBA. Además, elegir especie `Tomate` excluye las 970 filas de Corrientes, que están bajo tres especies distintas. La unidad no causa la desaparición de esas 55 filas: satisfacen el filtro actual de comparabilidad por kg. Los dos desajustes actúan independientemente.

Existe una tercera cuestión que impide resolver el problema sólo con aliases: el gráfico calcula promedios simples por fila, por lo que combina variedades y distintas cantidades de observaciones diarias y agregados mensuales. Una línea por mercado no representa por sí sola una comparación homogénea. Deben acordarse y explicitarse la combinación de variedades, presentaciones y el método de agregación antes de publicarla.

## Unidades y límites

MCBA informa ARS/kg; el derivado es una media mensual de precios modales diarios por serie detallada, sin ponderación por volumen. Corrientes conserva precio observado por bulto y `kg_bulto`; el pipeline calcula precio/bulto dividido por kg/bulto y asigna confianza media. **La moneda está vacía en el integrado de Corrientes; el símbolo `$` por sí solo no acredita ARS.** La matriz distingue 877 filas cuyo peso numérico figura también en el texto de presentación, 92 `Granel X Kg` sin peso numérico en ese texto y una `Doc. de Mazo X 1 Kg` atípica para tomate. Las últimas 93 se marcan para revisión, no se afirma que su precio sea inválido. Verificar el libro primario es necesario para confirmar moneda, significado de la unidad y peso. La coincidencia aritmética no verifica calidad, calibre ni representatividad entre mercados.

## Procedencia y jerarquía propuestas

Equivalencias comprobables en los valores de los fragmentos 2026: `Ctes.` / `Corrientes` → `Corrientes`; `E. Rios` / `Entre Ríos` → `Entre Ríos`; `Bs. As.` / `Buenos Aires` → `Buenos Aires`; `R. Negro` / `Río Negro` → `Río Negro`; `Cordoba` / `Córdoba` → `Córdoba`; `Tucuman` / `Tucumán` → `Tucumán`. No se supone que abreviaciones territoriales como `S.bs.as.` o `Se Bs.as` equivalgan a toda la provincia. Estas propuestas no han sido aplicadas al dashboard; el catálogo completo de duplicados de todos los años sigue pendiente.

Para tomate, mapear inequívocamente `Tomate Perita`, `Tomate Cherry` y `Tomate Redondo` a producto Tomate y sus respectivas variedades; conservar Tomate + Larga Vida como variedad Larga Vida. Preservar siempre los campos originales disponibles. No extender una regla de prefijos a otros productos sin verificar su significado.

## Otros productos: control preliminar

Los siguientes conteos corresponden a filas 2026 en la vista mensual, sin seleccionar procedencia ni variedad; no prueban que haya series comparables para un origen y una presentación comunes.

| Producto | MCBA | Corrientes | Filas con kg estimado y confianza alta/media en MCBA / Corrientes |
|---|---:|---:|---:|
| Zanahoria | 54 | 183 | 54 / 183 |
| Berenjena | 49 | 269 | 49 / 269 |
| Pepino | 30 | 229 | 30 / 229 |
| Espinaca | 20 | 250 | 20 / 250 |
| Brócoli | 30 | 173 | 30 / 172 |

## Pendiente para una corrección segura

Falta contrastar las presentaciones con el libro original, construir y probar el catálogo completo y la jerarquía sin perder etiquetas, definir una agregación comparable por variedad/mercado/mes, distinguir disponibilidad de comparabilidad y probar la interfaz y sus errores. No se cambió la vista ni su semántica durante esta auditoría. Una regresión completa debe comprobar ambas causas, unidades, filas excluidas y series resultantes, además de los cinco productos de control.
