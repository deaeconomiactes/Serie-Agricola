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
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "commodities_sio"
CONFIG_PATH = DATA_DIR / "sio_config.json"
CATALOG_PATH = DATA_DIR / "catalogo_productos_sio.csv"
DEFAULT_OUTPUT = DATA_DIR / "raw"
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
    catalog = read_catalog()
    products = parse_products(args.products, catalog)
    start, end = date_range(args)
    config = load_config()
    max_days = config["max_days_per_request"]
    windows = split_date_range(start, end, max_days)
    endpoints = candidate_endpoints(config)

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
