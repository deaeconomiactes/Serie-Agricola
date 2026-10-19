# MCBA initial_get: diagnóstico y retry acotado

## Causa observada en GitHub/Linux

El artefacto `mcba-update-diagnostics` del [run productivo 39257829299](https://github.com/deaeconomiactes/Serie-Agricola/actions/runs/39257829299), ejecutado el 2026-10-19, registra `stage=initial_get` y un único GET con **HTTP 403** al endpoint estable `https://ssma.magyp.gob.ar/frutas.precios.aspx`. Solicitó el día `2026-10-05`. No es un timeout ni un error XLSX: el acceso inicial fue rechazado. El artefacto anterior no permite identificar la regla interna que originó ese 403; no se atribuye sin evidencia a un proveedor WAF o bloqueo de IP específico.

El [smoke verde 39254408212](https://github.com/deaeconomiactes/Serie-Agricola/actions/runs/39254408212) instaló dependencias/Chromium y pasó tests offline. Su step `Una captura opcional, fuera del checkout` quedó **skipped**. No navegó al endpoint para adquirir datos reales, por lo que no acredita acceso desde el runner ni equivale a la captura productiva.

## Cambio exclusivo de adquisición

Cada intento de initial GET registra en logs y diagnostics: `acquisition_stage`, `error_type`, `http_status` si existe, `final_url` sanitizada, `duration_seconds`, `request_count`, motor/canal y `requested_date`. Se conserva el historial `initial_get_attempts` y `retry_performed`; los consumidores existentes ya guardan esos diagnostics en los artifacts de error. El registro no incluye texto libre de excepciones, cuerpos HTTP, cookies, headers de autorización, valores GXState ni identificadores de sesión. Se eliminó la lectura de cookies del adaptador.

Sólo se conserva la URL estable conocida; queries, credenciales y paths inesperados/temporales se redactan. Los códigos de red se inspeccionan en memoria para emitir categorías cerradas: TIMEOUT, CONNECTION, DNS, NAVIGATION_ABORTED, UNEXPECTED_REDIRECT, HTTP_nnn, HTTP_5XX, NAVIGATION_NO_RESPONSE u OTHER. Los estados desconocidos no se convierten en transitorios.

Ante HTTP 401/403 en GitHub Actions: **GITHUB_RUNNER_ACCESS_BLOCKED**, sin retry, sin bypass. Mantiene navegador/UA, allowlist, HTTPS y validaciones existentes. No se rotan IPs, proxies ni identificaciones.

Sólo TIMEOUT, CONNECTION o HTTP 5xx en initial_get permiten **un** retry: finalizar contexto/browser anteriores, esperar **10 segundos** y crear una sesión limpia. No se repite filtrado, exportación ni descarga si fallan después del GET. Se conserva el presupuesto total de requests entre ambos intentos. No hay retry para 401/403/404/429, DNS, navegación abortada, redirect inesperado, respuesta no reconocida o schema inesperado. Un segundo fallo termina con error visible.

No cambia frontend, parser XLSX, normalización, analytical, publicación/Git, deploy, Commodities ni Corrientes. El actualizador sigue preservando los CSV y registrando MAGYP_LAST_VALID cuando falla la adquisición. El 403 real continúa bloqueando nuevas capturas hasta que el origen permita acceso autorizado al runner; el fix no pretende superarlo mediante retry.

## Pruebas

Mocks del protocolo real del adaptador verifican GET 200, timeout/conexión/500 seguidos de éxito, orden cierre → espera → nueva sesión, segundo fallo sin tercer intento, presupuesto global, 401/403 sin retry, 404/429, DNS, navegación abortada, redirect/schema inesperados y redacción de datos privados. El test integrado 403 confirma CSV idénticos, MAGYP_LAST_VALID y diagnóstico persistido. La prueba anterior de limpieza del motor se conserva con navegación abortada; los timeouts tienen ahora casos específicos de dos sesiones.

No se hicieron nuevos requests al sitio MCBA para eludir/reprobar el bloqueo. La causa se obtuvo del artefacto real de Actions. Una prueba mock satisfactoria no equivale a adquisición real Linux exitosa.
