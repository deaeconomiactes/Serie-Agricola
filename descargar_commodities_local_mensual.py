#!/usr/bin/env python3
"""Descarga controlada de una fuente local mensual de commodities.

Por diseño no realiza llamadas web por defecto. La URL se configura fuera del
código mediante LOCAL_MENSUAL_SOURCE_URL o --source-url y sólo se usa con
--allow-web.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from local_mensual_common import DEFAULT_RAW_DIR, ROOT, text


DEFAULT_PRODUCTS = "soja,maiz,trigo,girasol,sorgo,cebada"
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024


def load_dotenv() -> dict[str, str]:
    values: dict[str, str] = {}
    path = ROOT / ".env"
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_value(name: str, dotenv: dict[str, str], default: str = "") -> str:
    return os.getenv(name) or dotenv.get(name, default)


def parse_iso_date(raw: str, label: str) -> date:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit(f"{label} debe tener formato YYYY-MM-DD: {raw}") from exc


def redact_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        return "URL configurada pero no reconocible"
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Descarga controlada de commodities locales mensuales")
    parser.add_argument("--days-back", type=int, default=30, help="días hacia atrás para documentar el rango intentado")
    parser.add_argument("--date-start", help="inicio del rango YYYY-MM-DD")
    parser.add_argument("--date-end", help="fin del rango YYYY-MM-DD")
    parser.add_argument("--products", default=DEFAULT_PRODUCTS, help="productos separados por coma")
    parser.add_argument("--output-dir", default=str(DEFAULT_RAW_DIR), help="directorio local de salida")
    parser.add_argument("--source-url", default="", help="URL configurada para una única descarga controlada")
    parser.add_argument("--filename", default="", help="nombre de archivo de salida; por defecto se toma de la configuración")
    parser.add_argument("--allow-web", action="store_true", help="habilita la única descarga desde la URL configurada")
    parser.add_argument("--dry-run", action="store_true", help="muestra la consulta sin descargar")
    return parser.parse_args()


def build_range(args: argparse.Namespace) -> tuple[date, date]:
    end = parse_iso_date(args.date_end, "--date-end") if args.date_end else date.today()
    start = parse_iso_date(args.date_start, "--date-start") if args.date_start else end - timedelta(days=max(args.days_back, 0))
    if start > end:
        raise SystemExit("--date-start no puede ser posterior a --date-end")
    return start, end


def safe_filename(candidate: str, content_type: str = "") -> str:
    name = Path(candidate or "commodities_local_mensual_source").name
    if not Path(name).suffix:
        lowered = content_type.lower()
        suffix = ".xlsx" if "spreadsheet" in lowered or "excel" in lowered else ".csv"
        name += suffix
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    return name or "commodities_local_mensual_source.csv"


def download(url: str, destination: Path, timeout: int) -> int:
    request = Request(url, headers={"User-Agent": "Serie-Agricola/commodities-local-mensual"})
    with urlopen(request, timeout=timeout) as response:  # nosec B310: URL is explicit operator configuration and opt-in.
        content = response.read(MAX_DOWNLOAD_BYTES + 1)
        if len(content) > MAX_DOWNLOAD_BYTES:
            raise RuntimeError(f"la respuesta supera el límite controlado de {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB")
        destination.write_bytes(content)
        return len(content)


def main() -> int:
    args = parse_args()
    dotenv = load_dotenv()
    configured_url = args.source_url or env_value("LOCAL_MENSUAL_SOURCE_URL", dotenv)
    start, end = build_range(args)
    products = [item.strip() for item in args.products.split(",") if item.strip()]
    output_dir = Path(args.output_dir)
    configured_name = args.filename or env_value("LOCAL_MENSUAL_RAW_FILENAME", dotenv, "")
    timeout = int(env_value("LOCAL_MENSUAL_HTTP_TIMEOUT", dotenv, "30") or "30")

    print("Pipeline local mensual de commodities")
    print(f"Rango intentado: {start.isoformat()} a {end.isoformat()}")
    print(f"Productos: {', '.join(products) or 'sin especificar'}")
    print(f"Salida local: {output_dir.resolve()}")
    print(f"URL configurada: {'sí (' + redact_url(configured_url) + ')' if configured_url else 'no'}")
    print("Modo web: habilitado sólo con --allow-web" if args.allow_web else "Modo web: deshabilitado")

    if args.dry_run:
        print("Dry-run: no se descarga nada.")
        if not configured_url:
            print("No hay URL configurada. Defina LOCAL_MENSUAL_SOURCE_URL en .env o use --source-url para una prueba controlada.")
        else:
            print(f"Se intentaría consultar una única URL configurada: {redact_url(configured_url)}")
        return 0

    if not args.allow_web:
        print("Modo seguro: no se realizan llamadas web. Use --dry-run para revisar la consulta o --allow-web con una URL configurada.")
        return 0
    if not configured_url:
        print("No hay URL configurada para la fuente local mensual. Use .env o --source-url; no se realiza ninguna llamada.")
        return 0

    filename = safe_filename(configured_name, "")
    destination = output_dir / filename
    try:
        size = download(configured_url, destination, max(timeout, 1))
    except Exception as exc:  # keep a controlled exploratory pipeline non-destructive
        print(f"Descarga no realizada: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"Descarga guardada: {destination} ({size} bytes)")
    print("La respuesta debe auditarse antes de integrarse al dashboard.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
