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

## Decisión operativa inicial

- La fuente piloto es BCR / Cámara Arbitral de Cereales.
- Se priorizan precios de pizarra / precios Cámara por su cercanía con precios locales de mercado.
- Se incluirán todos los commodities disponibles con cobertura útil, empezando por soja, maíz, trigo, girasol y sorgo; cebada y otros granos se incorporarán si la cobertura es consistente.
- El foco inicial es lo más actual posible.
- El módulo futuro tendrá uso analítico, pero todavía no tiene interfaz visual.
- La actualización ideal será automatizada, siempre respetando acceso, permisos y condiciones de uso.
- Si la API requiere autenticación, las credenciales se manejarán mediante variables de entorno y nunca en el frontend.
- Si no hay API estable o credenciales, se mantiene el fallback de descarga manual.

## Flujo recomendado

1. Configurar `.env` si se cuenta con API/credenciales.
2. Ejecutar una simulación segura:

   ```powershell
   python .\descargar_commodities_bcr.py --dry-run --days-back 30
   ```

3. Si no hay API, descargar manualmente y colocar los archivos originales en `raw/`.
4. Ejecutar `python .\integrar_commodities_bcr.py`.
5. Ejecutar `python .\auditar_commodities_bcr.py`.
6. Revisar los reportes de cobertura, actualidad y calidad.
7. Recién después decidir la implementación visual.

La configuración API y el flujo de seguridad están documentados en `API_BCR_PLAN.md`.
