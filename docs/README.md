# Documentación Serie Agrícola

Este índice distingue contratos vigentes de informes fechados: los últimos describen el estado observado en su corte y no sustituyen la operación actual.

## Arquitectura

- [Arquitectura MAGyP](MAGYP_DATA_ARCHITECTURE.md), [diccionario de campos](MAGYP_SCHEMA_DICTIONARY.md) y [dependencias e inventario](DEPENDENCIAS_E_INVENTARIO.md).
- [Frescura y estados](PRICE_FRESHNESS.md).

## Política de fuentes

- [Política de datos](DATA_SOURCE_POLICY.md) y [fuentes de commodities](../FUENTES_COMMODITIES_AGRICOLAS.md).

## Precios mayoristas

- [Fragmentos y construcción](MAYORISTAS_FRAGMENTED_OUTPUTS.md), [MCBA diario](MCBA_DASHBOARD_INTEGRATION.md), [mensual derivado](MCBA_MERCADO_CENTRAL_MONTHLY.md) y [cobertura histórica](MCBA_HISTORICAL_COVERAGE.md).

## Commodities

- [Familias MAGyP](MAGYP_COMMODITIES.md), [historia](MAGYP_COMMODITIES_HISTORY.md), [cutover](COMMODITIES_CUTOVER.md) y [catálogo](../data/commodities/README.md).
- [BCR](../data/commodities_bcr/README.md), [precios locales mensuales](../data/commodities_local_mensual/README.md) y [World Bank](../data/commodities_worldbank/README.md).

## SIO

- [Pipeline y guías](../data/commodities_sio/README.md), [actualización diaria](../data/commodities_sio/GUIA_ACTUALIZACION_DIARIA_SIO.md) y [grano transaccional](SIO_TRANSACTIONAL_GRAIN.md).

## Carnes

- [Plataforma y fuentes](CARNES_DATA_PLATFORM.md), [interfaz](CARNES_UI_IMPLEMENTATION.md) y [datos](../data/carnes/README.md).

## Cantidades

- [Sistema visual y límites](CANTIDADES_UI_DESIGN_SYSTEM.md); la metodología visible en el módulo describe la base estática 2024–2025.

## Operación y workflows

- [Inventario operativo actual](OPERACION_WORKFLOWS.md), [validación local](reports/VALIDACION_FASE2.md) y [paquete Pages](reports/PAGES_BUILD.md); [auditoría operativa fechada](WORKFLOWS_AUDITORIA_OPERATIVA.md); [política MCBA](MCBA_PRODUCTION_POLICY.md).

## Design system

- [Sistema institucional](SERIE_AGRICOLA_DESIGN_SYSTEM.md), [Mayoristas](MAYORISTAS_UI_DESIGN_SYSTEM.md), [Commodities](COMMODITIES_UI_DESIGN_SYSTEM.md) y [Cantidades](CANTIDADES_UI_DESIGN_SYSTEM.md).

## Auditorías históricas

Los documentos de `audit/`, las verificaciones visuales y los informes de cierre o pilotos conservan evidencia del momento de su elaboración. Los textos que mencionan ramas, propuestas o fechas anteriores deben leerse como históricos; consultar la operación actual para horarios y workflows.

- [Auditoría institucional](DASHBOARD_INSTITUTIONAL_AUDIT.md), [cierre Mayoristas](MAYORISTAS_CIERRE_VALIDACION_2026-10-24.md) y [evidencia de navegador](audit/2026-10-22/).
- [Manifiesto de consolidación](REPO_CLEANUP_MANIFEST.json).
