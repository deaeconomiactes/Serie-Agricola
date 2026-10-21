"""Capturas históricas de enlaces publicados; HTTP público acotado, sin retries."""
from __future__ import annotations
import argparse
import json
import re
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import Request, build_opener
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.grains import references as r

INDEX = 'https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/granos/index.php'
VERSION = 'magyp-history-v1'


def official_url(url):
    p = urlsplit(url)
    if (p.scheme != 'https' or p.hostname not in {'www.magyp.gob.ar', 'magyp.gob.ar', 'dinem.magyp.gob.ar','infra.datos.gob.ar'}
            or p.username or p.password or p.port not in (None, 443) or p.fragment
            or '..' in unquote(p.path).split('/') or '\ufffd' in url):
        raise r.Error('URL histórica fuera de origen oficial')
    if p.query and not (p.path.endswith('/precios_fob.php') and re.fullmatch(r'Fecha=\d{2}%2F\d{2}%2F\d{4}', p.query)):
        raise r.Error('Parámetros históricos no autorizados')
    return quote(url, safe=':/?=&%')


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and dict(attrs).get('href'):
            self.links.append(dict(attrs)['href'])


def published_links(body, url):
    p = Links(); p.feed(body.decode('utf-8', errors='replace'))
    links = []
    for href in p.links:
        # Sólo se extrae el literal publicado; nunca se ejecuta JavaScript.
        popup = re.search(r"window\.open\('([^']+)'", href)
        if popup: href = popup[1]
        if href.startswith(('javascript:', '#')): continue
        candidate = urljoin(url, href)
        if candidate.startswith('http://'):
            candidate = 'https://' + candidate[7:]  # Mismo host/ruta, transporte HTTPS explícito.
        try: links.append(official_url(candidate))
        except r.Error: continue
    return sorted(set(links))


def get(url, limit=1_500_000):
    url = official_url(url)
    with build_opener(r.NoRedirect()).open(Request(url, headers={'User-Agent': 'SerieAgricola-history/1.0'}), timeout=25) as response:
        body = response.read(limit+1)
        if len(body) > limit: raise r.Error('Recurso histórico excede límite')
        return body, response.status, response.headers.get('Content-Type', ''), response.headers.get_content_charset() or 'utf-8'


def discover(root):
    # El índice incluye años de estadísticas ajenas al alcance después de precios.
    # Leer sólo su prefijo hasta el inicio de Estadísticas, nunca descargar esas series.
    with build_opener(r.NoRedirect()).open(Request(INDEX, headers={'User-Agent':'SerieAgricola-history/1.0'}), timeout=30) as response:
        parts = []; total = 0
        while total < 8_000_000:
            part = response.read(262144)
            if not part: break
            parts.append(part); total += len(part)
            if b'000058_Estad' in part: break
        body = b''.join(parts)
    links = published_links(body, INDEX)
    families = {'board': [], 'futures': [], 'internal': []}
    for url in links:
        if '/000020_Precios' in url and re.search(r'camaras\d{4}-\d{2}-\d{2}\.php$',url): families['board'].append(url)
        elif '/000010_Futuros' in url and re.search(r'cotiza_\d{4}-\d{2}-\d{2}\.php$',url): families['futures'].append(url)
        elif '/000010_Precios%20Internos' in url and (url.endswith('.xlsx') or re.search(r'/\d+_20\d\d\.php$',url)):
            families['internal'].append(url)
    result = {'schema_version':VERSION, 'index_url':INDEX, 'captured_at_utc':datetime.now(timezone.utc).isoformat(),
              'index_prefix_sha256':r.digest(body),'index_bytes_read':len(body),
              'scope':'Prefijo de precios hasta inicio de estadísticas; no índice completo del organismo', 'families':families,
              'series_indices':[url for url in links if '000061_Series' in url]}
    previous=root/'reports/COMMODITIES_HISTORY_LINKS.json'
    if previous.exists():
        old=json.loads(previous.read_bytes())
        if old.get('future_matrix_indices'):
            result['families']['futures_daily_indexed']=families['futures']
            result['families']['futures']=old['families']['futures']
            result['future_matrix_indices']=old['future_matrix_indices']
    r.atomic(root/'reports/COMMODITIES_HISTORY_LINKS.json', r.encoded(result))
    return result


def save_capture(root, family, url, body, status, content_type, encoding, representation='public_json', **extra):
    if representation=='public_json':
        try:body.decode(encoding)
        except UnicodeDecodeError:
            # Variantes oficiales antiguas declaran UTF-8 pero contienen bytes CP1252.
            # Se conserva el hash de respuesta y el encoding realmente aplicado.
            body.decode('cp1252');encoding='cp1252'
    content = r.encoded(r.project(body, family, encoding)) if representation == 'public_json' else body
    stamp = datetime.now(timezone.utc).isoformat()
    capture = stamp.replace(':','').replace('.','')+'_'+uuid.uuid4().hex[:8]
    folder = root/'raw/commodities/history'/family/capture
    folder.mkdir(parents=True, exist_ok=False)
    name = {'public_json':'response.json','metadata_json':'response.json','csv':'response.csv','xlsx':'response.xlsx'}[representation]
    (folder/name).write_bytes(content)
    manifest = dict(schema_version=VERSION,parser_version=VERSION,family=family,source_url=url,
        captured_at_utc=stamp,capture_id=capture,http_status=status,content_type=content_type,encoding=encoding,
        sha256=r.digest(content),response_sha256=r.digest(body),size_bytes=len(content),method='GET',
        representation=representation,raw_file=name,public_parameters={},**extra)
    (folder/'manifest.json').write_bytes(r.encoded(manifest))
    return manifest


def future_matrix_catalog(root):
    path=root/'reports/COMMODITIES_HISTORY_LINKS.json'
    catalog=json.loads(path.read_bytes())
    if not catalog.get('series_indices'):
        catalog=discover(root)
    matrices=[];indices=[]
    for url in catalog.get('series_indices',[]):
        body,_,_,_=get(url)
        markets=[link for link in published_links(body,url) if link.endswith(('/_chicago/chicago.php','/_kansas/kansas.php'))]
        for market in markets:
            time.sleep(1)
            body,_,_,_=get(market)
            selected=[link for link in published_links(body,market) if re.search(r'/\d+_[a-z_]+_\d{4}\.php$',link)]
            indices.append(dict(url=market,sha256=r.digest(body),linked_files=len(selected)))
            matrices.extend(selected)
    if not matrices:raise r.Error('Índices de matrices de futuros no disponibles')
    if 'futures_daily_indexed' not in catalog['families']:
        catalog['families']['futures_daily_indexed']=catalog['families']['futures']
    catalog['families']['futures']=sorted(set(matrices))
    catalog['future_matrix_indices']=indices
    r.atomic(path,r.encoded(catalog))
    return catalog


def capture_sspm(root):
    catalog_url='https://infra.datos.gob.ar/catalog/sspm/data.json'
    body,status,ct,enc=get(catalog_url,25_000_000)
    datasets=[d for d in json.loads(body)['dataset'] if any(str(x.get('identifier'))=='358.1' for x in d.get('distribution',[]))]
    if len(datasets)!=1:raise r.Error('Distribución FOB SSPM ausente/repetida')
    dataset=datasets[0]
    distribution=next(d for d in dataset['distribution'] if str(d.get('identifier'))=='358.1')
    manifest=save_capture(root,'fob',catalog_url,r.encoded(dataset),status,ct,enc,'metadata_json',
                         catalog_response_sha256=r.digest(body),catalog_response_size=len(body))
    resource=official_url(distribution['downloadURL'].replace('http:','https:'))
    body,status,ct,enc=get(resource,25_000_000)
    return save_capture(root,'fob',resource,body,status,ct,enc,'csv',
                        dictionary_capture_id=manifest['capture_id'],variant='sspm_358.1')


def capture_fas_export(root, start, end, regime='D.E.C.'):
    from playwright.sync_api import sync_playwright
    if regime not in ('D.E.C.','D.E.R.'):raise r.Error('Régimen export FAS inválido')
    url=r.SOURCES['fas'];prefix='W0031' if regime=='D.E.C.' else 'W0039'
    def civil(value):return datetime.strptime(value,'%Y-%m-%d').strftime('%d/%m/%Y')
    with sync_playwright() as p:
        # Edge instalado; Chromium sólo si el ejecutable Edge no está disponible.
        import os
        edge=any((Path(os.environ.get(var,''))/'Microsoft/Edge/Application/msedge.exe').is_file()
                 for var in ('ProgramFiles','ProgramFiles(x86)','LOCALAPPDATA'))
        browser=p.chromium.launch(**({'channel':'msedge'} if edge else {}),headless=True)
        context=browser.new_context(accept_downloads=True)
        try:
            page=context.new_page()
            response=page.goto(url,wait_until='domcontentloaded',timeout=60000)
            if response is None or response.status!=200:raise r.Error('FAS export no disponible')
            first=page.locator('#'+prefix+'vFAS_TEOHIS_DIA')
            last=page.locator('#'+prefix+'vFAS_TEOHIS_DIA_TO')
            first.wait_for(state='visible',timeout=60000)
            first.fill(civil(start));first.press('Tab')
            last.fill(civil(end));last.press('Tab')
            with page.expect_download(timeout=60000) as downloaded:
                page.locator('input[name="'+prefix+'BTNEXPORT"]').click(timeout=60000)
            download=downloaded.value
            if download.failure():raise r.Error('Export FAS sin descarga válida')
            body=Path(download.path()).read_bytes()
            if not body.startswith(b'PK') or len(body)>5_000_000:raise r.Error('Export FAS no es XLSX acotado')
            return save_capture(root,'fas',url,body,200,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'binary','xlsx',requested_from=start,requested_to=end,regime=regime,
                browser_channel='msedge' if edge else 'chromium',acquisition_method='public_browser_export')
        finally:
            context.close();browser.close()


def capture_archives(root, family, urls, max_requests=3000, interval=1., refresh=False):
    if family not in ('board','futures','internal'): raise r.Error('Familia de adquisición inválida')
    known = {}
    for path in (root/'raw/commodities/history'/family).glob('*/manifest.json'):
        m = json.loads(path.read_bytes()); known[m['source_url']] = m
    pending = [url for url in urls if refresh or url not in known]
    if len(pending) > max_requests: raise r.Error('Presupuesto insuficiente: indicar límite explícito antes de descargar')
    gate = threading.Lock(); last = [0.]; stopped = threading.Event(); results = []
    def one(url):
        if stopped.is_set(): return {'url':url,'status':'NOT_ATTEMPTED_AFTER_BLOCK'}
        with gate:
            time.sleep(max(0., interval-(time.monotonic()-last[0])))
            last[0] = time.monotonic()
        try:
            body,status,ct,enc = get(url)
            m = save_capture(root,family,url,body,status,ct,enc,'xlsx' if url.endswith('.xlsx') else 'public_json')
            return {'url':url,'status':'CAPTURED','capture_id':m['capture_id']}
        except HTTPError as exc:
            if exc.code in (401,403,429): stopped.set()
            return {'url':url,'status':'SOURCE_UNAVAILABLE','http_status':exc.code}
        except (URLError,TimeoutError,OSError): return {'url':url,'status':'SOURCE_UNAVAILABLE'}
        except (r.Error,ValueError,TypeError): return {'url':url,'status':'SCHEMA_ERROR'}
    # Hasta tres requests en vuelo, con inicios espaciados globalmente. Nunca retries.
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(one,url) for url in pending]
        for future in as_completed(futures):
            result = future.result(); results.append(result)
            if len(results)%50==0 or len(results)==len(pending):
                print('[HISTORY FETCH]',family,len(results),'/',len(pending),flush=True)
    report = dict(family=family,indexed_resources=len(urls),cached_resources=sum(u in known for u in urls),
                  requests=len([x for x in results if x['status']!='NOT_ATTEMPTED_AFTER_BLOCK']),results=results)
    r.atomic(root/f'reports/COMMODITIES_HISTORY_FETCH_{family}.json',r.encoded(report))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',choices=['discover','future-catalog','internal','board','futures','fas','fob'],required=True)
    p.add_argument('--allow-web',action='store_true')
    p.add_argument('--max-requests',type=int,default=3000)
    p.add_argument('--interval',type=float,default=1.)
    p.add_argument('--data-root',type=Path,default=ROOT/'data/magyp')
    p.add_argument('--from-date',default='2007-01-01')
    p.add_argument('--to-date',default=datetime.now(timezone.utc).date().isoformat())
    p.add_argument('--fas-regime',choices=['D.E.C.','D.E.R.'],default='D.E.C.')
    p.add_argument('--futures-daily',action='store_true',help='Informes diarios enlazados, acotados por --from-date/--to-date')
    p.add_argument('--refresh',action='store_true',help='Nueva captura inmutable de URLs seleccionadas; respetar presupuesto')
    a=p.parse_args()
    if not a.allow_web or a.interval<1.: raise SystemExit('Requiere --allow-web y al menos 1 segundo entre requests')
    if a.source=='discover': discover(a.data_root)
    elif a.source=='future-catalog':future_matrix_catalog(a.data_root)
    elif a.source=='fob':capture_sspm(a.data_root)
    elif a.source=='fas':
        capture_fas_export(a.data_root,a.from_date,a.to_date,a.fas_regime)
    else:
        catalog=json.loads((a.data_root/'reports/COMMODITIES_HISTORY_LINKS.json').read_bytes())
        urls=catalog['families'][a.source]
        if a.futures_daily:
            if a.source!='futures':raise r.Error('--futures-daily sólo aplica a futuros')
            urls=[u for u in catalog['families'].get('futures_daily_indexed',[]) if
                  (match:=re.search(r'cotiza_(\d{4}-\d{2}-\d{2})\.php$',u)) and a.from_date<=match[1]<=a.to_date]
        capture_archives(a.data_root,a.source,urls,a.max_requests,a.interval,a.refresh)
    return 0


if __name__=='__main__': raise SystemExit(main())
