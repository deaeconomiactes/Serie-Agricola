# Guía de descarga manual BCR

## Objetivo

La carpeta `data/commodities_bcr/raw/` recibe las descargas originales del piloto de commodities agrícolas de la Bolsa de Comercio de Rosario / Cámara Arbitral de Cereales. El objetivo es conservar una copia sin modificar de la fuente antes de integrarla y auditarla.

## Archivos a colocar en `raw/`

Colocar únicamente archivos descargados manualmente desde BCR/Cámara Arbitral:

- Excel (`.xlsx` o `.xls`);
- CSV (`.csv`), si la fuente ofrece ese formato.

No se realiza scraping automático ni se hacen llamadas de red desde este repositorio. Los archivos temporales de Excel, `desktop.ini` y la plantilla generada por el integrador se ignoran.

## Productos iniciales

Para la primera prueba, priorizar:

- soja;
- maíz;
- trigo;
- girasol;
- sorgo.

La cebada y otros granos pueden incorporarse después de confirmar que la fuente publica una serie consistente.

## Período sugerido

1. Descargar primero una muestra corta, por ejemplo los últimos 3 o 6 meses.
2. Verificar que el formato, las fechas, las unidades, la moneda y la condición comercial se integren correctamente.
3. Si el formato funciona, ampliar la prueba al período 2024–2026.

No se deben inventar fechas diarias a partir de archivos mensuales o anuales.

## Nombres de archivo

Usar nombres claros que incluyan fuente, tipo de precio, commodity y período. Por ejemplo:

```text
BCR_pizarra_soja_2024_2026.xlsx
BCR_pizarra_maiz_2024_2026.xlsx
BCR_pizarra_trigo_2024_2026.xlsx
BCR_pizarra_girasol_2024_2026.xlsx
BCR_pizarra_sorgo_2024_2026.xlsx
```

El integrador puede detectar el commodity desde el nombre si el archivo no trae una columna explícita de producto o grano.

## Conservación y procesamiento

- No editar manualmente los archivos originales descargados.
- Mantener los originales en `raw/` para trazabilidad.
- Ejecutar `python .\integrar_commodities_bcr.py` para generar archivos limpios en `processed/`.
- Ejecutar `python .\auditar_commodities_bcr.py` para producir los reportes en `reports/`.

La unidad, moneda, tipo de precio y condición comercial deben conservarse. Las referencias de pizarra, disponible, FOB/FAS y futuros no deben mezclarse como si fueran la misma serie ni con precios o cantidades frutihortícolas.
