# Exploración SIO Granos

Esta carpeta corresponde a la exploración técnica de SIO Granos / Secretaría de Agricultura como posible fuente local automatizable de commodities agrícolas. Se evalúa como alternativa ante la falta de credenciales BCR/API GIX, pero todavía no está integrada al dashboard ni se presume que sus datos sean equivalentes a los precios de pizarra BCR.

## Estructura

- `raw/`: respuestas originales obtenidas mediante exploración pública autorizada o descargas manuales.
- `processed/`: CSV integrado de SIO, separado de BCR y de las fuentes frutihortícolas.
- `reports/`: auditorías de cobertura, calidad, actualidad y aptitud analítica.
- `sio_config.example.json`: esquema sin credenciales ni endpoints inventados.
- `sio_config.json`: configuración local real, ignorada por Git.
- `catalogo_productos_sio.csv`: catálogo inicial sin IDs inventados.

Debe conservarse en cada registro `fuente`, `mercado`, `tipo_precio`, `moneda`, `unidad`, `frecuencia`, `condicion_comercial` y procedencia. SIO puede representar operaciones declaradas, precios de referencia o datos agregados según el recurso consultado; no debe mezclarse con BCR, futuros, FOB/FAS ni precios mayoristas frutihortícolas en un mismo CSV final.

## Flujo seguro

Por defecto el explorador no hace llamadas web:

```powershell
python .\explorar_sio_granos.py
python .\explorar_sio_granos.py --dry-run --date-start 2026-08-01 --date-end 2026-09-01 --products soja,maiz,trigo
```

Para una exploración pública controlada, completar localmente `sio_config.json` con endpoints públicos documentados y ejecutar con `--allow-web`, limitando `--max-requests`. `--save-response` conserva las respuestas en `raw/`.

Luego:

```powershell
python .\integrar_commodities_sio.py
python .\auditar_commodities_sio.py
```

No generar datos ficticios ni cargar datos SIO en el navegador. La eventual visualización será un módulo analítico de commodities separado de cantidades y precios frutihortícolas.
