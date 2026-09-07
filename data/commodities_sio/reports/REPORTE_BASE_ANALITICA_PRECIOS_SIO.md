# Reporte de base analítica de precios SIO

## Objetivo

Construir una base de precios apta para análisis, separada de la base completa de operaciones. Los registros excluidos permanecen en la base completa y no se imputan.

## Fuente

- Archivo completo usado: `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/processed/COMMODITIES_SIO_EXPORTACION_MANUAL.csv`.
- Origen: SIO Granos / Secretaría de Agricultura.
- Filas de la base completa procesada: 396971.
- Fecha de integración/auditoría: 2026-09-07.
- Archivo analítico generado: `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/processed/COMMODITIES_SIO_ANALITICO_PRECIOS.csv` (152.79 MB).
- Versionado: no; el archivo supera 100 MB y queda ignorado por Git.
- Muestra liviana: `C:/Users/acer/Oficina/Serie-Agricola/data/commodities_sio/processed/COMMODITIES_SIO_ANALITICO_PRECIOS_SAMPLE.csv`; máximo 1000 filas.

## Regla de inclusión

Se incluye una fila sólo si cumple simultáneamente:
- `precio_valido_para_serie=sí`.
- `precio > 0`.
- fecha válida.
- commodity informado y no `Sin especificar`.
- moneda explícita (`moneda_explicitamente_informada=sí`).
- unidad explícita.
- fuente no vacía.

## Regla de exclusión

Se excluyen de la base analítica los precios cero, faltantes o no positivos; registros con moneda o unidad sin especificar; fechas inválidas; commodities vacíos; fuentes vacías; y cualquier fila marcada como no válida para serie. La base completa conserva todos esos registros para trazabilidad.

## Resultados

- Filas analíticas: 351600.
- Filas excluidas: 45371.
- Porcentaje usable: 88.57%.
- Precios cero excluidos: 40796.
- Commodities: ACEITE SOJA, ARROZ C.L.A, ARROZ C.L.F, CEBADA CERV., CEBADA FORR., Girasol, Maíz, Soja, Sorgo, TRIGO CAND., TRIGO PAN.
- Monedas: ARS, USD.
- Unidades: TN.
- Rango de fechas: 2026-03-12 a 2026-09-07.
- Precios positivos válidos: 351600.
- Principales series detectadas:
  - ACEITE SOJA / ARS / TN / Canje / condición Sin especificar: 4 filas, 4 días.
  - ACEITE SOJA / ARS / TN / Compraventa / condición Sin especificar: 55 filas, 45 días.
  - ACEITE SOJA / USD / TN / Canje / condición Sin especificar: 2 filas, 2 días.
  - ACEITE SOJA / USD / TN / Compraventa / condición Sin especificar: 648 filas, 122 días.
  - ARROZ C.L.A / ARS / TN / Canje / condición Sin especificar: 126 filas, 40 días.
  - ARROZ C.L.A / ARS / TN / Compraventa / condición Sin especificar: 109 filas, 46 días.
  - ARROZ C.L.F / ARS / TN / Canje / condición Sin especificar: 453 filas, 68 días.
  - ARROZ C.L.F / ARS / TN / Compraventa / condición Sin especificar: 363 filas, 92 días.
  - CEBADA CERV. / ARS / TN / Canje / condición Sin especificar: 1 filas, 1 días.
  - CEBADA CERV. / ARS / TN / Compraventa / condición Sin especificar: 1 filas, 1 días.
  - CEBADA CERV. / USD / TN / Canje / condición Sin especificar: 17 filas, 13 días.
  - CEBADA CERV. / USD / TN / Compraventa / condición Sin especificar: 1691 filas, 119 días.
  - CEBADA FORR. / ARS / TN / Canje / condición Sin especificar: 25 filas, 8 días.
  - CEBADA FORR. / ARS / TN / Compraventa / condición Sin especificar: 231 filas, 74 días.
  - CEBADA FORR. / USD / TN / Canje / condición Sin especificar: 221 filas, 82 días.
  - CEBADA FORR. / USD / TN / Compraventa / condición Sin especificar: 2841 filas, 128 días.
  - Girasol / ARS / TN / Canje / condición Sin especificar: 558 filas, 103 días.
  - Girasol / ARS / TN / Compraventa / condición Sin especificar: 9109 filas, 130 días.
  - Girasol / USD / TN / Canje / condición Sin especificar: 660 filas, 114 días.
  - Girasol / USD / TN / Compraventa / condición Sin especificar: 11901 filas, 143 días.

## Comparabilidad

- ARS y USD no deben mezclarse en una misma serie.
- Las series deben separarse por commodity, moneda, unidad, tipo_precio y condición comercial.
- No se deben comparar directamente operaciones con distinta condición comercial.
- Esta base no equivale a precio de pizarra BCR.

## Aptitud para dashboard

- Apta para exploración analítica: sí, con filtros de moneda, unidad, commodity y tipo de precio.
- Apta para dashboard piloto: parcial; requiere validar actualización, frecuencia, interpretación y selección de series.
- Apta para dashboard productivo: no, hasta validar actualización automática e interpretación metodológica.

## Recomendación próxima

Si la base analítica queda consistente, preparar un dataset mensual/diario agregado por commodity-moneda-unidad; definir reglas de visualización separando ARS/USD; no mostrar precios cero; y no integrar todavía al dashboard hasta validar actualización automática y metodología.

## Exclusiones por motivo

| Motivo | Registros |
| --- | ---: |
| moneda_no_explicita | 45370 |
| precio_valido_para_serie_no | 40796 |
| precio_no_positivo | 40796 |
| precio_cero | 40796 |
