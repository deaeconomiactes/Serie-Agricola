# Evaluación de fuentes para commodities agrícolas

**Estado:** evaluación exploratoria. **No hay integración de commodities en el dashboard.**

Este documento evalúa fuentes potenciales para una incorporación futura. En esta etapa no se integran commodities al dashboard ni se realizan llamadas automáticas de red. Sí se deja preparada documentación, estructura técnica exploratoria y scripts de apoyo para futuras pruebas controladas.

Los scripts disponibles preparan integración, auditoría y descarga controlada, pero no publican información en el dashboard.

## 1. Objetivo

Evaluar la posibilidad de incorporar precios de commodities agrícolas como una tercera familia de datos del dashboard **“Tránsito y Comercialización Frutihortícola”**.

El módulo sería conceptualmente separado de:

- las cantidades frutihortícolas transadas;
- los precios mayoristas frutihortícolas.

La evaluación cubre fuentes, cobertura, unidades, monedas, frecuencia de actualización, factibilidad técnica, riesgos y una posible arquitectura futura. Las fuentes y CSV actualmente disponibles en el proyecto corresponden al dominio frutihortícola; ninguna de ellas se interpreta aquí como fuente de commodities.

## 2. Alcance posible

### Productos a evaluar

- soja;
- maíz;
- trigo;
- girasol;
- sorgo;
- cebada, si existe disponibilidad consistente;
- otros granos u oleaginosas relevantes publicados por la fuente seleccionada.

### Variables deseables

- `fecha`;
- `commodity`;
- `mercado` o ámbito de referencia;
- `fuente`;
- `precio`;
- `moneda`;
- `unidad`;
- `frecuencia`;
- `tipo_precio` — por ejemplo, pizarra, disponible, FOB, FAS, cierre o futuro;
- `condicion_comercial` — entrega, pago, calidad o especificación cuando corresponda;
- `contrato` y `vencimiento` para derivados;
- `fuente_original` o URL;
- `fecha_actualizacion` y, si fuera posible, fecha de descarga.

El alcance debe mantener la condición comercial y el mercado de referencia. Un precio de pizarra, un cierre de futuro y un precio FOB no son observaciones intercambiables aunque correspondan al mismo commodity.

## 3. Fuentes locales argentinas

### 3.1 Bolsa de Comercio de Rosario / Cámara Arbitral de Cereales

La [Cámara Arbitral de Cereales de la BCR](https://www.cac.bcr.com.ar/es/precios-de-pizarra/consultas) ofrece consultas históricas de precios de pizarra por producto y período, con períodos diario, mensual y anual y opción de descarga de Excel. La propia publicación aclara que la fecha consultada es la fecha de mercado, no necesariamente la fecha en que se fijó o publicó la pizarra.

**Qué podría aportar:**

- precios locales de granos físicos, especialmente soja, maíz, trigo, girasol y sorgo;
- una referencia de mercado disponible, diferenciada de los precios minoristas o mayoristas frutihortícolas;
- cobertura histórica consultable, sujeta a validar producto por producto y período por período.

**Unidad y moneda:** en la publicación de pizarra, la unidad probable es pesos argentinos por tonelada (`$/Tn`). La BCR también puede mostrar una conversión informativa a dólares por tonelada. Esa conversión no debe recalcularse sin conservar el tipo de cambio y la regla aplicada: la publicación consultada indica que utiliza el dólar estadounidense divisa al cierre, tipo comprador, del Banco de la Nación Argentina. El valor en USD debe conservarse como referencia informativa, no como una segunda observación independiente.

**Condición comercial:** la BCR describe los precios corrientes como mercadería con entrega inmediata, pago contado y puesta sobre camión y/o vagón en zona Rosario. La condición exacta debe almacenarse junto con el precio y no inferirse si cambia la publicación.

**Frecuencia y actualización:** potencialmente diaria en días de mercado para la pizarra; la frecuencia efectiva debe validarse con el calendario y con la disponibilidad de cada producto. Las consultas mensual y anual parecen ser agregaciones o vistas históricas de la fuente, por lo que se deberá documentar su método antes de usarlas para cálculos.

**Acceso y automatización:** hay una interfaz HTML de consulta histórica y descarga de Excel. En la revisión realizada no se asume la existencia de una API pública estable. Antes de automatizar, habría que verificar si existe un canal oficial de descarga estructurada, si la descarga requiere sesión, cómo se identifica la fecha de publicación y cuáles son las condiciones de uso.

**Ventajas:** alta pertinencia para precios físicos argentinos; fuente institucional; productos y condiciones comerciales relativamente cercanos al mercado local; posibilidad de recuperar historia.

**Limitaciones y riesgos:** puede no fijarse una pizarra cuando no hay operaciones representativas; pueden coexistir precios estimativos, referencias o valores expresados con marcas especiales; la estructura HTML o del archivo descargable puede cambiar; la cobertura de cebada y otros granos puede ser irregular; la conversión a USD depende de un tipo de cambio y una convención específicos.

**Recomendación:** primera candidata para un piloto futuro de precios locales, siempre que se confirme un mecanismo de acceso autorizado y estable, se audite una muestra histórica y se registre la metodología de cada serie. No iniciar scraping ni redistribución automática sin revisar estabilidad, licencia y condiciones de uso.

### 3.2 Bolsa de Comercio de Rosario: cotizaciones locales / FOB-FAS

La sección de [Cotizaciones Locales de la BCR](https://www.bcr.com.ar/es/mercados/mercado-de-granos/cotizaciones/cotizaciones-locales-1) presenta, en forma separada, referencias de la Cámara Arbitral, del Mercado Físico de Rosario y de **FOB/FAS Argentina**.

**Precios locales:** sirven para observar referencias del mercado físico de Rosario. Pueden expresarse en pesos o dólares según el producto, mercado y pantalla; no debe suponerse que todas las filas comparten moneda, fecha de entrega o condición.

**FOB/FAS:** son referencias vinculadas a exportación y capacidad de pago/export payment capacity. La página las presenta como precios de granos y oleaginosas en USD por tonelada e incluye, según producto y vencimiento, fechas de embarque, ofertas de compra/venta, derechos de exportación y costos portuarios. FOB y FAS representan posiciones comerciales distintas de un precio local disponible y requieren campos metodológicos propios.

**Productos:** pueden incluir trigo, maíz, soja, sorgo, girasol y otras referencias según la fecha, el puerto, la calidad y el vencimiento publicados. La disponibilidad debe relevarse en forma periódica y no codificarse como un catálogo fijo sin validación.

**Frecuencia:** aparenta estar asociada a cotizaciones o cierres de mercado, con actualización vinculada a ruedas y publicaciones de la BCR. Se deberá comprobar la hora de corte, si el valor es intradiario o de cierre y cómo se tratan datos faltantes.

**Utilidad para el dashboard:** puede servir como subfuente de referencias locales o de exportación dentro del módulo de commodities. No debe combinarse en una misma serie con la pizarra sin mostrar el mercado, la condición comercial y la moneda.

**Limitaciones:** riesgo de confundir FOB, FAS, precio local, oferta, cierre y precio de pizarra; presencia de contratos o fechas de embarque distintos; posible dependencia de tablas HTML o archivos cuya estructura cambie; necesidad de revisar permisos de reutilización y atribución.

**Recomendación:** mantenerla como una opción complementaria de BCR. Para un primer piloto, seleccionar una sola convención —por ejemplo, pizarra local o una referencia FOB/FAS bien definida— en lugar de mezclar todas las pantallas.

### 3.3 MATba Rofex / Primary / ICE

MATba Rofex —actualmente presentado institucionalmente como A3 Mercados— ofrece futuros y opciones sobre productos agrícolas, incluyendo referencias sobre soja, maíz, trigo, sorgo y cebada, además de contratos mini y contratos sobre mercados externos según el instrumento. La [página institucional del mercado](https://matbarofex.com.ar/) lista productos, horarios, datos de mercado y documentación de contratos.

La [documentación de Primary API](https://apihub.primary.com.ar/assets/docs/Primary-API.pdf) documenta acceso a market data histórica mediante consultas de trades por instrumento y fecha o rango de fechas, identificando `ROFX` como mercado MATBA ROFEX. También se observan endpoints y documentación institucional que requieren autorización o token en determinados servicios.

**Qué podría aportar:**

- precios de futuros, opciones, ajustes y operaciones, según el producto y permiso;
- contratos con vencimientos explícitos;
- datos estructurados y potencialmente históricos, más adecuados para una serie de mercado financiero que para un precio físico mayorista;
- referencias de mercado local y, en ciertos casos, contratos ligados a mercados internacionales.

**Unidades y monedas:** dependen del contrato. La unidad del precio, el tamaño del contrato, la moneda de cotización, el tipo de cambio aplicable y el precio de ajuste deben tomarse de la especificación oficial de cada instrumento. No se debe normalizar todo a `$/Tn` sin conservar la unidad contractual original.

**Frecuencia:** puede ser intradiaria, diaria o de cierre/ajuste. La frecuencia útil para el dashboard dependerá del producto, del dato adquirido y de la hora de corte. Las series de futuros también requieren distinguir fecha de operación, fecha de liquidación y vencimiento.

**Factibilidad técnica:** existe una vía documentada mediante Primary/REST y, según la modalidad, WebSocket o proveedores de datos. La automatización probablemente requiere cuenta, credenciales, token, límites y autorización comercial. ICE también ofrece datos de Matba Rofex mediante servicios de market data; esa alternativa es de carácter comercial y no debe asumirse como descarga abierta.

**Ventajas:** estructura más apta para automatización institucional; identificación de instrumentos y contratos; datos de mercado con potencial de baja latencia e historia.

**Limitaciones y riesgos:** no representa automáticamente el precio físico disponible; riesgo de usar un futuro como si fuera una cotización spot; cambios de contratos, símbolos o reglas; dependencia de credenciales y disponibilidad del servicio; costos, licencias, restricciones de redistribución y riesgo legal si se expone market data a usuarios no autorizados.

**Recomendación:** evaluar sólo después de confirmar con el equipo el objetivo financiero y disponer de acceso institucional autorizado. No implementar una conexión a Primary, MATba Rofex o ICE en esta etapa.

## 4. Fuentes internacionales

### 4.1 World Bank Commodity Prices — Pink Sheet

El [World Bank Commodity Markets](https://www.worldbank.org/en/research/commodity-markets) publica el conjunto **Commodity Markets / Pink Sheet**, con archivos mensuales y anuales descargables. La [página de datos de precios de commodities](https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/world-bank-commodities-price-data-the-pink-sheet) enlaza, entre otros recursos, archivos históricos mensuales y anuales.

**Cobertura:** incluye series internacionales de commodities, con referencias para granos y oleaginosas como trigo, maíz, soja y aceites, además de otras familias. El catálogo exacto puede cambiar; al incorporar se deberá conservar la versión del archivo y el nombre de la serie original.

**Frecuencia, moneda y unidad:** la referencia principal es mensual, usualmente en USD y con unidades específicas por commodity. La unidad no necesariamente es tonelada para todas las series; debe tomarse del encabezado y metadatos de cada archivo.

**Utilidad:** construir contexto internacional, comparar tendencias de commodities o complementar una serie local con una referencia global mensual. Es especialmente útil cuando se necesita historia amplia y una fuente relativamente estable.

**Limitación metodológica:** no representa precios locales argentinos diarios, condiciones de entrega en Rosario, calidad argentina, impuestos locales, fletes internos ni un precio mayorista frutihortícola. Una comparación con BCR requeriría explicitar la diferencia de mercado, unidad, fecha y moneda.

**Ventajas:** descarga estructurada en Excel; cobertura histórica amplia; referencia internacional documentada; frecuencia compatible con análisis mensual.

**Riesgos:** revisiones de series, cambios de archivo o nombre, definiciones distintas entre productos y posibles restricciones de uso/atribución. Se debe conservar fecha de descarga, versión y metadatos.

**Recomendación:** usarla sólo como referencia internacional mensual dentro del módulo separado de commodities; no utilizarla para reemplazar precios locales ni para presentarla como precio argentino.

### 4.2 FAO / AMIS / USDA / FRED

Estas fuentes pueden complementar el análisis, pero no son equivalentes entre sí:

- **FAO/FAOSTAT:** ofrece datos agrícolas y un dominio de precios de productores, con observaciones anuales y mensuales según país y producto. Son precios recibidos por productores o estadísticas nacionales, no necesariamente cotizaciones de mercado de granos. [FAO describe sus datos de precios](https://www.fao.org/prices/en) y [FAOSTAT ofrece descarga y API](https://www.fao.org/Faostat/en/). Puede ser una fuente útil para contexto productivo o comparación de precios de origen, con revisión de cobertura para Argentina.
- **AMIS:** la base y el *Market Monitor* se concentran en trigo, maíz, arroz y soja, con información internacional y publicación mensual o periódica. Es útil para contexto de oferta, demanda y seguridad alimentaria; no sustituye un precio local diario. [FAO describe la cobertura y frecuencia de AMIS](https://www.fao.org/statistics/events/events-detail/amis-market-monitor.-july-2026-update/en).
- **USDA/WASDE:** publica mensualmente estimaciones y pronósticos de oferta y uso de trigo, arroz, granos gruesos, oleaginosas y algodón, con archivos históricos y formatos como CSV, Excel y XML. Es una fuente de fundamentos y proyecciones, no una serie única de precios spot. [USDA documenta WASDE y su frecuencia](https://www.usda.gov/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report).
- **FRED:** agrega series económicas de distintos organismos. Puede servir para índices de precios de productores o series estadounidenses, pero se debe guardar el identificador de la serie, organismo originante, unidad y ajuste estacional. Por ejemplo, la serie de maíz del [BLS disponible en FRED](https://fred.stlouisfed.org/series/WPU01220205) es un índice mensual, no un precio en USD/Tn.

**Recomendación:** comenzar con World Bank para un contexto internacional de precios. Evaluar FAO/AMIS, USDA o FRED sólo si la pregunta analítica requiere productores, fundamentos, pronósticos o índices y si se puede explicar claramente la diferencia con un precio de mercado.

## 5. Comparabilidad metodológica

Los commodities agrícolas no deben mezclarse directamente con los precios mayoristas frutihortícolas ni con las cantidades frutihortícolas. Son observaciones de cadenas, mercados y convenciones distintas.

| Dimensión | Frutas y hortalizas | Commodities agrícolas |
|---|---|---|
| Producto | Especies, variedades, calibres, calidades y procedencias heterogéneas | Granos u oleaginosas con especificaciones y estándares comerciales más homogéneos |
| Mercado | Mercado mayorista y operaciones físicas por plaza | Mercado físico de granos, exportación o mercado de futuros |
| Unidad | Frecuentemente kg, bulto, cajón, bolsa o envase | Frecuentemente tonelada; en futuros, unidad y tamaño de contrato específicos |
| Moneda | Puede ser pesos argentinos y variar por mercado o fuente | Pesos o dólares; la conversión exige tipo de cambio y fecha documentados |
| Frecuencia | Según registro, mercado y disponibilidad del producto | Diaria o intradiaria para mercados locales/futuros; mensual para referencias internacionales |
| Lógica comercial | Fuerte efecto de variedad, calidad, origen, estacionalidad y presentación | Precio por especificación, entrega, puerto, contrato, calidad y vencimiento |

Por lo tanto:

- un precio por tonelada no debe compararse sin transformación y contexto con un precio por kg o por envase;
- pesos y dólares no deben mezclarse en una misma variación sin declarar el tipo de cambio;
- un futuro, un precio de pizarra, un FOB/FAS y un índice no deben entrar en la misma serie sin una etiqueta de `tipo_precio`;
- variación mensual o anual debe calcularse sobre observaciones homogéneas, manteniendo producto, fuente, mercado, moneda, unidad y condición;
- no se debe inferir causalidad, escasez ni relación precio-cantidad entre ambas familias sólo porque sus fechas coincidan.

## 6. Propuesta de arquitectura futura

Si se incorpora, la arquitectura conceptual debería mostrar tres módulos separados:

1. **Cantidades transadas**.
2. **Precios mayoristas**.
3. **Commodities agrícolas**.

El módulo **Commodities agrícolas** podría incluir:

- selector de commodity;
- selector de fuente y mercado;
- selector de moneda y unidad, con conversión sólo cuando esté documentada;
- selector de frecuencia;
- serie temporal de precios;
- variación mensual y anual sobre series comparables;
- comparación entre commodities;
- tabla de precios recientes;
- semáforo de variaciones con umbrales definidos y explicados;
- fecha de última actualización y fecha de descarga;
- ficha metodológica visible con fuente original, condición comercial, cobertura y advertencias.

La capa de datos debería conservar el valor original y evitar sobrescribirlo con conversiones. Las conversiones y agregaciones deben ser derivadas, reproducibles y trazables a la observación original.

## 7. Modelo de datos sugerido

En una etapa posterior podría crearse el archivo `COMMODITIES_AGRICOLAS_INTEGRADO.csv` con las siguientes columnas:

| Columna | Propósito |
|---|---|
| `fecha` | Fecha de mercado, observación o cierre; definir cuál aplica |
| `año` | Año derivado de `fecha` |
| `mes` | Mes derivado de `fecha` |
| `commodity` | Producto normalizado, conservando el nombre original en observaciones si hace falta |
| `fuente` | Institución o proveedor |
| `mercado` | Mercado físico, Rosario, FOB/FAS, ROFX, Chicago, índice, etc. |
| `tipo_precio` | Pizarra, disponible, estimativo, FOB, FAS, cierre, ajuste, futuro, índice |
| `moneda` | ARS, USD u otra, según la fuente original |
| `unidad` | Tn, kg, índice base u otra unidad oficial |
| `precio` | Valor numérico en la moneda y unidad originales |
| `frecuencia` | Diaria, intradiaria, mensual, anual, etc. |
| `condicion_comercial` | Entrega, pago, calidad, puerto u otras condiciones relevantes |
| `contrato` | Símbolo o código contractual, si corresponde |
| `vencimiento` | Fecha o período de vencimiento, si corresponde |
| `fuente_url` | URL original o identificador estable |
| `fecha_actualizacion` | Fecha informada por la fuente |
| `observaciones` | Tipo de cambio usado, flags de estimación, dato faltante, versión y notas metodológicas |

Como controles mínimos, cada registro debería conservar la procedencia, la unidad original, el tipo de precio y la condición comercial. Para futuros también deberían auditarse símbolo, tamaño de contrato, vencimiento y precio de ajuste.

## 8. Recomendación inicial

1. Empezar por una fuente local argentina y por una sola convención de precio físico.
2. Priorizar BCR/Cámara Arbitral si el acceso a pizarra histórica resulta estable, autorizado y reproducible.
3. Tratar las cotizaciones FOB/FAS de BCR como una referencia distinta, con campos de puerto, embarque, moneda y condición.
4. Usar World Bank Pink Sheet sólo como referencia internacional mensual.
5. Evaluar MATba Rofex/Primary/ICE únicamente si se cuenta con acceso técnico, credenciales y autorización para el uso previsto.
6. No automatizar scraping ni redistribuir market data sin revisar estabilidad, términos de uso, licencias y restricciones.
7. Mantener commodities como módulo separado de frutas y hortalizas.
8. No mezclar commodities con frutas/hortalizas sin una nota metodológica visible sobre mercado, unidad, moneda, frecuencia y tipo de precio.

## 9. Próximos pasos sugeridos

1. Validar con el equipo qué commodities son prioritarios y qué decisión debería apoyar el módulo.
2. Confirmar la fuente oficial preferida y la convención de precio: pizarra, disponible, FOB/FAS, futuro o referencia internacional.
3. Verificar si existe descarga estructurada, API autorizada o sólo HTML/descarga manual.
4. Seleccionar una muestra histórica y auditar cobertura, faltantes, revisiones, unidades, monedas y fechas.
5. Crear un script exploratorio de descarga sólo después de elegir la fuente y aprobar sus condiciones de uso.
6. Definir reglas de normalización y conversión sin perder los valores originales.
7. Diseñar el módulo visual separado, con filtros, series, tabla reciente y ficha metodológica.
8. Documentar fecha de actualización, versión de fuente y procedimiento de reproducción antes de publicar cualquier dato.

## Decisión operativa inicial para BCR

- Se prioriza BCR/Cámara Arbitral como fuente piloto.
- Se priorizan Precios de Pizarra / Precios Cámara por su cercanía con precios locales de mercado.
- Se incluirán todos los commodities disponibles con cobertura útil, empezando por soja, maíz, trigo, girasol, sorgo y cebada si resulta consistente.
- El foco inicial será lo más actual posible.
- El módulo futuro tendrá uso analítico, no sólo informativo.
- La actualización ideal será automatizada desde el inicio cuando exista un canal autorizado y técnicamente estable.
- La automatización evitará exponer credenciales y respetará las condiciones de uso de la fuente.
- Si una API requiere autenticación, las credenciales se manejarán con variables de entorno y nunca desde el frontend.
- Si no hay API disponible, se mantendrá el fallback de descarga manual.

## Evaluación de fuentes alternativas con API

BCR/Cámara Arbitral sigue siendo la fuente local preferida para precios de pizarra. Como actualmente no se cuenta con credenciales BCR/GIX, se evaluarán alternativas automatizables sin presentarlas como equivalentes metodológicos ni como reemplazos automáticos de la pizarra local.

### SIO Granos / Secretaría de Agricultura

SIO-Granos es una plataforma argentina para informar operaciones de compraventa y publicar precios de referencia. La plataforma publica documentación de acceso y una documentación de API pública; debe verificarse qué datos están disponibles sin autenticación, qué límites aplican y si la licencia permite el uso previsto. Pasa a ser la primera alternativa local automatizable a explorar por su posible relación con operaciones, precios de referencia y un dashboard analítico argentino. Todavía no está integrada al dashboard ni se validó una respuesta real. Antes de incorporarla se deben confirmar endpoints, producto, frecuencia, condición comercial, unidad, moneda, cobertura histórica y permisos.

### World Bank Pink Sheet

El Banco Mundial ofrece archivos públicos mensuales y anuales de precios de commodities. Es una alternativa internacional estable para contexto y comparación de tendencias, pero no reemplaza una cotización local argentina ni sirve para seguimiento operativo diario. Deben conservarse serie original, unidad, moneda, versión del archivo y fecha de descarga.

### BCRA IPMP

El Índice de Precios de las Materias Primas del BCRA se publica diariamente y combina precios internacionales de materias primas relevantes para las exportaciones argentinas. Incluye, entre otros, maíz, trigo, soja y cebada, además de derivados y otras materias primas. Es útil como indicador agregado/contextual, no como precio local individual por commodity; debe mantenerse separado de precios de mercado físico.

### FAOSTAT / FAO

FAOSTAT ofrece acceso público a datos estadísticos agrícolas mediante API y descargas masivas. Puede aportar precios de productores, índices o datos agrícolas según el dominio y la cobertura, pero probablemente sea más estructural que operativo diario. Se debe validar periodicidad, país, producto, unidad, moneda y definición antes de usarlo para commodities.

### granos.ar

granos.ar expone un monitor técnico con información JSON aparentemente accesible sin una API key obligatoria y declara utilizar fuentes externas, entre ellas SIO-Granos, BCR/CAC, MATBA-ROFEX y organismos públicos. Es técnicamente cómodo para un piloto, pero no es la fuente primaria oficial y sus propios términos advierten sobre limitaciones de exactitud, actualidad e idoneidad. Sólo debe usarse como complemento no oficial después de validar estabilidad, procedencia, licencia y metodología.

No debe usarse como fuente principal para reportes institucionales sin validación previa de procedencia, licencia y estabilidad.

La comparación detallada y el catálogo de evaluación se encuentran en [data/commodities_bcr/FUENTES_API_COMMODITIES_COMPARATIVO.md](data/commodities_bcr/FUENTES_API_COMMODITIES_COMPARATIVO.md) y [data/commodities/catalogo_fuentes_commodities.csv](data/commodities/catalogo_fuentes_commodities.csv). Para SIO Granos existe únicamente un explorador técnico separado y no productivo. No se crean todavía descargadores específicos para World Bank, BCRA, FAO o granos.ar. El pipeline BCR existente se mantiene como prueba controlada separada.

## Estado de integración

En esta etapa no se modifican `app.js`, `index.html` ni `styles.css`, no se crea una pestaña de commodities y no se cargan datos externos en el navegador. El pipeline exploratorio permanece separado de frutas y hortalizas; esta documentación y los scripts sólo preparan la validación para una decisión posterior.
