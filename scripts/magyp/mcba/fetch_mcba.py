"""Adquisición autónoma acotada por navegador; HTTP GeneXus no validado."""
from __future__ import annotations
import argparse
import sys
import uuid
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import (PipelineError, RawManifest, official_url,
                                           sha256, store_raw, utc_now, atomic_write)
from scripts.magyp.mcba.model import ENDPOINT, CONTEXT_URL, PARSER_VERSION, SCHEMA_VERSION, parse_export
from scripts.magyp.mcba.acquisition import select_fetcher, browser_fetch, validate_window

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


def capture(payload, requested_date, data_root, mode, status=None, content_type=None, response_url=None,
            date_to=None, request_method=None, request_count=None, acquisition_classification=None):
    if len(payload) > MAX_BYTES:
        raise PipelineError("Export excede límite de 2 MB")
    date_to = date_to or requested_date
    validate_window(requested_date, date_to)
    records = parse_export(payload, requested_date, date_to)
    stamp = utc_now()
    capture_id = stamp.replace(":", "").replace(".", "_") + "-" + uuid.uuid4().hex[:8]
    manifest = RawManifest("mcba", "market_price_observation", ENDPOINT,
                           request_method if mode == "browser_automation" else None if mode == "browser_export_import" else "GET",
                           {"date_from": requested_date, "date_to": date_to}, stamp,
                           status, content_type, None, len(payload), sha256(payload), SCHEMA_VERSION,
                           PARSER_VERSION, len(records), "validated", capture_id, mode,
                           "ARS", "ARS/kg", CONTEXT_URL, response_url,
                           "documented", acquisition_classification, request_count)
    folder = store_raw(data_root, payload, manifest)
    print(f"[FETCH] MCBA {requested_date} modo={mode} HTTP={status or 'no_observado'}")
    print(f"[VALIDATE] {len(records)} registros; SHA256={manifest.sha256}")
    print(f"[FETCH] RAW inmutable: {folder}")
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date")
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-web", action="store_true")
    parser.add_argument("--export-url", help="URL pública XLSX generada con un filtro de un día")
    parser.add_argument("--import-export", type=Path, help="Export oficial descargado; no afirma autonomía")
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--acquisition", choices=("auto", "browser", "http"), default="auto")
    parser.add_argument("--browser-channel", choices=("msedge", "chromium"), default="msedge")
    parser.add_argument("--max-requests", type=int, default=80)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data/magyp")
    args = parser.parse_args()
    if args.dry_run:
        print("[FETCH] DRY-RUN: sin requests ni escrituras. Modo auto: navegador; HTTP autónomo no validado.")
        return
    if args.date and (args.date_from or args.date_to):
        parser.error("Elegir --date o --date-from/--date-to")
    start = args.date or args.date_from
    end = args.date or args.date_to or start
    if not start or not 1 <= args.timeout <= 60:
        parser.error("Se requiere fecha/ventana y timeout entre 1 y 60")
    if args.import_export and args.export_url:
        parser.error("Elegir importación o URL, no ambas")
    try:
        validate_window(start, end)
        if args.import_export:
            if args.import_export.stat().st_size > MAX_BYTES:
                raise PipelineError("Archivo excede límite")
            capture(args.import_export.read_bytes(), start, args.data_root, "browser_export_import", date_to=end,
                    acquisition_classification="MANUAL_ONLY")
        elif args.allow_web and args.export_url:
            payload, status, content_type = fetch_export(args.export_url, args.timeout)
            capture(payload, start, args.data_root, "http_export", status, content_type, args.export_url, date_to=end,
                    acquisition_classification="MANUAL_ONLY")
        elif args.allow_web:
            print(f"[FETCH] {start} a {end}; adquisición {args.acquisition}; límite {args.max_requests} requests")
            result = select_fetcher(start, end, args.acquisition,
                       browser=lambda a, b: browser_fetch(a, b, args.timeout, args.max_requests, args.browser_channel))
            folder = capture(result.payload, start, args.data_root, "browser_automation", result.http_status,
                             result.content_type, date_to=end, request_method=result.request_method,
                             request_count=result.diagnostics["request_count"], acquisition_classification=result.classification)
            atomic_write(args.data_root / "reports" / ("MCBA_ACQUISITION_" + folder.name + ".json"),
                         (json.dumps(result.diagnostics, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            print(f"[FETCH] {result.classification}; {result.diagnostics['request_count']} requests")
        else:
            raise PipelineError("Red deshabilitada por defecto. Usar --allow-web para adquisición autónoma o importar export.")
    except Exception as e:
        # No URL de excepción, cookies, request bodies ni estado GeneXus en logs.
        message = str(e) if isinstance(e, PipelineError) else type(e).__name__
        if getattr(e, "diagnostics", None):
            stamp = utc_now().replace(":", "").replace(".", "_")
            public = {"requested_from": start, "requested_to": end, "captured_at_utc": utc_now(),
                      "result": "failed", "diagnostics": e.diagnostics}
            atomic_write(args.data_root / "reports" / ("MCBA_ACQUISITION_FAILED_" + stamp + ".json"),
                         (json.dumps(public, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print(f"[FETCH] ERROR {message}; última salida preservada", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
