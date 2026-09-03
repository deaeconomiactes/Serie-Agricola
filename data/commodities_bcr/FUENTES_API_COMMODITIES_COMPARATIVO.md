# Comparativo de fuentes API para commodities agrícolas

## Objetivo

Evaluar fuentes automatizables para commodities agrícolas mientras BCR/Cámara Arbitral sigue siendo la referencia local preferida, pero no se dispone de credenciales BCR/GIX. Este documento orienta la selección de una única fuente alternativa para un futuro piloto; no implementa descargas.

## Criterios de evaluación

- oficialidad y responsabilidad de publicación;
- relación con el mercado argentino;
- productos disponibles;
- frecuencia y fecha de actualización;
- cobertura histórica;
- unidad y moneda;
- facilidad de automatización;
- necesidad de credenciales;
- estabilidad esperada;
- riesgo legal/licencia y redistribución;
- utilidad para un dashboard analítico.

## Tabla comparativa

| Fuente | Tipo de fuente | Productos | Frecuencia | Unidad/moneda | Acceso | Credenciales | Ventajas | Limitaciones | Recomendación |
|---|---|---|---|---|---|---|---|---|---|
| BCR / Cámara Arbitral | Local oficial; precio de pizarra | Soja, maíz, trigo, girasol, sorgo, cebada y otros según cobertura | Potencialmente diaria | Según publicación; validar $/Tn y ARS/USD | Consulta y descarga manual; API/GIX a confirmar | API puede requerir credenciales | Mayor cercanía con mercado físico argentino y referencia de pizarra | Sin credenciales actuales; condiciones de uso y estructura deben confirmarse | Mantener como fuente preferida; usar manual hasta contar con acceso estable |
| SIO Granos | Local institucional; operaciones y precios de referencia | Granos y oleaginosas según operación/cobertura | Operativa/diaria, validar | La publicación puede unificar condiciones; validar unidad y moneda | Plataforma y documentación de API pública | Evaluar según recurso | Alternativa local prioritaria y potencialmente analítica | Deben validarse API, cobertura, permisos, condición y definición de precio | Primera alternativa a investigar |
| World Bank Pink Sheet | Internacional oficial; precios de commodities | Granos, oleaginosas, aceites, energía y metales según serie | Mensual y anual | Principalmente USD con unidad propia de cada serie | Descarga pública XLS | No aparente para descarga | Estable, histórica y reproducible | No es precio argentino ni seguimiento diario; no mezclar con pizarra | Usar para contexto internacional mensual |
| BCRA IPMP | Índice institucional argentino basado en mercados internacionales | Maíz, trigo, soja, cebada, derivados y otras materias primas | Diaria | Índice agregado; metodología y base propias | Página BCRA y serie histórica XLSX | No aparente para descarga | Contexto exportador argentino y actualización diaria | No es precio local por commodity; no es una serie spot comparable | Usar como indicador contextual separado |
| FAOSTAT / FAO | Estadística internacional oficial | Productos agrícolas según dominio | Anual/mensual según dominio | Depende del dominio y definición | API pública y descarga masiva | No aparente para acceso básico | Cobertura internacional y documentación estadística | Puede ser productor/índice/estadística, no cotización operativa diaria | Usar para contexto estructural tras validar dominio |
| granos.ar | Terceros; agregador no oficial | Soja, maíz, trigo, girasol, sorgo, cebada según monitor | Aparente actualización operativa; validar | Puede mostrar USD/Tn y cálculos derivados; validar metodología | JSON público aparentemente sin key obligatoria | No aparente, pero confirmar | Cómodo para piloto técnico y visualización exploratoria | No es fuente primaria; depende de terceros, licencia y estabilidad | Sólo piloto técnico/complemento no oficial |

## Ranking preliminar

1. SIO Granos, si la API pública permite datos suficientes, trazables y reutilizables.
2. BCR manual/API, si se consiguen credenciales o descargas estables.
3. World Bank Pink Sheet para contexto internacional mensual.
4. BCRA IPMP para indicador agregado contextual.
5. FAOSTAT/FAO para contexto estadístico.
6. granos.ar sólo como piloto técnico no oficial.

## Recomendación metodológica

- No mezclar fuentes con distinta unidad, moneda, frecuencia o tipo de precio.
- Mantener siempre `fuente`, `mercado`, `tipo_precio`, `moneda`, `unidad` y `frecuencia`.
- Separar precio local, precio internacional, índice y futuro.
- No presentar una fuente no oficial como dato oficial.
- Conservar URL, fecha de descarga, versión, metodología y condiciones de uso.
- No transformar USD/tonelada a ARS/tonelada sin conservar tipo de cambio, fecha y regla de conversión.
- No mezclar commodities con frutas/hortalizas ni con los CSV existentes del dashboard.

## Fuentes revisadas

- [BCR/Cámara Arbitral — consultas de precios de pizarra](https://www.cac.bcr.com.ar/es/precios-de-pizarra/consultas)
- [SIO Granos](https://www.siogranos.com.ar/)
- [SIO Granos — consulta pública](https://www.siogranos.com.ar/consulta_publica/)
- [World Bank — Commodity Markets / Pink Sheet](https://www.worldbank.org/en/research/commodity-markets)
- [BCRA — Precios de Materias Primas / IPMP](https://www.bcra.gob.ar/precios-de-materias-primas/)
- [FAOSTAT](https://www.fao.org/Faostat/en/) y [FAO — Prices](https://www.fao.org/prices/en)
- [granos.ar](https://granos.ar/)

Las fuentes alternativas sólo están documentadas. No se crean todavía scripts de descarga ni se realizan llamadas automáticas.
