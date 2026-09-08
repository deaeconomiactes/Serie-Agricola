# Commodities World Bank — Pink Sheet

## Objetivo

Preparar una integración futura de la serie mensual histórica **World Bank Commodity Markets / Pink Sheet** como referencia internacional separada del módulo SIO.

## Alcance

- Fuente internacional del Banco Mundial.
- Frecuencia principal mensual.
- Precios generalmente expresados en USD, según la serie original.
- Candidatos iniciales: soja, maíz, trigo, aceites y otros commodities agrícolas con cobertura consistente.
- La unidad debe conservarse desde el archivo original; no asumir que todas las series están en toneladas.

World Bank no reemplaza SIO ni representa precios locales argentinos, operaciones informadas, condiciones de entrega en Rosario o precios de pizarra BCR. Puede aportar contexto histórico mensual internacional.

## Regla de no mezcla

No combinar World Bank con SIO en una misma serie, mediana, variación o ranking. SIO representa operaciones informadas con su propia moneda, unidad, frecuencia y definición; Pink Sheet representa referencias internacionales mensuales. Si se muestran juntas, deben aparecer como fuentes y series distintas, con fuente, mercado, moneda, unidad y frecuencia visibles.

## Estructura

- `raw/`: archivos originales Pink Sheet, locales y fuera de Git.
- `processed/`: transformaciones auditadas, manteniendo el nombre y la unidad de la serie original.
- `dashboard/`: futuros agregados livianos exclusivos de World Bank.
- `reports/`: reportes de cobertura, mapeo y calidad.
- `WORLDBANK_PINKSHEET_PLAN.md`: plan técnico y metodológico.

No se descarga ni se carga World Bank al dashboard en esta etapa. Primero se debe validar la versión del archivo, fecha de descarga, series, unidades, moneda, revisiones y condiciones de uso.
