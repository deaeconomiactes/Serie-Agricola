# Checklist de validación BCR

## Fuente y alcance

- [ ] La fuente es BCR / Cámara Arbitral.
- [ ] El tipo de precio es Pizarra / Precio Cámara o está explícitamente separado.
- [ ] La cobertura de soja, maíz, trigo, girasol, sorgo y cebada fue comprobada.
- [ ] Los commodities nuevos se conservan aunque aún no estén en el catálogo.
- [ ] No se inventaron `bcr_id_grano`.

## Calidad de cada descarga

- [ ] Las fechas son fechas de mercado y no sólo fecha de descarga.
- [ ] La unidad está documentada y es comparable dentro de cada serie.
- [ ] La moneda está documentada y es comparable dentro de cada serie.
- [ ] El mercado y la condición comercial se conservaron.
- [ ] Se distinguieron datos faltantes, estimativos, conversiones y revisiones.
- [ ] La fecha máxima y la frecuencia real fueron verificadas.
- [ ] La procedencia y el nombre del archivo original quedaron registrados.

## Automatización y seguridad

- [ ] Existe un canal API o descarga estructurada autorizado.
- [ ] El endpoint fue confirmado y no está hardcodeado sin autorización.
- [ ] Las credenciales viven en variables de entorno o un gestor seguro.
- [ ] No hay secretos en el repo ni en el frontend.
- [ ] El fallback manual sigue funcionando.
- [ ] La integración y la auditoría corren con `raw/` vacío.

## Antes de crear el módulo visual

- [ ] ¿La fuente elegida es Precio de Pizarra / Precio Cámara?
- [ ] ¿La unidad es homogénea?
- [ ] ¿La moneda es homogénea?
- [ ] ¿Qué commodities tienen datos suficientes?
- [ ] ¿Cuál es la frecuencia real?
- [ ] ¿Cuál es la fecha máxima disponible?
- [ ] ¿La actualización puede automatizarse?
- [ ] ¿Hay permiso para uso interno?
- [ ] ¿Se debe mostrar fuente y fecha de descarga en el dashboard?
- [ ] ¿Qué indicadores analíticos se quieren mostrar?

No crear la pestaña de commodities ni cargar estos datos en el dashboard hasta completar esta sección.
