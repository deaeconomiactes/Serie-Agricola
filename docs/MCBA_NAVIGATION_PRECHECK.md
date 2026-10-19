# MCBA: comparacion de ejecuciones y precheck

## Comparacion verificada

- Exito real Actions: run 39273415979, commit 85107bf, 2026-10-19 15:02 UTC, 370 filas para 2026-10-05, primer intento.
- Fallo real Actions: run 39302176543, commit 0650c1f (merge del mismo cambio), 2026-10-19 18:28-18:32 UTC, tres initial_get TIMEOUT, sin status, una request por intento.
- Main inspeccionado: e98ceae. Git diff contra 85107bf no tiene diferencias en acquisition.py, fetch_mcba.py, update_mcba_dashboard.py ni update-magyp-mcba.yml. Los cambios de main son merge y estado de datos.

| Elemento | Exito / fallo |
| --- | --- |
| Comando | python scripts/magyp/mcba/update_mcba_dashboard.py --date "$env:MCBA_DATE" --data-root "$env:MCBA_CAPTURE_ROOT" --allow-web --browser-channel "$env:MCBA_BROWSER_CHANNEL" |
| Fecha / canal | 2026-10-05 / msedge en ambos |
| Lanzamiento | headless=True, channel=msedge; sin argumentos extra |
| Navegacion / timeout | domcontentloaded / 60000 ms en ambos |
| User agent | navigator.userAgent nativo + SerieAgricola-MAGyP-MCBA-Pilot/2.0; misma regla, sin ocultar motor |
| Recursos | aborta image/font/media; permite CSS y JavaScript oficiales en ambos |
| Entorno | mismos nombres y reglas TEMP, TMP, MCBA_JOB_ROOT, MCBA_CAPTURE_ROOT, PLAYWRIGHT_BROWSERS_PATH; cambia el ID de ejecucion en la ruta |
| Temporales | C:/actions-runner/actions-runner/_work/_temp/mcba-<run>-1; contexto no persistente |
| Ejecucion | Ambos GitHub Actions, mismo runner DESKTOP-MHFH88Q, grupo Default, runner 2.337.0 |
| Cuenta Windows | Logs historicos no la registraron. Listener actual PID 13840: DESKTOP-MHFH88Q/acer, iniciado 2026-10-19T14:08:57Z, antes de ambas corridas. Es evidencia de continuidad del listener; la cuenta historica del proceso hijo no fue registrada directamente |

No se atribuye el fallo a una regresion de configuracion que no existe en Git. La version binaria historica de Edge y las condiciones externas de conectividad no quedaron registradas y no se inventan.

## Cambio acotado

Un solo GET publico desde el propio proceso de adquisicion, antes de Playwright, sin cookies, persistencia, redirects ni cuerpos guardados. Diagnostico restringido a DNS, conexion TCP, TLS/HTTPS, HTTP status y duracion. Solo un HTTP 401/403/404 explicito impide abrir el navegador. Timeout, fallo de conexion/DNS o ausencia de status se registran como PRECHECK_INCONCLUSIVE y permiten continuar; 5xx se registra PRECHECK_TRANSIENT y tambien permite continuar. HTTP 200 queda PRECHECK_OK. El XLSX validado por Edge sigue siendo la unica evidencia de adquisicion exitosa. No suma reintentos ni modifica los timeouts existentes.

Con precheck no bloqueante, goto espera commit (respuesta del documento) y la disponibilidad funcional sigue dependiendo de esperas explicitas de GeneXus. No espera load ni networkidle. Despues del goto registra solamente status, readyState, URL sanitizada, existencia de controles Desde/Hasta y conteo de requests. Se mantiene la allowlist y el parser de XLSX sin modificaciones; HTTP 200 no es exito de adquisicion.

Se registra ademas la cuenta Windows/canal/contexto de la ejecucion nueva, sin credenciales ni valores de sesion. Los tests del protocolo existente simulan el precheck para seguir siendo offline.

## Verificacion real del candidato

Run real del candidato: https://github.com/deaeconomiactes/Serie-Agricola/actions/runs/39307494652, commit 59e1b95, cuenta acer, runner DESKTOP-MHFH88Q, fecha solicitada 2026-10-05.

A las 19:08:38 UTC el precheck registro:

```json
{"dns_resolves":true,"tcp_connected":true,"https_connected":true,"http_status":null,"duration_seconds":15.187}
```

Resultado historico del candidato anterior: DNS, TCP y TLS funcionaron, pero el GET no recibio cabeceras HTTP dentro del limite del precheck (15 s). La politica anterior impidio lanzar Playwright. Esa conclusion era insuficiente: un cliente HTTP sin respuesta no demuestra que Edge no pueda adquirir. La correccion actual elimina ese bloqueo, sin reintentar el precheck ni aumentar timeouts. El fallo anterior de Edge tambien carecia de status despues del timeout de 60 s. No hay evidencia de una diferencia de configuracion en main que explique ambos resultados.

El step capture tiene continue-on-error: su conclusion success NO acredita captura valida. Su outcome fue failure y el comando termino con codigo 1. Se verifico el log del comando y el artefacto de diagnostico; no se afirma exito a partir del resumen del step.

Los CSV previos y MAGYP_LAST_VALID se conservaron. Adicionalmente fallo el test frontend Corrientes rows, price averages, rankings and monthly semaphore match committed baseline al final de Actions; no se modifico frontend ni Corrientes para ocultar ese error. Localmente pasaron 98 tests MCBA, 45 comunes y 24 frontend; en Actions los tests previos tambien pasaron. No se abrio PR porque no se alcanzo la condicion exigida de XLSX real valido. La rama conserva el candidato para revision, sin merge ni deploy.

## Correccion final: precheck informativo

Se mantienen hasta tres intentos completos de navegador, 60 segundos por etapa, sesiones limpias y espera de 10 segundos. El precheck no sustituye la validacion de schema, filas y fecha del XLSX. Los tests comprueban continuacion con timeout/conexion/DNS/5xx, 403 sin navegador, XLSX valido despues de precheck inconcluso y tres fallos reales con MAGYP_LAST_VALID.

## Validacion real del ajuste final (sin commit)

Prueba directa en el host del runner DESKTOP-MHFH88Q, cuenta Windows acer, desde el directorio de trabajo del runner, con el codigo aun sin commit y temporales aislados fuera del repositorio. No se presenta como una corrida de GitHub Actions.

Fecha solicitada: 2026-10-05; canal msedge; timeout configurado 60 segundos y tres sesiones como maximo. El precheck dio PRECHECK_INCONCLUSIVE, DNS/TCP/TLS correctos, status null, duracion 15.25 segundos. Edge se ejecuto igualmente.

Resultados observados: intento 1 initial_get TIMEOUT (85.781 s de sesion), intento 2 initial_get TIMEOUT (67.11 s), intento 3 initial_get OTHER (1850.812 s registrados). Todos sin HTTP status y con una request. Esa duracion observada del tercer intento se conserva sin atribuirle una causa no verificada. No se descargo XLSX ni se modificaron los CSV publicados. No hubo cuarto intento.

Validacion offline final: 101 tests MCBA, 45 comunes y 24 frontend correctos; git diff --check correcto. Se verifico en particular que precheck timeout/conexion/DNS y 5xx permiten Edge, que 403 lo bloquea, que un precheck inconcluso permite XLSX sintetico valido y que tres fallos Edge conservan MAGYP_LAST_VALID.

La correccion logica queda sin commit ni PR: no se alcanzo la captura real exitosa exigida por el usuario para autorizar esos pasos. No se considera resuelta la adquisicion productiva.

La solicitud posterior de cierre productivo reemplaza la condición de esperar una captura real exitosa antes del PR. La entrega de disponibilidad se describe en MCBA_PRODUCTION_AVAILABILITY.md; no acredita una nueva captura real.
