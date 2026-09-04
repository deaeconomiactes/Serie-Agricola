# Exploración SIO Granos

Esta carpeta contiene una exploración local y separada de SIO Granos / Secretaría de Agricultura. El foco inicial es la consulta pública de operaciones informadas y sus posibles exportaciones, para evaluar si SIO puede aportar una alternativa automatizable de precios y operaciones de soja, maíz, trigo, girasol, sorgo y cebada.

SIO no se presume equivalente a los precios de pizarra BCR. La información debe conservar su fuente, mercado, tipo de precio, moneda, unidad, frecuencia, volumen, procedencia, precio puesto en y condiciones comerciales. No se mezcla con BCR, futuros, FOB/FAS ni precios mayoristas frutihortícolas.

## Estructura

- `raw/`: respuestas originales de exploración pública controlada o descargas manuales.
- `processed/`: CSV integrado de SIO, separado de BCR y de las fuentes frutihortícolas.
- `reports/`: auditorías de cobertura, calidad, actualidad y aptitud analítica.
- `sio_config.example.json`: configuración de referencia con URLs públicas candidatas, sin credenciales.
- `sio_config.json`: configuración local real, ignorada por Git.
- `catalogo_productos_sio.csv`: catálogo inicial; los IDs SIO quedan pendientes de validación y no se inventan.

La exploración inicial usa los últimos 30 días. Las consultas se dividen en ventanas de hasta 180 días. No se realizan llamadas externas por defecto: sólo `--allow-web` habilita una exploración pública controlada con timeout, User-Agent explícito y límite de requests.

## Flujo recomendado

1. Copiar `sio_config.example.json` como `sio_config.json` sólo si se validaron las URLs públicas que se usarán.
2. Revisar la consulta sin red:

```powershell
python .\explorar_sio_granos.py --dry-run --days-back 30 --products soja,maiz,trigo,girasol,sorgo
```

Para analizar la evidencia local de moneda sin hacer requests web:

```powershell
python .\explorar_sio_granos.py --analyze-currency
```

Este modo revisa HTML, JSON, JavaScript y CSV ya existentes, incluyendo columnas y posiciones `Row`; no hace requests web, no integra el dashboard y sirve para decidir si la muestra piloto puede avanzar a análisis.

Para extraer una muestra paginada limitada del endpoint validado:

```powershell
python .\explorar_sio_granos.py --sample-pages --allow-web --save-response --pages 3 --page-size 15 --max-requests 3
```

Este modo no es scraping masivo: limita páginas y requests, conserva el `raw` fuera del repo, no integra al dashboard y requiere auditoría antes de ampliar la extracción.

Para diagnosticar específicamente si la paginación de `GetOperaciones` es real:

```powershell
python .\explorar_sio_granos.py --test-pagination --allow-web --save-response --max-requests 3
```

Este modo usa únicamente parámetros respaldados por la evidencia local (`pPageSize` y `pCurrentPage`), registra cada payload, compara IDs/Rows y tiene un máximo efectivo de tres requests. No descarga masivamente ni integra el dashboard. Si las páginas se repiten, no ampliar la extracción: revisar `reports/REPORTE_PAGINACION_SIO.md` y observar el request real en DevTools antes de probar otra variante.

3. Si la automatización aún no está validada, generar URLs para consulta/descarga manual:

```powershell
python .\explorar_sio_granos.py --manual-urls --days-back 30 --products soja,maiz,trigo
```

4. Para una exploración pública puntual, habilitarla explícitamente y guardar sólo el diagnóstico:

```powershell
python .\explorar_sio_granos.py --allow-web --save-response --max-requests 3 --days-back 30 --products maiz
```

Para realizar descubrimiento técnico controlado de HTML, scripts, grillas y posibles endpoints:

```powershell
python .\explorar_sio_granos.py --discover-web --save-response --max-requests 5 --days-back 30 --products maiz
```

`--discover-web` busca pistas técnicas en recursos públicos explícitamente configurados, sin enviar formularios complejos, inventar parámetros, integrar datos ni hacer scraping masivo. El resultado se resume en `reports/REPORTE_DESCUBRIMIENTO_SIO.md`. Los archivos HTML, JavaScript y JSON de `raw/` son diagnósticos locales y no se commitean.

5. Colocar respuestas reales en `raw/`, ejecutar integración y auditoría:

```powershell
python .\integrar_commodities_sio.py
python .\auditar_commodities_sio.py
```

6. Revisar `reports/` antes de considerar cualquier uso analítico.

El explorador no asume el payload de SIO: inspecciona formularios, campos y enlaces de exportación HTML. Si no detecta una exportación estable, debe mantenerse el fallback manual. No generar datos ficticios, no exponer credenciales y no cargar SIO en el navegador ni en el dashboard visual.
