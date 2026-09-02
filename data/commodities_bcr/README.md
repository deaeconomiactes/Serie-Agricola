# Commodities agrícolas BCR

Esta carpeta corresponde al trabajo exploratorio de precios de commodities agrícolas de la **Bolsa de Comercio de Rosario / Cámara Arbitral de Cereales**.

- `raw/` contiene las descargas originales realizadas manualmente desde BCR. No se realizan llamadas de red ni scraping automático.
- `processed/` contiene el CSV integrado que produce `integrar_commodities_bcr.py`.
- `reports/` contiene las auditorías y resúmenes que produce `auditar_commodities_bcr.py`.

Estos datos corresponden a granos y commodities agrícolas. No deben mezclarse directamente con los precios mayoristas frutihortícolas ni con las cantidades transadas. Tampoco deben cruzarse con esas familias para inferir causalidad o relaciones precio-cantidad.

La unidad, moneda, mercado, tipo de precio y condición comercial originales deben conservarse. Precio de pizarra, disponible, FOB/FAS y futuros son referencias distintas y no deben tratarse como una única serie.
