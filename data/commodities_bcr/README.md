# Commodities agrícolas BCR

Pipeline exploratorio separado de cantidades y precios mayoristas frutihortícolas. En esta etapa no existe integración visual: no se modifican `app.js`, `index.html` ni `styles.css` y no se cargan datos de commodities en el navegador.

## Decisión operativa

- Fuente piloto: BCR / Cámara Arbitral de Cereales.
- Precio prioritario: Precios de Pizarra / Precios Cámara.
- Productos: todos los commodities con cobertura útil; el catálogo inicial prioriza soja, maíz, trigo, girasol, sorgo y cebada.
- Período: lo más actual posible.
- Uso futuro: analítico.
- Actualización: automatizada cuando sea técnicamente viable y autorizada; descarga manual como fallback.

## Estructura

- `raw/`: archivos originales descargados manualmente o por un proceso autorizado.
- `processed/`: CSV normalizado, reproducible y separado del dashboard.
- `reports/`: auditorías de cobertura, calidad y actualidad.
- `catalogo_commodities_bcr.csv`: nombres, alias, prioridad e identificadores BCR confirmados.
- `API_BCR_PLAN.md`: estrategia de automatización segura.

## Flujo operativo

1. Si se cuenta con acceso autorizado, copiar `.env.example` como `.env` y completar sólo localmente las variables necesarias.
2. Ejecutar el diagnóstico sin descargar:

   ```powershell
   python .\descargar_commodities_bcr.py --dry-run --days-back 30
   ```

3. Si no hay API, descargar manualmente desde BCR/Cámara Arbitral y colocar los archivos en `raw/`.
4. Integrar:

   ```powershell
   python .\integrar_commodities_bcr.py
   ```

5. Auditar:

   ```powershell
   python .\auditar_commodities_bcr.py
   ```

6. Revisar los reportes y sólo después decidir si corresponde diseñar el módulo visual.

Con `raw/` vacío, integración y auditoría terminan correctamente y explican el próximo paso; no se generan reportes vacíos que parezcan datos válidos.

## Primer ensayo manual recomendado

Descargar desde BCR/Cámara Arbitral archivos de prueba para soja, maíz, trigo, girasol y sorgo, preferentemente de los últimos 30 días o los últimos 3 meses. Guardarlos en `raw/` con nombres como:

```text
BCR_pizarra_soja_ultimos_3_meses.xlsx
BCR_pizarra_maiz_ultimos_3_meses.xlsx
BCR_pizarra_trigo_ultimos_3_meses.xlsx
BCR_pizarra_girasol_ultimos_3_meses.xlsx
BCR_pizarra_sorgo_ultimos_3_meses.xlsx
```

Antes de analizar, verificar fuente, tipo de precio, moneda, unidad, frecuencia, fecha máxima y condiciones de uso. Los archivos de plantilla o simulación sólo sirven para probar el pipeline.
