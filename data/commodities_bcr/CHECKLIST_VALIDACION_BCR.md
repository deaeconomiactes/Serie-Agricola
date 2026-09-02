# Checklist de validación BCR

Completar este checklist con el jefe o el equipo antes de incorporar datos al dashboard.

## Decisiones ya tomadas

- Fuente piloto: BCR / Cámara Arbitral de Cereales.
- Tipo de precio prioritario: precios de pizarra / precios Cámara.
- Cobertura: todos los commodities disponibles con cobertura útil, priorizando soja, maíz, trigo, girasol y sorgo.
- Actualidad: usar lo más actual posible.
- Uso futuro: módulo analítico separado.
- Actualización: automatizar desde el inicio si existe una vía técnica y autorizada; conservar descarga manual como fallback.

1. ¿Qué commodities son prioritarios?
2. ¿Qué fuente exacta de BCR se usará?
3. ¿Se utilizará precio de pizarra, disponible, FOB/FAS u otro?
4. ¿La unidad es siempre `$/Tn` o cambia según el archivo/producto?
5. ¿La moneda es siempre ARS o hay referencias en USD?
6. ¿Qué período histórico se requiere?
7. ¿La descarga manual es suficiente o se requiere automatización?
8. ¿Se permite el uso y la republicación interna de los datos?
9. ¿Se necesita mostrar la fecha de descarga y la fecha de actualización de la fuente?
10. ¿El módulo debe ser sólo informativo o también analítico?

11. ¿La API BCR/GIX requiere autenticación y qué método de token utiliza?
12. ¿Qué variables de entorno o gestor de secretos administrará las credenciales?
13. ¿La API o descarga estructurada autoriza el uso y la republicación interna?
14. ¿Qué mecanismo de fallback se utilizará si la API deja de estar disponible?

## Evidencia a conservar

- archivo original descargado;
- URL o pantalla de origen;
- fecha de descarga;
- período consultado;
- unidad, moneda y condición comercial;
- confirmación de permisos de uso;
- resultado de la auditoría y casos problemáticos.

La validación debe mantener commodities agrícolas/granos como una familia separada de cantidades y precios mayoristas frutihortícolas.
