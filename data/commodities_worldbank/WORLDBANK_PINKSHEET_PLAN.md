# Plan World Bank Pink Sheet

## Objetivo

Evaluar una serie mensual histórica internacional para contexto y comparación de tendencias, manteniéndola separada de las operaciones SIO y de los precios locales argentinos.

## Fuente

World Bank Commodity Markets / Pink Sheet. La descarga futura deberá conservar el archivo original, la versión o fecha de publicación, la fecha de descarga y los metadatos de cada serie. No se implementa descarga en esta etapa.

## Archivo mensual esperado

Se espera trabajar con el archivo mensual histórico de Pink Sheet, preferentemente en el formato estructurado publicado por el Banco Mundial. El nombre real debe registrarse cuando se disponga del archivo; no se inventa un endpoint ni una URL sensible.

## Variables esperadas

- `fecha` o período mensual;
- identificador y nombre original de la serie;
- commodity normalizado sólo como campo derivado;
- precio o índice original;
- moneda;
- unidad original;
- frecuencia;
- fuente, versión y fecha de descarga;
- observaciones metodológicas y revisiones.

## Commodities candidatos

Explorar, sujeto a disponibilidad y nombres de serie: soja, maíz, trigo, aceite de soja, aceite de girasol y otros granos u oleaginosas. El catálogo debe conservar el nombre original de Pink Sheet y una normalización separada para facilitar búsquedas, sin borrar la etiqueta de la fuente.

## Unidad, moneda y frecuencia

- Frecuencia objetivo: mensual.
- Moneda esperada: USD, confirmada por serie y archivo.
- Unidad: la informada por World Bank para cada serie; puede ser tonelada, unidad física distinta o índice.
- No convertir a USD/TN ni a ARS/TN sin conservar valor original, regla, tipo de cambio, fecha y unidad derivada.

## Reglas de no mezcla con SIO

1. No unir filas SIO y World Bank en un mismo CSV analítico sin una dimensión explícita `fuente`.
2. No calcular una mediana o variación con observaciones de ambas fuentes.
3. No usar World Bank para rellenar meses faltantes de SIO.
4. No presentar una referencia internacional como precio local argentino.
5. Mantener separados mercado, tipo de precio, moneda, unidad y frecuencia.
6. Publicar siempre la fuente y una nota metodológica visible.

## Propuesta visual futura

La opción preferida es un dashboard o submódulo separado de referencias internacionales, con selector de fuente y advertencia explícita. Alternativamente, un selector de fuente puede convivir en el módulo de commodities sólo si cada selección reemplaza la serie completa y mantiene métricas, unidades, frecuencias y notas diferenciadas; nunca debe comparar fuentes incompatibles como si fueran una sola serie.

## Validación antes de integrar

- verificar cobertura mensual y fecha máxima;
- validar nombres, unidades, monedas y frecuencia;
- medir faltantes, revisiones y duplicados;
- reconciliar una muestra con la publicación original;
- documentar licencia, atribución y versión;
- generar salidas livianas y auditadas;
- mantener World Bank fuera del dashboard hasta completar estas verificaciones.
