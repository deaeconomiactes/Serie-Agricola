# Plan de exploración SIO Granos

## 1. Objetivo y alcance

Evaluar SIO Granos como fuente local argentina para precios y operaciones de commodities agrícolas. Esta fase es exploratoria: no integra commodities al dashboard, no modifica sus archivos visuales y no supone que SIO sea equivalente a BCR.

El foco inicial es la consulta pública de operaciones informadas y la detección prudente de exportaciones disponibles para soja, maíz, trigo, girasol, sorgo y cebada. Se prioriza lo más actual posible, comenzando con los últimos 30 días.

## 2. Automatización controlada

- El modo seguro no hace llamadas externas.
- `--dry-run` muestra productos, fechas, ventanas, endpoints configurados y límite de requests sin descargar.
- `--allow-web` es obligatorio para una exploración pública; sólo usa endpoints explícitos en `sio_config.json`.
- Cada ventana puede cubrir como máximo 180 días y los rangos mayores se dividen antes de consultar.
- Se usa timeout de 30 segundos, User-Agent identificable y no se implementan scraping agresivo ni reintentos automáticos.
- `--save-response` conserva el HTML de diagnóstico como `SIO_diagnostico_consulta_publica_{timestamp}.html` o la respuesta estructurada recibida.
- No se asume el payload de formularios: primero se inspeccionan campos, acciones y enlaces de exportación.
- Si no se detecta exportación estable, se usa `--manual-urls` o se descargan archivos manualmente en `raw/`.

## 3. Variables deseables

- `fecha` de declaración, concertación o entrega, identificando cuál se usa;
- `commodity` y eventual `sio_id_producto` validado;
- `precio`, con definición del precio;
- `moneda` y `unidad`;
- `volumen` y unidad de volumen, si existen;
- `tipo_precio` y `operacion`;
- `procedencia`, provincia, localidad, zona y `precio_puesto_en`, si existen;
- `condicion_pago` y `condicion_comercial`;
- `mercado`, `fuente`, `frecuencia` y archivo original.

El integrador no completa automáticamente moneda, unidad ni tipo de precio: cuando faltan, conserva `Sin especificar` y deja una observación para auditoría.

## 4. Relación con BCR y el dashboard

SIO debe permanecer separado del pipeline BCR y de las familias frutihortícolas. No se mezclan fuentes con distinta moneda, unidad, frecuencia o definición de precio. Tampoco se presentan operaciones SIO como precios de pizarra BCR, ni se cargan datos SIO en `app.js`, `index.html` o `styles.css`.

## 5. Riesgos metodológicos

SIO puede contener operaciones declaradas, precios de referencia o datos agregados según el recurso consultado. No asumir que es lo mismo que precio de pizarra BCR, FOB/FAS, futuros o precio mayorista frutihortícola. La auditoría debe verificar fecha, definición del precio, condición de pago, operación, volumen, procedencia, destino, unidad, moneda, frecuencia, duplicados, cobertura temporal y permisos de uso.

## 6. Criterios de decisión

SIO será una alternativa útil sólo si presenta cobertura real para los productos prioritarios, datos recientes, definición clara del precio, metadatos homogéneos, procedencia trazable, permisos compatibles y una consulta/exportación estable. La recomendación final debe apoyarse en respuestas reales, no en datos inventados ni en la mera existencia de una URL.

## 7. Comandos de referencia

```powershell
python .\explorar_sio_granos.py --dry-run --days-back 30 --products soja,maiz,trigo,girasol,sorgo
python .\explorar_sio_granos.py --manual-urls --days-back 30 --products soja,maiz,trigo
python .\explorar_sio_granos.py --allow-web --save-response --max-requests 3 --days-back 30 --products maiz
python .\integrar_commodities_sio.py
python .\auditar_commodities_sio.py
```
