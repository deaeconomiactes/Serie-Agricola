# Commodities agrícolas BCR

Esta carpeta corresponde al trabajo exploratorio de precios de commodities agrícolas de la **Bolsa de Comercio de Rosario / Cámara Arbitral de Cereales**.

## Estructura

- `raw/`: archivos originales descargados manualmente desde BCR. No se editan; tampoco se realizan llamadas de red ni scraping automático.
- `processed/`: archivos integrados y normalizados generados por Python, en particular `COMMODITIES_BCR_INTEGRADO.csv`.
- `reports/`: reportes y resúmenes de auditoría generados por Python a partir del CSV integrado.

## Uso

Desde la raíz del repositorio:

```powershell
python .\integrar_commodities_bcr.py
python .\auditar_commodities_bcr.py
```

Para integrar una carpeta externa de descargas manuales:

```powershell
python .\integrar_commodities_bcr.py "C:\ruta\a\descargas\bcr"
```

La plantilla que el integrador puede crear en `raw/` no se considera un dato real y se ignora automáticamente. Primero se deben colocar allí archivos completados descargados desde BCR.

Estos datos corresponden a commodities agrícolas/granos y forman una tercera familia separada de:

- cantidades frutihortícolas;
- precios mayoristas frutihortícolas.

No deben mezclarse directamente ni cruzarse con esas familias para inferir causalidad o relaciones precio-cantidad. La unidad, moneda, mercado, tipo de precio y condición comercial originales deben conservarse. Precio de pizarra, disponible, FOB/FAS y futuros son referencias distintas y no deben tratarse como una única serie.
