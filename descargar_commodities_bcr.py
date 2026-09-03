#!/usr/bin/env python3
"""Diagnóstico y descarga opcional de commodities BCR.

La red sólo se utiliza cuando el usuario configura explícitamente un endpoint
y la autenticación requerida. Sin esa configuración, el script es un fallback
manual seguro y termina con código cero.
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


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Carga un .env simple sin sobrescribir variables ya presentes."""
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
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


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
    base_url = os.getenv("BCR_API_BASE_URL", "").strip()
    endpoint = os.getenv("BCR_API_PRICES_ENDPOINT", "").strip()
    user = os.getenv("BCR_API_USER", "").strip()
    password = os.getenv("BCR_API_PASSWORD", "").strip()
    token = os.getenv("BCR_API_TOKEN", "").strip()
    use_auth = env_bool("BCR_API_USE_AUTH", True)
    # No se inventa un flujo de login: si la API exige auth, sólo se consulta
    # cuando ya existe un token Bearer explícito.
    auth_ready = not use_auth or bool(token)
    return {
        "base_url": base_url,
        "endpoint": endpoint,
        "user": user,
        "password": password,
        "token": token,
        "use_auth": use_auth,
        "auth_ready": auth_ready,
        "has_endpoint": bool(endpoint),
        "api_ready": bool(base_url and endpoint and auth_ready),
    }


def read_catalog() -> list[dict[str, str]]:
    if not CATALOG_PATH.exists():
        return []
    with CATALOG_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def normalize(value: str) -> str:
    value = value.strip().lower()
    return re.sub(r"\s+", " ", value)


def catalog_products(catalog: list[dict[str, str]]) -> list[str]:
    return [row["commodity"].strip() for row in catalog if row.get("commodity") and normalize(row.get("activo", "true")) == "true"]


def parse_products(value: str | None, catalog: list[dict[str, str]]) -> list[str]:
    requested = [item.strip() for item in (value or "").split(",") if item.strip()]
    if not requested:
        requested = catalog_products(catalog) or ["Soja", "Maíz", "Trigo", "Girasol", "Sorgo", "Cebada"]
    alias_map: dict[str, str] = {}
    for row in catalog:
        canonical = row.get("commodity", "").strip()
        for alias in (row.get("aliases", "") + "|" + canonical).split("|"):
            if alias.strip():
                alias_map[normalize(alias)] = canonical
    result: list[str] = []
    for item in requested:
        canonical = alias_map.get(normalize(item), item)
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


def windows(start: date, end: date, size: int = 7) -> list[tuple[date, date]]:
    result = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=size - 1), end)
        result.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return result


def catalog_id(catalog: list[dict[str, str]], product: str) -> str:
    target = normalize(product)
    for row in catalog:
        names = [row.get("commodity", "")] + row.get("aliases", "").split("|")
        if target in {normalize(name) for name in names if name}:
            return row.get("bcr_id_grano", "").strip()
    return ""


def endpoint_url(config: dict[str, Any]) -> str:
    base = config["base_url"].rstrip("/")
    endpoint = config["endpoint"]
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return f"{base}/{endpoint.lstrip('/')}"


def fetch_window(config: dict[str, Any], product: str, grain_id: str, start: date, end: date) -> Any:
    """Realiza una consulta sólo con configuración explícita.

    El esquema de parámetros se mantiene genérico hasta confirmar la API BCR.
    """
    params = {
        "date_start": start.isoformat(),
        "date_end": end.isoformat(),
        "commodity": product,
    }
    if grain_id:
        params["bcr_id_grano"] = grain_id
    url = endpoint_url(config) + "?" + urllib.parse.urlencode(params)
    headers = {"Accept": "application/json"}
    if config["use_auth"] and config["token"]:
        headers["Authorization"] = f"Bearer {config['token']}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310: URL is explicit user config
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"falló la consulta para {product} ({start} a {end}): {exc.__class__.__name__}") from exc


def save_response(output_dir: Path, product: str, start: date, end: date, payload: Any) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_product = re.sub(r"[^a-z0-9]+", "_", normalize(product)).strip("_")
    path = output_dir / f"bcr_api_{safe_product}_{start}_{end}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico/descarga controlada de precios de commodities BCR")
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
    query_windows = windows(start, end)
    missing_ids = [product for product in products if not catalog_id(catalog, product)]

    print("Modo dry-run activo: no se descargará nada." if args.dry_run else "Modo descarga controlada activo.")
    print(f"Productos considerados: {', '.join(products)}")
    print(f"Rango de fechas: {start.isoformat()} a {end.isoformat()} ({(end - start).days + 1} días)")
    print(f"Ventanas de consulta: {len(query_windows)} de hasta 7 días")
    print(f"Configuración API: {'disponible' if config['api_ready'] else 'incompleta'}")
    print(f"Endpoint: {safe_url(config['endpoint']) if config['endpoint'] else '(faltante)'}")
    print(f"BCR_API_BASE_URL: {safe_url(config['base_url'])}")
    print(f"BCR_API_USER: {mask_user(config['user'])}")
    print(f"BCR_API_PASSWORD: {mask_secret(config['password'])}")
    print(f"BCR_API_TOKEN: {mask_secret(config['token'])}")
    print(f"Autenticación requerida: {'sí' if config['use_auth'] else 'no'}")
    if not config["has_endpoint"]:
        print("Falta BCR_API_PRICES_ENDPOINT: no se conoce un endpoint confirmado; no se hará ninguna llamada.")
    if config["use_auth"] and not config["auth_ready"]:
        print("Falta token Bearer API BCR: configure BCR_API_TOKEN en .env (o gestione el intercambio usuario/contraseña fuera de este script) para un acceso autorizado.")
    if missing_ids:
        print(f"bcr_id_grano pendiente de validar para: {', '.join(missing_ids)}")
    print(f"Salida prevista: {Path(args.output_dir)}")

    if args.dry_run:
        for product in products:
            print(f"  - {product}: {len(query_windows)} ventana(s)")
        print("Dry-run finalizado. Próximo paso: descargue archivos manuales en data/commodities_bcr/raw/ o complete .env con acceso autorizado.")
        return 0

    if not config["api_ready"]:
        print("No hay credenciales/API BCR configurada. Para avanzar, descargue archivos manuales en data/commodities_bcr/raw/ o complete .env con acceso autorizado.")
        return 0

    errors = 0
    for product in products:
        grain_id = catalog_id(catalog, product)
        for window_start, window_end in query_windows:
            try:
                payload = fetch_window(config, product, grain_id, window_start, window_end)
                saved = save_response(Path(args.output_dir), product, window_start, window_end, payload)
                print(f"Descargado {product}: {saved}")
            except RuntimeError as exc:
                errors += 1
                print(f"ERROR: {exc}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
