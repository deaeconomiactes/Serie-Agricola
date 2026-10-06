"""Acquisición controlada de una exportación MCBA, nunca del histórico completo.

La generación autónoma del export GeneXus sigue pendiente. No se simula una
API REST: --allow-web necesita una URL pública XLSX ya generada por la UI.
"""
from __future__ import annotations
import argparse
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import (PipelineError, RawManifest, official_url,
                                           sha256, store_raw, utc_now)
from scripts.magyp.mcba.model import ENDPOINT, CONTEXT_URL, PARSER_VERSION, SCHEMA_VERSION, parse_export

MAX_BYTES = 2_000_000


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        official_url(newurl)
        if urlparse(newurl).query:
            raise PipelineError("Redirect con parámetros de sesión rechazado")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_export(url, timeout=25):
    official_url(url)
    p = urlparse(url)
    if p.query or not p.path.lower().endswith(".xlsx"):
        raise PipelineError("Se requiere URL pública XLSX sin tokens ni parámetros de sesión")
    opener = build_opener(SafeRedirect())
    req = Request(url, headers={"User-Agent": "SerieAgricola-MAGyP-MCBA-Pilot/1.0",
                               "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"})
    with opener.open(req, timeout=timeout) as response:
        if response.status != 200:
            raise PipelineError("HTTP no exitoso")
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise PipelineError("Respuesta excede límite de 2 MB")
        return body, response.status, response.headers.get("Content-Type")


def capture(payload, requested_date, data_root, mode, status=None, content_type=None, response_url=None):
    if len(payload) > MAX_BYTES:
        raise PipelineError("Export excede límite de 2 MB")
    records = parse_export(payload, requested_date)
    stamp = utc_now()
    capture_id = stamp.replace(":", "").replace(".", "_") + "-" + uuid.uuid4().hex[:8]
    manifest = RawManifest("mcba", "market_price_observation", ENDPOINT,
                           None if mode == "browser_export_import" else "GET",
                           {"date_from": requested_date, "date_to": requested_date}, stamp,
                           status, content_type, None, len(payload), sha256(payload), SCHEMA_VERSION,
                           PARSER_VERSION, len(records), "validated", capture_id, mode,
                           "ARS", "ARS/kg", CONTEXT_URL, response_url)
    folder = store_raw(data_root, payload, manifest)
    print(f"[FETCH] MCBA {requested_date} modo={mode} HTTP={status or 'no_observado'}")
    print(f"[VALIDATE] {len(records)} registros; SHA256={manifest.sha256}")
    print(f"[FETCH] RAW inmutable: {folder}")
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-web", action="store_true")
    parser.add_argument("--export-url", help="URL pública XLSX generada con un filtro de un día")
    parser.add_argument("--import-export", type=Path, help="Export oficial descargado; no afirma autonomía")
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data/magyp")
    args = parser.parse_args()
    if args.dry_run:
        print("[FETCH] DRY-RUN: sin requests ni escrituras. GeneXus autónomo pendiente.")
        return
    if not args.date or not 1 <= args.timeout <= 60:
        parser.error("Se requiere --date YYYY-MM-DD y timeout entre 1 y 60")
    if args.import_export and args.export_url:
        parser.error("Elegir importación o URL, no ambas")
    try:
        if args.import_export:
            if args.import_export.stat().st_size > MAX_BYTES:
                raise PipelineError("Archivo excede límite")
            capture(args.import_export.read_bytes(), args.date, args.data_root, "browser_export_import")
        elif args.allow_web and args.export_url:
            payload, status, content_type = fetch_export(args.export_url, args.timeout)
            capture(payload, args.date, args.data_root, "http_export", status, content_type, args.export_url)
        else:
            raise PipelineError("Red deshabilitada por defecto. --allow-web requiere --export-url; "
                                "generación autónoma GeneXus pendiente. Puede importar un export oficial.")
    except Exception as e:
        # No URL de excepción, cookies, request bodies ni estado GeneXus en logs.
        message = str(e) if isinstance(e, PipelineError) else type(e).__name__
        print(f"[FETCH] ERROR {message}; última salida preservada", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
