"""Descargador BCR seguro con dry-run, ventanas y fallback manual.

La API sólo se consulta cuando el usuario configura explícitamente un endpoint
en ``BCR_API_PRECIOS_CAMARA_ENDPOINT`` y una autenticación válida. En dry-run
no se realiza ninguna llamada ni se escriben archivos de datos.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "data" / "commodities_bcr" / "raw"
CATALOG_PATH = PROJECT_DIR / "data" / "commodities_bcr" / "catalogo_commodities_bcr.csv"
DEFAULT_PRODUCTS = ("soja", "maiz", "trigo", "girasol", "sorgo")
FALLBACK_ALIASES = {
    "soja": "Soja", "soya": "Soja", "maiz": "Maíz", "maíz": "Maíz", "corn": "Maíz",
    "trigo": "Trigo", "wheat": "Trigo", "girasol": "Girasol", "sunflower": "Girasol",
    "sorgo": "Sorgo", "sorghum": "Sorgo", "cebada": "Cebada", "barley": "Cebada",
}


def mask_secret(value: str) -> str:
    """Oculta completamente un secreto, indicando sólo si está presente."""
    return "********" if value else "(vacío)"


def _mask_user(value: str) -> str:
    if not value:
        return "(vacío)"
    return f"{value[0]}***@***" if "@" in value else f"{value[0]}***"


def _safe_url(value: str) -> str:
    if not value:
        return "(vacía)"
    try:
        parts = urlsplit(value)
        if not parts.scheme or not parts.netloc:
            return "(configurada; formato no verificable)"
        return urlunsplit((parts.scheme, parts.hostname or parts.netloc, parts.path, "", ""))
    except ValueError:
        return "(configurada; formato no verificable)"


def _slug(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _env_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "sí", "si", "yes", "y"}


def load_dotenv(path: Path = PROJECT_DIR / ".env") -> None:
    """Carga valores locales sin sobrescribir el entorno del proceso."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_bcr_config() -> dict[str, object]:
    """Devuelve un resumen seguro de configuración, sin valores secretos."""
    base_url = os.getenv("BCR_API_BASE_URL", "").strip()
    user = os.getenv("BCR_API_USER", "").strip()
    password = os.getenv("BCR_API_PASSWORD", "")
    token = os.getenv("BCR_API_TOKEN", "")
    endpoint = os.getenv("BCR_API_PRECIOS_CAMARA_ENDPOINT", "").strip()
    use_auth = _env_bool(os.getenv("BCR_API_USE_AUTH"), True)
    has_credentials = not use_auth or bool(token or (user and password))
    return {
        "api_base_url": base_url,
        "has_user": bool(user),
        "has_password": bool(password),
        "has_token": bool(token),
        "use_auth": use_auth,
        "is_configured": bool(base_url and endpoint and has_credentials),
        "has_endpoint": bool(endpoint),
        "precios_camara_endpoint": endpoint,
    }


def _read_catalog() -> dict[str, dict[str, str]]:
    catalog: dict[str, dict[str, str]] = {}
    if not CATALOG_PATH.exists():
        return catalog
    with CATALOG_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            commodity = (row.get("commodity") or "").strip()
            if not commodity:
                continue
            aliases = [commodity, *(item.strip() for item in (row.get("aliases") or "").split("|"))]
            entry = {"commodity": commodity, "bcr_id_grano": (row.get("bcr_id_grano") or "").strip()}
            for alias in aliases:
                key = re.sub(r"[^a-záéíóúüñ0-9]", "", alias.lower())
                if key:
                    catalog[key] = entry
    return catalog


def normalize_product(value: str, catalog: dict[str, dict[str, str]] | None = None) -> str:
    catalog = catalog if catalog is not None else _read_catalog()
    key = re.sub(r"[^a-záéíóúüñ0-9]", "", value.strip().lower())
    if key in catalog:
        return catalog[key]["commodity"]
    return FALLBACK_ALIASES.get(key, value.strip())


def parse_products(value: str, catalog: dict[str, dict[str, str]] | None = None) -> tuple[list[str], list[str]]:
    catalog = catalog if catalog is not None else _read_catalog()
    requested = [item.strip() for item in value.split(",") if item.strip()]
    normalized = list(dict.fromkeys(normalize_product(item, catalog) for item in requested))
    return requested, normalized


def split_date_range(start_date: date, end_date: date, max_days: int = 7) -> list[tuple[date, date]]:
    """Divide un rango inclusivo en ventanas de como máximo ``max_days`` días."""
    if max_days < 1:
        raise ValueError("max_days debe ser mayor que cero")
    if start_date > end_date:
        raise ValueError("la fecha inicial no puede ser posterior a la fecha final")
    windows = []
    cursor = start_date
    while cursor <= end_date:
        window_end = min(cursor + timedelta(days=max_days - 1), end_date)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


def _endpoint_url(config: dict[str, object]) -> str:
    endpoint = str(config.get("precios_camara_endpoint", "") or "")
    base = str(config.get("api_base_url", "") or "")
    return endpoint if endpoint.startswith(("http://", "https://")) else urljoin(base.rstrip("/") + "/", endpoint.lstrip("/"))


def fetch_bcr_prices(product: str, start_date: date, end_date: date, config: dict[str, object]):
    """Consulta el endpoint configurado, o retorna ``None`` con diagnóstico claro."""
    endpoint = str(config.get("precios_camara_endpoint", "") or "")
    if not endpoint:
        print("Falta configurar BCR_API_PRECIOS_CAMARA_ENDPOINT; no se realiza llamada API.")
        return None
    if not bool(config.get("is_configured")):
        print("La configuración API BCR está incompleta; no se realiza llamada API.")
        return None
    token = os.getenv("BCR_API_TOKEN", "")
    if bool(config.get("use_auth")) and not token:
        print("La consulta API requiere un token Bearer configurado; no se realiza llamada API.")
        return None
    params = {"product": product, "dateStart": start_date.isoformat(), "dateEnd": end_date.isoformat()}
    if config.get("_bcr_id_grano"):
        params["bcr_id_grano"] = str(config["_bcr_id_grano"])
    request = Request(f"{_endpoint_url(config)}?{urlencode(params)}", headers={"Accept": "application/json"})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(request, timeout=30) as response:  # sólo se ejecuta con endpoint configurado explícitamente
            body = response.read()
    except Exception as exc:
        print(f"Error consultando API BCR para {product}: {type(exc).__name__}")
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        print(f"La respuesta API BCR para {product} no es JSON válido; no se guarda.")
        return None


def _unique_output_path(output_dir: Path, product: str, start_date: date, end_date: date) -> Path:
    base = output_dir / f"BCR_API_precios_camara_{_slug(product)}_{start_date}_{end_date}.json"
    candidate, suffix = base, 1
    while candidate.exists():
        candidate = base.with_name(f"{base.stem}_{suffix}{base.suffix}")
        suffix += 1
    return candidate


def save_raw_response(payload, output_dir: Path, product: str, start_date: date, end_date: date, endpoint: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = _unique_output_path(output_dir, product, start_date, end_date)
    wrapped = {"metadata": {"fecha_descarga": date.today().isoformat(), "producto": product, "rango": f"{start_date} a {end_date}", "endpoint": _safe_url(endpoint)}, "data": payload}
    path.write_text(json.dumps(wrapped, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _resolve_dates(args: argparse.Namespace, default_days: int) -> tuple[date, date]:
    end = date.fromisoformat(args.date_end) if args.date_end else date.today()
    start = date.fromisoformat(args.date_start) if args.date_start else end - timedelta(days=args.days_back if args.days_back is not None else default_days)
    if start > end:
        raise ValueError("--date-start no puede ser posterior a --date-end")
    return start, end


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days-back", type=int, default=None)
    parser.add_argument("--date-start")
    parser.add_argument("--date-end")
    parser.add_argument("--products", default=",".join(DEFAULT_PRODUCTS))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    default_days = int(os.getenv("BCR_COMMODITIES_DEFAULT_DAYS_BACK", "30") or "30")
    if (args.days_back if args.days_back is not None else default_days) < 0:
        parser.error("--days-back debe ser mayor o igual a cero")
    try:
        start_date, end_date = _resolve_dates(args, default_days)
    except ValueError as exc:
        parser.error(str(exc))
    catalog = _read_catalog()
    requested, products = parse_products(args.products, catalog)
    config = load_bcr_config()
    windows = split_date_range(start_date, end_date, max_days=7)
    days = (end_date - start_date).days + 1
    print("Modo dry-run BCR" if args.dry_run else "Preparación de descarga BCR")
    print(f"Productos solicitados: {', '.join(requested)}")
    print(f"Productos normalizados: {', '.join(products)}")
    print(f"Rango: {start_date} a {end_date}")
    print(f"Cantidad de días consultados: {days}")
    print(f"Ventanas de consulta ({len(windows)}):")
    for window_start, window_end in windows:
        print(f"- {window_start} a {window_end} ({(window_end - window_start).days + 1} días)")
    print(f"API configurada: {'sí' if config['is_configured'] else 'no'}")
    print(f"Endpoint configurado: {'sí' if config['has_endpoint'] else 'no'}")
    print(f"Credenciales presentes: {'sí' if (config['has_token'] or (config['has_user'] and config['has_password'])) else 'no'}")
    print(f"Carpeta de salida: {args.output_dir.expanduser().resolve()}")
    print(f"Acción: {'se usaría API' if config['is_configured'] else 'fallback manual'}")
    print_configuration(config)
    print("Archivos que se generarían:")
    for product in products:
        print(f"- {args.output_dir / f'BCR_API_precios_camara_{_slug(product)}_<inicio>_<fin>.json'}")
        entry = catalog.get(re.sub(r"[^a-záéíóúüñ0-9]", "", product.lower()))
        if not entry or not entry.get("bcr_id_grano"):
            print(f"No hay id BCR para {product}. Complete bcr_id_grano en catalogo_commodities_bcr.csv para descarga API.")
    if args.dry_run:
        print("Dry-run: no se descargan datos ni se crean archivos reales.")
        if not config["is_configured"]:
            print("Acción: no se descargan datos. Use descarga manual o configure .env.")
        return 0
    if not config["is_configured"]:
        print("No hay credenciales/configuración API BCR. Use descarga manual en data/commodities_bcr/raw/ o configure .env.")
        return 0
    downloaded = 0
    for product in products:
        entry = catalog.get(re.sub(r"[^a-záéíóúüñ0-9]", "", product.lower()))
        if not entry or not entry.get("bcr_id_grano"):
            continue
        product_config = dict(config)
        product_config["_bcr_id_grano"] = entry["bcr_id_grano"]
        for window_start, window_end in windows:
            payload = fetch_bcr_prices(product, window_start, window_end, product_config)
            if payload is not None:
                path = save_raw_response(payload, args.output_dir.expanduser().resolve(), product, window_start, window_end, str(config["precios_camara_endpoint"]))
                print(f"Respuesta raw guardada: {path}")
                downloaded += 1
    print(f"Archivos raw guardados: {downloaded}")
    return 0


def print_configuration(config: dict[str, object]) -> None:
    print("Configuración detectada (secretos enmascarados):")
    print(f"BCR_API_BASE_URL={_safe_url(str(config['api_base_url']))}")
    print(f"BCR_API_USER={_mask_user(os.getenv('BCR_API_USER', ''))}")
    print(f"BCR_API_PASSWORD={mask_secret(os.getenv('BCR_API_PASSWORD', ''))}")
    print(f"BCR_API_TOKEN={mask_secret(os.getenv('BCR_API_TOKEN', ''))}")
    print(f"BCR_API_USE_AUTH={'true' if config['use_auth'] else 'false'}")
    print(f"BCR_API_PRECIOS_CAMARA_ENDPOINT={_safe_url(str(config['precios_camara_endpoint']))}")


if __name__ == "__main__":
    raise SystemExit(main())
