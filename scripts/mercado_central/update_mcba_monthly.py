"""Official MCBA ZIP daily observations and an explicitly derived monthly view."""
from __future__ import annotations
import argparse
import csv
import io
import json
import math
import re
import sys
import time
import zipfile
from collections import defaultdict
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import atomic_write, csv_bytes, sha256, stable_id, utc_now
from scripts.magyp.mcba.labels import normalized_label, load_rules

PAGE = 'https://www.mercadocentral.gob.ar/informaci%C3%B3n/precios-mayoristas'
REFERENCE = 'https://mercadocentral.gob.ar/img/Precios-referentes.jpg'
CURRENCY_CONTEXT = 'https://ssma.magyp.gob.ar/frutas.preciospromediof.aspx'
VERSION = 'mcba-central-monthly-v1'
PARSER_VERSION = 'mcba-central-biff2-v1'
CODES = json.loads((ROOT/'config/mercado_central_codes.json').read_text(encoding='utf-8'))
FILE = 'MCBA_MC_MONTHLY_DERIVED.csv'
MAX_ZIP = 25_000_000
MAX_EXPANDED = 60_000_000
MONTHS = {'ENERO':1,'FEBRERO':2,'MARZO':3,'ABRIL':4,'MAYO':5,'JUNIO':6,'JULIO':7,'AGOSTO':8,
          'SEPTIEMBRE':9,'SEPTIENBRE':9,'OCTUBRE':10,'NOVIEMBRE':11,'DICIEMBRE':12}
MEMBER = re.compile(r'R([FH])(\d{6})\.XLS', re.I)
DIMENSIONS = ('type','product_normalized','variety_normalized','origin_normalized','package_normalized',
              'kg_raw','quality','size','grade','currency','price_unit','observation_level')
MONTH_FIELDS = ('date','period','type','product_raw','product_normalized','variety_raw','variety_normalized',
 'origin_raw','origin_normalized','package_raw','package_normalized','kg_raw','quality','size','grade',
 'currency','price_unit','currency_basis','price_type','price','price_min','price_max','observed_days',
 'observation_count','first_observation_date','last_observation_date','period_status','method',
 'observation_level','source','source_url','capture_id','capture_timestamp','raw_sha256','raw_members',
 'schema_version','observation_id','lineage_json','multiple_quotes_days','quality_raw','quality_normalized','size_raw','size_normalized','grade_raw','grade_normalized')

class SourceUnavailable(Exception): pass
class InvalidSource(ValueError): pass

def allowed(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in {'mercadocentral.gob.ar','www.mercadocentral.gob.ar'} or p.username or p.password or p.port not in (None,443) or p.query or p.fragment or '..' in unquote(p.path).split('/'):
        raise InvalidSource('URL outside official allowlist')
    return url

class Redirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        allowed(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

class PublishedLinks(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]
    def handle_starttag(self, tag, attrs):
        if tag != 'a': return
        href=dict(attrs).get('href','')
        if urlsplit(href).path.lower().endswith('.zip'):
            self.links.append(urljoin(PAGE,href))

def discover(html, year):
    parser=PublishedLinks(); parser.feed(html)
    result=[]
    for url in dict.fromkeys(parser.links):
        allowed(url)
        if not urlsplit(url).path.startswith('/sites/default/files/precios_mayoristas/'):
            raise InvalidSource('ZIP outside official publication directory')
        name=unquote(urlsplit(url).path.rsplit('/',1)[-1]); upper=name.upper()
        if not re.search(r'(?<!\d)(?:'+str(year)+'|'+str(year)[-2:]+r')(?!\d)',upper): continue
        month=next((n for label,n in MONTHS.items() if label in upper),None)
        category='Frutas' if upper.startswith('FRUT') else 'Hortalizas' if upper.startswith('HORT') else None
        if not month or not category: raise InvalidSource('Unrecognized publication period/category')
        result.append({'url':url,'name':name,'period':f'{year:04d}-{month:02d}','type':category})
    if len(result)>30: raise InvalidSource('Publication request budget exceeded')
    if len({(r['period'],r['type']) for r in result})!=len(result):
        raise InvalidSource('Multiple ZIPs for one month/category require explicit review')
    return sorted(result,key=lambda r:(r['period'],r['type']))

def request(url, limit, headers=None):
    allowed(url)
    try:
        with build_opener(Redirect()).open(Request(url,headers={'User-Agent':'SerieAgricola-MCBA-monthly/1.0',**(headers or {})}),timeout=30) as response:
            allowed(response.url)
            body=response.read(limit+1)
            if len(body)>limit: raise InvalidSource('HTTP size limit exceeded')
            return body,dict(response.headers),response.status
    except HTTPError as exc:
        if exc.code==304: return None,{},304
        raise SourceUnavailable('Official HTTP response unavailable') from None
    except (URLError,TimeoutError,OSError):
        raise SourceUnavailable('Official connection unavailable') from None

def inventory(payload):
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries=archive.infolist()
            if len(entries)>500 or sum(i.file_size for i in entries)>MAX_EXPANDED:
                raise InvalidSource('ZIP expansion limit exceeded')
            safe=[i for i in entries if MEMBER.fullmatch(i.filename)]
            if not safe: raise InvalidSource('ZIP has no recognized root price books')
            if len({i.filename.upper() for i in safe})!=len(safe): raise InvalidSource('Duplicate ZIP members')
            if any(i.flag_bits & 1 or i.file_size>2_000_000 for i in safe): raise InvalidSource('Unsupported price member')
            # Never extract or interpret unrelated files, HTML, shortcuts or scripts.
            return [{'name':i.filename,'size':i.file_size,'compressed_size':i.compress_size} for i in safe],len(entries)-len(safe)
    except zipfile.BadZipFile: raise InvalidSource('Invalid ZIP') from None

def number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
        raise InvalidSource('Invalid numeric price/weight')
    return Decimal(str(value))

def normalize_book(payload, name, manifest, rules):
    import xlrd
    match=MEMBER.fullmatch(name)
    if not match: raise InvalidSource('Unrecognized XLS filename')
    day=datetime.strptime(match[2],'%d%m%y').date().isoformat()
    if day[:4]!=manifest['period'][:4] or ('Frutas' if match[1].upper()=='F' else 'Hortalizas')!=manifest['type']:
        raise InvalidSource('Book date/category differs from publication')
    try: book=xlrd.open_workbook(file_contents=payload,encoding_override='cp1252',logfile=io.StringIO())
    except Exception: raise InvalidSource('Unreadable XLS BIFF') from None
    if book.nsheets!=1: raise InvalidSource('Unexpected workbook sheets')
    sheet=book.sheet_by_index(0)
    expected=['ESP','VAR','PROC','ENV','KG','CAL','TAM','GRADO','MA'+match[2],'MO'+match[2],'MI'+match[2],'MAPK','MOPK','MIPK']
    if sheet.ncols!=14 or sheet.row_values(0)!=expected: raise InvalidSource('XLS schema/date changed')
    member_hash=sha256(payload); rows=[]
    for index in range(1,sheet.nrows):
        cells=sheet.row_values(index)
        if not any(v not in ('',None) for v in cells): continue
        if not isinstance(cells[0],str) or not cells[0].strip(): raise InvalidSource('Missing product')
        for col in [4,8,9,10,11,12,13]: number(cells[col])
        raw=dict(zip(expected,cells))
        norm=lambda dimension,value: normalized_label(dimension,value,rules) or ''
        row={'source':'MERCADO_CENTRAL','date':day,'period':day[:7],'type':manifest['type'],
             'product_raw':cells[0],'product_normalized':norm('product',cells[0]),
             'variety_raw':cells[1],'variety_normalized':norm('variety',cells[1]),
             'origin_raw':cells[2],'origin_normalized':norm('origin',cells[2]),
             'package_raw':cells[3],'package_normalized':norm('package',CODES['package'].get(str(cells[3]).strip().upper(),cells[3])),
             'kg_raw':str(cells[4]),'quality_raw':str(cells[5]),'size_raw':str(cells[6]),'grade_raw':str(cells[7]),
             'quality':CODES['quality'].get(str(cells[5]).strip().upper(),str(cells[5])),
             'size':str(cells[6]),'grade':CODES['grade'].get(str(cells[7]).strip().upper(),str(cells[7])),
             'price':str(number(cells[12])),'price_min':str(number(cells[13])),'price_max':str(number(cells[11])),
             'currency':'ARS','price_unit':'kg','currency_raw':'','unit_raw':'MOPK',
             'currency_basis':'documented_MCBA_pesos_context_MAGyP; ISO_ARS_mapping; no_conversion',
             'observation_level':'species_summary' if str(cells[1]).strip().upper()=='PROM.ESP.' else 'detail',
             'source_url':manifest['url'],'raw_sha256':manifest['sha256'],'capture_id':manifest['capture_id'],
             'capture_timestamp':manifest['captured_at_utc'],'member':name,'member_sha256':member_hash,
             'sheet':sheet.name,'row_number':index+1,'raw_fields':raw,'schema_version':VERSION,
             'publication_period':manifest['period'],'cross_period_member':day[:7]!=manifest['period']}
        row['quality_normalized']=norm('quality',row['quality'])
        row['size_normalized']=norm('size',row['size'])
        row['grade_normalized']=norm('grade',row['grade'])
        row['observation_id']=stable_id([manifest['sha256'],name,index+1])
        rows.append(row)
    book.release_resources()
    if not rows: raise InvalidSource('Empty price book')
    return rows

def monthly_view(rows, as_of):
    groups=defaultdict(lambda:defaultdict(dict))
    for row in rows:
        if row['observation_level']!='detail' or Decimal(row['price'])<=0 or row['date']>as_of.isoformat(): continue
        key=(row['period'],)+tuple(row[k] for k in DIMENSIONS)
        signature=stable_id(row['raw_fields'])
        groups[key][row['date']][signature]=row  # Exact duplicates cannot overweight a date.
    output=[]
    for key,days in sorted(groups.items()):
        part=[r for quotes in days.values() for r in quotes.values()]
        representative=max(part,key=lambda r:r['date'])
        prices=[sum(Decimal(r['price']) for r in quotes.values())/len(quotes) for quotes in days.values()]
        item={k:representative.get(k,'') for k in MONTH_FIELDS}
        item.update(date=key[0]+'-01',period=key[0],price=str(sum(prices)/len(prices)),
            price_min=str(min(prices)),price_max=str(max(prices)),observed_days=len(days),observation_count=len(part),
            first_observation_date=min(days),last_observation_date=max(days),
            period_status='observed_days_only',
            price_type='Media mensual derivada de precios modales diarios',
            method='Unweighted mean of daily means of distinct published MOPK quotes, full dimensions; no volume weights or interpolation',
            multiple_quotes_days=sum(len(q)>1 for q in days.values()),
            raw_members=json.dumps(sorted({r['member'] for r in part}),ensure_ascii=False),schema_version=VERSION)
        item['capture_timestamp']=max(r['capture_timestamp'] for r in part)
        lineage={r['capture_id']:{k:r[k] for k in ['capture_id','raw_sha256','source_url']} for r in part}
        item['lineage_json']=json.dumps([lineage[k] for k in sorted(lineage)],ensure_ascii=False,sort_keys=True)
        item['observation_id']=stable_id([VERSION,key,representative['raw_sha256']])
        output.append(item)
    if not output: raise InvalidSource('No publishable monthly detail')
    return output

def validate_monthly(rows):
    if not rows: raise InvalidSource('Empty monthly view')
    ids=set()
    for row in rows:
        if row['schema_version']!=VERSION or row['currency']!='ARS' or row['price_unit']!='kg' or row['source']!='MERCADO_CENTRAL' or row['observation_level']!='detail' or not Decimal(row['price']).is_finite() or Decimal(row['price'])<=0:
            raise InvalidSource('Monthly view contract invalid')
        if not re.fullmatch(r'[a-f0-9]{64}',row['raw_sha256']) or row['observation_id'] in ids:
            raise InvalidSource('Monthly identity/hash invalid')
        allowed(row['source_url']); date.fromisoformat(row['date'])
        if row['date']!=row['period']+'-01' or row['last_observation_date'][:7]!=row['period'] or int(row['observed_days'])<1:
            raise InvalidSource('Monthly period/coverage invalid')
        ids.add(row['observation_id'])
    return rows

def read_published(root):
    folder=root/'dashboard/mcba'
    marker=json.loads((folder/'_SUCCESS.json').read_bytes())
    body=(folder/FILE).read_bytes()
    if marker['files'].get(FILE)!=sha256(body): raise InvalidSource('Monthly output hash mismatch')
    rows=list(csv.DictReader(io.StringIO(body.decode('utf-8'))))
    if marker['record_count']!=len(rows): raise InvalidSource('Monthly count mismatch')
    return validate_monthly(rows)

def run(root,year,as_of,allow_web=False,replay=False):
    raw=root/'raw/mcba'; raw.mkdir(parents=True,exist_ok=True)
    previous=read_published(root) if (root/'dashboard/mcba/_SUCCESS.json').exists() else []
    state={'source':'Mercado Central de Buenos Aires','requested_date':as_of.isoformat(),'attempted_at':utc_now()}
    try:
        if replay:
            publications=json.loads((raw/'.published_index.json').read_bytes())
        else:
            if not allow_web: raise InvalidSource('Network requires --allow-web')
            html,_,_=request(PAGE,2_000_000)
            publications=discover(html.decode('utf-8'),year)
            atomic_write(raw/'.published_index.json',(json.dumps(publications)+'\n').encode())
        if not publications:
            state['status']='NO_PUBLICATION'
            rows=previous
        else:
            stored={}
            for path in sorted(raw.glob('*/manifest.json')):
                m=json.loads(path.read_text(encoding='utf-8'));stored[m['url']]=(path.parent,m)
            cache=json.loads((raw/'.http_cache.json').read_bytes()) if (raw/'.http_cache.json').exists() else {}
            selected=[]; changed=False
            for publication in publications:
                url=publication['url']; headers={}
                if url in cache:
                    if cache[url].get('etag'):headers['If-None-Match']=cache[url]['etag']
                    elif cache[url].get('last_modified'):headers['If-Modified-Since']=cache[url]['last_modified']
                body,response_headers,status=(None,{},304) if replay else request(url,MAX_ZIP,headers)
                if status==304:
                    if url not in stored: raise InvalidSource('304 without local RAW')
                    folder,m=stored[url]
                else:
                    members,excluded=inventory(body);digest=sha256(body)
                    if url in stored and stored[url][1]['sha256']==digest:
                        folder,m=stored[url]
                    else:
                        stamp=utc_now();capture=stamp.replace(':','').replace('.','')+'-'+digest[:12]
                        folder=raw/capture;folder.mkdir()
                        m={**publication,'original_name':publication['name'],'captured_at_utc':stamp,
                           'sha256':digest,'size_bytes':len(body),'http_status':status,
                           'content_type':response_headers.get('Content-Type',''),'members':members,
                           'excluded_member_count':excluded,'capture_id':capture,'schema_version':VERSION,
                           'parser_version':PARSER_VERSION,'method':'GET','public_parameters':{},'index_url':PAGE}
                        (folder/'response.zip').write_bytes(body)
                        (folder/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
                        changed=True
                    cache[url]={'etag':response_headers.get('ETag'),'last_modified':response_headers.get('Last-Modified')}
                m={**m,**publication}  # Older exploratory manifests stay immutable; add only in-memory evidence.
                selected.append((folder,m))
                if not replay:time.sleep(.2)
            atomic_write(raw/'.http_cache.json',(json.dumps(cache)+'\n').encode())
            fingerprints={m['url']:m['sha256'] for _,m in selected}
            index_path=root/'dashboard/mcba/SOURCE_INDEX.json'
            known=json.loads(index_path.read_bytes()) if index_path.exists() else {}
            if previous and known.get('fingerprints')==fingerprints and known.get('parser_version')==PARSER_VERSION:
                state.update(status='NO_OP_ALREADY_CURRENT',last_observation_date=max(r['last_observation_date'] for r in previous),
                    last_successful_update=max(r['capture_timestamp'] for r in previous),row_count=len(previous),
                    frequency='mensual derivada de observaciones diarias',source_url=PAGE)
                atomic_write(root/'dashboard/mcba/UPDATE_STATUS.json',(json.dumps(state,ensure_ascii=False,indent=2)+'\n').encode())
                print('[PUBLISH] MCBA Mercado Central '+json.dumps(state,ensure_ascii=True))
                return state
            normalized=[];rules=load_rules()
            for folder,m in selected:
                body=(folder/'response.zip').read_bytes()
                if sha256(body)!=m['sha256']: raise InvalidSource('RAW SHA mismatch')
                members,_=inventory(body)
                with zipfile.ZipFile(io.BytesIO(body)) as archive:
                    part=[]
                    for member in members: part.extend(normalize_book(archive.read(member['name']),member['name'],m,rules))
                target=root/'normalized/mcba'/m['capture_id']/'observations.jsonl'
                atomic_write(target,(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in part)).encode())
                normalized.extend(part)
            rows=monthly_view(normalized,as_of);validate_monthly(rows)
            atomic_write(root/'analytical/mcba/daily.jsonl',(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in normalized)).encode())
            atomic_write(root/'analytical/mcba/monthly.jsonl',(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)).encode())
            # Preserve older, uncovered years/periods rather than silently truncating history.
            covered={(r['period'],r['type']) for r in rows}
            rows=[r for r in previous if (r['period'],r['type']) not in covered]+rows
            validate_monthly(rows)
            candidate=csv_bytes(rows,list(MONTH_FIELDS))
            different=not previous or candidate!=(root/'dashboard/mcba'/FILE).read_bytes()
            if different:
                from scripts.magyp.common.platform import publish_bundle
                publish_bundle(root/'dashboard/mcba',{FILE:candidate},len(rows))
                state['status']='UPDATED'
            else: state['status']='NO_OP_ALREADY_CURRENT'
            atomic_write(index_path,(json.dumps({'schema_version':VERSION,'parser_version':PARSER_VERSION,'fingerprints':fingerprints},sort_keys=True,indent=2)+'\n').encode())
        state['status']=state.get('status','NO_PUBLICATION')
    except Exception as exc:
        state['status']='SOURCE_UNAVAILABLE' if isinstance(exc,SourceUnavailable) else 'PIPELINE_ERROR'
        state['error_type']=type(exc).__name__
        rows=previous
        atomic_write(root/'dashboard/mcba/UPDATE_STATUS.json',(json.dumps({**state,'last_observation_date':max((r['last_observation_date'] for r in rows),default=None),'last_successful_update':max((r['capture_timestamp'] for r in rows),default=None)})+'\n').encode())
        raise
    state.update(last_observation_date=max((r['last_observation_date'] for r in rows),default=None),
                 last_successful_update=max((r['capture_timestamp'] for r in rows),default=None),row_count=len(rows),
                 frequency='mensual derivada de observaciones diarias',source_url=PAGE)
    atomic_write(root/'dashboard/mcba/UPDATE_STATUS.json',(json.dumps(state,ensure_ascii=False,indent=2)+'\n').encode())
    print('[PUBLISH] MCBA Mercado Central '+json.dumps(state,ensure_ascii=True))
    return state

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root',type=Path,default=ROOT/'data/mercado_central')
    p.add_argument('--year',type=int,default=2026)
    p.add_argument('--as-of',type=date.fromisoformat,default=datetime.now(timezone(timedelta(hours=-3))).date())
    p.add_argument('--allow-web',action='store_true')
    p.add_argument('--replay',action='store_true',help='Reprocess verified local RAW, no network')
    args=p.parse_args()
    try:run(args.data_root,args.year,args.as_of,args.allow_web,args.replay)
    except Exception as exc:
        print('[VALIDATE] '+type(exc).__name__+': '+str(exc)+'; last valid retained',file=sys.stderr)
        return 1
    return 0
if __name__=='__main__': raise SystemExit(main())
