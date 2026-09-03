#!/usr/bin/env python3
"""Exploración pública controlada de SIO Granos.

No contiene endpoints de SIO ni credenciales. Sólo consulta URLs que el usuario
configure explícitamente en data/commodities_sio/sio_config.json y con
--allow-web.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
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
USER_AGENT = "Serie-Agricola commodities-sio exploratory client"


def normalize(value: str) -> str:
    import unicodedata
    value = unicodedata.normalize("NFKD", value.strip().lower())
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
        requested = [row["commodity"] for row in catalog if row.get("commodity") and normalize(row.get("activo", "true")) == "true"]
    aliases: dict[str, str] = {}
    for row in catalog:
        canonical = row.get("commodity", "").strip()
        for alias in [canonical] + row.get("aliases", "").split("|"):
            if alias:
                aliases[normalize(alias)] = canonical
    result = []
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


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"base_url": "", "endpoints": {}, "configured": False}
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR leyendo {CONFIG_PATH}: {exc}")
        return {"base_url": "", "endpoints": {}, "configured": False}
    endpoints = raw.get("endpoints", {}) if isinstance(raw, dict) else {}
    endpoints = {str(name): str(value).strip() for name, value in endpoints.items() if value}
    base_url = str(raw.get("base_url", "")).strip() if isinstance(raw, dict) else ""
    return {"base_url": base_url, "endpoints": endpoints, "configured": bool(base_url and endpoints)}


def endpoint_url(base_url: str, endpoint: str) -> str:
    if endpoint.startswith(("http://", "https://")):
        return endpoint
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def candidate_endpoints(config: dict[str, Any]) -> list[tuple[str, str]]:
    preferred = ("precios_referencia", "consulta_publica", "operaciones")
    return [(name, endpoint_url(config["base_url"], config["endpoints"][name])) for name in preferred if config["endpoints"].get(name)]


def suggested_url(endpoint: str, product: str, product_id: str, start: date, end: date) -> str:
    params = {"date_start": start.isoformat(), "date_end": end.isoformat(), "producto": product}
    if product_id:
        params["sio_id_producto"] = product_id
    return endpoint + ("&" if "?" in endpoint else "?") + urllib.parse.urlencode(params)


def catalog_row(catalog: list[dict[str, str]], product: str) -> dict[str, str] | None:
    target = normalize(product)
    for row in catalog:
        names = [row.get("commodity", "")] + row.get("aliases", "").split("|")
        if target in {normalize(name) for name in names if name}:
            return row
    return None


def save_response(output_dir: Path, product: str, start: date, end: date, endpoint_name: str, content: bytes, content_type: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    extension = ".json" if "json" in content_type or not content_type else ".json"
    if "spreadsheet" in content_type:
        extension = ".xlsx"
    elif "csv" in content_type:
        extension = ".csv"
    filename = f"SIO_{endpoint_name}_{start}_{end}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{normalize(product).replace(' ', '_')}{extension}"
    path = output_dir / re.sub(r"[^A-Za-z0-9_.-]", "_", filename)
    path.write_bytes(content)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Exploración controlada de SIO Granos")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-web", action="store_true")
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
    catalog = read_catalog()
    products = parse_products(args.products, catalog)
    start, end = date_range(args)
    config = load_config()
    endpoints = candidate_endpoints(config)

    if not args.allow_web and not args.dry_run:
        print("Modo seguro: no se realizan llamadas externas. Use --dry-run para ver la consulta o --allow-web para ejecutar una exploración pública controlada.")
        return 0
    print("Fuente: SIO Granos / Secretaría de Agricultura")
    print(f"Productos solicitados: {', '.join(products)}")
    print(f"Rango de fechas: {start.isoformat()} a {end.isoformat()}")
    print(f"Endpoints candidatos configurados: {', '.join(name for name, _ in endpoints) if endpoints else 'ninguno'}")
    print(f"Carpeta raw de salida: {Path(args.output_dir)}")
    print(f"Cantidad máxima de requests: {args.max_requests}")
    if args.dry_run:
        print("Dry-run: no se descargará nada.")
        for name, endpoint in endpoints:
            print(f"  {name}: {endpoint} (URL sugerida por producto y rango)")
        print("Próximo paso: complete sio_config.json sólo con endpoints públicos documentados y use --allow-web, o coloque una respuesta manual en raw/.")
        return 0
    if not endpoints:
        print("No hay endpoints SIO configurados. Complete data/commodities_sio/sio_config.json con una URL pública documentada o use una respuesta manual en raw/.")
        return 0

    requests_done = 0
    for product in products:
        if requests_done >= args.max_requests:
            print("Se alcanzó --max-requests; no se harán más consultas.")
            break
        row = catalog_row(catalog, product)
        product_id = row.get("sio_id_producto", "").strip() if row else ""
        endpoint_name, endpoint = endpoints[0]
        url = suggested_url(endpoint, product, product_id, start, end)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}, method="GET")
            with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310: endpoint is explicit local config and --allow-web is required
                content = response.read()
                content_type = response.headers.get_content_type()
            requests_done += 1
            print(f"Consulta pública completada para {product}: HTTP response recibida.")
            if args.save_response:
                saved = save_response(Path(args.output_dir), product, start, end, endpoint_name, content, content_type)
                print(f"Respuesta guardada: {saved}")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            requests_done += 1
            print(f"No se pudo consultar SIO para {product}: {exc.__class__.__name__}")
            print(f"Revise el endpoint configurado o use descarga manual para: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
