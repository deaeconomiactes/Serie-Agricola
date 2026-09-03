#!/usr/bin/env python3
"""Descarga controlada de precios BCR: manual, public-web o API opt-in.

Por defecto no se realizan llamadas externas. Los modos web y API requieren
una bandera explícita y nunca imprimen secretos.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "data" / "commodities_bcr" / "catalogo_commodities_bcr.csv"
PUBLIC_QUERY_URL = "https://www.cac.bcr.com.ar/es/precios-de-pizarra/consultas"
USER_AGENT = "Serie-Agricola commodities-bcr manual/public-web client"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def mask_secret(value: str | None) -> str:
    return "********" if value else "(vacío)"


def mask_user(value: str | None) -> str:
    if not value:
        return "(vacío)"
    if "@" in value:
        local, domain = value.split("@", 1)
        return f"{local[:1]}***@{domain[:1]}***"
    return f"{value[:1]}***"


def safe_url(value: str | None) -> str:
    if not value:
        return "(vacío)"
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "(configurada, formato no mostrado)"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def load_config() -> dict[str, Any]:
    prices_endpoint = os.getenv("BCR_API_PRECIOS_CAMARA_ENDPOINT", "").strip() or os.getenv("BCR_API_PRICES_ENDPOINT", "").strip()
    return {
        "base_url": os.getenv("BCR_API_BASE_URL", "").strip(),
        "login_endpoint": os.getenv("BCR_API_LOGIN_ENDPOINT", "").strip(),
        "prices_endpoint": prices_endpoint,
        "user": os.getenv("BCR_API_USER", "").strip(),
        "password": os.getenv("BCR_API_PASSWORD", "").strip(),
        "api_key": os.getenv("BCR_API_KEY", "").strip(),
        "api_secret": os.getenv("BCR_API_SECRET", "").strip(),
        "token": os.getenv("BCR_API_TOKEN", "").strip(),
        "use_auth": env_bool("BCR_API_USE_AUTH", True),
    }


def api_ready(config: dict[str, Any]) -> bool:
    auth_ready = not config["use_auth"] or bool(config["token"] or (config["api_key"] and config["api_secret"]))
    return bool(config["base_url"] and config["prices_endpoint"] and auth_ready)


def read_catalog() -> list[dict[str, str]]:
    if not CATALOG_PATH.exists():
        return []
    with CATALOG_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def normalize(value: str) -> str:
    import unicodedata
    value = unicodedata.normalize("NFKD", value.strip().lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value)


def catalog_products(catalog: list[dict[str, str]]) -> list[str]:
    return [row["commodity"].strip() for row in catalog if row.get("commodity") and normalize(row.get("activo", "true")) == "true"]


def parse_products(value: str | None, catalog: list[dict[str, str]]) -> list[str]:
    requested = [item.strip() for item in (value or "").split(",") if item.strip()]
    if not requested:
        requested = catalog_products(catalog) or ["Soja", "Maíz", "Trigo", "Girasol", "Sorgo", "Cebada"]
    aliases: dict[str, str] = {}
    for row in catalog:
        canonical = row.get("commodity", "").strip()
        for alias in (row.get("aliases", "") + "|" + canonical).split("|"):
            if alias.strip():
                aliases[normalize(alias)] = canonical
    result: list[str] = []
    for item in requested:
        canonical = aliases.get(normalize(item), item)
        if canonical not in result:
            result.append(canonical)
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


def split_date_range(start: date, end: date, max_days: int = 7) -> list[tuple[date, date]]:
    result: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=max_days - 1), end)
        result.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return result


def catalog_row(catalog: list[dict[str, str]], product: str) -> dict[str, str] | None:
    target = normalize(product)
    for row in catalog:
        names = [row.get("commodity", "")] + row.get("aliases", "").split("|")
        if target in {normalize(name) for name in names if name}:
            return row
    return None


def catalog_id(catalog: list[dict[str, str]], product: str, field: str) -> str:
    row = catalog_row(catalog, product)
    return row.get(field, "").strip() if row else ""


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize(value)).strip("_")


def manual_url(product: str, start: date, end: date, catalog: list[dict[str, str]]) -> str:
    public_id = catalog_id(catalog, product, "bcr_public_product_id")
    query = {
        "producto": public_id or product,
        "desde": start.isoformat(),
        "hasta": end.isoformat(),
        "periodo": "diario",
        "precios": "Precio de Pizarra",
    }
    return f"{PUBLIC_QUERY_URL}?{urllib.parse.urlencode(query)}"


def print_manual_urls(products: list[str], start: date, end: date, catalog: list[dict[str, str]]) -> None:
    print(f"Consulta pública BCR/Cámara Arbitral: {PUBLIC_QUERY_URL}")
    print("Nota: la página puede requerir completar los filtros manualmente si no acepta parámetros en la URL.")
    for product in products:
        print(f"\n{product}:")
        print(f"URL: {manual_url(product, start, end, catalog)}")
        print("Guardar como:")
        print(f"data/commodities_bcr/raw/BCR_pizarra_{slug(product)}_{start}_{end}.xlsx")
        if not catalog_id(catalog, product, "bcr_public_product_id"):
            print(f"No se conoce el identificador BCR para {product}. Complete bcr_id_grano o bcr_public_product_id en catalogo_commodities_bcr.csv.")


def fetch_url(url: str, headers: dict[str, str] | None = None) -> tuple[bytes, str]:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310: URL is a public/configured target after explicit opt-in
        return response.read(), response.headers.get_content_type()


def find_download_link(html: bytes, page_url: str) -> str | None:
    text = html.decode("utf-8", errors="ignore")
    match = re.search(r"(?:href|src)\s*=\s*[\"']([^\"']+\.(?:xlsx?|csv)(?:\?[^\"']*)?)[\"']", text, re.IGNORECASE)
    if not match:
        return None
    candidate = urllib.parse.urljoin(page_url, match.group(1))
    parsed = urllib.parse.urlsplit(candidate)
    return candidate if parsed.scheme in {"http", "https"} else None


def safe_diagnostic(html: bytes) -> bool:
    return not re.search(rb"password|token|api[_-]?key|secret", html[:500000], re.IGNORECASE)


def save_bytes(output_dir: Path, filename: str, data: bytes) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    if path.exists():
        path = output_dir / f"{path.stem}_{datetime.now().strftime('%H%M%S')}{path.suffix}"
    path.write_bytes(data)
    return path


def public_web_download(products: list[str], start: date, end: date, catalog: list[dict[str, str]], output_dir: Path) -> int:
    errors = 0
    for product in products:
        query_url = manual_url(product, start, end, catalog)
        try:
            html, content_type = fetch_url(query_url)
            link = find_download_link(html, query_url)
            if not link:
                if safe_diagnostic(html):
                    diagnostic = save_bytes(output_dir, f"BCR_public_web_diagnostic_{slug(product)}_{start}_{end}.html", html[:500000])
                    print(f"Diagnóstico HTML guardado: {diagnostic}")
                print("No se pudo detectar automáticamente el enlace de descarga Excel. Use la URL manual generada.")
                print(f"{product}: {query_url}")
                continue
            data, link_type = fetch_url(link)
            extension = ".xlsx" if ".xlsx" in link.lower() or "spreadsheetml" in link_type else ".xls" if ".xls" in link.lower() else ".csv"
            filename = f"BCR_pizarra_{slug(product)}_{start}_{end}{extension}"
            saved = save_bytes(output_dir, filename, data)
            print(f"Descarga public-web completada para {product}: {saved}")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            errors += 1
            print(f"No se pudo descargar public-web para {product}: {exc.__class__.__name__}")
            print("No se pudo detectar automáticamente el enlace de descarga Excel. Use la URL manual generada.")
            print(f"{product}: {query_url}")
    return 1 if errors == len(products) and products else 0


def endpoint_url(config: dict[str, Any]) -> str:
    endpoint = config["prices_endpoint"]
    if endpoint.startswith(("http://", "https://")):
        return endpoint
    return f"{config['base_url'].rstrip('/')}/{endpoint.lstrip('/')}"


def next_page(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    candidates = [payload.get("next"), payload.get("next_url"), payload.get("nextPage")]
    pagination = payload.get("pagination")
    if isinstance(pagination, dict):
        candidates.extend([pagination.get("next"), pagination.get("next_url")])
    return next((value for value in candidates if isinstance(value, str) and value), None)


def fetch_api_window(config: dict[str, Any], product: str, grain_id: str, start: date, end: date) -> list[Any]:
    base = endpoint_url(config)
    params = {"date_start": start.isoformat(), "date_end": end.isoformat(), "commodity": product, "bcr_id_grano": grain_id}
    current = base + "?" + urllib.parse.urlencode(params)
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if config["token"]:
        headers["Authorization"] = f"Bearer {config['token']}"
    elif config["api_key"] and config["api_secret"]:
        headers["X-API-Key"] = config["api_key"]
        headers["X-API-Secret"] = config["api_secret"]
    pages: list[Any] = []
    for _ in range(20):
        body, _ = fetch_url(current, headers)
        payload = json.loads(body.decode("utf-8"))
        pages.append(payload)
        link = next_page(payload)
        if not link:
            break
        current = urllib.parse.urljoin(current, link)
    return pages


def save_api_response(output_dir: Path, product: str, grain_id: str, start: date, end: date, config: dict[str, Any], pages: list[Any]) -> Path:
    metadata = {"commodity": product, "id_grano": grain_id, "fecha_desde": start.isoformat(), "fecha_hasta": end.isoformat(), "fecha_descarga": datetime.now().isoformat(timespec="seconds"), "endpoint_usado": safe_url(endpoint_url(config))}
    return save_bytes(output_dir, f"BCR_API_{slug(product)}_{start}_{end}.json", json.dumps({"metadata": metadata, "data": pages}, ensure_ascii=False, indent=2).encode("utf-8"))


def api_download(products: list[str], start: date, end: date, catalog: list[dict[str, str]], config: dict[str, Any], output_dir: Path) -> int:
    missing = [product for product in products if not catalog_id(catalog, product, "bcr_id_grano")]
    if not api_ready(config):
        print("No hay configuración API BCR completa. Use --manual-urls o coloque archivos manuales en raw.")
        return 0
    if missing:
        for product in missing:
            print(f"No se conoce el identificador BCR para {product}. Complete bcr_id_grano en catalogo_commodities_bcr.csv.")
        return 0
    errors = 0
    for product in products:
        grain_id = catalog_id(catalog, product, "bcr_id_grano")
        for window_start, window_end in split_date_range(start, end, max_days=7):
            try:
                pages = fetch_api_window(config, product, grain_id, window_start, window_end)
                saved = save_api_response(output_dir, product, grain_id, window_start, window_end, config, pages)
                print(f"API descargada para {product}, ventana {window_start} a {window_end}: {saved}")
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                errors += 1
                print(f"ERROR API para {product}, ventana {window_start} a {window_end}: {exc.__class__.__name__}", file=sys.stderr)
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Descarga controlada de precios BCR/Cámara Arbitral")
    parser.add_argument("--source", choices=("manual", "public-web", "api"), default="manual")
    parser.add_argument("--manual-urls", action="store_true")
    parser.add_argument("--allow-web", action="store_true")
    parser.add_argument("--allow-api", action="store_true")
    parser.add_argument("--days-back", default=os.getenv("BCR_COMMODITIES_DEFAULT_DAYS_BACK", "30"))
    parser.add_argument("--date-start")
    parser.add_argument("--date-end")
    parser.add_argument("--products", help="Lista separada por comas; por defecto usa el catálogo activo")
    parser.add_argument("--output-dir", default="data/commodities_bcr/raw/")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    config = load_config()
    catalog = read_catalog()
    products = parse_products(args.products, catalog)
    start, end = date_range(args)
    output_dir = Path(args.output_dir)

    print(f"Modo seleccionado: {'dry-run' if args.dry_run else 'manual-urls' if args.manual_urls else args.source}")
    print(f"Productos: {', '.join(products)}")
    print(f"Rango: {start.isoformat()} a {end.isoformat()}; período: diario; tipo de precio: Precio de Pizarra")
    print(f"Ventanas API de máximo 7 días: {len(split_date_range(start, end))}")
    print(f"Configuración API detectada: {'completa' if api_ready(config) else 'incompleta'}")
    print(f"BCR_API_BASE_URL: {safe_url(config['base_url'])}")
    print(f"Endpoint precios Cámara: {safe_url(config['prices_endpoint']) if config['prices_endpoint'] else '(faltante)'}")
    print(f"BCR_API_USER: {mask_user(config['user'])}")
    print(f"BCR_API_PASSWORD: {mask_secret(config['password'])}")
    print(f"BCR_API_KEY: {mask_secret(config['api_key'])}")
    print(f"BCR_API_SECRET: {mask_secret(config['api_secret'])}")
    print(f"BCR_API_TOKEN: {mask_secret(config['token'])}")
    missing_grain = [product for product in products if not catalog_id(catalog, product, "bcr_id_grano")]
    if missing_grain:
        print(f"bcr_id_grano pendiente de validar para: {', '.join(missing_grain)}")

    if args.dry_run:
        print("Modo dry-run activo: no se descarga ni se consulta la red.")
        print_manual_urls(products, start, end, catalog)
        return 0
    if args.manual_urls:
        print_manual_urls(products, start, end, catalog)
        return 0
    if args.source == "public-web":
        if not args.allow_web:
            print("Modo seguro: no se realizan llamadas externas. Use --dry-run, --manual-urls, --allow-web o --allow-api según corresponda.")
            print_manual_urls(products, start, end, catalog)
            return 0
        return public_web_download(products, start, end, catalog, output_dir)
    if args.source == "api":
        if not args.allow_api:
            print("Modo seguro: no se realizan llamadas externas. Use --dry-run, --manual-urls, --allow-web o --allow-api según corresponda.")
            return 0
        return api_download(products, start, end, catalog, config, output_dir)
    print("Modo seguro: no se realizan llamadas externas. Use --dry-run, --manual-urls, --allow-web o --allow-api según corresponda.")
    print("Para avanzar sin red, use --manual-urls y descargue el Excel manualmente en data/commodities_bcr/raw/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
