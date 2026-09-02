"""Prepara una descarga BCR segura, con API futura y fallback manual.

No hay endpoints BCR/GIX confirmados en este repositorio, por lo que esta
versión no realiza llamadas HTTP. Con configuración API muestra el plan y
deja encapsulado el punto donde deberá agregarse el adaptador autorizado.
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "data" / "commodities_bcr" / "raw"
DEFAULT_PRODUCTS = ("soja", "maiz", "trigo", "girasol", "sorgo")
ALIASES = {
    "soja": "soja", "soya": "soja", "maiz": "maiz", "maíz": "maiz", "corn": "maiz",
    "trigo": "trigo", "wheat": "trigo", "girasol": "girasol", "sunflower": "girasol",
    "sorgo": "sorgo", "sorghum": "sorgo", "cebada": "cebada", "barley": "cebada",
}


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    user: str
    password: str
    token: str
    use_auth: bool

    @property
    def configured(self) -> bool:
        if not self.base_url:
            return False
        return not self.use_auth or bool(self.token or (self.user and self.password))


def load_dotenv(path: Path) -> None:
    """Carga .env sin sobrescribir variables ya definidas en el entorno."""
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


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "si", "sí", "yes", "y"}


def read_config() -> ApiConfig:
    return ApiConfig(
        base_url=os.getenv("BCR_API_BASE_URL", "").strip(),
        user=os.getenv("BCR_API_USER", "").strip(),
        password=os.getenv("BCR_API_PASSWORD", ""),
        token=os.getenv("BCR_API_TOKEN", ""),
        use_auth=env_bool("BCR_API_USE_AUTH", True),
    )


def mask_secret(value: str, replacement: str = "********") -> str:
    return replacement if value else "(vacío)"


def mask_user(value: str) -> str:
    if not value:
        return "(vacío)"
    if "@" in value:
        return f"{value[0]}***@***"
    return f"{value[0]}***"


def safe_base_url(value: str) -> str:
    if not value:
        return "(vacía)"
    try:
        parts = urlsplit(value)
        if not parts.scheme or not parts.netloc:
            return "(configurada; formato no verificable)"
        return urlunsplit((parts.scheme, parts.hostname or parts.netloc, parts.path, "", ""))
    except ValueError:
        return "(configurada; formato no verificable)"


def normalize_product(value: str) -> str:
    key = re.sub(r"[^a-záéíóúüñ]", "", value.strip().lower())
    return ALIASES.get(key, key)


def parse_products(value: str) -> list[str]:
    products = [normalize_product(item) for item in value.split(",") if item.strip()]
    return list(dict.fromkeys(product for product in products if product))


def resolve_dates(days_back: int, date_start: str | None, date_end: str | None) -> tuple[date, date]:
    end = date.fromisoformat(date_end) if date_end else date.today()
    start = date.fromisoformat(date_start) if date_start else end - timedelta(days=days_back)
    if start > end:
        raise ValueError("--date-start no puede ser posterior a --date-end")
    return start, end


def print_configuration(config: ApiConfig) -> None:
    print("Configuración detectada (secretos enmascarados):")
    print(f"BCR_API_BASE_URL={safe_base_url(config.base_url)}")
    print(f"BCR_API_USER={mask_user(config.user)}")
    print(f"BCR_API_PASSWORD={mask_secret(config.password)}")
    print(f"BCR_API_TOKEN={mask_secret(config.token)}")
    print(f"BCR_API_USE_AUTH={'true' if config.use_auth else 'false'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days-back", type=int, default=None, help="Cantidad de días hacia atrás")
    parser.add_argument("--date-start", help="Fecha inicial YYYY-MM-DD")
    parser.add_argument("--date-end", help="Fecha final YYYY-MM-DD")
    parser.add_argument("--products", default=",".join(DEFAULT_PRODUCTS), help="Commodities separados por coma")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Carpeta destino de descargas originales")
    parser.add_argument("--dry-run", action="store_true", help="Sólo mostrar el plan; no descargar ni escribir archivos")
    return parser


def main() -> int:
    load_dotenv(PROJECT_DIR / ".env")
    parser = build_parser()
    args = parser.parse_args()
    default_days = int(os.getenv("BCR_COMMODITIES_DEFAULT_DAYS_BACK", "30") or "30")
    days_back = args.days_back if args.days_back is not None else default_days
    if days_back < 0:
        parser.error("--days-back debe ser mayor o igual a cero")
    try:
        start, end = resolve_dates(days_back, args.date_start, args.date_end)
    except ValueError as exc:
        parser.error(str(exc))
    products = parse_products(args.products)
    if not products:
        parser.error("--products debe contener al menos un commodity")
    config = read_config()
    mode = "API" if config.configured else "manual/fallback"
    print(f"Modo detectado: {mode}")
    print(f"Productos: {', '.join(products)}")
    print(f"Período a consultar: {start.isoformat()} a {end.isoformat()}")
    print(f"Carpeta de salida: {args.output_dir.expanduser().resolve()}")
    print_configuration(config)
    if not config.configured:
        print("No hay credenciales/configuración API BCR. Use descarga manual en data/commodities_bcr/raw/ o configure .env.")
        if not args.dry_run:
            print("El script no descargará archivos. Coloque las descargas originales en raw/ y ejecute la integración.")
        return 0
    if args.dry_run:
        print("Dry-run: no se realizará ninguna descarga ni escritura.")
        print("Dry-run API: se prepararía una consulta autenticada; no se ejecuta porque el endpoint BCR/GIX no está confirmado en este proyecto.")
        return 0
    print("Configuración API detectada, pero no se ejecuta HTTP: falta confirmar el endpoint y contrato oficial BCR/GIX.")
    print("Mantenga el fallback manual o complete el adaptador autorizado antes de habilitar descargas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
