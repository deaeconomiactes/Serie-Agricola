"""Inventario acotado de enlaces oficiales; nunca enumera nombres de archivos."""
from __future__ import annotations
import argparse
import json
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import atomic_write, sha256, utc_now
from scripts.mercado_central.update_mcba_monthly import ROOT, PAGE, discover

SITEMAP = 'https://www.mercadocentral.gob.ar/sitemap.xml'
PORTAL = ('https://datos.magyp.gob.ar/dataset/precios-mayoristas-frutas-hortalizas/'
          'archivo/6dce1e87-7988-4eaf-b0e1-b3abbb3964da')
HOSTS = {'www.mercadocentral.gob.ar', 'mercadocentral.gob.ar', 'datos.magyp.gob.ar'}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and dict(attrs).get('href'):
            self.links.append(dict(attrs)['href'])


def safe(url):
    p = urlsplit(url)
    if (p.scheme != 'https' or p.hostname not in HOSTS or p.username or p.password
            or p.port not in (None, 443) or '..' in unquote(p.path).split('/')
            or (p.query and (p.path != '/sitemap.xml' or p.query not in ('page=1', 'page=2')))):
        raise ValueError('URL fuera de los índices oficiales autorizados')
    return url


def extract_links(body, url):
    parser = Links()
    parser.feed(body.decode('utf-8'))
    return list(dict.fromkeys(urljoin(url, href) for href in parser.links))


def collect(root=ROOT/'data/mercado_central', allow_web=False):
    if not allow_web:
        raise ValueError('La consulta de índices requiere --allow-web')
    stamp = utc_now()
    capture = stamp.replace(':', '').replace('.', '')
    folder = root/'raw/history'/capture
    folder.mkdir(parents=True, exist_ok=False)
    evidence = []
    count = 0

    def get(url, kind, discovered_from):
        nonlocal count
        safe(url)
        if count >= 14:
            raise ValueError('Presupuesto de índices agotado')
        if count:
            time.sleep(10)  # Crawl-delay institucional; sin concurrencia ni retries.
        count += 1
        start = time.monotonic()
        body = b''
        try:
            with urlopen(Request(url, headers={'User-Agent': 'SerieAgricola-history/1.0'}), timeout=30) as response:
                safe(response.url)
                body = response.read(3_000_001)
                status = response.status
                content_type = response.headers.get('Content-Type', '')
                if len(body) > 3_000_000:
                    raise ValueError('Índice excede límite de tamaño')
            error = None
        except HTTPError as exc:
            status, content_type, error = exc.code, '', 'HTTP_ERROR'
        except (URLError, OSError, TimeoutError):
            status, content_type, error = None, '', 'SOURCE_UNAVAILABLE'
        entry = dict(url=url, kind=kind, discovered_from=discovered_from,
                     captured_at_utc=stamp, http_status=status, content_type=content_type,
                     duration_seconds=round(time.monotonic()-start, 3), size_bytes=len(body),
                     sha256=sha256(body) if body else None, error_type=error)
        evidence.append(entry)
        print('[DISCOVER]', kind, status, url, flush=True)
        return body, entry

    body, entry = get(PAGE, 'current_price_index', 'official_price_page')
    publications = []
    if entry['http_status'] == 200:
        entry['links'] = extract_links(body, PAGE)
        # Año inferido desde nombres enlazados, no desde un rango de años supuesto.
        import re
        years = {int(y) for link in entry['links'] for y in re.findall(r'(?<!\d)(20\d{2})(?!\d)', unquote(link))}
        for year in sorted(years):
            publications.extend(discover(body.decode('utf-8'), year))
        # La raíz es un enlace derivado del directorio confirmado, nunca nombres ZIP probados.
        if publications:
            parent = publications[0]['url'].rsplit('/', 1)[0]+'/'
            listing, directory = get(parent, 'confirmed_archive_directory', PAGE)
            if directory['http_status'] == 200:
                directory['links'] = extract_links(listing, parent)
                for year in sorted({int(y) for link in directory['links'] for y in re.findall(r'(?<!\d)(20\d{2})(?!\d)', unquote(link))}):
                    publications.extend(discover(listing.decode('utf-8'), year))
    body, entry = get(SITEMAP, 'sitemap_index', 'standard_official_sitemap')
    site_urls = []
    if entry['http_status'] == 200:
        children = [e.text for e in ET.fromstring(body).findall('.//{*}loc')]
        entry['links'] = children
        for child in children[:2]:
            body, part = get(child, 'sitemap', SITEMAP)
            if part['http_status'] == 200:
                urls = [e.text for e in ET.fromstring(body).findall('.//{*}loc')]
                part['url_count'] = len(urls)
                site_urls.extend(urls)
    relevant = [u for u in site_urls if '/publicaciones/informe-monitoreo-federal-' in u]
    samples = relevant[:1] + [u for u in site_urls if u.endswith('/relevamiento-de-precios-mayoristas-del-110222')][:1]
    for url in samples:
        body, entry = get(url, 'historical_publication_sample', SITEMAP)
        if entry['http_status'] == 200:
            entry['links'] = [u for u in extract_links(body, url) if any(x in u.lower() for x in ('.zip', '.xls', '.csv', '.pdf', '/img/compromiso/'))]
    body, entry = get(PORTAL, 'official_usd_catalog', 'official_dataset_catalog')
    if entry['http_status'] == 200:
        entry['links'] = [u for u in extract_links(body, PORTAL) if '6dce1e87-7988-4eaf-b0e1-b3abbb3964da/download/' in u]
        for url in entry['links'][:1]:
            payload, resource = get(url, 'usd_historical_csv', PORTAL)
            if resource['http_status'] == 200:
                # Archivo público CSV; se conserva para auditoría, sin convertir ni mezclar con ARS.
                (folder/'usd_history.csv').write_bytes(payload)
                resource['raw_file'] = 'usd_history.csv'
                resource['encoding'] = 'cp1252'
    unique = {p['url']: p for p in publications}
    result = dict(schema_version='mcba-history-discovery-v1', captured_at_utc=stamp,
                  capture_id=capture, request_count=count, requests=evidence,
                  current_zip_publications=list(unique.values()),
                  historical_report_pages=relevant,
                  scope='Índices y muestras oficiales; sin enumerar archivos ni afirmar inexistencia global de históricos')
    # No guardar HTML, formularios, cookies, cabeceras de sesión ni cuerpos de errores.
    atomic_write(folder/'manifest.json', (json.dumps(result, ensure_ascii=False, indent=2)+'\n').encode())
    atomic_write(root/'reports/MCBA_HISTORY_DISCOVERY.json', (json.dumps(result, ensure_ascii=False, indent=2)+'\n').encode())
    return result


if __name__ == '__main__':
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-web', action='store_true')
    args = parser.parse_args()
    collect(allow_web=args.allow_web)
