"""Adaptador de adquisición GeneXus separado del parser.

Sólo reproduce controles públicos de UI; sin modificar scripts de la página,
sin evadir validaciones, sin HAR/traces/storage_state ni persistencia de sesión.
"""
from __future__ import annotations
import time
import json
import os
import sys
import socket
import http.client
import getpass
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from scripts.magyp.common.platform import PipelineError, official_url

URL = "https://ssma.magyp.gob.ar/frutas.precios.aspx"
MAX_FILE = 2_000_000


def connectivity_precheck(timeout=15):
    """Diagnostic GET: only an explicit 401/403/404 may prevent browser acquisition."""
    started = time.monotonic()
    result = {'dns_resolves': False, 'tcp_connected': False, 'https_connected': False,
              'http_status': None, 'duration_seconds': None}
    connection = None
    try:
        host = urlsplit(URL).hostname
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        result['dns_resolves'] = True
        connection = http.client.HTTPSConnection(host, timeout=timeout)
        tcp_connect = connection._create_connection
        def tracked_tcp(*args, **kwargs):
            transport = tcp_connect(*args, **kwargs)
            result['tcp_connected'] = True
            return transport
        connection._create_connection = tracked_tcp
        connection.connect()  # Default verified TLS; never ignore certificates.
        result['https_connected'] = True
        connection.request('GET', urlsplit(URL).path,
                           headers={'User-Agent': 'SerieAgricola-MAGyP-MCBA-Precheck/1.0',
                                    'Connection': 'close'})
        result['http_status'] = connection.getresponse().status
    except (OSError, http.client.HTTPException):
        # No response bodies, Set-Cookie, IPs, proxy values or exception text are retained.
        pass
    finally:
        if connection is not None:
            connection.close()
        result['duration_seconds'] = round(time.monotonic() - started, 3)
    status = result['http_status']
    blocked = status in {401, 403, 404}
    result['classification'] = ('PRECHECK_BLOCKED' if blocked else
        'PRECHECK_OK' if status == 200 else
        'PRECHECK_TRANSIENT' if status is not None and 500 <= status <= 599 else
        'PRECHECK_INCONCLUSIVE')
    print('[PRECHECK] MCBA ' + json.dumps(result, sort_keys=True), flush=True)
    if blocked:
        failure = PipelineError(f'PRECHECK HTTP {status} explícito; no se inicia Playwright')
        failure.diagnostics = {'acquisition_stage': 'precheck',
                               'error_type': f'HTTP_{status}', 'precheck': result,
                               'acquisition_attempts': [], 'request_count': 1}
        raise failure
    return result


def navigation_snapshot(page, status, request_count):
    """Only public state/booleans, never DOM contents or input/session values."""
    state = {}
    try:
        state = page.evaluate("() => ({ready_state: document.readyState, "
            "date_from_exists: !!document.querySelector('#vDDO_FRUTAS_PRECIOS_FECHAAUXDATE'), "
            "date_to_exists: !!document.querySelector('#vDDO_FRUTAS_PRECIOS_FECHAAUXDATETO')})")
    except Exception:
        pass  # A navigation can destroy the old document; readiness remains explicit below.
    state = state if isinstance(state, dict) else {}
    return {'http_status': status, 'ready_state': state.get('ready_state')
            if state.get('ready_state') in {'loading', 'interactive', 'complete'} else None,
            'final_url': safe_initial_url(page.url),
            'date_from_exists': state.get('date_from_exists') is True,
            'date_to_exists': state.get('date_to_exists') is True,
            'request_count': request_count}


def preferred_browser_channel():
    """Use installed Edge on Windows; absence alone selects bundled Chromium."""
    if sys.platform == 'win32':
        for name in ('PROGRAMFILES(X86)', 'PROGRAMFILES', 'LOCALAPPDATA'):
            root = os.environ.get(name)
            if root and (Path(root) / 'Microsoft/Edge/Application/msedge.exe').is_file():
                return 'msedge'
    return 'chromium'


def wait_for_genexus_controls(page, timeout):
    """Wait for usable controls, re-resolving locators after an initial reload.

    One shared deadline bounds readiness, including any navigation during rendering.
    No element handles or load/networkidle readiness assumptions are retained.
    """
    deadline = time.monotonic() + timeout
    navigation = [0]

    def navigated(frame):
        if frame == page.main_frame:
            navigation[0] += 1

    def remaining():
        value = int((deadline - time.monotonic()) * 1000)
        if value <= 0:
            raise TimeoutError('GeneXus controls unavailable within deadline')
        return value

    page.on('framenavigated', navigated)
    try:
        while True:
            revision = navigation[0]
            try:
                page.wait_for_load_state('domcontentloaded', timeout=remaining())
                for selector in ('#GridContainerTbl', '#EXPORT', '#DDO_GRIDContainer_TF_1_btnGroupDrop'):
                    page.locator(selector).wait_for(state='visible', timeout=remaining())
                if not page.locator('#vDDO_FRUTAS_PRECIOS_FECHAAUXDATE').is_visible():
                    page.locator('#DDO_GRIDContainer_TF_1_btnGroupDrop').click(timeout=remaining())
                for selector in ('#vDDO_FRUTAS_PRECIOS_FECHAAUXDATE', '#vDDO_FRUTAS_PRECIOS_FECHAAUXDATETO'):
                    page.locator(selector).wait_for(state='visible', timeout=remaining())
                if revision == navigation[0]:
                    return
            except Exception as error:
                # Inspect only fixed browser errors in memory; never log exception text.
                reload_error = 'Execution context was destroyed' in str(error)
                if revision == navigation[0] and not reload_error:
                    raise
            remaining()  # Reloads cannot extend the readiness deadline.
    finally:
        page.remove_listener('framenavigated', navigated)


def validate_window(start, end):
    try:
        a, b = date.fromisoformat(start), date.fromisoformat(end)
    except (ValueError, TypeError) as e:
        raise PipelineError("Ventana requiere fechas ISO YYYY-MM-DD") from e
    if a > b or (b - a).days > 6:
        raise PipelineError("Ventana piloto entre 1 y 7 días; sin backfill")
    return a, b


def public_endpoint(url):
    p = urlsplit(url)
    # Descargas GeneXus pueden incluir un identificador temporal en el path.
    # Nunca persistirlo; todos los exports se identifican por su origen estable.
    if p.path.lower().endswith(".xlsx") or "publictempstorage" in p.path.lower():
        return "https://" + (p.hostname or "") + "/<temporary-export>"
    return "https://" + (p.hostname or "") + p.path


def describe_genexus(html):
    """Sólo nombres de campos/protocolo; nunca devuelve valores hidden."""
    import re
    names = re.findall(r'<input\b[^>]*\bname=["\']([^"\']+)', html, re.I)
    return {"hidden_field_names": sorted(set(names)), "has_gxstate": "GXState" in names,
            "has_date_controls": all(n in names for n in
              ("vDDO_FRUTAS_PRECIOS_FECHAAUXDATE", "vDDO_FRUTAS_PRECIOS_FECHAAUXDATETO"))}


@dataclass
class AcquisitionResult:
    payload: bytes
    classification: str
    http_status: int | None = None
    content_type: str | None = None
    request_method: str | None = None
    diagnostics: dict = field(default_factory=dict)
    label_evidence: list[dict] = field(default_factory=list)


def select_fetcher(start, end, strategy="auto", browser=None, http=None):
    validate_window(start, end)
    if strategy == "http":
        if http is None:
            raise PipelineError("HTTP autónomo GeneXus no validado; usar --acquisition browser")
        return http(start, end)
    if strategy == "auto" and http is not None:
        try:
            return http(start, end)
        except PipelineError:
            # Un candidato HTTP explícito puede caer al navegador sin alterar las capas.
            pass
    return (browser or browser_fetch)(start, end)


def safe_initial_url(value):
    """Only the stable public endpoint is retained; never session paths or query values."""
    if not isinstance(value, str):
        return None
    try:
        p = urlsplit(value)
        if p.scheme not in {'http', 'https'}:
            return '<redacted-url>'
        host = 'ssma.magyp.gob.ar' if p.hostname == 'ssma.magyp.gob.ar' else '<unexpected-host>'
        path = '/frutas.precios.aspx' if p.path.lower() == '/frutas.precios.aspx' else '/<redacted-path>'
        return p.scheme + '://' + host + path
    except ValueError:
        return '<redacted-url>'


def initial_error_type(error, status=None):
    if status is not None and status != 200:
        return 'HTTP_5XX' if 500 <= status <= 599 else f'HTTP_{status}'
    # Inspect messages only for fixed network codes; never persist exception text/URLs.
    text = str(error)
    if type(error).__name__ == 'TimeoutError' or 'net::ERR_TIMED_OUT' in text:
        return 'TIMEOUT'
    if 'ERR_NAME_NOT_RESOLVED' in text or 'getaddrinfo' in text:
        return 'DNS'
    if isinstance(error, (ConnectionError,)) or any(code in text for code in (
            'ERR_CONNECTION_', 'ERR_NETWORK_CHANGED', 'ERR_INTERNET_DISCONNECTED')):
        return 'CONNECTION'
    if 'ERR_ABORTED' in text:
        return 'NAVIGATION_ABORTED'
    if 'ERR_TOO_MANY_REDIRECTS' in text:
        return 'UNEXPECTED_REDIRECT'
    return 'OTHER'


def browser_fetch(start, end, timeout=60, max_requests=80, channel="auto"):
    """At most three complete acquisitions, each with a fresh browser/session.

    Each complete session has its own bounded request budget (at most three budgets).
    Validation failures never retry.
    """
    channel = preferred_browser_channel() if channel == 'auto' else channel
    validate_window(start, end)
    precheck = connectivity_precheck()
    print('[ACQUISITION_CONTEXT] MCBA ' + json.dumps({
        'windows_user': getpass.getuser(), 'runner_name': os.environ.get('RUNNER_NAME'),
        'github_actions': os.environ.get('GITHUB_ACTIONS') == 'true',
        'browser_channel': channel}, sort_keys=True), flush=True)
    attempts, initial_attempts, previous_requests = [], [], []
    for number in range(1, 4):
        remaining = max_requests
        started = time.monotonic()

        def record_attempt(diag, succeeded=False):
            initial = diag.get('initial_get')
            if initial:
                initial_attempts.append({**initial, 'attempt': number})
            record = {'attempt': number,
                      'acquisition_stage': 'completed' if succeeded else diag.get('acquisition_stage', 'session_setup'),
                      'error_type': None if succeeded else diag.get('error_type', 'OTHER'),
                      'duration_seconds': round(time.monotonic() - started, 3),
                      'http_status': diag.get('http_status'),
                      'browser': 'chromium', 'browser_channel': channel,
                      'request_count': len(diag.get('requests', [])), 'requested_date': start}
            attempts.append(record)
            print('[FETCH] MCBA acquisition ' + json.dumps(record, sort_keys=True))

        try:
            result = _browser_fetch_once(start, end, timeout, remaining, channel)
        except PipelineError as error:
            diag = getattr(error, 'diagnostics', {})
            record_attempt(diag)
            requests = previous_requests + diag.get('requests', [])
            error.diagnostics = {**diag, 'precheck': precheck, 'initial_get_attempts': initial_attempts,
                                 'acquisition_attempts': attempts, 'retry_performed': number > 1,
                                 'request_count': len(requests), 'requests': requests}
            kind = diag.get('error_type')
            transient = (kind in {'CONNECTION', 'HTTP_5XX'} or
                         (kind == 'TIMEOUT' and diag.get('acquisition_stage') in {
                             'initial_get', 'date_controls', 'filter_ajax', 'export_download'}))
            if number < 3 and transient and len(diag.get('requests', [])) < max_requests:
                # _browser_fetch_once has already closed its context/browser before this wait.
                print(f'[FETCH] MCBA acquisition retry {number}/2; sesión cerrada; espera 10 segundos')
                previous_requests = requests
                time.sleep(10)
                continue
            raise
        record_attempt(result.diagnostics, succeeded=True)
        requests = previous_requests + result.diagnostics.get('requests', [])
        result.diagnostics.update(precheck=precheck, initial_get_attempts=initial_attempts, acquisition_attempts=attempts,
                                  retry_performed=number > 1,
                                  requests=requests, request_count=len(requests))
        return result


def _browser_fetch_once(start, end, timeout=60, max_requests=80, channel="msedge"):
    a, b = validate_window(start, end)
    if not 1 <= max_requests <= 120 or not 1 <= timeout <= 60:
        raise PipelineError("Límites de adquisición inválidos")
    if channel not in {"msedge", "chromium"}:
        raise PipelineError("Canal de navegador no permitido")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise PipelineError("Instalar requirements-browser.txt y un navegador compatible") from e
    network = []
    errors = []
    filtered = False
    export_meta = {}
    downloads = []
    inspected_rows = []
    protocol = {}
    stage = "initial_get"
    initial = {}
    stage_error = None
    stage_status = None
    navigation = {}
    # Perfil/contexto no persistente, sin certificados ignorados ni almacenamiento de estado.
    with sync_playwright() as p:
        options = {"headless": True}
        if channel != "chromium":
            options["channel"] = channel
        try:
            browser = p.chromium.launch(**options)
        except Exception as e:
            raise PipelineError("Navegador no disponible; instalar Chromium de Playwright o Edge") from e
        # Conservar identificación de motor: GeneXus usa detección de navegador.
        # El sufijo identifica el piloto, sin ocultar HeadlessChrome ni su versión.
        probe = browser.new_context()
        probe_page = probe.new_page()
        native_ua = probe_page.evaluate("navigator.userAgent")
        probe.close()
        context = browser.new_context(accept_downloads=True,
                                     user_agent=native_ua + " SerieAgricola-MAGyP-MCBA-Pilot/2.0")
        page = context.new_page()
        page.set_default_timeout(timeout * 1000)
        page.set_default_navigation_timeout(timeout * 1000)

        def route_request(route):
            request = route.request
            try:
                official_url(request.url)
            except (PipelineError, ValueError):
                if request.resource_type == 'document':
                    errors.append('unexpected_redirect')
                route.abort()
                return
            if request.resource_type in {"image", "font", "media"}:
                # Evitar recursos no necesarios para filtrar/exportar; no cuenta como request enviado.
                route.abort()
                return
            if len(network) >= max_requests:
                errors.append("request_budget_exceeded")
                route.abort()
                return
            item = {"sequence": len(network) + 1, "method": request.method,
                    "endpoint": public_endpoint(request.url), "status": None,
                    "stage": "filtered" if filtered else "initial"}
            if request.method == "POST":
                # Inspeccionar sólo claves/estructura y nombres de eventos públicos.
                try:
                    data = request.post_data_json
                    if isinstance(data, dict):
                        item["json_keys"] = sorted(data)
                        item["events"] = [x for x in data.get("events", [])
                                          if isinstance(x, str) and len(x) < 80]
                        item["parameter_count"] = len(data.get("parms", []))
                        item["hashed_parameter_count"] = len(data.get("hsh", []))
                    item["header_names"] = sorted(request.headers)
                except Exception:
                    item["body_format"] = "not_json"
            network.append(item)
            route.continue_()

        def on_response(response):
            nonlocal stage_error, stage_status
            for item in reversed(network):
                if item["endpoint"] == public_endpoint(response.url) and item["status"] is None:
                    item["status"] = response.status
                    break
            if response.status >= 400 and response.request.resource_type in {'document', 'xhr', 'fetch'}:
                stage_status = response.status
                stage_error = initial_error_type(None, stage_status)
                errors.append('http_error')
            if response.headers.get("content-disposition", "").lower().find("attachment") >= 0 or \
                    urlsplit(response.url).path.lower().endswith(".xlsx"):
                declared_size = response.headers.get("content-length")
                if declared_size and int(declared_size) > MAX_FILE:
                    errors.append("export_size_exceeded")
                export_meta.update(status=response.status,
                                   content_type=response.headers.get("content-type"),
                                   method=response.request.method)

        context.route("**/*", route_request)
        page.on("response", on_response)
        page.on("download", lambda d: downloads.append(d))
        context.on("page", lambda new_page: (new_page.on("download", lambda d: downloads.append(d)),
                                              new_page.on("response", on_response)))
        def initial_record(error_type, status, final_url):
            return {'acquisition_stage': 'initial_get', 'error_type': error_type,
                    'http_status': status, 'final_url': safe_initial_url(final_url),
                    'duration_seconds': round(time.monotonic() - started, 3),
                    'request_count': len(network), 'browser': 'chromium',
                    'browser_channel': channel, 'requested_date': start}

        started = time.monotonic()
        try:
            try:
                # Commit establishes the document response, without waiting for scripts/resources.
                # GeneXus readiness is validated separately through explicit controls below.
                response = page.goto(URL, wait_until="commit")
                status = response.status if response and isinstance(response.status, int) else None
                final_url = response.url if response and isinstance(response.url, str) else page.url
                kind = None
                if not response:
                    kind = 'NAVIGATION_NO_RESPONSE'
                elif status != 200:
                    kind = initial_error_type(None, status)
                elif isinstance(final_url, str) and safe_initial_url(final_url) != URL:
                    kind = 'UNEXPECTED_REDIRECT'
                initial = initial_record(kind, status, final_url)
                navigation = navigation_snapshot(page, status, len(network))
                print('[NAVIGATION] MCBA ' + json.dumps(navigation, sort_keys=True), flush=True)
                if kind:
                    raise PipelineError('GET inicial no exitoso: ' + kind)
            except Exception as error:
                if not initial:
                    status = next((item['status'] for item in reversed(network)
                                   if item['endpoint'] == URL and isinstance(item['status'], int)), None)
                    kind = 'UNEXPECTED_REDIRECT' if 'unexpected_redirect' in errors else initial_error_type(error, status)
                    initial = initial_record(kind, status, page.url)
                    navigation = navigation_snapshot(page, status, len(network))
                    print('[NAVIGATION] MCBA ' + json.dumps(navigation, sort_keys=True), flush=True)
                if initial['http_status'] in {401, 403}:
                    initial['classification'] = ('GITHUB_RUNNER_ACCESS_BLOCKED'
                        if os.environ.get('GITHUB_ACTIONS') == 'true' else 'HTTP_ACCESS_BLOCKED')
                failure = PipelineError('GET inicial no exitoso: ' + initial['error_type'] +
                    ('; ' + initial['classification'] if 'classification' in initial else ''))
                raise failure from None
            stage = "date_controls"
            wait_for_genexus_controls(page, timeout)
            protocol = describe_genexus(page.content())
            page.locator("#vDDO_FRUTAS_PRECIOS_FECHAAUXDATE").fill(a.strftime("%d/%m/%Y"))
            page.locator("#vDDO_FRUTAS_PRECIOS_FECHAAUXDATETO").fill(b.strftime("%d/%m/%Y"))
            filtered = True
            stage = "filter_ajax"
            # La respuesta AJAX debe terminar antes de leer/exportar. No esperar un timeout fijo.
            with page.expect_response(lambda r: r.request.method == "POST" and
                    urlsplit(r.url).path.lower().endswith("frutas.precios.aspx")) as filtering:
                page.locator("#search_DDO_GRIDContainer_TF_1").click()
            filter_response = filtering.value
            if filter_response.status != 200:
                stage_status = filter_response.status
                stage_error = initial_error_type(None, stage_status)
                raise PipelineError("Filtro GeneXus no exitoso")
            stage = "filtered_grid"
            page.wait_for_function("([start,end]) => {const t=document.querySelector('#GridContainerTbl'); "
                                   "const dates=t?.innerText.match(/\\d{2}\\/\\d{2}\\/\\d{4}/g)||[]; "
                                   "return dates.length && dates.every(d=>{const v=d.split('/').reverse().join('-'); "
                                   "return v>=start && v<=end;});}", arg=[start, end])
            table_rows = page.locator("#GridContainerTbl tr[id^='GridContainerRow_']").all()
            for tr in table_rows:
                cells = tr.locator("td:visible").all_text_contents()
                if len(cells) == 11:
                    date_text = cells[0].strip()
                    try:
                        from datetime import datetime
                        parsed = datetime.strptime(date_text, "%d/%m/%Y").date()
                    except ValueError:
                        continue
                    if not a <= parsed <= b:
                        raise PipelineError("Grilla aún fuera de la ventana solicitada; no exportar")
                    inspected_rows.append(dict(zip(("date", "type", "product", "variety", "origin", "package",
                                                   "quality", "size", "grade", "kg", "price"),
                                                   (c.strip() for c in cells))))
            if not inspected_rows:
                raise PipelineError("Sin filas visibles filtradas; no exportar un histórico sin filtro")
            stage = "export_download"
            # GeneXus abre el export en otra página; escuchar descargas de todo el contexto.
            page.locator("#EXPORT").wait_for(state="visible")
            page.locator("#EXPORT").click()
            deadline = time.monotonic() + timeout
            while not downloads and time.monotonic() < deadline and not errors:
                page.wait_for_timeout(100)
            stage_status = export_meta.get('status', stage_status)
            if stage_status is not None and stage_status != 200:
                stage_error = initial_error_type(None, stage_status)
                raise PipelineError("Export HTTP no exitoso: " + stage_error)
            if not downloads:
                if not errors:
                    stage_error = 'TIMEOUT'
                raise PipelineError("Export no generó descarga dentro del límite")
            download = downloads[0]
            failure = download.failure()
            if failure:
                kind = initial_error_type(RuntimeError(failure))
                if kind in {'TIMEOUT', 'CONNECTION'}:
                    stage_error = kind
                raise PipelineError("Descarga de export fallida")
            path = Path(download.path())
            if path.stat().st_size > MAX_FILE or errors:
                raise PipelineError("Adquisición excedió límites")
            payload = path.read_bytes()
            # Descargar en contexto efímero; no copiar archivos intermedios/formularios al repo.
            download.delete()
            stage = "validate_xlsx"
            # Reuse the existing parser unchanged; HTTP 200/download alone is not success.
            from scripts.magyp.mcba.model import parse_export
            try:
                records = parse_export(payload, start, end)
            except PipelineError as exc:
                # Only the parser's confirmed known-header/zero-row export is absence.
                # HTML, wrong schema, wrong dates and invalid XLSX remain integrity errors.
                if str(exc) == "Exportación vacía; ausencia de publicación no demostrada":
                    stage_error = 'NO_PUBLICATION'
                raise
            if not records:
                raise PipelineError("Export sin filas válidas")
            return AcquisitionResult(payload, "BROWSER_AUTOMATION_REQUIRED", export_meta.get("status"),
                                     export_meta.get("content_type"), export_meta.get("method"),
                                     {"requests": network, "request_count": len(network),
                                      "http_status": export_meta.get('status'),
                                      "xlsx_valid": True, "validated_rows": len(records),
                                      "browser_channel": channel, "browser_version": str(browser.version),
                                      "headless": True, "persistent_profile": False,
                                      "export_response": export_meta,
                                      "protocol": protocol, "initial_get": initial,
                                      "navigation": navigation,
                                      "visible_grid_rows": inspected_rows}, inspected_rows)
        except PipelineError as e:
            e.diagnostics = {"stage": stage, "acquisition_stage": stage, "navigation": navigation,
                             "error_type": stage_error or 'VALIDATION_ERROR',
                             "http_status": stage_status,
                             "requests": network, "errors": errors, "protocol": protocol}
            if stage == 'initial_get':
                # Keep only fixed public metadata, without GXState, cookie names or session paths.
                safe_requests = [{k: (safe_initial_url(v) if k == 'endpoint' else v)
                                  for k, v in item.items() if k in {'sequence','method','endpoint','status','stage'}}
                                 for item in network]
                e.diagnostics = {'stage': stage, **initial, 'initial_get': initial,
                                 'navigation': navigation, 'requests': safe_requests, 'errors': errors}
            elif initial:
                e.diagnostics['initial_get'] = initial
            raise
        except Exception as e:
            # Evitar repr de Playwright: puede contener URL cifrada, cookies o estado privado.
            failure = PipelineError("Adquisición navegador falló en " + stage + ": " + type(e).__name__)
            failure.diagnostics = {"stage": stage, "acquisition_stage": stage, "navigation": navigation,
                                   "error_type": stage_error or initial_error_type(e),
                                   "http_status": stage_status,
                                   "requests": network, "errors": errors,
                                   "protocol": protocol, "initial_get": initial}
            raise failure from None
        finally:
            try:
                context.close()
            finally:
                browser.close()
