# Diagnóstico de fuentes locales mensuales de commodities

## Objetivo

Comparar alternativas para ampliar la historia mensual de precios de commodities argentinos sin presentar como equivalentes operaciones SIO, precios internos, FAS teórico, FOB oficiales ni referencias internacionales.

## Comparativo metodológico

| Fuente | Oficialidad | Mercado / relación local | Frecuencia | Unidad y moneda | Productos esperados | Cobertura histórica | Automatización | Limitaciones | Recomendación |
|---|---|---|---|---|---|---|---|---|---|
| Precios internos de principales granos — Secretaría de Agricultura / Mercados Agropecuarios | Oficial/institucional; página y tabla declaran pesos argentinos por tonelada | Mercado interno argentino, separado por plaza/puerto | Mensual | ARS/TN | Trigo, maíz, sorgo, soja, girasol, cebada forrajera | Páginas anuales 2020–2025 e informe actual 2026; validar cobertura por commodity/plaza | Media: HTML oficial con descarga controlada; mantener fallback manual | Puede cambiar la estructura o la cobertura; el año en curso puede estar incompleto | **Primera opción** para histórico local mensual |
| FAS teórico — Secretaría de Agricultura / series de granos y subproductos | Oficial/institucional como referencia publicada; no equivale a una operación | Paridad/capacidad de pago vinculada a exportación | Mensual y/o según publicación | Sólo conservar moneda/unidad explícitas; no asumir ARS/TN o USD/TN | Granos, oleaginosas y subproductos según serie | A relevar en la publicación original | Media: depende del formato y metadatos disponibles | No es precio transado ni necesariamente comparable con precio interno o SIO | Opción complementaria, en tipo de precio separado |
| FOB oficiales — Datos Argentina | Oficial | Exportación argentina; no mercado interno | Diaria, agregable a mensual | Usualmente USD/TN si la fuente lo explicita | Granos y productos exportables según dataset | A relevar según dataset y serie | Media/alta si existe descarga estructurada estable | Agregar diarios puede ocultar dispersión; no equivale a precio interno/FAS/SIO | **Fallback** si no hay serie mensual local descargable; documentar mediana/promedio |
| SIO Granos histórico por tramos | Institucional; operaciones informadas | Operaciones declaradas en la plataforma argentina | Diaria; consultas históricas por ventanas de hasta 180 días | ARS/USD y unidad sólo cuando están explícitas | Granos y oleaginosas disponibles | La cobertura debe reconstruirse por tramos; la base actual comienza en marzo de 2026 | Controlada/manual; no scraping masivo | Cobertura desigual, límites de consulta, duplicados y cambios de estructura | Mantener separado; no usarlo como sustituto de la serie mensual local |
| World Bank Pink Sheet | Oficial internacional | Referencia internacional, no precio local argentino | Mensual | Generalmente USD, unidad según serie | Granos, oleaginosas y aceites según archivo | Historia internacional amplia, a confirmar por serie | Alta por descarga estructurada | No representa mercado interno argentino, Rosario, impuestos, fletes ni condiciones locales | Contexto posterior, no prioridad local |

## Lectura recomendada

1. Usar primero la serie mensual de precios internos de la Secretaría y conservar la plaza/puerto como dimensión de mercado; volver a confirmar nombre, fecha, unidad, moneda, cobertura y condiciones de uso en cada descarga.
2. Mantener FAS teórico en una serie propia porque expresa una referencia de paridad, no necesariamente una transacción.
3. Usar FOB oficial sólo si la serie mensual local no puede descargarse de forma estable; agregar diarios con método visible y conservar la frecuencia original en las observaciones.
4. Ampliar SIO por tramos de hasta 180 días únicamente como línea de operaciones informadas; no rellenar con ella los meses faltantes del histórico local.
5. Dejar World Bank para contexto internacional posterior, sin mezclarlo con ninguna serie argentina.

## Reglas mínimas de publicación

- Mantener separadas `fuente`, `mercado`, `tipo_precio`, `moneda`, `unidad` y `frecuencia`.
- No calcular variaciones con ARS y USD juntos ni con unidades distintas.
- No transformar FOB o FAS en precio interno sin una metodología explícita.
- No asumir cobertura histórica por el nombre de una fuente; auditar fechas y meses disponibles.
- No presentar una fuente no oficial como oficial ni una referencia institucional como una operación observada.
- Publicar sólo agregados livianos y acompañarlos con la fecha de descarga, versión y nota metodológica.

## Estado de la implementación

El pipeline local mensual queda preparado con una configuración pública versionada de ejemplo, pero sin descargar datos por defecto. La fuente local aparece como opción independiente en el módulo Commodities y se alimenta sólo de sus propios CSV dashboard-ready después de auditar el HTML. SIO continúa consumiendo sus propios CSV; World Bank no se carga en esta etapa.
