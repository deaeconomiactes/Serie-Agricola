# Plan de exploración SIO Granos

## 1. Objetivo

Evaluar SIO Granos como fuente local argentina automatizable para precios y operaciones de commodities agrícolas, sin asumir todavía una estructura definitiva ni utilizar datos en el dashboard.

## 2. Relación con el dashboard

SIO podría alimentar un futuro módulo analítico de commodities, separado de:

- cantidades frutihortícolas transadas;
- precios mayoristas frutihortícolas.

No se debe mezclar SIO con el pipeline BCR ni con los CSV visuales actuales hasta validar comparabilidad, cobertura, permisos y procedencia.

## 3. Variables deseables

- `fecha`;
- `commodity`;
- `precio`;
- `moneda`;
- `unidad`;
- `volumen`, si existe;
- `operacion` o `tipo_precio`;
- `zona`, `localidad`, `provincia` o `puerto`, si existe;
- `condicion_comercial`;
- `fuente`;
- `fecha_descarga`.

## 4. Riesgos metodológicos

SIO puede contener operaciones declaradas, precios de referencia o datos agregados según el endpoint disponible. No asumir que:

- es lo mismo que el precio de pizarra BCR;
- es lo mismo que FOB/FAS;
- es lo mismo que un futuro;
- es lo mismo que un precio mayorista frutihortícola.

Cada respuesta debe auditarse por fecha de concertación, fecha de entrega, condición de pago, calidad, zona, unidad, moneda y definición del precio. Un promedio ponderado por volumen tampoco debe confundirse con una cotización puntual.

## 5. Criterios para decidir si sirve

- disponibilidad sin credenciales;
- cobertura de soja, maíz, trigo, girasol, sorgo y cebada;
- frecuencia reciente;
- unidad clara;
- moneda clara;
- campo de precio claro;
- posibilidad de automatización;
- permisos de uso;
- estabilidad de la API;
- utilidad analítica.

La decisión deberá basarse en respuestas reales y trazables. Hasta entonces SIO queda como exploración técnica, sin integración visual ni publicación.
