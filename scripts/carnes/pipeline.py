"""Controlled official meat-source discovery, immutable capture and atomic prepared data.

No frontend, network by default, contract reconstruction, unit conversion or scheduling.
"""
from __future__ import annotations
import argparse
import calendar
import csv
import gzip
import io
import json
import os
import re
import sys
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.carnes.model import DataError, FIELDS, FAMILIES, VERSION, digest
from scripts.carnes.csv_sources import parse_csv
from scripts.magyp.common.platform import atomic_write

DATA=ROOT/'data/carnes'
SSPM='https://infra.datos.gob.ar/catalog/sspm/data.json'
MAGYP='https://www.magyp.gob.ar/sitio/areas/gestion/bovinos.php?accion=imp'
INDICATORS='https://datos.magyp.gob.ar/dataset/indicadores-mensuales-sector-bovino/archivo/7afe10d1-e9bc-4383-9e3c-c8066bc21f65'
HOSTS={'infra.datos.gob.ar','www.magyp.gob.ar','datos.magyp.gob.ar'}
IDENTITY=['source_id','table_id','family','metric','species','observation_date','period_end','frequency',
    'category','age_class','geography','geography_level','market','entity_type','entity_id',
    'entity_name','entity_tax_id','entity_activity','currency','unit','weight_basis','methodology']


def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def now():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def read_json(path,default=None):return json.loads(path.read_bytes()) if path.exists() else default


@contextmanager
def writer_lock(root):
    root.mkdir(parents=True,exist_ok=True);path=root/'.writer.lock'
    try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:raise DataError('Another Carnes writer owns the lock') from None
    try:
        os.write(fd,str(os.getpid()).encode());os.close(fd)
        yield
    finally:path.unlink()


def public_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.fragment or p.port not in (None,443):
        raise DataError('URL outside official HTTPS allowlist')
    if p.query and not (p.path.endswith('/gestion/bovinos.php') and p.query=='accion=imp'):
        raise DataError('Undeclared URL parameters')
    return url


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            target=dict(attrs).get('href')
            if target:self.urls.append(target)


class SourceUnavailable(Exception):pass


class CaptureClient:
    def __init__(self,root=DATA):self.root=Path(root);self.requests=0
    def get(self,source_id,url,extension,max_bytes=8_000_000):
        if not re.fullmatch('[a-z0-9_]+',source_id):raise DataError('Invalid source ID')
        public_url(url)
        if self.requests>=24:raise DataError('Controlled request budget exhausted')
        if self.requests:time.sleep(1)
        self.requests+=1;start=time.monotonic()
        try:
            req=Request(url,headers={'User-Agent':'Serie-Agricola official-meat-source-inventory/1.0'})
            with build_opener(NoRedirect()).open(req,timeout=30) as response:
                body=response.read(max_bytes+1);status=response.status
                content_type=response.headers.get('Content-Type','')
                encoding=response.headers.get_content_charset()
        except (HTTPError,URLError,OSError) as error:
            raise SourceUnavailable(f'HTTP/service unavailable ({getattr(error,"code",type(error).__name__)})') from None
        if status!=200:raise SourceUnavailable(f'HTTP {status}')
        if len(body)>max_bytes:raise DataError('Response exceeds size limit')
        stamp=now();capture_id=stamp.replace(':','').replace('.','')+'_'+uuid.uuid4().hex[:12]
        folder=self.root/'raw'/source_id/capture_id
        folder.mkdir(parents=True,exist_ok=False)
        path=folder/('response.'+extension)
        # Exclusive files; failed/invalid downloads remain auditable RAW, never publication.
        with path.open('xb') as stream:stream.write(body)
        manifest=dict(source_id=source_id,source_url=url,method='GET',public_parameters={'accion':'imp'} if url==MAGYP else {},
            capture_date=stamp,capture_id=capture_id,status=status,content_type=content_type,encoding=encoding,
            size_bytes=len(body),raw_sha256=digest(body),parser_version=VERSION,schema_version=VERSION,
            duration_seconds=round(time.monotonic()-start,3),response_file=path.name)
        with (folder/'manifest.json').open('xb') as stream:stream.write(encoded(manifest))
        print(f'[FETCH] {source_id} HTTP {status} bytes={len(body)}',flush=True)
        return body,manifest


def discovered_links(body,base):
    parser=Links();parser.feed(body.decode('utf-8','strict'))
    return sorted({urljoin(base,url).replace(' ','%20') for url in parser.urls})


def discover(client):
    catalog_body,cat_manifest=client.get('catalog_sspm',SSPM,'json',20_000_000)
    catalog=json.loads(catalog_body)
    dataset=next(d for d in catalog['dataset'] if d['identifier']=='40')
    if dataset['title']!='Faena pecuaria':raise DataError('SSPM dataset identity changed')
    specs=[]
    for distribution in dataset['distribution']:
        if distribution['identifier'] not in {'40.1','40.3'}:continue
        specs.append(dict(source_id='sspm_'+distribution['identifier'].replace('.','_'),source='SAGyP / SSPM',
            url=public_url(distribution['downloadURL']),kind='sspm_faena',
            frequency='annual' if distribution['identifier']=='40.1' else 'monthly',
            units={f['title']:f.get('units','') for f in distribution['field'] if f['title']!='indice_tiempo'},
            license=dataset['license'],methodology='Published national aggregate; no reconstruction',
            catalog_url=SSPM,catalog_sha256=cat_manifest['raw_sha256'],source_metadata=distribution,
            temporal_metadata_warning='Catalog temporal field stale; actual CSV dates validated'))
    index_body,index_manifest=client.get('catalog_magyp',MAGYP,'html')
    for url in discovered_links(index_body,MAGYP):
        decoded=unquote(url)
        if not decoded.endswith('.xlsx'):continue
        if '/000001_Faena Bovina Serie Anual/' in decoded:
            match=re.search(r'Faena Bovina (\d{4})\.xlsx$',decoded)
            if not match:continue
            year=int(match[1]);source_id=f'magyp_slaughter_{year}';kind='slaughter_detail'
        elif decoded.endswith('0000001_faena-informe-bovino.xlsx'):
            year=None;source_id='magyp_slaughter_current';kind='slaughter_detail'
        elif decoded.endswith('000001_produccion-informe-bovino.xlsx'):
            year=None;source_id='magyp_production_current';kind='production_detail'
        else:continue
        specs.append(dict(source_id=source_id,source='MAGyP / DNCCA',url=public_url(url),kind=kind,
            expected_year=year,license='NOT_SPECIFIED',catalog_url=MAGYP,catalog_sha256=index_manifest['raw_sha256'],
            source_lifecycle='PUBLISHED_ANNUAL_ARCHIVE' if year else 'CURRENT_PUBLICATION'))
    indicators_body,ind_manifest=client.get('catalog_indicators',INDICATORS,'html')
    candidates=[u for u in discovered_links(indicators_body,INDICATORS) if u.endswith('/serie-tiempo-indicadores-mensuales-bovinos.csv')]
    if len(candidates)!=1:raise DataError('Historical indicator distribution changed')
    specs.append(dict(source_id='magyp_indicators_archive',source='MAGyP / Subsecretaría de Ganadería',
        url=public_url(candidates[0]),kind='bovine_indicators',frequency='monthly',license='NOT_SPECIFIED',
        catalog_url=INDICATORS,catalog_sha256=ind_manifest['raw_sha256'],source_lifecycle='HISTORICAL_ENDED',
        excluded_fields=['consumo_interno_aparente_en_miles_de_toneladas_res_c_hueso',
            'consumo_interno_per_capita_kg_por_habitante','consumo_interno_per_capita_kg_por_habitante_por_anio']))
    required={'sspm_40_1','sspm_40_3','magyp_slaughter_current','magyp_production_current','magyp_indicators_archive'}
    if not required.issubset({s['source_id'] for s in specs}):raise DataError('Official discovery missing required sources')
    ids=[s['source_id'] for s in specs]
    if len(ids)!=len(set(ids)):raise DataError('Duplicate discovered source')
    result=dict(schema_version=VERSION,discovered_at=now(),sources=sorted(specs,key=lambda s:s['source_id']))
    atomic_write(client.root/'catalog/sources.json',encoded(result))
    return result


def latest_capture(root,spec):
    captures=sorted((root/'raw'/spec['source_id']).glob('*/manifest.json'))
    if not captures:raise DataError('No RAW capture for source')
    path=captures[-1];manifest=read_json(path)
    if manifest['source_url']!=spec['url'] or manifest['source_id']!=spec['source_id']:
        raise DataError('Capture/catalog identity mismatch')
    body=(path.parent/manifest['response_file']).read_bytes()
    if manifest['status']!=200 or manifest['raw_sha256']!=digest(body) or manifest['size_bytes']!=len(body):
        raise DataError('RAW integrity failure')
    return body,manifest


def enrich(rows,spec,manifest,as_of):
    if not rows:raise DataError('Empty normalized output')
    seen=set();count=0
    for row in rows:
        if set(row)!=set(FIELDS):raise DataError('Normalizer observation contract changed')
        if row['family'] not in FAMILIES or row['frequency'] not in {'monthly','annual','year_to_date'}:
            raise DataError('Unknown family/frequency')
        day=date.fromisoformat(row['observation_date'])
        if day>as_of:raise DataError('Future observation')
        if not row['period_end']:
            row['period_end']=date(day.year,12,31).isoformat() if row['frequency']=='annual' else date(day.year,day.month,calendar.monthrange(day.year,day.month)[1]).isoformat()
        if row['period_end']<row['observation_date']:raise DataError('Invalid period bounds')
        if not row['unit'] or not row['currency'] or not row['geography'] or not row['source_locator']:
            raise DataError('Incomplete economic dimensions')
        row.update(source_id=spec['source_id'],source=spec['source'],source_url=spec['url'],
            capture_date=manifest['capture_date'],capture_id=manifest['capture_id'],raw_sha256=manifest['raw_sha256'])
        row['observation_id']=digest([row[k] for k in IDENTITY])
        if row['observation_id'] in seen:raise DataError('Duplicate economic observation')
        seen.add(row['observation_id'])
        row['record_id']=digest([row['observation_id'],row['capture_id'],row['raw_sha256']])
        from scripts.carnes.csv_sources import decimal_value
        if row['value_status']=='observed':
            if row['value'] is None or decimal_value(row['value']) is None:
                raise DataError('Observed value must be a nonempty number')
            count+=1
        elif row['value_status']=='missing':
            if row['value'] is not None:raise DataError('Missing flag conceals value')
        else:raise DataError('Unknown value status')
    if count==0:raise DataError('All values missing; last valid preserved')
    return rows


def csv_bytes(rows):
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=FIELDS,lineterminator='\n')
    writer.writeheader()
    for row in rows:writer.writerow({**row,'quality_flags':json.dumps(row['quality_flags'],ensure_ascii=False,separators=(',',':'))})
    return stream.getvalue().encode()


def build_source(root,spec,as_of):
    body,manifest=latest_capture(root,spec)
    if spec['kind'] in {'sspm_faena','bovine_indicators'}:rows=parse_csv(body,spec,as_of)
    else:
        from scripts.carnes.magyp_workbooks import parse_workbook
        rows=parse_workbook(body,spec['kind'],as_of,spec.get('expected_year'))
    rows=enrich(rows,spec,manifest,as_of)
    normalized=gzip.compress(b''.join(encoded(row) for row in rows),mtime=0)
    atomic_write(root/'normalized'/spec['source_id']/(manifest['capture_id']+'.jsonl.gz'),normalized)
    atomic_write(root/'analytical'/spec['source_id']/(manifest['capture_id']+'.csv.gz'),gzip.compress(csv_bytes(rows),mtime=0))
    # Full entity grain stays NORMALIZED/ANALYTICAL; dashboard begins with published
    # national/province/category observations, never an aggregate of redundant tables.
    public=[row for row in rows if row['entity_type'] not in {'establishment','user','slaughter_user','unlabelled_published_row'}
        and 'bird_count_scale_requires_validation' not in row['quality_flags']]
    if not public:raise DataError('No prepared dashboard observations')
    groups=defaultdict(list)
    for row in public:groups[(row['family'],row['frequency'],row['observation_date'][:4])].append(row)
    descriptors=[]
    for (family,frequency,year),part in sorted(groups.items()):
        compressed=gzip.compress(csv_bytes(part),mtime=0)
        if len(compressed)>5_000_000:raise DataError('Dashboard shard too large')
        name=f'{spec["source_id"]}-{family}-{frequency}-{year}-{digest(compressed)[:16]}.csv.gz'
        atomic_write(root/'dashboard'/name,compressed)
        descriptors.append(dict(path=name,sha256=digest(compressed),bytes=len(compressed),rows=len(part),family=family,frequency=frequency,year=year))
    entry=dict(source=spec['source'],source_url=spec['url'],source_id=spec['source_id'],kind=spec['kind'],
        capture_id=manifest['capture_id'],raw_sha256=manifest['raw_sha256'],last_successful_capture=manifest['capture_date'],
        first_observation=min(r['observation_date'] for r in rows),last_observation=max(r['observation_date'] for r in rows),
        rows=len(rows),observed_rows=sum(r['value'] is not None for r in rows),dashboard_rows=len(public),
        source_lifecycle=spec.get('source_lifecycle') or ('PUBLISHED_ANNUAL_ARCHIVE' if spec.get('expected_year') else 'CURRENT_PUBLICATION'),license=spec.get('license','NOT_SPECIFIED'),
        files=descriptors)
    from scripts.carnes.validate import validate_entry
    validate_entry(root/'dashboard',entry)
    index_path=root/'dashboard/index.json'
    index=read_json(index_path,dict(schema_version=VERSION,sources={}))
    if index['schema_version']!=VERSION:raise DataError('Unknown prepared index')
    previous=index['sources'].get(spec['source_id'])
    index['sources'][spec['source_id']]=entry
    atomic_write(index_path,encoded(index))
    print(f'[PUBLISH] {spec["source_id"]}: {len(rows)} normalized / {len(public)} dashboard',flush=True)
    return 'NO_OP_ALREADY_CURRENT' if previous==entry else 'UPDATED'


def inventory(root):
    catalog=read_json(root/'catalog/sources.json',{});index=read_json(root/'dashboard/index.json',{'sources':{}})
    output=[]
    for spec in catalog.get('sources',[]):
        entry=index['sources'].get(spec['source_id'])
        if not entry:continue
        path=root/'normalized'/spec['source_id']/(entry['capture_id']+'.jsonl.gz')
        groups=defaultdict(list)
        with gzip.open(path,'rt',encoding='utf-8') as stream:
            for line in stream:
                row=json.loads(line)
                groups[(row['family'],row['frequency'],row['species'],row['currency'],row['unit'])].append(row)
        for (family,frequency,species,currency,unit),part in sorted(groups.items()):
            observed=[r for r in part if r['value'] is not None]
            dates=[r['observation_date'] for r in observed]
            output.append(dict(family=family,source=spec['source'],source_id=spec['source_id'],source_url=spec['url'],
                oldest_date=min(dates,default=None),latest_date=max(dates,default=None),frequency=frequency,
                rows=len(part),observed_rows=len(observed),categories=sorted({r['category'] for r in part}),
                geography=sorted({r['geography_level'] for r in part}),geographies=len({r['geography'] for r in part}),
                currency=currency,unit=unit,species=species,metrics=sorted({r['metric'] for r in part}),
                automation_status='HTTP_REPRODUCIBLE',quality_status='VALIDATED_WITH_EXPLICIT_FLAGS',
                quality_flags=sorted({f for r in part for f in r['quality_flags']}),
                last_successful_capture=entry['last_successful_capture'],license=spec.get('license','NOT_SPECIFIED'),
                source_lifecycle=entry['source_lifecycle']))
    candidates=read_json(root/'catalog/candidates.json',{'sources':[]})
    output.extend(candidates['sources'])
    atomic_write(root/'reports/CARNES_SOURCE_INVENTORY.json',encoded(dict(schema_version=VERSION,sources=output)))
    stream=io.StringIO(newline='')
    if output:
        writer=csv.DictWriter(stream,fieldnames=list(dict.fromkeys(k for row in output for k in row)),lineterminator='\n');writer.writeheader()
        for row in output:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in row.items()})
    atomic_write(root/'reports/CARNES_SOURCE_INVENTORY.csv',stream.getvalue().encode())
    return output


def validate_catalog(catalog):
    if not catalog or catalog.get('schema_version')!=VERSION or not isinstance(catalog.get('sources'),list) or not catalog['sources']:
        raise DataError('Missing/unknown source catalog')
    ids=set()
    for spec in catalog['sources']:
        source_id=spec.get('source_id','')
        if not re.fullmatch('[a-z0-9_]+',source_id) or source_id in ids:raise DataError('Invalid/duplicate catalog source')
        ids.add(source_id);public_url(spec['url'])
        if not spec.get('source') or spec.get('kind') not in {'sspm_faena','bovine_indicators','slaughter_detail','production_detail'}:
            raise DataError('Unknown catalog source contract')
        if spec['kind']=='sspm_faena':
            from scripts.carnes.csv_sources import SSPM_COLUMNS
            if spec.get('frequency') not in {'monthly','annual'} or set(spec.get('units',{}))!=set(SSPM_COLUMNS[1:]):
                raise DataError('Unknown SSPM catalog contract')
    return catalog


def execute(args):
    root=args.data_root;client=CaptureClient(root)
    if args.command=='inventory':inventory(root);return 0
    states=read_json(root/'reports/CARNES_UPDATE_STATUS.json',dict(schema_version=VERSION,sources={}))
    try:
        if args.command in {'run','discover'}:
            try:
                catalog=discover(client)
                states['discovery']=dict(status='UPDATED',attempted_at=now(),used_existing_catalog=False)
            except SourceUnavailable as error:
                catalog=read_json(root/'catalog/sources.json')
                states['discovery']=dict(status='SOURCE_UNAVAILABLE',attempted_at=now(),reason=str(error),used_existing_catalog=bool(catalog))
                atomic_write(root/'reports/CARNES_UPDATE_STATUS.json',encoded(states))
                print('[STATE] discovery: SOURCE_UNAVAILABLE; last valid preserved',flush=True)
                if not catalog:return 0
        else:catalog=read_json(root/'catalog/sources.json')
        validate_catalog(catalog)
    except (DataError,ValueError,KeyError,TypeError,StopIteration) as error:
        states['discovery']=dict(status='PIPELINE_ERROR',attempted_at=now(),reason=f'{type(error).__name__}: {error}')
        atomic_write(root/'reports/CARNES_UPDATE_STATUS.json',encoded(states))
        print('[STATE] discovery: PIPELINE_ERROR; last valid preserved',flush=True)
        return 1
    atomic_write(root/'reports/CARNES_UPDATE_STATUS.json',encoded(states))
    if args.command=='discover':return 0
    specs=[s for s in catalog['sources'] if args.source=='all' or s['source_id']==args.source]
    if not specs:raise DataError('Unknown source selection')
    failed=False
    for spec in specs:
        status='PIPELINE_ERROR';reason=None
        try:
            if args.command=='run':client.get(spec['source_id'],spec['url'],'csv' if spec['kind'] in {'sspm_faena','bovine_indicators'} else 'xlsx')
            status=build_source(root,spec,args.as_of)
        except SourceUnavailable as error:status='SOURCE_UNAVAILABLE';reason=str(error)
        except (DataError,ValueError,KeyError,TypeError,OSError) as error:
            failed=True;reason=f'{type(error).__name__}: {error}'
        states['sources'][spec['source_id']]=dict(status=status,attempted_at=now(),reason=reason,last_valid_preserved=status not in {'UPDATED','NO_OP_ALREADY_CURRENT'})
        atomic_write(root/'reports/CARNES_UPDATE_STATUS.json',encoded(states))
        print(f'[STATE] {spec["source_id"]}: {status}'+(f' {reason}' if reason else ''),flush=True)
    inventory(root)
    return int(failed)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['discover','run','build','inventory'])
    parser.add_argument('--data-root',type=Path,default=DATA)
    parser.add_argument('--as-of',type=date.fromisoformat,default=datetime.now(timezone.utc).date())
    parser.add_argument('--source',default='all')
    parser.add_argument('--allow-web',action='store_true')
    args=parser.parse_args()
    if args.command in {'discover','run'} and not args.allow_web:
        print('[FETCH] DRY-RUN; use --allow-web for controlled public HTTP');return 0
    with writer_lock(args.data_root):return execute(args)


if __name__=='__main__':raise SystemExit(main())
