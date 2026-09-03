# Guía de descarga BCR / Cámara Arbitral

## Próximo paso operativo

Realizar una prueba manual desde la consulta oficial de Precios de Pizarra / Precios Cámara para:

- soja;
- maíz;
- trigo;
- girasol;
- sorgo.

Usar inicialmente los últimos 30 días o, si la cobertura diaria es escasa, los últimos 3 meses. Guardar los archivos en `data/commodities_bcr/raw/`.

Nombres sugeridos:

```text
BCR_pizarra_soja_ultimos_3_meses.xlsx
BCR_pizarra_maiz_ultimos_3_meses.xlsx
BCR_pizarra_trigo_ultimos_3_meses.xlsx
BCR_pizarra_girasol_ultimos_3_meses.xlsx
BCR_pizarra_sorgo_ultimos_3_meses.xlsx
```

El nombre es orientativo: se conserva el archivo original y el integrador intenta leer también CSV o JSON estructurado.

## Revisión antes de copiar

Confirmar que cada descarga indique, o permita documentar, fecha de mercado, commodity, tipo de precio, valor, moneda, unidad, mercado/condición y fuente original. No mezclar pizarra, FOB/FAS, futuros o índices en una misma serie.

Si la descarga ofrece una conversión a dólares, conservar la moneda y regla de conversión informadas por BCR; no recalcular ni reemplazar el valor original sin trazabilidad.

## Ejecución local

Sin API, el diagnóstico es seguro y no hace llamadas de red:

```powershell
python .\descargar_commodities_bcr.py --dry-run --days-back 30
python .\integrar_commodities_bcr.py
python .\auditar_commodities_bcr.py
```

La automatización sólo se habilita con un endpoint y configuración autorizados en `.env`. Nunca colocar credenciales en `app.js`, HTML, CSS, el catálogo ni archivos versionados.

## Fuente y permisos

Revisar las condiciones de uso de BCR/Cámara Arbitral antes de automatizar o redistribuir datos. Si no existe API estable o autorización suficiente, mantener el fallback de descarga manual y registrar fecha de descarga y procedencia.
