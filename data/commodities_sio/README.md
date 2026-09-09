# Exploración SIO Granos

Esta carpeta contiene una exploración local y separada de SIO Granos / Secretaría de Agricultura. El foco inicial es la consulta pública de operaciones informadas y sus posibles exportaciones, para evaluar si SIO puede aportar una alternativa automatizable de precios y operaciones de soja, maíz, trigo, girasol, sorgo y cebada.

SIO no se presume equivalente a los precios de pizarra BCR. La información debe conservar su fuente, mercado, tipo de precio, moneda, unidad, frecuencia, volumen, procedencia, precio puesto en y condiciones comerciales. No se mezcla con BCR, futuros, FOB/FAS ni precios mayoristas frutihortícolas.

## Estructura

- `raw/`: respuestas originales de exploración pública controlada o descargas manuales.
- `processed/`: CSV integrado de SIO, separado de BCR y de las fuentes frutihortícolas.
- `reports/`: auditorías de cobertura, calidad, actualidad y aptitud analítica.
- `devtools/`: diagnósticos locales de HAR/cURL; sus archivos sensibles están ignorados por Git.
- `GUIA_DEVTOOLS_SIO.md`: pasos para capturar y sanear el request real de la grilla.
- `GUIA_EXPORTAR_OPERACIONES_SIO.md`: captura segura del botón Exportar Operaciones y descarga manual.
- `sio_config.example.json`: configuración de referencia con URLs públicas candidatas, sin credenciales.
- `sio_config.json`: configuración local real, ignorada por Git.
- `catalogo_productos_sio.csv`: catálogo inicial; los IDs SIO quedan pendientes de validación y no se inventan.

La exploración inicial usa los últimos 30 días. Las consultas se dividen en ventanas de hasta 180 días. No se realizan llamadas externas por defecto: sólo `--allow-web` habilita una exploración pública controlada con timeout, User-Agent explícito y límite de requests.

## Actualización diaria automática

El modo `--update-latest` consulta una sola vez por corrida el endpoint público `GetOperaciones` con el payload observado `{"pPageSize":"20","pCurrentPage":"1"}`. Es un snapshot de las últimas operaciones disponibles: no pagina, no representa un histórico completo y no reemplaza la exportación manual como evidencia histórica.

Cuando se ejecuta con `--save-response`, la respuesta se guarda localmente en `raw/` como `SIO_latest_GetOperaciones_YYYYMMDD_HHMMSS.json`; los raw quedan ignorados por Git. `integrar_commodities_sio.py` genera `processed/COMMODITIES_SIO_LATEST_SNAPSHOT.csv` y acumula nuevas operaciones, deduplicando por `id_operacion_sio` o por la clave compuesta documentada. El histórico de snapshots queda local y fuera de Git.

Luego, `auditar_commodities_sio.py` genera el reporte de actualización diaria y `preparar_commodities_dashboard.py` utiliza el histórico acumulado para regenerar sólo los CSV livianos que consume el navegador. Se excluyen precios cero y se mantienen ARS y USD separados. La cobertura histórica comienza en la fecha en que se inicia el monitoreo; para períodos anteriores se utiliza el histórico local mensual como fuente separada.

La automatización no se ejecuta desde `app.js`, no expone credenciales y no hace commits ni pushes. Para una ejecución local programada, revisar [GUIA_ACTUALIZACION_DIARIA_SIO.md](GUIA_ACTUALIZACION_DIARIA_SIO.md) y usar `scripts/update_sio_daily.ps1`.

Prueba manual controlada:

```powershell
python .\explorar_sio_granos.py --update-latest --allow-web --save-response
python .\integrar_commodities_sio.py
python .\auditar_commodities_sio.py
python .\preparar_commodities_dashboard.py
```

## Salidas procesadas

- `COMMODITIES_SIO_INTEGRADO.csv`: integración piloto principal, generada sólo a partir de respuestas base no paginadas.
- `COMMODITIES_SIO_MUESTRA_PAGINADA.csv`: muestra técnica de paginación, separada para diagnosticar requests, páginas y duplicados.

Las pruebas paginadas no deben pisar el CSV principal. Si la paginación está duplicada, la muestra técnica no es apta para dashboard y se conserva exclusivamente como evidencia de diagnóstico.

`GetOperaciones` responde, pero la prueba observada con `pCurrentPage=0/1/2` devolvió filas e IDs idénticos. La paginación no está validada y no debe ampliarse mediante ese endpoint. El siguiente camino técnico es analizar **Exportar Operaciones** o usar una descarga manual.

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

Cuando DevTools haya mostrado el payload `{"pPageSize":"20","pCurrentPage":"1"}`, validar su índice sin asumir si empieza en cero o en uno:

```powershell
python .\explorar_sio_granos.py --test-observed-pagination --allow-web --save-response --max-requests 3
```

Este modo envía únicamente `pCurrentPage=0`, `1` y `2`, siempre con `pPageSize=20`, sin filtros ni fechas. Guarda las respuestas técnicas ignoradas por Git, genera `reports/REPORTE_PAGINACION_OBSERVADA_SIO.md` y mantiene el resultado en `COMMODITIES_SIO_MUESTRA_PAGINADA.csv`, separado del CSV principal.

## Exportación manual desde SIO

El botón Exportar Operaciones puede usarse como alternativa cuando `GetOperaciones` no pagina de forma confiable. Para analizar el mecanismo, seguir [GUIA_EXPORTAR_OPERACIONES_SIO.md](GUIA_EXPORTAR_OPERACIONES_SIO.md). Si el navegador descarga un archivo manualmente, colocarlo en `raw/` con el nombre `SIO_exportar_operaciones_*.xlsx`, `.xls` o `.csv`; `raw/` no debe commitearse. Luego ejecutar:

```powershell
python .\integrar_commodities_sio.py
python .\auditar_commodities_sio.py
```

La exportación manual es válida cuando la automatización directa depende de sesión. El CSV completo se genera localmente en `COMMODITIES_SIO_EXPORTACION_MANUAL.csv`, pero no se versiona por su tamaño. Tanto el raw descargado como los processed completos quedan fuera de Git. Git conserva los scripts, reportes, resúmenes livianos y muestras pequeñas, como `COMMODITIES_SIO_EXPORTACION_MANUAL_SAMPLE.csv`, sin pisar el CSV principal ni la muestra paginada.

Los registros con precio cero se conservan para trazabilidad, pero no deben usarse en series de precios, promedios, rankings ni semáforos. El campo `precio_valido_para_serie` indica qué registros pueden usarse para análisis de precios.

## Base analítica de precios

La base completa de operaciones conserva todos los registros de la exportación manual, incluidos precios cero, faltantes y filas con moneda o unidad sin especificar. La base `COMMODITIES_SIO_ANALITICO_PRECIOS.csv` aplica el filtro metodológico y conserva sólo registros con precio positivo, fecha válida, commodity, fuente, moneda explícita y unidad explícita.

Los precios cero no se borran de la base completa: sólo se excluyen de la base analítica y de sus series, promedios, rankings y semáforos. La base analítica alimenta la preparación del módulo visual mediante agregados livianos; no se carga directamente en el navegador. ARS y USD deben graficarse por separado, junto con commodity, unidad, tipo de precio y condición comercial.

Por su tamaño, la base analítica completa se genera localmente y queda fuera de Git cuando supera el límite razonable. Se conserva una muestra liviana en `processed/COMMODITIES_SIO_ANALITICO_PRECIOS_SAMPLE.csv` y resúmenes agregados en `reports/`. No se mezclan SIO con BCR ni con frutas/hortalizas.

## Dashboard

El módulo visual de commodities usa únicamente los archivos agregados livianos de `dashboard/`: series diarias, series mensuales, últimos precios, resumen general y semáforo mensual. No carga en el navegador `COMMODITIES_SIO_EXPORTACION_MANUAL.csv` ni `COMMODITIES_SIO_ANALITICO_PRECIOS.csv`.

La base completa permanece local y fuera de Git; los precios cero, faltantes y registros no aptos se excluyen antes de generar los agregados. ARS y USD se mantienen separados por commodity, unidad y tipo de precio. El dashboard permite seleccionar hasta tres commodities para comparación simultánea. SIO Granos corresponde a operaciones informadas y no equivale a BCR.

## Cobertura histórica por tramos

La consulta pública observada de SIO Granos no permite solicitar rangos superiores a 180 días. Por lo tanto, una ampliación histórica debe realizarse mediante ventanas consecutivas de hasta 180 días; no debe asumirse que una sola exportación cubre un año completo ni que todos los años anteriores están disponibles.

Cada tramo debe conservar su archivo original, fecha solicitada, fecha mínima y máxima efectivamente recibida, cantidad de filas, commodities, monedas, unidades, operaciones y advertencias. Antes de unir tramos se debe auditar cada ventana, deduplicar por `id_operacion_sio` o por una clave compuesta documentada y conservar los conflictos para revisión. No se debe automatizar scraping masivo ni publicar la ampliación en el dashboard hasta validar continuidad temporal y comparabilidad.

La estrategia detallada está documentada en [PLAN_HISTORICO_SIO_POR_TRAMOS.md](reports/PLAN_HISTORICO_SIO_POR_TRAMOS.md). La cobertura actualmente visible se resume en [REPORTE_COBERTURA_TEMPORAL_SIO.md](reports/REPORTE_COBERTURA_TEMPORAL_SIO.md).

Para regenerar las salidas dashboard-ready después de actualizar la base analítica:

```powershell
python .\preparar_commodities_dashboard.py
```

La fuente completa es la opción normal. Si no está disponible, el script usa la muestra analítica sólo como fallback y lo advierte; ese resultado no debe interpretarse como una serie completa.

Para analizar una captura local de DevTools sin hacer llamadas web, seguir [GUIA_DEVTOOLS_SIO.md](GUIA_DEVTOOLS_SIO.md):

```powershell
python .\explorar_sio_granos.py --analyze-har data\commodities_sio\devtools\sio_paginacion.har
python .\explorar_sio_granos.py --analyze-curl data\commodities_sio\devtools\getoperaciones_page2.curl
```

Estos modos sólo analizan archivos locales, no ejecutan cURL ni consultan la red. Sirven para identificar el payload real de paginación y generan un reporte sanitizado. Los HAR/cURL reales no deben commitearse porque pueden contener cookies, tokens o headers de sesión.

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
