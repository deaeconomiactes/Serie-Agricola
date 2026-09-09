#!/usr/bin/env python3
"""Descarga controlada de la serie oficial de precios internos mensuales.

La red está deshabilitada por defecto. El modo web sólo descarga las URLs
explícitamente configuradas para los años solicitados y guarda el HTML en
``data/commodities_local_mensual/raw/``. No se realizan búsquedas ni scraping
masivo y no se inventan URLs cuando un año no está configurado.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from local_mensual_common import DEFAULT_CONFIG_PATH, DEFAULT_RAW_DIR, DEFAULT_REPORT_DIR, ROOT, load_source_config, text


DEFAULT_PRODUCTS = "soja,maiz,trigo,girasol,sorgo,cebada"
DEFAULT_YEARS = "2020,2021,2022,2023,2024,2025,2026"
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
MANIFEST_FIELDS = ["año", "url", "archivo", "fecha_descarga", "bytes", "estado", "observaciones"]


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


def parse_years(raw: str) -> list[int]:
    years: list[int] = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        try:
            year = int(value)
        except ValueError as exc:
            raise SystemExit(f"--years debe contener años separados por coma: {raw}") from exc
        if year < 1900 or year > 2200:
            raise SystemExit(f"Año fuera de rango: {year}")
        if year not in years:
            years.append(year)
    return sorted(years)


def redact_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        return "URL configurada pero no reconocible"
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Descarga controlada de precios internos locales mensuales")
    parser.add_argument("--days-back", type=int, default=30, help="compatibilidad con el pipeline anterior")
    parser.add_argument("--date-start", help="compatibilidad con el pipeline anterior")
    parser.add_argument("--date-end", help="compatibilidad con el pipeline anterior")
    parser.add_argument("--products", default=DEFAULT_PRODUCTS, help="productos separados por coma")
    parser.add_argument("--years", default=DEFAULT_YEARS, help="años separados por coma")
    parser.add_argument("--output-dir", default=str(DEFAULT_RAW_DIR), help="directorio local de salida")
    parser.add_argument("--config", default="", help="configuración JSON alternativa")
    parser.add_argument("--source-url", default="", help="URL única para una prueba controlada; no reemplaza el mapa por año")
    parser.add_argument("--filename", default="", help="nombre base del HTML cuando se usa --source-url")
    parser.add_argument("--allow-web", action="store_true", help="habilita las descargas explícitamente configuradas")
    parser.add_argument("--dry-run", action="store_true", help="muestra años y URLs sin descargar")
    return parser.parse_args()


def url_entries(config: dict[str, object]) -> dict[int, tuple[str, str]]:
    entries: dict[int, tuple[str, str]] = {}
    raw_urls = config.get("urls", [])
    if isinstance(raw_urls, dict):
        raw_urls = [{"year": year, "url": url} for year, url in raw_urls.items()]
    if not isinstance(raw_urls, list):
        return entries
    for item in raw_urls:
        if isinstance(item, str):
            match = re.search(r"(19|20)\d{2}", item)
            if not match:
                continue
            entries[int(match.group(0))] = (item, "")
            continue
        if not isinstance(item, dict):
            continue
        raw_year = item.get("year", item.get("año"))
        raw_url = item.get("url")
        if raw_year is None or not raw_url:
            continue
        try:
            year = int(str(raw_year))
        except ValueError:
            continue
        entries[year] = (str(raw_url), text(item.get("description", item.get("descripcion", ""))))
    return entries


def safe_html_filename(candidate: str, year: int) -> str:
    raw = text(candidate) or f"precios_internos_granos_{year}.html"
    raw = raw.replace("{year}", str(year)).replace("{año}", str(year))
    name = Path(raw).name
    if Path(name).suffix.lower() not in {".html", ".htm"}:
        name += ".html"
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    return name or f"precios_internos_granos_{year}.html"


def target_urls(args: argparse.Namespace, config: dict[str, object], years: list[int]) -> list[tuple[int, str, str]]:
    if args.source_url:
        return [(year, args.source_url, "URL única suministrada por el operador") for year in years]
    entries = url_entries(config)
    return [(year, *entries[year]) for year in years if year in entries and entries[year][0]]


def download(url: str, destination: Path, timeout: int) -> int:
    request = Request(url, headers={"User-Agent": "Serie-Agricola/commodities-local-mensual"})
    with urlopen(request, timeout=timeout) as response:  # nosec B310: URL opt-in desde configuración del operador.
        content = response.read(MAX_DOWNLOAD_BYTES + 1)
        if len(content) > MAX_DOWNLOAD_BYTES:
            raise RuntimeError(f"la respuesta supera el límite controlado de {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB")
        if not content:
            raise RuntimeError("la respuesta está vacía")
        destination.write_bytes(content)
        return len(content)


def write_manifest(rows: list[dict[str, str]]) -> Path:
    path = DEFAULT_REPORT_DIR / "REGISTRO_DESCARGAS_LOCAL_MENSUAL.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def main() -> int:
    args = parse_args()
    dotenv = load_dotenv()
    config_path = Path(args.config) if args.config else None
    config, loaded_path = load_source_config(config_path)
    years = parse_years(args.years)
    products = [item.strip() for item in args.products.split(",") if item.strip()]
    output_dir = Path(args.output_dir)
    timeout_raw = env_value("LOCAL_MENSUAL_HTTP_TIMEOUT", dotenv, "30")
    try:
        timeout = max(int(timeout_raw), 1)
    except ValueError:
        timeout = 30
    targets = target_urls(args, config, years)

    print("Pipeline local mensual de commodities")
    print(f"Años solicitados: {', '.join(str(year) for year in years) or 'sin especificar'}")
    print(f"Productos de referencia: {', '.join(products) or 'sin especificar'}")
    print(f"Salida local: {output_dir.resolve()}")
    print(f"Configuración: {loaded_path.resolve() if loaded_path else 'no encontrada'}")
    print(f"URLs previstas: {len(targets)} de {len(years)} año(s)")
    print("Modo web: habilitado sólo con --allow-web" if args.allow_web else "Modo web: deshabilitado")

    for year, url, description in targets:
        suffix = f" — {description}" if description else ""
        print(f"- {year}: {redact_url(url)}{suffix}")
    target_years = {item[0] for item in targets}
    missing_years = [str(year) for year in years if year not in target_years]
    if missing_years:
        print(f"Años sin URL configurada: {', '.join(missing_years)}")

    if args.dry_run:
        print("Dry-run: no se descarga nada.")
        return 0
    if not args.allow_web:
        print("Modo seguro: no se realizan llamadas web. Use --dry-run para revisar o --allow-web para descargar URLs configuradas.")
        return 0
    if not targets:
        print("No hay URLs configuradas para los años solicitados; no se realiza ninguna llamada.")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []
    failures = 0
    download_date = datetime.now().astimezone().isoformat(timespec="seconds")
    for year, url, _description in targets:
        template = args.filename or str(config.get("raw_filename_template", ""))
        destination = output_dir / safe_html_filename(template, year)
        try:
            size = download(url, destination, timeout)
            status = "descargado"
            note = "HTML guardado localmente; revisar antes de integrar"
            print(f"Descarga guardada: {destination} ({size} bytes)")
        except Exception as exc:  # pipeline exploratorio controlado
            failures += 1
            size = 0
            status = "error"
            note = f"{exc.__class__.__name__}: {exc}"
            print(f"Descarga no realizada para {year}: {note}", file=sys.stderr)
        manifest.append({
            "año": str(year), "url": url, "archivo": destination.name,
            "fecha_descarga": download_date, "bytes": str(size), "estado": status, "observaciones": note,
        })
    manifest_path = write_manifest(manifest)
    print(f"Registro de descarga: {manifest_path.resolve()}")
    print("La respuesta debe auditarse antes de alimentar el dashboard.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
