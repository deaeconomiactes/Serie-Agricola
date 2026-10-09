"""Comprobación acotada Corrientes. No adquiere ni publica series productivas."""
from __future__ import annotations
import argparse
import csv
import json
import math
import socket
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[2]
PAGES = (
    "https://www.magyp.gob.ar/mercadosagropecuarios/",
    "https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/frutas/index.php",
    "https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/hortalizas/",
)
ALLOWED = {"www.magyp.gob.ar", "www.mptt.gov.ar", "mptt.gov.ar"}
MAX_BYTES = 500_000
MAX_REQUESTS = 5


class PublicLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.active = None
        self.ignore = 0
        self.text = []
        self.tables = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.ignore += 1
        if tag == "a":
            self.active = [attrs.get("href", ""), ""]
        if tag == "img" and self.active:
            self.active[1] += " " + attrs.get("alt", "") + " " + attrs.get("title", "")
        if tag == "table":
            self.tables += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.ignore = max(0, self.ignore - 1)
        if tag == "a" and self.active:
            self.links.append(tuple(self.active))
            self.active = None

    def handle_data(self, value):
        if self.ignore:
            return
        if self.active:
            self.active[1] += " " + value
        self.text.append(value)


class NoRedirect(HTTPRedirectHandler):
    # No automatic traversal to unknown hosts, URLs or session-bearing query strings.
    def redirect_request(self, *args, **kwargs):
        return None


def probe(url, timeout=15):
    parsed = urlsplit(url)
    if (parsed.hostname not in ALLOWED or parsed.scheme not in ("http", "https") or
            parsed.query or parsed.fragment or parsed.username or parsed.password):
        raise ValueError("URL no autorizada para esta investigación")
    start = time.monotonic()
    result = {"url": url, "method": "GET", "timeout_seconds": timeout, "max_bytes": MAX_BYTES,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(), "status": None}
    try:
        request = Request(url, headers={"User-Agent": "Serie-Agricola controlled-source-check/1.0"})
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            body = response.read(MAX_BYTES + 1)
            result.update(status=response.status, content_type=response.headers.get("Content-Type"),
                byte_size=len(body), encoding=response.headers.get_content_charset() or "utf-8")
            if len(body) > MAX_BYTES:
                result["result"] = "size_limit"
            else:
                parser = PublicLinks()
                parser.feed(body.decode(result["encoding"], errors="replace"))
                result["result"] = "html_received"
                result["corrientes_links"] = []
                for target, label in parser.links:
                    if "corrient" not in label.lower() and "preciosmercado" not in target.lower():
                        continue
                    public = urljoin(url, target)
                    address = urlsplit(public)
                    if address.scheme not in {"http", "https"} or address.query or address.fragment or address.username or address.password:
                        continue
                    result["corrientes_links"].append({"url": public, "label": " ".join(label.split())})
                if parsed.hostname in {"www.mptt.gov.ar", "mptt.gov.ar"}:
                    result.update(table_count=parser.tables,
                        public_text_excerpt=" ".join(parser.text).split()[:200])
    except HTTPError as error:
        result.update(status=error.code, result="http_error")
    except URLError as error:
        dns = isinstance(error.reason, socket.gaierror)
        result.update(result="dns_error" if dns else "network_error",
            error_class=type(error.reason).__name__)
    except (TimeoutError, OSError) as error:
        result.update(result="timeout" if isinstance(error, TimeoutError) else "network_error",
            error_class=type(error).__name__)
    result["elapsed_seconds"] = round(time.monotonic() - start, 3)
    print("[CHECK]", urlsplit(url).hostname, result["result"], result["status"])
    return result


def price(value):
    text = str(value or "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        number = float(text)
        return number if math.isfinite(number) and number > 0 else None
    except ValueError:
        return None


def inspect_legacy(path, as_of):
    """Lectura; no deduplica ni normaliza etiquetas, no modifica el integrado."""
    counts, dimensions, days, source_files = Counter(), {}, set(), set()
    dimensions = {key: set() for key in ("rubro", "especie", "variedad", "procedencia",
        "localidad_corrientes", "envase", "unidad", "unidad_precio_observado", "moneda")}
    precision = Counter()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            if row.get("mercado") != "Mercado de Corrientes":
                continue
            counts["rows"] += 1
            try:
                observation = date.fromisoformat(row.get("fecha", ""))
            except ValueError:
                counts["invalid_date_rows"] += 1
                continue
            if observation > as_of:
                counts["future_date_rows"] += 1
                continue
            counts["non_future_rows"] += 1
            observed = price(row.get("precio_observado") or row.get("precio_promedio") or row.get("precio"))
            if observed is None:
                counts["invalid_or_nonpositive_price_rows"] += 1
                continue
            counts["valid_observed_rows"] += 1
            comparable = price(row.get("precio_kg_estimado")) is not None and row.get(
                "confianza_conversion_precio") in {"Alta", "Media"}
            counts["comparable_rows"] += int(comparable)
            days.add(observation.isoformat())
            precision[row.get("fecha_precision") or "not_reported"] += 1
            source_files.add(row.get("archivo_origen", ""))
            for key in dimensions:
                if row.get(key):
                    dimensions[key].add(row[key])
    dates = sorted(days)
    return {"source_file": path.name, "as_of": as_of.isoformat(), **counts,
        "date_min": dates[0] if dates else None, "date_max": dates[-1] if dates else None,
        "observed_dates": len(dates), "date_precision_raw": dict(precision),
        "dimension_counts": {key: len(values) for key, values in dimensions.items()},
        "units_raw": sorted(dimensions["unidad"]),
        "currency_labels_raw": sorted(dimensions["moneda"]),
        "source_files": sorted(source_files)}


def classify(results):
    providers = [r for r in results if urlsplit(r["url"]).hostname in {"www.mptt.gov.ar", "mptt.gov.ar"}]
    if providers and all(r["result"] in {"dns_error", "network_error", "timeout", "http_error"} for r in providers):
        return "D_NO_UTILIZABLE"
    # A successful HTML response still requires publication-date/schema verification.
    # Never classify a source as current/automatic using its page title or a footer year.
    return "PENDING_REVIEW"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--allow-web", action="store_true")
    p.add_argument("--timeout", type=int, default=15)
    p.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    p.add_argument("--report-dir", type=Path, default=ROOT / "data/magyp/reports")
    args = p.parse_args()
    if not 1 <= args.timeout <= 20:
        p.error("Timeout debe estar entre 1 y 20 segundos")
    if not args.allow_web:
        print("[CHECK] DRY-RUN: hasta 5 requests controlados; sin red ni escrituras. Usar --allow-web.")
        return
    results = []
    if args.allow_web:
        for page in PAGES:
            results.append(probe(page, args.timeout))
        targets = {link["url"] for result in results for link in result.get("corrientes_links", [])
            if urlsplit(link["url"]).hostname in {"www.mptt.gov.ar", "mptt.gov.ar"}
            and not urlsplit(link["url"]).query}
        for target in sorted(targets):
            if len(results) >= MAX_REQUESTS:
                break
            results.append(probe(target, args.timeout))
            if target.startswith("http://") and len(results) < MAX_REQUESTS:
                results.append(probe("https://" + target[7:], args.timeout))
    report = {
        "investigation_only": True, "as_of": args.as_of.isoformat(),
        "controlled_requests": len(results), "max_requests": MAX_REQUESTS,
        "legacy": inspect_legacy(ROOT / "PRECIOS_MAYORISTAS_INTEGRADO.csv", args.as_of),
        "requests": results,
        "classification": classify(results),
        "note": "No inferir desactualización ni ausencia universal sin publicación fechada verificable."
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "CORRIENTES_MAGYP_SOURCE_CHECK.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[CHECK] Sólo diagnóstico; frontend, bases y pipelines existentes intactos")


if __name__ == "__main__":
    main()
