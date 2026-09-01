# Evaluación exploratoria de fuentes de commodities agrícolas

Este documento es una evaluación preliminar. No se incorporan commodities al dashboard ni se agregan llamadas externas desde `app.js`.

## Fuentes consideradas

| Fuente | Productos | Frecuencia/cobertura | Acceso y credenciales | Ventajas | Limitaciones y mantenimiento | Recomendación |
|---|---|---|---|---|---|---|
| Bolsa de Comercio de Rosario / Cámara Arbitral de Cereales | Soja, maíz, trigo, sorgo, girasol y otros granos | Cotizaciones y referencias locales; verificar calendario y cobertura histórica por producto | Revisar disponibilidad de archivos, servicios o publicaciones; no asumir API pública | Referencia local argentina y alta pertinencia para granos | Puede requerir acuerdos, descarga manual o adaptación ante cambios de publicación | Prioridad para precios locales, sujeto a validar formato, licencia y automatización permitida |
| MATba Rofex / Primary API | Futuros, contratos y market data de commodities | Intradiaria/diaria según instrumento y permiso | Puede requerir cuenta, credenciales y autorización comercial | Datos de mercado estructurados y útiles para seguimiento de futuros | No equivale al precio físico mayorista; acceso y condiciones pueden restringir el uso | Evaluar sólo con acceso institucional y revisión legal/técnica previa |
| World Bank Pink Sheet | Granos, aceites, alimentos y otros commodities internacionales | Principalmente mensual; series históricas extensas | Publicación descargable; confirmar versión y licencia vigente | Fuente internacional estable y comparable | No representa precios locales diarios ni mercados argentinos | Usar como contexto internacional en un módulo separado |
| Secretaría de Agricultura / datos.gob.ar | Datasets oficiales agropecuarios, según disponibilidad | Variable; depende de cada dataset | Portal abierto o descarga; validar actualización y licencia | Fuente pública nacional y potencialmente reutilizable | Cobertura y actualización pueden ser discontinuas | Buscar datasets específicos antes de diseñar una integración |
| USDA / FAO / FRED | Precios y series internacionales agroalimentarias | Variable: diaria, mensual o anual según serie | Portales y APIs con condiciones propias | Buen contexto internacional y series documentadas | No reemplazan fuentes locales; unidades, monedas y metodologías pueden diferir | Usar sólo para referencia contextual, con ficha metodológica |

## Criterios de evaluación antes de integrar

- Definir producto, unidad, moneda, mercado y frecuencia original.
- Confirmar cobertura histórica, fecha de actualización y tratamiento de revisiones.
- Verificar formato estable: CSV, API, descarga oficial o publicación estructurada.
- Revisar credenciales, límites de uso, licencia y autorización para redistribución.
- Registrar fuente, fecha de descarga y versión de cada archivo.
- Mantener commodities separados de frutas y hortalizas mayoristas.
- No mezclar precios locales, futuros e índices internacionales en un mismo indicador.

## Recomendación de arquitectura

1. Priorizar BCR/Cámara Arbitral para referencias físicas locales si existe un mecanismo de acceso autorizado y estable.
2. Evaluar MATba Rofex para futuros sólo con credenciales y permisos confirmados.
3. Utilizar World Bank Pink Sheet para contexto internacional mensual, no para sustituir precios mayoristas diarios.
4. Crear en el futuro un módulo independiente de commodities con su propia unidad, frecuencia, filtros y notas metodológicas.

La incorporación futura deberá mantener separados los precios de commodities, los precios frutihortícolas y las cantidades transadas. No se deben inferir causalidad, escasez ni relaciones precio-cantidad entre esas fuentes sin una metodología específica y una coincidencia validada de período, mercado, producto y unidad.
