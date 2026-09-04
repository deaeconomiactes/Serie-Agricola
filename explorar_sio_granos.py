#!/usr/bin/env python3
"""Exploración pública controlada de SIO Granos.

El modo seguro es el comportamiento por defecto. La red sólo se habilita con
``--allow-web`` y usando endpoints explícitos de ``sio_config.json``.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "commodities_sio"
CONFIG_PATH = DATA_DIR / "sio_config.json"
CATALOG_PATH = DATA_DIR / "catalogo_productos_sio.csv"
DEFAULT_OUTPUT = DATA_DIR / "raw"
REPORT_DIR = DATA_DIR / "reports"
USER_AGENT = "Serie-Agricola/commodities-sio-explorer (+consulta-publica)"
SAFE_MESSAGE = (
    "Modo seguro: no se realizan llamadas externas. Use --dry-run para ver la "
    "consulta o --allow-web para ejecutar una exploración pública controlada."
)
MAX_DAYS_HARD_LIMIT = 180


def normalize(value: Any) -> str:
    import unicodedata

    value = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value)


def read_catalog() -> list[dict[str, str]]:
    if not CATALOG_PATH.exists():
        return []
    with CATALOG_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def parse_products(value: str | None, catalog: list[dict[str, str]]) -> list[str]:
    requested = [item.strip() for item in (value or "").split(",") if item.strip()]
    if not requested:
        requested = [
            row["commodity"]
            for row in catalog
            if row.get("commodity") and normalize(row.get("activo", "true")) == "true"
        ]
    aliases: dict[str, str] = {}
    for row in catalog:
        canonical = row.get("commodity", "").strip()
        for alias in [canonical] + row.get("aliases", "").split("|"):
            if alias:
                aliases[normalize(alias)] = canonical
    result: list[str] = []
    for item in requested:
        canonical = aliases.get(normalize(item), item)
        if canonical not in result:
            result.append(canonical)
    if not result:
        raise SystemExit("No se especificaron productos y el catálogo SIO está vacío.")
    return result


def parse_date_arg(value: str, option: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit(f"{option} debe tener formato YYYY-MM-DD: {value}") from exc


def date_range(args: argparse.Namespace) -> tuple[date, date]:
    end = parse_date_arg(args.date_end, "--date-end") if args.date_end else date.today()
    if args.date_start:
        start = parse_date_arg(args.date_start, "--date-start")
    else:
        try:
            days_back = int(args.days_back)
        except ValueError as exc:
            raise SystemExit("--days-back debe ser un entero") from exc
        if days_back < 0:
            raise SystemExit("--days-back no puede ser negativo")
        start = end - timedelta(days=days_back)
    if start > end:
        raise SystemExit("--date-start no puede ser posterior a --date-end")
    return start, end


def split_date_range(start: date, end: date, max_days: int = MAX_DAYS_HARD_LIMIT) -> list[tuple[date, date]]:
    """Divide un rango inclusivo en ventanas de no más de ``max_days`` días."""

    if max_days < 1:
        raise ValueError("max_days debe ser mayor que cero")
    max_days = min(max_days, MAX_DAYS_HARD_LIMIT)
    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=max_days - 1), end)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"base_url": "", "endpoints": {}, "max_days_per_request": MAX_DAYS_HARD_LIMIT, "configured": False}
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR leyendo {CONFIG_PATH}: {exc}")
        return {"base_url": "", "endpoints": {}, "max_days_per_request": MAX_DAYS_HARD_LIMIT, "configured": False}
    if not isinstance(raw, dict):
        return {"base_url": "", "endpoints": {}, "max_days_per_request": MAX_DAYS_HARD_LIMIT, "configured": False}
    endpoints = raw.get("endpoints", {})
    endpoints = {str(name): str(value).strip() for name, value in endpoints.items() if str(value).strip()} if isinstance(endpoints, dict) else {}
    try:
        configured_limit = int(raw.get("max_days_per_request", MAX_DAYS_HARD_LIMIT))
    except (TypeError, ValueError):
        configured_limit = MAX_DAYS_HARD_LIMIT
    return {
        "base_url": str(raw.get("base_url", "")).strip(),
        "endpoints": endpoints,
        "max_days_per_request": min(max(configured_limit, 1), MAX_DAYS_HARD_LIMIT),
        "configured": bool(str(raw.get("base_url", "")).strip() and endpoints),
    }


def endpoint_url(base_url: str, endpoint: str) -> str:
    if endpoint.startswith(("http://", "https://")):
        return endpoint
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def candidate_endpoints(config: dict[str, Any]) -> list[tuple[str, str]]:
    preferred = ("consulta_publica", "operaciones_informadas", "operaciones_informadas_exportar")
    names = list(dict.fromkeys([name for name in preferred if config["endpoints"].get(name)] + list(config["endpoints"])))
    return [(name, endpoint_url(config["base_url"], config["endpoints"][name])) for name in names]


def catalog_row(catalog: list[dict[str, str]], product: str) -> dict[str, str] | None:
    target = normalize(product)
    for row in catalog:
        names = [row.get("commodity", "")] + row.get("aliases", "").split("|")
        if target in {normalize(name) for name in names if name}:
            return row
    return None


def suggested_url(endpoint: str, product: str, product_id: str, start: date, end: date) -> str:
    # Estos parámetros son sólo una consulta orientativa: no se asume el payload
    # real de SIO hasta inspeccionar la respuesta pública.
    params = {"date_start": start.isoformat(), "date_end": end.isoformat(), "producto": product}
    if product_id:
        params["sio_id_producto"] = product_id
    return endpoint + ("&" if "?" in endpoint else "?") + urllib.parse.urlencode(params)


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)


def response_extension(content_type: str, content: bytes) -> str:
    lowered = content_type.lower()
    if "json" in lowered:
        return ".json"
    if "csv" in lowered:
        return ".csv"
    if "spreadsheet" in lowered or "excel" in lowered or content[:4] == b"PK\x03\x04":
        return ".xlsx"
    return ".html" if b"<html" in content[:1000].lower() or b"<form" in content[:1000].lower() else ".bin"


def save_response(output_dir: Path, product: str, start: date, end: date, endpoint_name: str, content: bytes, content_type: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"SIO_{endpoint_name}_{start}_{end}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{normalize(product).replace(' ', '_')}{response_extension(content_type, content)}"
    path = output_dir / safe_filename(filename)
    path.write_bytes(content)
    return path


def inspect_public_html(content: bytes) -> dict[str, list[str]]:
    source = content.decode("utf-8", errors="replace")
    fields = sorted(set(re.findall(r"<(?:input|select|textarea)\b[^>]*(?:name|id)=['\"]([^'\"]+)['\"]", source, flags=re.I)))
    exports = sorted(set(html.unescape(value) for value in re.findall(r"(?:href|action)=['\"]([^'\"]+\.(?:csv|xlsx?|xls)(?:\?[^'\"]*)?)['\"]", source, flags=re.I)))
    forms = re.findall(r"<form\b[^>]*(?:action=['\"]([^'\"]*)['\"])?[^>]*>", source, flags=re.I)
    return {"fields": fields, "exports": exports, "forms": [html.unescape(value) for value in forms]}


def print_html_diagnostic(content: bytes) -> dict[str, list[str]]:
    diagnostic = inspect_public_html(content)
    print(f"Campos detectados (sin asumir payload): {', '.join(diagnostic['fields']) or 'ninguno'}")
    print(f"Formularios detectados: {len(diagnostic['forms'])}")
    print(f"Enlaces de exportación detectados: {', '.join(diagnostic['exports']) or 'ninguno'}")
    return diagnostic


def save_html_diagnostic(output_dir: Path, content: bytes) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    path = output_dir / f"SIO_diagnostico_consulta_publica_{timestamp}.html"
    path.write_bytes(content)
    return path


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def same_domain(url: str, base_url: str) -> bool:
    return urllib.parse.urlparse(url).netloc.lower() == urllib.parse.urlparse(base_url).netloc.lower()


def generic_script(url: str) -> bool:
    name = urllib.parse.urlparse(url).path.lower()
    return any(marker in name for marker in ("jquery", "jqgrid", "bootstrap", "analytics", "google-analytics", "jquery-ui", "grid.locale"))


def extract_discovery_evidence(content: bytes, page_url: str) -> dict[str, Any]:
    source = content.decode("utf-8", errors="replace")
    title_match = re.search(r"<title\b[^>]*>(.*?)</title>", source, flags=re.I | re.S)
    scripts = [urllib.parse.urljoin(page_url, html.unescape(value)) for value in re.findall(r"<script\b[^>]*\bsrc=['\"]([^'\"]+)['\"]", source, flags=re.I)]
    urls = unique([html.unescape(value) for value in re.findall(r"(?:href|src|action|url)\s*[:=]\s*['\"]([^'\"]+)['\"]", source, flags=re.I)])
    endpoint_refs = unique(re.findall(r"(?:[A-Za-z0-9_./-]+\.(?:aspx|ashx|asmx)(?:/[A-Za-z0-9_./-]+)?(?:[?#][^'\"\s]*)?)", source, flags=re.I))
    endpoint_refs = [html.unescape(value) for value in endpoint_refs]
    endpoint_urls = unique([urllib.parse.urljoin(page_url, value) for value in endpoint_refs])
    ajax_markers = unique(re.findall(r"(?i)(?:fetch\s*\(|XMLHttpRequest|\$\.ajax|PageMethods|WebMethods|\.ajax\s*\(|dataType\s*:|contentType\s*:)", source))
    export_refs = unique([value for value in urls + endpoint_refs if re.search(r"export|excel|xlsx|csv|descarg|download", value, flags=re.I)])
    grid_markers = unique(re.findall(r"(?i)(?:jqGrid|jsonReader|colNames|colModel|#grid|\bgrid\b)", source))
    column_blocks = re.findall(r"colNames\s*:\s*\[(.*?)\]", source, flags=re.I | re.S)
    columns: list[str] = []
    for block in column_blocks:
        columns.extend(re.findall(r"['\"]([^'\"]+)['\"]", block))
    columns.extend(re.findall(r"\b(?:label|index)\s*:\s*['\"]([^'\"]+)['\"]", source, flags=re.I))
    columns = [re.sub(r"<[^>]+>", " ", html.unescape(value)).strip() for value in columns]
    methods = unique(re.findall(r"(?:/|\.)((?:Get|Set|Post|Put|Export|Buscar|Consulta|Search|Download|Refresh)[A-Za-z0-9_]*)\b", source))
    function_names = unique(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", source))
    linked_functions = [name for name in function_names if re.search(r"grid|search|buscar|consulta|export|download|refresh|ajax|data", name, flags=re.I)]
    parameter_keys: list[str] = []
    parameters_by_endpoint: dict[str, list[str]] = {}
    for endpoint in endpoint_refs:
        endpoint_parameters: list[str] = []
        for match in re.finditer(re.escape(endpoint), source, flags=re.I):
            context = source[max(0, match.start() - 500): match.end() + 800]
            if re.search(r"\.(?:aspx|ashx|asmx)/[A-Za-z_][A-Za-z0-9_]*", endpoint, flags=re.I):
                endpoint_parameters.extend(re.findall(r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*:", context))
        parameters_by_endpoint[urllib.parse.urljoin(page_url, endpoint)] = unique(endpoint_parameters)
        parameter_keys.extend(endpoint_parameters)
    html_diagnostic = inspect_public_html(content)
    return {
        "title": re.sub(r"\s+", " ", html.unescape(title_match.group(1))).strip() if title_match else "",
        "size": len(content),
        "scripts": scripts,
        "urls": urls,
        "endpoint_refs": endpoint_refs,
        "endpoint_urls": endpoint_urls,
        "ajax_markers": ajax_markers,
        "export_refs": export_refs,
        "grid_markers": grid_markers,
        "columns": unique(columns),
        "methods": methods,
        "functions": linked_functions,
        "parameters": unique(parameter_keys),
        "parameters_by_endpoint": parameters_by_endpoint,
        "fields": html_diagnostic["fields"],
        "forms": html_diagnostic["forms"],
    }


def fetch_resource(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/javascript,text/javascript,*/*;q=0.1"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310: URL comes from the configured public page or same-domain HTML
            content = response.read()
            return {"url": url, "content": content, "status": response.status, "content_type": response.headers.get_content_type(), "error": ""}
    except urllib.error.HTTPError as exc:
        return {"url": url, "content": b"", "status": exc.code, "content_type": "", "error": f"HTTPError: {exc.code}"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"url": url, "content": b"", "status": "", "content_type": "", "error": exc.__class__.__name__}


def save_discovery_resource(output_dir: Path, content: bytes, resource_type: str, index: int, source_url: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlparse(source_url)
    stem = Path(parsed.path).stem or resource_type
    extension = ".js" if resource_type == "script" else ".html"
    filename = f"SIO_descubrimiento_{index:02d}_{safe_filename(stem)}{extension}"
    path = output_dir / filename
    path.write_bytes(content)
    return path


def discovery_endpoint_rows(evidence: dict[str, Any], source_url: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for endpoint in evidence["endpoint_urls"]:
        raw = urllib.parse.urlparse(endpoint)
        path = raw.path.lower()
        probable = "WebMethod/PageMethod AJAX" if re.search(r"\.(?:aspx|ashx|asmx)/[A-Za-z_][A-Za-z0-9_]*", raw.path, flags=re.I) else "página ASP.NET pública" if path.endswith((".aspx", ".ashx", ".asmx")) else "recurso server-side"
        confidence = "alta" if any(method.lower() in endpoint.lower() for method in evidence["methods"]) and any(marker in evidence["ajax_markers"] for marker in ["fetch(", "XMLHttpRequest", "$.ajax", ".ajax(", "PageMethods", "WebMethods"]) else "media" if path.endswith((".aspx", ".ashx", ".asmx")) else "baja"
        parameters = evidence.get("parameters_by_endpoint", {}).get(endpoint, [])
        rows.append({"endpoint": endpoint, "evidencia": f"Referencia encontrada en {source_url}", "tipo": probable, "parametros": ", ".join(parameters) or "no detectados", "confianza": confidence, "validacion": "sí", "observaciones": "No se ejecutó este endpoint durante el descubrimiento."})
    return rows


def write_discovery_report(command: str, requests: list[dict[str, Any]], html_evidence: dict[str, Any] | None, scripts: list[dict[str, Any]], endpoint_rows: list[dict[str, str]], recommendation: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "REPORTE_DESCUBRIMIENTO_SIO.md"
    lines = ["# Reporte de descubrimiento técnico SIO Granos", "", "## Fecha de ejecución", "", date.today().isoformat(), "", "## Comando ejecutado", "", f"`{command}`", "", "## Requests realizados", "", "| Número | URL | Tipo de recurso | Status code | Guardado como | Observaciones |", "| --- | --- | --- | --- | --- | --- |"]
    for index, item in enumerate(requests, start=1):
        lines.append(f"| {index} | {item['url']} | {item['type']} | {item['status'] or 'sin respuesta'} | {item.get('saved', 'no')} | {item.get('observations', '')} |")
    if not requests:
        lines.append("| — | — | — | — | no | No había endpoint público configurado. |")
    lines.extend(["", "## HTML analizado", ""])
    if html_evidence:
        lines.extend([f"- Título: {html_evidence['title'] or 'no detectado'}.", f"- Tamaño: {html_evidence['size']} bytes.", f"- Scripts detectados: {len(html_evidence['scripts'])}.", f"- Grillas detectadas: {', '.join(html_evidence['grid_markers']) or 'ninguna'}.", f"- Columnas detectadas: {', '.join(html_evidence['columns']) or 'ninguna'}.", f"- Formularios detectados: {len(html_evidence['forms'])}.", f"- Inputs/selects detectados: {', '.join(html_evidence['fields']) or 'ninguno'}.", f"- Llamadas AJAX/JavaScript detectadas: {', '.join(html_evidence['ajax_markers']) or 'ninguna'}.", f"- Referencias de exportación: {', '.join(html_evidence['export_refs']) or 'ninguna'}."])
    else:
        lines.append("No se recibió HTML para analizar.")
    lines.extend(["", "## Scripts analizados", "", "| Archivo/script | Tipo | Evidencia útil | Endpoints candidatos | Observaciones |", "| --- | --- | --- | --- | --- |"])
    for script in scripts:
        evidence = "; ".join([f"grillas: {', '.join(script['evidence']['grid_markers'])}" if script["evidence"]["grid_markers"] else "", f"métodos: {', '.join(script['evidence']['methods'])}" if script["evidence"]["methods"] else "", f"funciones: {', '.join(script['evidence']['functions'])}" if script["evidence"]["functions"] else ""])
        lines.append(f"| {script['url']} | {script['type']} | {evidence or 'sin evidencia útil'} | {', '.join(script['evidence']['endpoint_urls']) or 'ninguno'} | {script.get('observations', '')} |")
    if not scripts:
        lines.append("| — | — | No se analizaron scripts. | — | — |")
    lines.extend(["", "## Endpoints candidatos", ""])
    if endpoint_rows:
        lines.extend(["| Endpoint | Evidencia | Tipo probable | Parámetros detectados | Confianza | Requiere validación | Observaciones |", "| --- | --- | --- | --- | --- | --- | --- |"])
        lines.extend(f"| {row['endpoint']} | {row['evidencia']} | {row['tipo']} | {row['parametros']} | {row['confianza']} | {row['validacion']} | {row['observaciones']} |" for row in endpoint_rows)
    else:
        lines.append("No se detectaron endpoints candidatos robustos en HTML/scripts analizados.")
    lines.extend(["", "## Columnas y campos detectados", ""])
    columns = html_evidence["columns"] if html_evidence else []
    fields = html_evidence["fields"] if html_evidence else []
    for field in unique(columns + fields):
        lines.append(f"- {field}")
    if not columns and not fields:
        lines.append("No se detectaron nombres de columnas o campos HTML.")
    lines.extend(["", "## Hipótesis técnica", "", "- " + ("La página contiene una grilla/configuración JavaScript y referencias a servicios ASP.NET; los endpoints y parámetros requieren validación adicional." if html_evidence and (html_evidence["grid_markers"] or html_evidence["endpoint_refs"]) else "No hay evidencia suficiente para formular una hipótesis técnica."), "- No se enviaron formularios ni se ejecutaron endpoints candidatos durante este descubrimiento.", "- Los parámetros se informan sólo cuando aparecen literalmente en el HTML/script analizado.", "", "## Recomendación próxima", "", recommendation, ""])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def run_discovery(args: argparse.Namespace, config: dict[str, Any], endpoints: list[tuple[str, str]], products: list[str], windows: list[tuple[date, date]]) -> int:
    consultation = next(((name, url) for name, url in endpoints if name in {"consulta_publica", "operaciones_informadas"}), None)
    requests: list[dict[str, Any]] = []
    scripts: list[dict[str, Any]] = []
    html_evidence: dict[str, Any] | None = None
    endpoint_rows: list[dict[str, str]] = []
    output_dir = Path(args.output_dir)
    if consultation:
        result = fetch_resource(consultation[1])
        requests.append({"url": consultation[1], "type": "HTML público", "status": result["status"], "saved": "no", "observations": result["error"] or "respuesta recibida"})
        if result["content"]:
            html_evidence = extract_discovery_evidence(result["content"], consultation[1])
            if args.save_response:
                saved = save_discovery_resource(output_dir, result["content"], "html", 1, consultation[1])
                requests[-1]["saved"] = saved.name
            endpoint_rows.extend(discovery_endpoint_rows(html_evidence, consultation[1]))
            script_index = 1
            for script_url in html_evidence["scripts"]:
                if len(requests) >= args.max_requests:
                    break
                if not same_domain(script_url, config["base_url"]):
                    scripts.append({"url": script_url, "type": "script externo", "evidence": {"grid_markers": [], "methods": [], "functions": [], "endpoint_urls": []}, "observations": "No descargado: dominio externo."})
                    continue
                if generic_script(script_url):
                    scripts.append({"url": script_url, "type": "script interno", "evidence": {"grid_markers": [], "methods": [], "functions": [], "endpoint_urls": []}, "observations": "No descargado: librería genérica."})
                    continue
                script_result = fetch_resource(script_url)
                requests.append({"url": script_url, "type": "script interno", "status": script_result["status"], "saved": "no", "observations": script_result["error"] or "script recibido"})
                if script_result["content"]:
                    script_evidence = extract_discovery_evidence(script_result["content"], script_url)
                    script_item = {"url": script_url, "type": "script interno", "evidence": script_evidence, "observations": "analizado"}
                    scripts.append(script_item)
                    endpoint_rows.extend(discovery_endpoint_rows(script_evidence, script_url))
                    if args.save_response:
                        saved = save_discovery_resource(output_dir, script_result["content"], "script", script_index + 1, script_url)
                        requests[-1]["saved"] = saved.name
                    script_index += 1
    recommendation = "Realizar prueba controlada del endpoint candidato con máximo 1 request." if any(row["confianza"] == "alta" for row in endpoint_rows) else "Usar descarga manual desde navegador y probar integrador con archivo real." if html_evidence and not endpoint_rows else "Analizar tráfico desde navegador/DevTools manualmente y documentar request observado." if endpoint_rows else "Usar descarga manual desde navegador y probar integrador con archivo real."
    report = write_discovery_report(" ".join(sys.argv), requests, html_evidence, scripts, unique_endpoint_rows(endpoint_rows), recommendation)
    print(f"Descubrimiento finalizado: {len(requests)} request(s) realizados; máximo permitido: {args.max_requests}.")
    print(f"Reporte generado: {report}")
    if html_evidence:
        print(f"Título: {html_evidence['title'] or 'no detectado'}; scripts: {len(html_evidence['scripts'])}; grillas: {', '.join(html_evidence['grid_markers']) or 'ninguna'}; columnas: {', '.join(html_evidence['columns']) or 'ninguna'}.")
    else:
        print("No se recibió HTML para analizar.")
    return 0


def unique_endpoint_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if row["endpoint"] not in seen:
            seen.add(row["endpoint"])
            result.append(row)
    return result


def print_plan(products: list[str], windows: list[tuple[date, date]], endpoints: list[tuple[str, str]], output_dir: Path, max_requests: int, label: str) -> None:
    print(f"Productos solicitados: {', '.join(products)}")
    print(f"Ventanas de fechas ({len(windows)}, máximo {MAX_DAYS_HARD_LIMIT} días cada una):")
    for start, end in windows:
        print(f"  {start.isoformat()} a {end.isoformat()}")
    print(f"Endpoints candidatos configurados: {', '.join(name for name, _ in endpoints) if endpoints else 'ninguno'}")
    print(f"Carpeta raw de salida: {output_dir}")
    print(f"Cantidad máxima de requests: {max_requests}")
    print(label)


def main() -> int:
    parser = argparse.ArgumentParser(description="Exploración controlada de SIO Granos")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-web", action="store_true")
    parser.add_argument("--discover-web", action="store_true", help="analizar HTML y scripts públicos de forma controlada")
    parser.add_argument("--manual-urls", action="store_true", help="mostrar URLs para consulta manual sin llamar a la red")
    parser.add_argument("--days-back", default="30")
    parser.add_argument("--date-start")
    parser.add_argument("--date-end")
    parser.add_argument("--products", default="soja,maiz,trigo,girasol,sorgo,cebada")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--save-response", action="store_true")
    parser.add_argument("--max-requests", type=int, default=5)
    args = parser.parse_args()
    if args.max_requests < 1:
        raise SystemExit("--max-requests debe ser mayor que cero")
    if args.allow_web and args.manual_urls:
        raise SystemExit("Use --allow-web o --manual-urls, no ambos")
    if args.discover_web and (args.dry_run or args.allow_web or args.manual_urls):
        raise SystemExit("Use --discover-web como modo independiente")
    catalog = read_catalog()
    products = parse_products(args.products, catalog)
    start, end = date_range(args)
    config = load_config()
    max_days = config["max_days_per_request"]
    windows = split_date_range(start, end, max_days)
    endpoints = candidate_endpoints(config)

    if args.discover_web:
        return run_discovery(args, config, endpoints, products, windows)

    if not args.allow_web and not args.dry_run and not args.manual_urls:
        print(SAFE_MESSAGE)
        return 0

    print("Fuente: SIO Granos / Secretaría de Agricultura")
    print_plan(products, windows, endpoints, Path(args.output_dir), args.max_requests, "")
    if args.dry_run:
        print("Dry-run: no se descargará nada.")
        for name, endpoint in endpoints:
            print(f"  {name}: {endpoint}")
        print("No se realizan llamadas externas ni se guardan respuestas.")
        return 0

    consultation = next(((name, url) for name, url in endpoints if name in {"consulta_publica", "operaciones_informadas"}), None)
    if args.manual_urls:
        if not consultation:
            print("No hay endpoint de consulta pública configurado; use la URL pública de SIO y coloque las descargas en raw/.")
            return 0
        for product in products:
            row = catalog_row(catalog, product)
            product_id = row.get("sio_id_producto", "").strip() if row else ""
            for window_start, window_end in windows:
                print(suggested_url(consultation[1], product, product_id, window_start, window_end))
        print("URLs generadas para descarga manual; no se realizaron llamadas externas.")
        return 0

    if not endpoints or not consultation:
        print("No hay endpoints SIO configurados. Complete data/commodities_sio/sio_config.json con una URL pública documentada o use una respuesta manual en raw/.")
        return 0

    output_dir = Path(args.output_dir)
    requests_done = 0
    diagnostic_saved = False
    exports_found = False
    for product in products:
        for window_start, window_end in windows:
            if requests_done >= args.max_requests:
                print("Se alcanzó --max-requests; no se harán más consultas.")
                break
            row = catalog_row(catalog, product)
            product_id = row.get("sio_id_producto", "").strip() if row else ""
            url = suggested_url(consultation[1], product, product_id, window_start, window_end)
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}, method="GET")
            try:
                with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310: explicit local config plus --allow-web
                    content = response.read()
                    content_type = response.headers.get_content_type()
                requests_done += 1
                print(f"Consulta pública completada para {product} ({window_start} a {window_end}).")
                if "html" in content_type or b"<form" in content[:1000].lower():
                    diagnostic = print_html_diagnostic(content)
                    exports_found = exports_found or bool(diagnostic["exports"])
                    if args.save_response and not diagnostic_saved:
                        saved = save_html_diagnostic(output_dir, content)
                        diagnostic_saved = True
                        print(f"Diagnóstico HTML guardado: {saved}")
                elif args.save_response:
                    saved = save_response(output_dir, product, window_start, window_end, consultation[0], content, content_type)
                    print(f"Respuesta guardada: {saved}")
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
                requests_done += 1
                print(f"No se pudo consultar SIO para {product}: {exc.__class__.__name__}")
        if requests_done >= args.max_requests:
            break
    if not exports_found:
        print("No se pudo automatizar la exportación todavía. Use --manual-urls o descargue manualmente desde la consulta pública.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
