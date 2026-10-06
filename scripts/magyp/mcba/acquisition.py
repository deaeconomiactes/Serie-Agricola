"""Adaptador de adquisición GeneXus separado del parser.

Sólo reproduce controles públicos de UI; sin modificar scripts de la página,
sin evadir validaciones, sin HAR/traces/storage_state ni persistencia de sesión.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from scripts.magyp.common.platform import PipelineError, official_url

URL = "https://ssma.magyp.gob.ar/frutas.precios.aspx"
MAX_FILE = 2_000_000


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


def browser_fetch(start, end, timeout=25, max_requests=80, channel="msedge"):
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
    cookie_names = []
    stage = "initial_get"
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
            for item in reversed(network):
                if item["endpoint"] == public_endpoint(response.url) and item["status"] is None:
                    item["status"] = response.status
                    break
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
        try:
            response = page.goto(URL, wait_until="load")
            if not response or response.status != 200:
                raise PipelineError("GET inicial no exitoso")
            protocol = describe_genexus(page.content())
            cookie_names = sorted(c["name"] for c in context.cookies())
            stage = "date_controls"
            page.locator("#DDO_GRIDContainer_TF_1_btnGroupDrop").click()
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
            page.locator("#EXPORT").click()
            deadline = time.monotonic() + timeout
            while not downloads and time.monotonic() < deadline and not errors:
                page.wait_for_timeout(100)
            if not downloads:
                raise PipelineError("Export no generó descarga dentro del límite")
            download = downloads[0]
            failure = download.failure()
            if failure:
                raise PipelineError("Descarga de export fallida")
            path = Path(download.path())
            if path.stat().st_size > MAX_FILE or errors:
                raise PipelineError("Adquisición excedió límites")
            payload = path.read_bytes()
            # Descargar en contexto efímero; no copiar archivos intermedios/formularios al repo.
            download.delete()
            return AcquisitionResult(payload, "BROWSER_AUTOMATION_REQUIRED", export_meta.get("status"),
                                     export_meta.get("content_type"), export_meta.get("method"),
                                     {"requests": network, "request_count": len(network),
                                      "browser_channel": channel, "browser_version": str(browser.version),
                                      "headless": True, "persistent_profile": False,
                                      "export_response": export_meta,
                                      "protocol": protocol, "cookie_names_only": cookie_names,
                                      "visible_grid_rows": inspected_rows}, inspected_rows)
        except PipelineError as e:
            e.diagnostics = {"stage": stage, "requests": network, "errors": errors, "protocol": protocol}
            raise
        except Exception as e:
            # Evitar repr de Playwright: puede contener URL cifrada, cookies o estado privado.
            failure = PipelineError("Adquisición navegador falló en " + stage + ": " + type(e).__name__)
            failure.diagnostics = {"stage": stage, "requests": network, "errors": errors,
                                   "protocol": protocol}
            raise failure from None
        finally:
            context.close()
            browser.close()
