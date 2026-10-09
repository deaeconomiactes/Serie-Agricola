"""Referencias MAGyP independientes. Stdlib; RAW público sin estado de sesión."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import os
import re
import tempfile
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from statistics import median
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[3]
BASE = 'https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/'
GRAINS = BASE + 'areas/granos/_archivos/'
SOURCES = {
    'internal': GRAINS + '000056_Precios%20Locales/000010_Precios%20Internos%20de%20los%20Principales%20Granos/000001_Informe%20Actual%20de%20la%20Evolucion%20Precios%20Internos%20de%20Granos.php',
    'board': GRAINS + '000056_Precios%20Locales/000020_Precios%20C%C3%A1mara%20-%20Diario/000001_Cotizaciones%20de%20Pizarra%20sobre%20Puerto%20-%20Precios%20C%C3%A1maras.php?accion=imp',
    'fas': 'https://dinem.magyp.gob.ar/dinem_fas.cfas_all.aspx',
    'fob': BASE + 'ws/ssma/precios_fob.php',
    'futures': GRAINS + '000057_Precios%20Internacionales/000010_Futuros%20-%20Chicago,%20Kansas,%20Winnipeg%20(Diario)/000001_Informe.php',
}
VERSION = 'magyp-references-v1'
MAX_BYTES = 1_500_000
MONTHS = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,
          'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
SHORT = {'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,'jul':7,'ago':8,'sep':9,'set':9,'oct':10,'nov':11,'dic':12}
FAS_CODES = ['TP','MA','CEBC','CEBF','SOR','SO','GI','AS','AG']
# Exact labels from the public DINEM grid JavaScript, not inferred expansions.
FAS_LABELS = ['Trigo Pan','Maíz','Cebada C.','Cebada F.','Sorgo','Soja','Girasol','Ac.Soja','Ac.Girasol']
FAS_DICTIONARY_URL = 'https://dinem.magyp.gob.ar/dinem_fas/cfasn_c.js'
CONTEXT_URL = 'https://www.magyp.gob.ar/mercadosagropecuarios/precios.php'
FIELDS = ['row_kind','fecha','periodo_ym','commodity','fuente','mercado','tipo_precio','moneda','unidad',
          'frecuencia','condicion_comercial','series_id','observation_id','record_id','price_raw','price',
          'value_status','position_raw','circular','shipment_window','regime','product_code','currency_evidence',
          'operaciones','volumen_total','precio_mediana','precio_promedio','precio_min','precio_max',
          'variacion_mensual_pct','variacion_interanual_pct','variacion_7d_pct','variacion_30d_pct',
          'estado','periodo_ultimo','fecha_ultima','precio_mediana_ultimo_periodo','operaciones_ultimo_periodo',
          'fecha_actualizacion_dashboard','fecha_min','fecha_max','filas_dashboard','source_url',
          'updated_at_utc','raw_sha256','capture_id','schema_version','coverage_note']


class Error(ValueError):
    """Only fixed diagnostic messages, never response bodies or session state."""


def digest(body):
    return hashlib.sha256(body).hexdigest()


def encoded(obj):
    return (json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')


def identity(obj):
    return digest(encoded(obj))


def atomic(path, body):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent,prefix='.stage-')
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(body); f.flush(); os.fsync(f.fileno())
        if not path.exists() or path.read_bytes()!=body:
            os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


@contextmanager
def lock(root):
    path=root/'references.lock'; root.mkdir(parents=True,exist_ok=True)
    try:
        with path.open('x',encoding='utf-8') as f: f.write(str(os.getpid()))
    except FileExistsError:
        raise Error('Otro proceso o lock pendiente; revisar antes de actualizar')
    try: yield
    finally: path.unlink()


class PublicPage(HTMLParser):
    """Tables/text plus two explicitly public data vectors. Ignore all other inputs."""
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
        self.ignore=0; self.text=[]; self.grids={}

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in {'script','style'}: self.ignore+=1
        if tag=='tr': self.row=[]
        if tag in {'td','th'} and self.row is not None: self.cell=[]
        if tag=='br' and self.cell is not None: self.cell.append(' ')
        if tag=='input' and attrs.get('name') in {'W0031GridContainerDataV','W0039GridContainerDataV'}:
            name=attrs['name']
            if name in self.grids: raise Error('Grilla repetida')
            try: self.grids[name]=json.loads(attrs.get('value',''))
            except ValueError: raise Error('JSON de grilla inválido')

    def handle_data(self,value):
        if self.ignore: return
        self.text.append(value)
        if self.cell is not None: self.cell.append(value)

    def handle_endtag(self,tag):
        if tag in {'script','style'}: self.ignore=max(0,self.ignore-1)
        if tag in {'td','th'} and self.cell is not None:
            if self.row is not None: self.row.append(' '.join(' '.join(self.cell).split()))
            self.cell=None
        if tag=='tr' and self.row is not None:
            self.rows.append(self.row); self.row=None


def unique_json(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise Error('Campo JSON repetido')
        result[key]=value
    return result


def project(body,source,encoding='utf-8'):
    try:
        if source=='fob':
            obj=json.loads(body.decode('utf-8-sig'),object_pairs_hook=unique_json)
            # Observed official no-publication response: exactly [], not a new row schema.
            # Preserve the original structure; never accept a populated root array.
            if isinstance(obj,list) and not obj:
                return obj
            if not isinstance(obj,dict) or set(obj)!={'posts'} or not isinstance(obj['posts'],list):
                raise Error('Schema FOB cambiado')
            required={'fecha','circular','posicion','precio','mesDesde','añoDesde','mesHasta','añoHasta'}
            if any(not isinstance(row,dict) or set(row)!=required for row in obj['posts']):
                raise Error('Campos FOB cambiados')
            return obj
        p=PublicPage(); p.feed(body.decode(encoding))
        obj={'rows':p.rows,'text':' '.join(' '.join(p.text).split())}
        if source=='fas': obj['grids']=p.grids
        return obj
    except (UnicodeError,LookupError,json.JSONDecodeError):
        raise Error('Respuesta no parseable')


def number(raw,style):
    text=str(raw).strip()
    if text in {'','-','S/C'}: return '', 'missing'
    if style=='ar':
        if not re.fullmatch(r'\d+(?:\.\d{3})*(?:,\d+)?',text): raise Error('Precio local inválido')
        text=text.replace('.','').replace(',','.')
    elif style=='us':
        if not re.fullmatch(r'\d+(?:,\d{3})*(?:\.\d+)?',text): raise Error('Precio pizarra inválido')
        text=text.replace(',','')
    elif not re.fullmatch(r'\d+(?:\.\d+)?',text): raise Error('Precio JSON inválido')
    try: value=Decimal(text)
    except InvalidOperation: raise Error('Precio inválido')
    if not value.is_finite() or value<0: raise Error('Precio no finito/negativo')
    return format(value,'f'), 'positive' if value>0 else 'zero'


def spanish_date(text):
    m=re.search(r'\b(\d{1,2}) de (\w+) de (\d{4})\b',text,re.I)
    if not m or m[2].lower() not in MONTHS: raise Error('Fecha publicada ausente')
    try: return date(int(m[3]),MONTHS[m[2].lower()],int(m[1])).isoformat()
    except ValueError: raise Error('Fecha publicada inválida')


def observation(source,day,product,market,kind,currency,unit,raw,style='ar',condition='',**extra):
    value,status=number(raw,style)
    row={'fecha':day,'periodo_ym':day[:7],'commodity':product,'fuente':'MAGyP',
         'mercado':market,'tipo_precio':kind,'moneda':currency,'unidad':unit,
         'frecuencia':'mensual' if source=='internal' else 'diaria',
         'condicion_comercial':condition,'price_raw':str(raw),'price':value,'value_status':status,
         'source_url':SOURCES[source],'schema_version':VERSION,**extra}
    # Every useful economic dimension is part of series identity, including maturity/regime/circular.
    row['series_id']=identity([source,product,market,kind,currency,unit,condition,
                               extra.get('circular',''),extra.get('product_code','')])
    row['observation_id']=identity([row['series_id'],day])
    return row


def parse_internal(obj):
    if 'Pesos Argentinos por Toneladas' not in obj['text']: raise Error('Unidad internos cambió')
    products=[['TRIGO']*5+['MAIZ']*4+['SORGO']*3,['SOJA']*4+['GIRASOL']*4+['CEBADA FORRAJERA']*2]
    plazas=[['DARSENA','ROSARIO','B.BLANCA','CORDOBA','QUEQUEN','DARSENA','ROSARIO','B.BLANCA','QUEQUEN','DARSENA','ROSARIO','B.BLANCA'],
            ['DARSENA','ROSARIO','B.BLANCA','QUEQUEN','DARSENA','ROSARIO','B.BLANCA','QUEQUEN','B.BLANCA','QUEQUEN']]
    out=[]; block=None; year=None; header=False; blocks=set()
    for cells in obj['rows']:
        if cells==['AÑO \\ MES','TRIGO','MAIZ','SORGO']: block=0; header=False; year=None; blocks.add(0);continue
        if cells==['AÑO \\ MES','SOJA','GIRASOL','CEBADA FORRAJERA']: block=1;header=False;year=None;blocks.add(1);continue
        if block is None: continue
        if cells==plazas[block]: header=True;continue
        if len(cells)==1 and re.fullmatch(r'20\d\d',cells[0]): year=int(cells[0]);continue
        if cells and cells[0].lower() in MONTHS:
            if not header or year is None or len(cells)!=len(products[block])+1: raise Error('Schema internos cambió')
            month=MONTHS[cells[0].lower()]; day=date(year,month,1).isoformat()
            for product,plaza,raw in zip(products[block],plazas[block],cells[1:]):
                out.append(observation('internal',day,product,plaza,'Precio interno mensual','ARS','TN',raw,
                                       currency_evidence='documented'))
    if blocks!={0,1}: raise Error('Bloque internos ausente')
    return out


def parse_board(obj):
    if '$/Tn' not in obj['text'] or 'provisorias' not in obj['text']: raise Error('Contexto pizarra cambió')
    day=spanish_date(obj['text']); header=['PRODUCTO','BUENOS AIRES','BAHIA BLANCA','QUEQUEN','ROSARIO','CORDOBA']
    expected={'GIRASOL','TRIGO PAN','MAIZ','SOJA','SORGO','CEBADA FORRAJERA'}
    active=False; seen=set(); out=[]
    for cells in obj['rows']:
        if cells==header: active=True;continue
        if active and cells and cells[0] in expected:
            if len(cells)!=6: raise Error('Schema pizarra cambió')
            seen.add(cells[0])
            for plaza,raw in zip(header[1:],cells[1:]):
                out.append(observation('board',day,cells[0],plaza,'Pizarra provisional','ARS','TN',raw,'us',
                                       currency_evidence='contextual'))
        elif active and len(cells)==6:
            raise Error('Producto pizarra desconocido')
    if seen!=expected: raise Error('Productos pizarra cambiados')
    return out


def parse_fas(obj):
    if set(obj.get('grids',{}))!={'W0031GridContainerDataV','W0039GridContainerDataV'}: raise Error('Grillas FAS cambiadas')
    # v1 first local smoke used the model whose labels were verified separately.
    # New acquisitions MUST verify and embed the public JS dictionary in fetch().
    columns=obj.get('columns',list(zip(FAS_CODES,FAS_LABELS)))
    if columns != list(zip(FAS_CODES,FAS_LABELS)) and columns != [list(x) for x in zip(FAS_CODES,FAS_LABELS)]:
        raise Error('Diccionario FAS cambiado/no validado')
    out=[]
    for name,regime in [('W0031GridContainerDataV','D.E.C.'),('W0039GridContainerDataV','D.E.R.')]:
        grid=obj['grids'][name]
        if not isinstance(grid,list) or not grid: raise Error('Grilla FAS vacía')
        for cells in grid:
            if not isinstance(cells,list) or len(cells)!=10: raise Error('Schema FAS cambió')
            try: day=datetime.strptime(cells[0],'%d/%m/%Y').date().isoformat()
            except (ValueError,TypeError): raise Error('Fecha FAS inválida')
            for code,product,raw in zip(FAS_CODES,FAS_LABELS,cells[1:]):
                # Portal corroborates ARS/t for seven grains; oil units need their own evidence.
                known=code not in {'AS','AG'}
                out.append(observation('fas',day,product,'Argentina / paridad teórica',f'FAS teórico {regime}',
                    'ARS' if known else 'Sin identificar','TN' if known else 'Sin identificar',raw,'json',regime,
                    regime=regime,product_code=code,currency_evidence='contextual' if known else 'unknown'))
    return out


def parse_fob(obj,requested):
    if obj==[] or obj=={'posts':[]}:
        raise Error('FOB sin publicación para la fecha solicitada; respuesta vacía no publicable')
    out=[]
    for r in obj['posts']:
        try:
            day=datetime.fromisoformat(r['fecha']).date().isoformat()
            months=[r['mesDesde'],r['mesHasta']]; years=[r['añoDesde'],r['añoHasta']]
            if any(isinstance(v,bool) or not isinstance(v,int) for v in months+years): raise ValueError()
            first=date(years[0],months[0],1);last=date(years[1],months[1],1)
            if first>last or day!=requested: raise ValueError()
        except (ValueError,TypeError): raise Error('Fecha/embarque FOB inválido')
        if not isinstance(r['posicion'],str) or not r['posicion'].strip(): raise Error('Posición FOB inválida')
        if not isinstance(r['circular'],str) or not r['circular'].strip(): raise Error('Circular FOB inválida')
        window=first.isoformat()[:7]+'/'+last.isoformat()[:7]
        out.append(observation('fob',day,'Posición '+r['posicion'],'FOB oficial / plaza no informada',
            'FOB oficial','Sin identificar','Sin identificar',r['precio'],'json',window,
            position_raw=r['posicion'],circular=r['circular'],shipment_window=window,currency_evidence='unknown'))
    return out


def parse_futures(obj):
    if 'Cotizaciones de cierre' not in obj['text'] or 'Dólares Estadounidenses/Ton.' not in obj['text']:
        raise Error('Definición futuros cambió')
    anchor=date.fromisoformat(spanish_date(obj['text'])); market=None; products=None; dates=None; out=[]
    markets=set()
    for cells in obj['rows']:
        if cells==['CHICAGO *'] or cells==['KANSAS *']:
            market=cells[0].replace(' *','');products=None;dates=None;markets.add(market);continue
        if cells and cells[0].startswith('COTIZACIONES FOB'): break  # Physical FOB is never futures.
        if not market: continue
        if cells and cells[0]=='POSICION':
            expected=['TRIGO','MAIZ','AVENA','SOJA','HARINA DE SOJA','ACEITE DE SOJA'] if market=='CHICAGO' else ['TRIGO']
            if cells[1:]!=expected: raise Error('Columnas futuros cambiaron')
            products=expected;continue
        if products and cells and re.fullmatch(r'\d{1,2}/[a-z]{3}',cells[0],re.I):
            if len(cells)!=len(products)*2: raise Error('Fechas futuros cambiaron')
            dates=[]
            for text in cells:
                dd,mm=text.lower().split('/')
                if mm not in SHORT: raise Error('Mes futuro desconocido')
                # Explicit full publication date anchors both columns; handle Dec/Jan only.
                year=anchor.year-(1 if anchor.month==1 and SHORT[mm]==12 else 0)
                try: day=date(year,SHORT[mm],int(dd))
                except ValueError: raise Error('Fecha futuros inválida')
                if not 0<=(anchor-day).days<=10: raise Error('Fecha de columna no compatible')
                dates.append(day.isoformat())
            continue
        if cells and re.fullmatch(r'[A-Z]{3}\d{4}',cells[0]):
            if not products or not dates or len(cells)!=1+2*len(products): raise Error('Schema futuros cambió')
            pos=cells[0];mm=pos[:3].lower()
            if mm not in SHORT: raise Error('Vencimiento desconocido')
            maturity=date(int(pos[3:]),SHORT[mm],1).isoformat()[:7]
            for i,raw in enumerate(cells[1:]):
                out.append(observation('futures',dates[i],products[i//2],market,'Futuro / cierre','USD','TN',raw,
                    condition=pos,position_raw=pos,shipment_window=maturity,currency_evidence='documented'))
    if markets!={'CHICAGO','KANSAS'}: raise Error('Mercados futuros cambiaron')
    return out


def parse(obj,source,as_of,requested=None):
    parsers={'internal':parse_internal,'board':parse_board,'fas':parse_fas,'futures':parse_futures}
    rows=parse_fob(obj,requested) if source=='fob' else parsers[source](obj)
    if not rows or not any(r['value_status']=='positive' for r in rows): raise Error('Respuesta sin precios positivos')
    seen=set()
    for row in rows:
        try: observed=date.fromisoformat(row['fecha'])
        except ValueError: raise Error('Fecha inválida')
        if observed>as_of: raise Error('Observación futura')
        if row['observation_id'] in seen: raise Error('Identidad duplicada/conflictiva')
        seen.add(row['observation_id'])
    newest=max(date.fromisoformat(r['fecha']) for r in rows)
    if (as_of-newest).days>(70 if source=='internal' else 10): raise Error('Fuente sin publicación reciente')
    return rows


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None


def fetch(source,requested,as_of,root):
    url=SOURCES[source]
    if source=='fob': url+='?'+urlencode({'Fecha':date.fromisoformat(requested).strftime('%d/%m/%Y')})
    try:
        with build_opener(NoRedirect()).open(Request(url,headers={'User-Agent':'Serie-Agricola references/1.0'}),timeout=20) as response:
            body=response.read(MAX_BYTES+1); status=response.status
            ctype=response.headers.get('Content-Type','');encoding=response.headers.get_content_charset() or 'utf-8'
    except (HTTPError,URLError,OSError): raise Error('Servicio HTTP no disponible; última salida preservada')
    print(f'[FETCH] {source} HTTP {status}')
    if status!=200 or len(body)>MAX_BYTES: raise Error('Status/tamaño inválido')
    obj=project(body,source,encoding)
    dictionary_hash=''
    if source=='fas':
        try:
            with build_opener(NoRedirect()).open(Request(FAS_DICTIONARY_URL,headers={'User-Agent':'Serie-Agricola references/1.0'}),timeout=20) as r:
                dictionary=r.read(200001)
                if r.status!=200 or len(dictionary)>200000: raise Error('Diccionario FAS inválido')
            columns=re.findall(r'addSingleLineEdit\("[^"\n]+",\d+,"v(TP|MA|CEBC|CEBF|SOR|SO|GI|AS|AG)","([^"\n]+)"',dictionary.decode('utf-8'))
            if columns!=list(zip(FAS_CODES,FAS_LABELS)): raise Error('Orden/etiquetas FAS cambiaron')
            obj['columns']=columns; dictionary_hash=digest(dictionary)
        except (HTTPError,URLError,OSError,UnicodeError): raise Error('Diccionario FAS no disponible')
    no_publication=source=='fob' and (obj==[] or obj=={'posts':[]})
    rows=[] if no_publication else parse(obj,source,as_of,requested)
    stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    capture=stamp.replace(':','').replace('.','')+'_'+uuid.uuid4().hex
    safe=encoded(obj)
    manifest={'source':source,'source_family':'commodity_reference_price','url':url,'method':'GET',
        'public_parameters':{'Fecha':requested} if source=='fob' else {},'requested_date':requested,
        'captured_at_utc':stamp,'status':status,'content_type':ctype,'encoding':encoding,
        'response_size_bytes':len(body),'response_sha256':digest(body),'sha256':digest(safe),'size_bytes':len(safe),
        'parser_version':VERSION,'schema_version':VERSION,'capture_id':capture,'record_count':len(rows),
        'raw_representation':'public_projection_json','private_state_stored':False,
        'dictionary_url':FAS_DICTIONARY_URL if source=='fas' else '', 'dictionary_sha256':dictionary_hash}
    if source=='fob':
        manifest['publication_status']='NO_PUBLICATION' if no_publication else 'PUBLISHED'
    folder=root/'raw'/'commodities'/source/capture
    folder.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.capture-',dir=folder.parent))
    try:
        (stage/'response.json').write_bytes(safe);(stage/'manifest.json').write_bytes(encoded(manifest))
        stage.rename(folder)
    finally:
        if stage.exists():
            for f in stage.iterdir(): f.unlink()
            stage.rmdir()
    if no_publication:
        print(f'[VALIDATE] fob NO_PUBLICATION fecha={requested}; última salida conservada')
        return None
    print(f'[VALIDATE] {source} {len(rows)} celdas válidas')
    return folder


def normalize(folder,root,as_of):
    try:
        payload=(folder/'response.json').read_bytes();m=json.loads((folder/'manifest.json').read_bytes())
        if (m['sha256']!=digest(payload) or m['size_bytes']!=len(payload) or m['status']!=200 or
                m['schema_version']!=VERSION or m['parser_version']!=VERSION or m['capture_id']!=folder.name):
            raise Error('Integridad RAW inválida')
        source=m['source']
        if source=='fob' and m.get('publication_status')=='NO_PUBLICATION':
            obj=project(payload,'fob')
            date.fromisoformat(m['requested_date'])
            if m['record_count']!=0 or not (obj==[] or obj=={'posts':[]}):
                raise Error('Metadata NO_PUBLICATION FOB inválida')
            print('[NORMALIZE] fob NO_PUBLICATION; captura sin observaciones')
            return []
        rows=parse(json.loads(payload),source,date.fromisoformat(m['requested_date']),m['requested_date'])
        if len(rows)!=m['record_count']: raise Error('Conteo RAW inválido')
        for row in rows:
            row.update(capture_id=m['capture_id'],updated_at_utc=m['captured_at_utc'],raw_sha256=m['sha256'])
            row['record_id']=identity([row['observation_id'],m['capture_id'],m['sha256']])
        path=root/'normalized'/'commodities'/source/(m['capture_id']+'.json')
        atomic(path,encoded(rows))
        print(f'[NORMALIZE] {source} {len(rows)} registros')
        return rows
    except (OSError,KeyError,ValueError,TypeError) as exc:
        if isinstance(exc,Error): raise
        raise Error('RAW/manifest inválido') from None


def csv_read(body):
    return list(csv.DictReader(io.StringIO(body.decode('utf-8-sig')),delimiter=';'))


def analytical(source,root):
    """Latest entire day/month capture, retaining withdrawals and zero/missing cells."""
    paths=sorted((root/'normalized'/'commodities'/source).glob('*.json'))
    partitions={}
    for path in paths:
        rows=json.loads(path.read_bytes())
        for day in sorted({r['fecha'] for r in rows}):
            part=[r for r in rows if r['fecha']==day]
            rank=(part[0]['updated_at_utc'],part[0]['capture_id'])
            if day not in partitions or rank>partitions[day][0]: partitions[day]=(rank,part)
    if not partitions: raise Error('No hay NORMALIZED válido')
    output=root/'dashboard'/'commodities'/(source+'.csv')
    # Dashboard observation rows are the small persistent analytical memory across Actions runs.
    # Current partitions replace the COMPLETE period; old dates are kept without cross-source filling.
    old=[]
    if output.exists():
        old=validate_bundle(output.read_bytes(),source)
    current=[r for _,part in partitions.values() for r in part]
    previous=[r for r in old if r['row_kind']=='observation' and r['fecha'] not in partitions]
    rows=sorted(previous+current,key=lambda r:(r['fecha'],r['series_id']))
    atomic(root/'analytical'/'commodities'/(source+'.json'),encoded(rows))
    return rows


def pct(value,previous):
    return '' if previous is None or previous<=0 else str((Decimal(str(value))/Decimal(str(previous))-1)*100)


def state(value):
    if value=='':return 'Sin dato'
    x=Decimal(value)
    return 'Revisar' if abs(x)>50 else 'Baja' if x < -5 else 'Estable' if x<=5 else 'Suba moderada' if x<=20 else 'Suba fuerte'


def shifted(period,months):
    y,m=map(int,period.split('-'));total=y*12+m-1+months
    return f'{total//12:04d}-{total%12+1:02d}'


def bundle(rows,source):
    positives=[r for r in rows if r['value_status']=='positive']
    if not positives: raise Error('Publicación vacía rechazada')
    output=[{**r,'row_kind':'observation'} for r in rows]
    groups=defaultdict(list)
    for r in positives: groups[(r['series_id'],r['periodo_ym'])].append(r)
    monthly=[]
    for (_,period),part in sorted(groups.items()):
        r=max(part,key=lambda r:r['fecha']);prices=[Decimal(x['price']) for x in part]
        monthly.append({**r,'row_kind':'mensual','frecuencia':'mensual','periodo_ym':period,
            'precio_mediana':str(median(prices)),'precio_promedio':str(sum(prices)/len(prices)),
            'precio_min':str(min(prices)),'precio_max':str(max(prices)),'operaciones':len(part),
            'coverage_note':'Valor mensual publicado' if source=='internal' else 'Mediana de días capturados; mes parcial, sin interpolar'})
    by_series=defaultdict(list)
    for r in monthly: by_series[r['series_id']].append(r)
    for series in by_series.values():
        lookup={r['periodo_ym']:Decimal(r['precio_mediana']) for r in series}
        for r in series:
            r['variacion_mensual_pct']=pct(r['precio_mediana'],lookup.get(shifted(r['periodo_ym'],-1)))
            r['variacion_interanual_pct']=pct(r['precio_mediana'],lookup.get(shifted(r['periodo_ym'],-12)))
            r['estado']=state(r['variacion_mensual_pct'])
        last=max(series,key=lambda r:r['periodo_ym'])
        output.append({**last,'row_kind':'ultimos','periodo_ultimo':last['periodo_ym'],
            'fecha_ultima':last['fecha'],'precio_mediana_ultimo_periodo':last['precio_mediana'],
            'operaciones_ultimo_periodo':last['operaciones']})
    output+=monthly
    output+=[{**r,'row_kind':'semaforo'} for r in monthly]
    if source!='internal':
        by_day={(r['series_id'],r['fecha']):Decimal(r['price']) for r in positives}
        for r in positives:
            day=date.fromisoformat(r['fecha'])
            output.append({**r,'row_kind':'diario','precio_mediana':r['price'],'precio_promedio':r['price'],
                'precio_min':r['price'],'precio_max':r['price'],'operaciones':1,
                'variacion_7d_pct':pct(r['price'],by_day.get((r['series_id'],(day-timedelta(days=7)).isoformat()))),
                'variacion_30d_pct':pct(r['price'],by_day.get((r['series_id'],(day-timedelta(days=30)).isoformat())))})
    output.append({'row_kind':'resumen','fecha_min':min(r['fecha'] for r in positives),
        'fecha_max':max(r['fecha'] for r in positives),'filas_dashboard':len(positives),
        'fecha_actualizacion_dashboard':max(r['updated_at_utc'] for r in positives),
        'source_url':SOURCES[source],'schema_version':VERSION})
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=FIELDS,delimiter=';',lineterminator='\n',extrasaction='raise')
    writer.writeheader()
    for r in output:writer.writerow(r)
    body=stream.getvalue().encode('utf-8')
    validate_bundle(body,source)
    return body


def validate_bundle(body,source):
    rows=csv_read(body)
    if not rows or set(rows[0])!=set(FIELDS): raise Error('Schema dashboard inválido')
    summary=[r for r in rows if r['row_kind']=='resumen']
    observations=[r for r in rows if r['row_kind']=='observation']
    if len(summary)!=1 or not observations: raise Error('Dashboard vacío/incompleto')
    if any(r['schema_version']!=VERSION for r in rows): raise Error('Versión dashboard inválida')
    ids=set()
    for r in observations:
        expected_source=SOURCES[source]
        if r['source_url']!=expected_source or not re.fullmatch('[a-f0-9]{64}',r['raw_sha256']):raise Error('Trazabilidad dashboard inválida')
        if not r['record_id'] or not r['series_id'] or r['observation_id'] in ids: raise Error('Identidad dashboard inválida')
        ids.add(r['observation_id'])
        date.fromisoformat(r['fecha'])
        value,status=number(r['price'],'json') if r['price'] else ('','missing')
        if status!=r['value_status']: raise Error('Precio/estado dashboard inválido')
    count=sum(r['value_status']=='positive' for r in observations)
    if count<=0 or int(summary[0]['filas_dashboard'])!=count: raise Error('Conteo dashboard inválido')
    for r in rows:
        if r['row_kind'] not in {'observation','diario','mensual','ultimos','semaforo','resumen'}:raise Error('Vista dashboard desconocida')
        if r['row_kind'] in {'diario','mensual','ultimos','semaforo'} and number(r['precio_mediana'],'json')[1]!='positive':raise Error('Precio dashboard inválido')
    return rows


def run(source,root,as_of,requested,allow_web=False):
    with lock(root):
        if allow_web and fetch(source,requested,as_of,root) is None: return
        folders=sorted((root/'raw'/'commodities'/source).glob('*'))
        for folder in folders:
            if folder.is_dir() and not folder.name.startswith('.'):
                normalize(folder,root,as_of)
        rows=analytical(source,root)
        body=bundle(rows,source)
        atomic(root/'dashboard'/'commodities'/(source+'.csv'),body)
        print(f'[PUBLISH] {source} actualizado; {sum(r["value_status"]=="positive" for r in rows)} precios positivos')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',choices=list(SOURCES)+['all'],default='all')
    p.add_argument('--date',type=date.fromisoformat,required=True,help='Fecha ISO de control y fecha solicitada FOB')
    p.add_argument('--data-root',type=Path,default=ROOT/'data'/'magyp')
    p.add_argument('--allow-web',action='store_true')
    p.add_argument('--dry-run',action='store_true')
    args=p.parse_args()
    if args.dry_run:print('[FETCH] DRY-RUN: máximo 6 GET, sin red/escrituras');return 0
    sources=list(SOURCES) if args.source=='all' else [args.source]
    failed=False
    for i,source in enumerate(sources):
        try:run(source,args.data_root,args.date,args.date.isoformat(),args.allow_web)
        except Error as error:
            print(f'[VALIDATE] {source}: {error}; última salida conservada');failed=True
        except (OSError,ValueError,TypeError,KeyError):
            print(f'[VALIDATE] {source}: integridad/archivo inválido; última salida conservada');failed=True
        if args.allow_web and i<len(sources)-1:time.sleep(1.5)
    return 1 if failed else 0


if __name__=='__main__':raise SystemExit(main())
