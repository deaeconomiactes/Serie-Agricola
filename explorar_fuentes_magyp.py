"""Exploración acotada; no integra series ni escribe salidas productivas.

Sin --allow-web sólo valida el plan. Ejemplo:
python explorar_fuentes_magyp.py --url https://www.magyp.gob.ar/mercadosagropecuarios/precios.php
python explorar_fuentes_magyp.py --allow-web --url URL --label precios
Las respuestas quedan en un directorio temporal externo a Git por defecto.
"""
import argparse
import hashlib
import html
import json
import re
import tempfile
import time
import csv
import io
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

ALLOWED = {"www.magyp.gob.ar", "magyp.gob.ar", "www.siogranos.com.ar",
           "siogranos.com.ar", "ssma.magyp.gob.ar", "dinem.magyp.gob.ar",
           "monitorsiogranos.magyp.gob.ar", "monitorssma.magyp.gob.ar",
           "sios.magyp.gob.ar", "siocarnes.magyp.gob.ar"}
MAX_BYTES = 1_500_000
SENSITIVE = re.compile(r"token|password|cookie|secret|authorization|gxhash|__VIEWSTATE|__EVENTVALIDATION|GX_AJAX|GX_WEBSOCKET|GX_CLI_NAV", re.I)


def validate_url(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED or parts.username or parts.password:
        raise ValueError("Sólo HTTPS en hosts oficiales explícitos, sin credenciales")
    if parts.query and re.search(r"token|password|cookie|secret|key", parts.query, re.I):
        raise ValueError("No registrar parámetros potencialmente sensibles")
    return url


def inspect_text(text, url):
    links = []
    for href, label in re.findall(r'<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>', text, re.S | re.I):
        label = " ".join(html.unescape(re.sub("<[^>]+>", " ", label)).split())
        if label:
            links.append({"label": label, "url": urljoin(url, html.unescape(href))})
    return {
        "links": links,
        "scripts_iframes": [urljoin(url, html.unescape(x)) for x in re.findall(r'<(?:script|iframe)[^>]+src=[\"\']([^\"\']+)', text, re.I)],
        "forms": re.findall(r'<form\b[^>]*>', text, re.I),
        "controls": [x for x in re.findall(r'<(?:input|select|button)\b[^>]*>', text, re.I)
                     if not re.search(r'hidden|GXState', x, re.I) and not SENSITIVE.search(x)],
        "ajax_hints": [line.strip()[:1500] for line in text.splitlines()
                       if re.search(r'ajax|fetch\(|url:|\.aspx/|\.php[?\"\']|\.csv|\.json', line, re.I)
                       and not re.search(r'hidden|GXState', line, re.I) and not SENSITIVE.search(line)],
    }


def redact(text):
    """No conservar estado de seguridad en evidencia HTML ni logs."""
    def replace_state(match):
        try:
            state = json.loads(html.unescape(match.group(2)))
            state = {k: v for k, v in state.items() if not SENSITIVE.search(k)}
            safe = html.escape(json.dumps(state, ensure_ascii=False), quote=True)
            return match.group(1) + safe + match.group(3)
        except (ValueError, TypeError):
            return match.group(1) + "REDACTED" + match.group(3)
    text = re.sub(r'(<input\b[^>]*name="GXState"[^>]*value=\')(.*?)(\')', replace_state, text, flags=re.S | re.I)
    text = re.sub(r'<input\b[^>]*(?:token|password|authorization|gxhash|__VIEWSTATE|__EVENTVALIDATION|GX_AJAX|GX_WEBSOCKET|GX_CLI_NAV)[^>]*>',
                  '<!-- security control omitted -->', text, flags=re.I)
    # GeneXus también puede incluir firmas JWT en grillas/scripts, fuera de GXState.
    text = re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', 'REDACTED_SIGNATURE', text)
    return text


def validate_payload(url, method, payload):
    if payload is not None and (method != "POST" or not isinstance(payload, dict)):
        raise ValueError("Payload requiere POST y objeto JSON")
    if payload is not None and SENSITIVE.search(json.dumps(payload)):
        raise ValueError("Payload potencialmente sensible")
    if method == "POST" and url.endswith("/GetOperaciones"):
        payload = payload or {}
        if not 1 <= int(payload.get("pPageSize", 0)) <= 50 or not 1 <= int(payload.get("pCurrentPage", 0)) <= 2:
            raise ValueError("SIO: muestra de 1–50 filas, páginas 1–2")
        start = datetime.strptime(payload.get("fFechaConcertacionDesde", ""), "%d/%m/%Y")
        end = datetime.strptime(payload.get("fFechaConcertacionHasta", ""), "%d/%m/%Y")
        if not 0 <= (end - start).days <= 6:
            raise ValueError("SIO: fechas explícitas con ventana máxima de 7 días")


class ControlledRedirect(HTTPRedirectHandler):
    max_redirections = 2
    max_repeats = 1

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def summarize_file(path):
    """Inspección local limitada; no normaliza ni integra observaciones."""
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError("Archivo de evidencia excede 1.5 MB")
    encoding = "utf-16-le" if b"\x00" in data[:100] else "utf-8-sig"
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp1252"
        text = data.decode(encoding)
    result = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "encoding": encoding}
    try:
        obj = json.loads(text)
        body = obj.get("d", obj) if isinstance(obj, dict) else obj
        if isinstance(body, str):
            body = json.loads(body)
        rows = body.get("posts", body.get("Items", [])) if isinstance(body, dict) else body
        result.update(format="JSON", records=len(rows) if isinstance(rows, list) else None,
                      keys=list(body) if isinstance(body, dict) else [],
                      row_fields=list(rows[0]) if isinstance(rows, list) and rows and isinstance(rows[0], dict) else [])
    except (ValueError, TypeError):
        if text.lstrip().startswith("<"):
            result.update(format="HTML/markup", inspection=inspect_text(redact(text), "https://www.magyp.gob.ar/"))
        else:
            rows = list(csv.reader(io.StringIO(text), delimiter=";"))
            result.update(format="CSV candidato", records=max(0, len(rows) - 1), fields=rows[0] if rows else [])
    return result


def probe(url, method="GET", payload=None, max_bytes=MAX_BYTES):
    validate_url(url)
    validate_payload(url, method, payload)
    headers = {"User-Agent": "MAGyP-source-research/1.0"}
    body = None
    if method == "POST":
        body = json.dumps(payload or {}).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = Request(url, data=body, headers=headers, method=method)
    result = {"requested_url": url, "method": method, "payload": payload,
              "fetched_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        with build_opener(ControlledRedirect()).open(req, timeout=25) as response:
            validate_url(response.url)
            data = response.read(max_bytes + 1)
            result.update(status=response.status, final_url=response.url,
                          content_type=response.headers.get("Content-Type", ""),
                          bytes_read=len(data), truncated=len(data) > max_bytes)
            if result["truncated"]:
                data = data[:max_bytes]
            result["sha256"] = hashlib.sha256(data).hexdigest()
            # UTF-8 first; several older MAGyP pages are Windows-1252.
            try:
                text = data.decode("utf-8")
                result["encoding"] = "utf-8"
            except UnicodeDecodeError:
                text = data.decode("cp1252", errors="replace")
                result["encoding"] = "cp1252"
            result["inspection"] = inspect_text(text, response.url)
            if "html" in result["content_type"].lower() and text.lstrip().startswith("<"):
                data = redact(text).encode("utf-8")
                result["stored_encoding"] = "utf-8"
                result["stored_sha256"] = hashlib.sha256(data).hexdigest()
                result["security_state_redacted"] = True
            return result, data
    except HTTPError as exc:
        result.update(status=exc.code, error="HTTPError")
    except (URLError, TimeoutError, OSError) as exc:
        result.update(status=None, error=type(exc).__name__)
    return result, b""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--inspect-file", type=Path, help="Resumir una muestra local sin red")
    parser.add_argument("--self-test", action="store_true", help="Verificar límites y redacción sin red")
    parser.add_argument("--allow-web", action="store_true")
    parser.add_argument("--method", choices=["GET", "POST"], default="GET")
    parser.add_argument("--payload", help="Objeto JSON sin credenciales; sólo POST")
    parser.add_argument("--label", default="probe")
    parser.add_argument("--max-requests", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=Path(tempfile.gettempdir()) / "magyp_research")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ExplorationChecks)
        if not unittest.TextTestRunner().run(suite).wasSuccessful():
            raise SystemExit(1)
        return
    if args.inspect_file:
        print(json.dumps(summarize_file(args.inspect_file), ensure_ascii=False, indent=2))
        return
    if not args.url:
        parser.error("Indique --url, --inspect-file o --self-test")
    if not 1 <= args.max_requests <= 10 or len(args.url) > args.max_requests:
        parser.error("Plan excede el límite: 1–10 requests por ejecución")
    payload = json.loads(args.payload) if args.payload else None
    for url in args.url:
        validate_url(url)
        validate_payload(url, args.method, payload)
    # Evitar guardar raw HTML o descargas en el repositorio aunque se cambie el destino.
    if args.allow_web and args.output_dir.resolve().is_relative_to(Path(__file__).resolve().parent):
        parser.error("La evidencia raw debe guardarse fuera del repositorio")
    label = re.sub(r"[^a-zA-Z0-9_-]", "_", args.label)
    if not args.allow_web:
        print(json.dumps({"dry_run": True, "urls": args.url, "method": args.method,
                          "payload": payload, "max_bytes": MAX_BYTES}, ensure_ascii=False))
        return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(args.url):
        if i:
            time.sleep(1.5)
        record, data = probe(url, args.method, payload)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        prefix = args.output_dir / f"{label}_{i}_{stamp}"
        if data:
            prefix.with_suffix(".response").write_bytes(data)
        prefix.with_suffix(".json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in record.items() if k != "inspection"}, ensure_ascii=False))
        print("Evidencia local:", prefix.with_suffix(".json"))


class ExplorationChecks(unittest.TestCase):
    def test_official_hosts_and_credentials(self):
        for url in ["http://www.magyp.gob.ar/", "https://example.com/", "https://user:pass@www.magyp.gob.ar/", "https://www.magyp.gob.ar/?token=x"]:
            with self.assertRaises(ValueError):
                validate_url(url)
        self.assertEqual(validate_url("https://ssma.magyp.gob.ar/frutas.precios.aspx"), "https://ssma.magyp.gob.ar/frutas.precios.aspx")

    def test_bounded_sio(self):
        url = "https://www.siogranos.com.ar/consulta_publica/operaciones_informadas.aspx/GetOperaciones"
        payload = {"pPageSize": "5", "pCurrentPage": "1", "fFechaConcertacionDesde": "02/10/2026", "fFechaConcertacionHasta": "02/10/2026"}
        validate_payload(url, "POST", payload)
        for change in [{"pPageSize": "5000"}, {"pCurrentPage": "3"}, {"fFechaConcertacionHasta": "31/10/2026"}, {"fFechaConcertacionDesde": ""}]:
            with self.assertRaises(ValueError):
                validate_payload(url, "POST", {**payload, **change})

    def test_redaction_keeps_price_data(self):
        sample = '<input type="hidden" name="GXState" value=\'{"GX_AJAX_KEY":"fixture_secret","gxhash_field":"fixture_hash","price":12}\'>'
        cleaned = redact(sample)
        self.assertNotIn("fixture_secret", cleaned)
        self.assertNotIn("fixture_hash", cleaned)
        self.assertIn("price", cleaned)
        webforms = '<input type="hidden" name="__VIEWSTATE" value="fixture_state">'
        self.assertNotIn("fixture_state", redact(webforms))
        self.assertNotIn("eyJfixture.payload.signature", redact('"eyJfixture.payload.signature"'))
        inspection = inspect_text(sample, "https://ssma.magyp.gob.ar/")
        self.assertEqual(inspection["controls"], [])


if __name__ == "__main__":
    main()
