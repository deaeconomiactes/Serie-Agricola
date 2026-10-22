# Carnes — plataforma oficial, sin frontend definitivo

- [Documentación y metodología](../../docs/CARNES_DATA_PLATFORM.md)
- [Inventario CSV](reports/CARNES_SOURCE_INVENTORY.csv) / [JSON](reports/CARNES_SOURCE_INVENTORY.json)
- [Estado por fuente](reports/CARNES_UPDATE_STATUS.json)
- [Validación y cantidades verificadas](reports/CARNES_VALIDATION_REPORT.json)
- [Catálogo de descargas verificadas](catalog/sources.json)
- [Candidatos no integrados](catalog/candidates.json)
- [Índice de datos preparados](dashboard/index.json)

RAW, NORMALIZED y ANALYTICAL permanecen fuera de Git. DASHBOARD contiene fragmentos
comprimidos y trazables, sin establecimientos/usuarios. No sumar tablas redundantes
ni familias/unidades diferentes. No hay cron ni cambios a otros módulos.
