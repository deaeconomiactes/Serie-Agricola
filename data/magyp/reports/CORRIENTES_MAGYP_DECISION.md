# Corrientes MAGyP — decisión de integración

Comprobación acotada del 06/10/2026, rama `codex/magyp-data-platform-mcba`, HEAD `9452166`. El estado inicial estaba limpio; la integración MCBA aceptada y todos los archivos existentes se preservaron.

**Clasificación: D — NO_UTILIZABLE actualmente para esta integración.**
El enlace institucional confirmado no permite recuperar datos. No se clasifica C: no se recuperó una publicación fechada que demuestre desactualización. Tampoco se afirma ausencia universal de fuentes correntinas.

1. **Fuente encontrada:** los índices oficiales MAGyP de [frutas](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/frutas/index.php) y [hortalizas](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/hortalizas/) enlazan a `http://www.mptt.gov.ar/site13/index.php/preciosmercado`. Es una referencia al proveedor provincial; no una API alojada en MAGyP. El portal actual no expuso un enlace Corrientes en su HTML examinado.
2. **Última publicación MAGyP/proveedor:** no verificable. El título del enlace y el año del portal no prueban fecha de las cotizaciones. Última observación válida de la **base actual local**: 25/08/2026; archivo origen `MARTIN MICELLI 26-08-2026.xlsx`. La fecha del nombre del archivo no se usa como fecha de precios.
3. **Frecuencia:** el índice de frutas denomina el enlace “Precios Diarios”; periodicidad efectiva no comprobable. La base actual tiene registros fechados en 400 fechas, entre 29/12/2024 y 25/08/2026; fecha_precision no informada en esas filas. El frontend mantiene su interpretación y agregaciones existentes.
4. **Granularidad:** campos MAGyP/proveedor no recuperados; no se inventan dimensiones. Legacy tiene fecha, rubro, especie, procedencia, localidad, envase, peso de bulto y precios/unidades originales y derivados. Entre registros válidos no futuros: 171 etiquetas de especie, 19 procedencias/localidades y 69 envases; variedad vacía. Calidad/tamaño/grado no se incorporan por no haber evidencia.
5. **Adquisición automatizable:** **no validada ni utilizable actualmente**. Se hicieron 5 GET controlados: tres páginas MAGyP HTTP 200; destino provincial HTTP y HTTPS con error DNS `gaierror`. Límite 500 KB por respuesta, timeout 15 segundos, sin retry, navegador, sesión, descarga histórica ni enumeración de endpoints. La comprobación se puede repetir, pero eso no constituye un pipeline de cotizaciones.
6. **Comparación:** imposible comparar fechas/precios/unidades/presentaciones entre fuentes: cero cotizaciones recuperadas de la ruta MAGyP. Se registró únicamente la referencia local: 46.587 filas Corrientes, 46.413 con precio observado positivo y fecha válida no futura; 46.409 comparables por kg según campos existentes. Se contabilizan por separado 115 fechas futuras, 3 inválidas y 56 precios no positivos/parseables. Nada se deduplicó ni corrigió.
7. **Reemplazo:** ninguno justificado. `CTES.` en MCBA es procedencia y no una cotización del Mercado de Corrientes; no se utiliza como sustituto ni relleno.
8. **Legacy:** se mantiene **como fuente principal actual**, además de respaldo histórico para una transición futura. Unidad original observada `$/bulto`; precios por kg continúan siendo conversiones existentes por peso del envase. Columna moneda vacía: no se agrega automáticamente ARS ni se redefine la unidad. Se preservan base, Excel y series.
9. **Integración realizada:** diagnóstico reproducible, evidencia de solicitudes y decisión documentada. No se cambiaron app.js, index.html, estilos, CSV productivos ni configuración; no se creó CSV MAGyP vacío ni workflow productivo sin fuente viable. Filtros, KPIs, evolución, rankings, semáforo y tablas permanecen intactos.
10. **Verificaciones:** cinco tests offline específicos del diagnóstico (clasificación, límites de URL, exclusión de estado privado, lectura conservadora de legacy y dry-run). Verificación SHA-256 de 268 archivos preexistentes, incluidos MCBA RAW/NORMALIZED/ANALYTICAL, frontend, bases y demás pipelines. No hubo cambios de comportamiento que requieran rehacer el navegador MCBA.
11. **Bloqueo real:** obtener del proveedor provincial el enlace vigente o una exportación oficial fechada accesible y su definición de precio/unidad. Con esa evidencia se podrá decidir principal/complementaria, comparar una ventana común y preparar el pipeline con las garantías existentes. No se activa cron.

## Archivos y reproducción

- `scripts/magyp/investigate_corrientes.py`: diagnóstico; por defecto dry-run sin red ni escrituras.
- `CORRIENTES_MAGYP_SOURCE_CHECK.json`: requests públicos, resultado y referencia local.
- `CORRIENTES_MAGYP_PRESERVATION.json`: resultado de preservación de archivos.

```powershell
python scripts/magyp/investigate_corrientes.py --allow-web --as-of 2026-10-06
python -m unittest discover -s tests/magyp_common -p test_corrientes_investigation.py -v
```

No se hicieron commit, push, merge ni deploy. No se modificaron MCBA, Commodities, SIO, FOB, Cantidades ni Carnes.
