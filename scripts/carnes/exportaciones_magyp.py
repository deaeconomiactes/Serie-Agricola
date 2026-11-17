"""Captura conservadora de la planilla oficial mensual de indicadores bovinos."""
from __future__ import annotations
import hashlib, io, json, math, os, tempfile, time, uuid
from http.client import IncompleteRead
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2] / 'data/carnes'
URL = 'https://www.magyp.gob.ar/sitio/areas/ss_ganaderia/archivos/Planilla_indicadores_bovinos_desde_1990_MENSUAL.xlsx'
REPORT = 'https://www.magyp.gob.ar/sitio/areas/bovinos/informacion_sectorial/_archivos/000030_Indicadores/000001-%20Indicadores%20bovinos.pdf'

def fetch_official():
    """Retry transient connection failures, preserving the existing size limit."""
    for attempt in range(3):
        try:
            request=Request(URL,headers={'User-Agent':'Mozilla/5.0 (compatible; SerieAgricola/1.0)'})
            with urlopen(request,timeout=45) as response:
                return response.read(5000001)
        except HTTPError as exc:
            if exc.code not in (429,500,502,503,504): raise
            error=exc
        except (OSError, URLError, IncompleteRead) as exc:
            error=exc
        print(f'[FETCH] intento {attempt+1}/3: {type(error).__name__}: {error}',flush=True)
        if attempt<2: time.sleep((3,9)[attempt])
    raise URLError(f'No se pudo descargar tras 3 intentos: {error}')

def parse(payload):
    if not payload.startswith(b'PK') or len(payload)>5000000: raise ValueError('XLSX inválido')
    book=load_workbook(io.BytesIO(payload),data_only=True,read_only=True)
    if len(book.sheetnames)!=1 or not book.sheetnames[0].startswith('Indicadores mensuales 1990-'): raise ValueError('Hoja desconocida')
    sheet=book.active; it=sheet.iter_rows(values_only=True); head=[next(it) for _ in range(5)]
    if 'EXPORTACION DE CARNE VACUNA' not in str(head[3][14]) or 'equivalentes' not in str(head[4][14]) or 'Miles de USD' not in str(head[4][15]): raise ValueError('Encabezado desconocido')
    rows=[]; previous=''
    for pos,row in enumerate(it,6):
        day=row[1]
        if not isinstance(day,datetime): continue
        d=day.date()
        if d.day!=1 or d>date.today(): raise ValueError('Fecha inválida')
        key=d.isoformat()
        if key<=previous: raise ValueError('Fechas repetidas o desordenadas')
        previous=key; values=row[14:16]
        if values==(None,None): continue
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 for x in values): raise ValueError(f'Valores incompletos fila {pos}')
        rows.append({'date':key,'tonnes_rch':values[0],'usd_thousands':values[1],'source_locator':f'{sheet.title}!O{pos}:P{pos}'})
    book.close()
    if not rows or rows[0]['date']!='1990-01-01': raise ValueError('Cobertura inicial incompleta')
    return rows

def atomic(path, obj):
    path.parent.mkdir(parents=True,exist_ok=True);fd,name=tempfile.mkstemp(dir=path.parent,suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf8') as f: json.dump(obj,f,ensure_ascii=False,separators=(',',':'));f.write('\n')
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def update(root=ROOT,fetch=None):
    root=Path(root);now=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z');out=root/'dashboard/exportaciones_magyp.json';status=root/'reports/EXPORTACIONES_MAGYP_STATUS.json'
    try:
        payload=(fetch or fetch_official)()
    except (OSError,URLError,TimeoutError) as e:
        result={'status':'SOURCE_UNAVAILABLE','checked_at':now,'message':str(e)};atomic(status,result);return result
    sha=hashlib.sha256(payload).hexdigest();capture=now.replace(':','').replace('-','')+'_'+uuid.uuid4().hex[:12];raw=root/'raw/exportaciones_magyp'/capture;raw.mkdir(parents=True)
    (raw/'response.xlsx').write_bytes(payload);atomic(raw/'manifest.json',{'url':URL,'capture_date':now,'sha256':sha,'bytes':len(payload)})
    try:
        rows=parse(payload);old=json.loads(out.read_text('utf8')) if out.exists() else None
        if old and (rows[-1]['date']<old['rows'][-1]['date'] or not {r['date'] for r in old['rows']}.issubset({r['date'] for r in rows})):raise ValueError('La captura reduce la cobertura')
        state='NO_PUBLICATION' if old and old.get('raw_sha256')==sha else 'UPDATED'
        if state=='UPDATED':atomic(out,{'schema_version':'exportaciones-magyp-v1','source_url':URL,'report_url':REPORT,'capture_date':now,'raw_sha256':sha,'rows':rows})
        result={'status':state,'checked_at':now,'last_observation':rows[-1]['date'],'raw_sha256':sha,'capture_id':capture}
    except Exception as e:result={'status':'PIPELINE_ERROR','checked_at':now,'message':f'{type(e).__name__}: {e}','raw_sha256':sha,'capture_id':capture}
    atomic(status,result);return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--allow-web',action='store_true');args=parser.parse_args()
    if not args.allow_web:raise SystemExit('Use --allow-web')
    result=update();print(json.dumps(result,ensure_ascii=False));raise SystemExit(result['status']=='PIPELINE_ERROR')
