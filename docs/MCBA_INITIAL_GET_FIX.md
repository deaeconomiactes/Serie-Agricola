# MCBA initial_get: diagnóstico y retry acotado

## Causa observada en GitHub/Linux

El artefacto `mcba-update-diagnostics` del [run productivo 39257829299](https://github.com/deaeconomiactes/Serie-Agricola/actions/runs/39257829299), ejecutado el 2026-10-19, registra `stage=initial_get` y un único GET con **HTTP 403** al endpoint estable `https://ssma.magyp.gob.ar/frutas.precios.aspx`. Solicitó el día `2026-10-05`. No es un timeout ni un error XLSX: el acceso inicial fue rechazado. El artefacto anterior no permite identificar la regla interna que originó ese 403; no se atribuye sin evidencia a un proveedor WAF o bloqueo de IP específico.

El [smoke verde 39254408212](https://github.com/deaeconomiactes/Serie-Agricola/actions/runs/39254408212) instaló dependencias/Chromium y pasó tests offline. Su step `Una captura opcional, fuera del checkout` quedó **skipped**. No navegó al endpoint para adquirir datos reales, por lo que no acredita acceso desde el runner ni equivale a la captura productiva.

## Cambio exclusivo de adquisición

Cada intento de initial GET registra en logs y diagnostics: `acquisition_stage`, `error_type`, `http_status` si existe, `final_url` sanitizada, `duration_seconds`, `request_count`, motor/canal y `requested_date`. Se conserva el historial `initial_get_attempts` y `retry_performed`; los consumidores existentes ya guardan esos diagnostics en los artifacts de error. El registro no incluye texto libre de excepciones, cuerpos HTTP, cookies, headers de autorización, valores GXState ni identificadores de sesión. Se eliminó la lectura de cookies del adaptador.

Sólo se conserva la URL estable conocida; queries, credenciales y paths inesperados/temporales se redactan. Los códigos de red se inspeccionan en memoria para emitir categorías cerradas: TIMEOUT, CONNECTION, DNS, NAVIGATION_ABORTED, UNEXPECTED_REDIRECT, HTTP_nnn, HTTP_5XX, NAVIGATION_NO_RESPONSE u OTHER. Los estados desconocidos no se convierten en transitorios.

Ante HTTP 401/403 en GitHub Actions: **GITHUB_RUNNER_ACCESS_BLOCKED**, sin retry, sin bypass. Mantiene navegador/UA, allowlist, HTTPS y validaciones existentes. No se rotan IPs, proxies ni identificaciones.

La política actual opera sobre la **adquisición completa**, desde initial_get hasta descarga del XLSX. Permite **hasta 3 intentos por fecha**, sin retries internos adicionales. Cada intento cierra contexto y browser antes de esperar **10 segundos** y abrir una sesión limpia. Se espera que el control de fechas GeneXus esté visible antes de usarlo. Cada intento completo tiene su propio presupuesto de requests (80 en producción, hasta 240 en tres intentos); se registra también el total. Una sesión que agota su presupuesto no se reintenta.

Sólo se reintentan TIMEOUT en initial_get, date_controls (incluida la espera de respuesta al aplicar fechas) o export_download, CONNECTION y HTTP 5xx. No hay retry para 401/403/404/429, DNS, navegación abortada, redirect inesperado, schema/XLSX inválido ni fecha incorrecta. El timeout verificando las fechas devueltas en filtered_grid tampoco se trata como transitorio: no se presupone que una grilla fuera de rango sea correcta.

Cada intento emite un registro seguro `acquisition_attempts`: attempt, acquisition_stage, error_type, duration_seconds, http_status (null sin respuesta de esa etapa), request_count del intento y requested_date. El éxito queda marcado como completed; se conserva además initial_get_attempts para compatibilidad y el request_count total. Los fallos HTTP durante filtro/export se clasifican por su status, sin convertir un 403 en timeout reintentable. Un éxito continúa con el pipeline existente; agotados los tres intentos se propaga el error y MAGYP_LAST_VALID conserva las salidas anteriores.

No cambia frontend, parser XLSX, normalización, analytical, publicación/Git, deploy, Commodities ni Corrientes. El actualizador sigue preservando los CSV y registrando MAGYP_LAST_VALID cuando falla la adquisición. El 403 real continúa bloqueando nuevas capturas hasta que el origen permita acceso autorizado al runner; el fix no pretende superarlo mediante retry.

## Pruebas

Mocks del protocolo real verifican initial_get timeout/conexión/500 seguido de éxito, date_controls y export/download timeout seguidos de éxito con nueva sesión, tercer intento exitoso y tres fallos sin cuarto intento. Comprueban cierre → espera → nueva sesión, presupuesto por sesión, registros por intento y redacción de datos privados. Casos de 401/403/404/429, DNS, navegación abortada, redirect/schema/XLSX inválidos y fecha incorrecta no reintentan. Pruebas integradas de tres timeouts, 403 y XLSX inválido confirman CSV idénticos y MAGYP_LAST_VALID.

No se hicieron nuevos requests al sitio MCBA para eludir/reprobar el bloqueo. La causa se obtuvo del artefacto real de Actions. Una prueba mock satisfactoria no equivale a adquisición real Linux exitosa.
