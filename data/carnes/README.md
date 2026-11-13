# Carnes — plataforma oficial y módulo visual

- [Documentación y metodología](../../docs/CARNES_DATA_PLATFORM.md)
- [UI: filtros, métricas, carga diferida y validación](../../docs/CARNES_UI_IMPLEMENTATION.md)
- [Inventario CSV](reports/CARNES_SOURCE_INVENTORY.csv) / [JSON](reports/CARNES_SOURCE_INVENTORY.json)
- [Estado por fuente](reports/CARNES_UPDATE_STATUS.json)
- [Validación y cantidades verificadas](reports/CARNES_VALIDATION_REPORT.json)
- [Catálogo de descargas verificadas](catalog/sources.json)
- [Candidatos no integrados](catalog/candidates.json)
- [Catálogo de precios MAG, endpoints y unidad atribuida](catalog/mag_prices.json)
- [Referencia diaria BCRA A3500](dashboard/bcra_a3500.json) y [estado de actualización](reports/BCRA_A3500_STATUS.json)
- [Fuentes, conversión y revisión de exportaciones](../../docs/CARNES_REVISION_FUENTES_2026-11-13.md)
- [Índice de datos preparados](dashboard/index.json)

RAW, NORMALIZED y ANALYTICAL permanecen fuera de Git. DASHBOARD contiene fragmentos
comprimidos y trazables, sin establecimientos/usuarios. No sumar tablas redundantes
ni familias/unidades diferentes. El workflow `update-carnes-mag.yml` actualiza sólo
las fuentes MAG y `update-carnes-bcra.yml` la referencia cambiaria de este módulo;
Caa Guazú, MCBA y Commodities mantienen sus flujos.

Los precios corrientes provienen del Mercado Agroganadero de Cañuelas desde el
17/05/2022. Los promedios diarios de seis categorías y el detalle más reciente de
precios mínimos/máximos/promedio/mediana, cabezas, importe y kilos permanecen
separados. El estado provisorio/definitivo se toma del encabezado del informe de
categorías. El I.N.M.A.G. es un índice distinto y se entrega en una familia separada.
La serie Liniers 1998–2019 continúa como histórica, sin empalme.
