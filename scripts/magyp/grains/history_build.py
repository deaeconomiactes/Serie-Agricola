"""Backfill reproducible: RAW verificado → SQLite/JSONL local → shards públicos livianos.

No modifica los cinco bundles de actualización corriente. El índice se publica al
final; un archivo rechazado nunca aporta una normalización parcial.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import io
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.magyp.grains import references as r, history_model as h

VERSION=h.VERSION
FAMILIES=tuple(r.SOURCES)
SERIES_FIELDS=('series_id','commodity','fuente','mercado','tipo_precio','moneda','unidad',
    'condicion_comercial','position_raw','circular','shipment_window','regime','product_code','currency_evidence')
COLUMNS=('fecha','series_key','price','price_raw','value_status','capture_key','source_locator','quality_flags',
    'operaciones','precio_promedio','precio_min','precio_max','variacion_mensual_pct',
    'variacion_interanual_pct','variacion_7d_pct','variacion_30d_pct','aggregation_captures')


def captures(root,family):
    latest={}
    for path in sorted((root/'raw/commodities/history'/family).glob('*/manifest.json')):
        m=json.loads(path.read_bytes())
        if m['family']!=family or m['schema_version']!=VERSION:raise r.Error('Manifest histórico incompatible')
        if m['representation']=='metadata_json':continue
        key=(m['source_url'],m.get('regime',''))
        if key not in latest or m['captured_at_utc']>latest[key][1]['captured_at_utc']:latest[key]=(path,m)
    return sorted(latest.values(),key=lambda item:item[1]['captured_at_utc'])


def parse_capture(path,m,as_of):
    if Path(m['raw_file']).name!=m['raw_file']:raise r.Error('Ruta RAW inválida')
    body=(path.parent/m['raw_file']).read_bytes()
    if r.digest(body)!=m['sha256'] or len(body)!=m['size_bytes']:raise r.Error('Hash/tamaño RAW histórico no coincide')
    family=m['family']
    if family=='internal':
        return h.internal_xlsx(body,m,as_of) if m['representation']=='xlsx' else h.internal_annual(json.loads(body),m,as_of)
    if family=='board':return h.board_archive(json.loads(body),m,as_of)
    if family=='fas':return h.fas_xlsx(body,m,as_of)
    if family=='futures':return (h.futures_daily if '/cotiza_' in m['source_url'] else h.futures_matrix)(json.loads(body),m,as_of)
    if family=='fob':
        dictionary=path.parent.parent/m['dictionary_capture_id']
        d=json.loads((dictionary/'manifest.json').read_bytes());b=(dictionary/d['raw_file']).read_bytes()
        if r.digest(b)!=d['sha256']:raise r.Error('Diccionario FOB sin integridad')
        dataset=json.loads(b)
        distributions=[x for x in dataset['distribution'] if str(x.get('identifier'))=='358.1']
        if len(distributions)!=1:raise r.Error('Diccionario FOB no unívoco')
        return h.fob_sspm(body,m,distributions[0],as_of)
    raise r.Error('Familia histórica desconocida')


def compact(row):
    result={k:row.get(k,'') for k in COLUMNS}
    result.update(series_key=row['series_id'][:16],capture_key=row['capture_id'],
        quality_flags='|'.join(row.get('quality_flags',[])))
    return result


def inventory_reports(root,index):
    for family,entry in index['families'].items():
        coverage=entry['coverage']
        coverage.update(files_endpoints_count=coverage['accepted_files']+len(coverage['rejected_files']),
            source_catalog='COMMODITIES_HISTORY_LINKS.json',traceability_registry=entry['registry']['path'])
        coverage['frequency']='mensual publicada' if family=='internal' else (
            'índice calendario diario; mensual derivada' if family=='fob' else 'diaria cuando publica; mensual derivada')
        if family=='fob':entry['monthly_method']='Median of published SSPM calendar-index values, including weekends; not an official monthly price'
    inventory={'schema_version':VERSION,'families':[e['coverage'] for e in index['families'].values()]}
    r.atomic(root/'reports/COMMODITIES_HISTORY_INVENTORY.json',r.encoded(inventory))
    columns=['family','oldest_verified_date','latest_verified_date','frequency','products','markets','currency','unit',
        'rows','positive_rows','monthly_rows','accepted_files','rejected_files','coverage_status','automation_status']
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,columns,delimiter=';',lineterminator='\n');writer.writeheader()
    for row in inventory['families']:
        item={k:row[k] for k in columns}
        for key in ('products','markets','currency','unit'):item[key]=' | '.join(item[key])
        item['rejected_files']=len(item['rejected_files']);writer.writerow(item)
    r.atomic(root/'reports/COMMODITIES_HISTORY_INVENTORY.csv',stream.getvalue().encode())
    labels={'internal':'Precio interno MAGyP','board':'Pizarra / Cámara','fas':'FAS D.E.C.',
        'fob':'FOB oficial / serie SSPM','futures':'Futuros externos'}
    lines=['HISTÓRICO OFICIAL DE PRECIOS COMMODITIES','',
        'Implementado localmente. No implica publicación ni despliegue.',
        'Cada familia, moneda, unidad, plaza y vencimiento permanece separado.','']
    for row in inventory['families']:
        lines += [labels[row['family']],
            f"  Cobertura verificada: {row['oldest_verified_date']} a {row['latest_verified_date']}",
            f"  Precios positivos: {row['positive_rows']:,}; filas normalizadas: {row['rows']:,}; filas mensuales: {row['monthly_rows']:,}",
            f"  Productos ({len(row['products'])}): {', '.join(row['products'])}",
            f"  Plazas ({len(row['markets'])}): {', '.join(row['markets'])}",
            f"  Moneda: {', '.join(row['currency'])}; unidad: {', '.join(row['unit'])}",
            f"  Frecuencia: {row['frequency']}",
            f"  Archivos aceptados: {row['accepted_files']}; apartados/no disponibles/sin publicación: {len(row['rejected_files'])}",
            '  Automatización: CLI reproducible; actualización corriente existente independiente.','']
    cutover=index['families'].get('internal',{}).get('legacy_comparison',{})
    if cutover:
        lines += [f"Histórico local mensual: {cutover['covered_rows']}/{cutover['legacy_rows']} filas cubiertas; huecos: {cutover['gap_rows']}; necesario: {cutover['legacy_still_needed_pct']}%.",
            f"Retiro de carga estática habitual autorizado por validación: {cutover['can_retire_legacy']}. Originales conservados para auditoría.",
            'El histórico local es de internos: no reemplaza FAS, FOB, Pizarra ni futuros.','']
    lines += ['Limitaciones:',
        '- FOB SSPM finaliza el 21/01/2025. Su índice calendario incluye fines de semana publicados; no confirma fecha de emisión MAGyP.',
        '- La API FOB corriente sigue separada: posición/circular/embarque y moneda/unidad sin identificar.',
        '- Futuros: matrices históricas y cierres diarios son tipos distintos; no existe roll automático.',
        '- FAS: aceites sin moneda/unidad identificadas. D.E.R. mantiene sólo su circuito histórico existente.',
        '- Internos mensual es publicado; las otras vistas mensuales son medianas derivadas, sin interpolar.',
        '- Archivos con fechas o precios conflictivos no se corrigen por inferencia. Ver rejected_files en inventario JSON.',
        '- No se afirma cobertura completa de ruedas/días no publicados. No se calcula porcentaje de huecos sin calendario oficial.',
        '- Detalle diario cargado por año; mensual permite toda la historia. Filtros, KPIs, gráficos y tablas conservados.',
        '', 'Documentación: docs/MAGYP_COMMODITIES_HISTORY.md',
        'Evidencia: COMMODITIES_HISTORY_INVENTORY.json/csv, COMMODITIES_HISTORY_LEGACY_COMPARISON.json y catálogo de enlaces.']
    r.atomic(root/'reports/COMMODITIES_HISTORY_FEEDBACK.txt',('\n'.join(lines)+'\n').encode())


def csv_bytes(rows):
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,COLUMNS,delimiter=';',lineterminator='\n')
    writer.writeheader();writer.writerows(rows)
    return stream.getvalue().encode()


def shard(folder,name,body,rows):
    compressed=gzip.compress(body,mtime=0)
    if len(compressed)>5_000_000 or len(body)>45_000_000:raise r.Error('Shard público excede límite')
    filename=f'{name}-{r.digest(compressed)[:16]}.gz'
    # Lectura de vuelta antes de publicar. Los archivos se direccionan por hash.
    if gzip.decompress(compressed)!=body:raise r.Error('Shard comprimido inválido')
    r.atomic(folder/filename,compressed)
    return dict(path=filename,sha256=r.digest(compressed),bytes=len(compressed),decoded_bytes=len(body),rows=rows)


def method_key(row):
    # No se calcula una variación a través de la modificación explícita de FAS girasol.
    return tuple(x for x in row.get('quality_flags',[]) if x.startswith('sunflower_formula_'))


def build_family(root,family,as_of):
    work=root/'analytical/commodities/history';work.mkdir(parents=True,exist_ok=True)
    stage=work/(family+'.stage.sqlite');stage.unlink(missing_ok=True)
    db=sqlite3.connect(stage)
    db.execute('create table obs (id text primary key, series text, day text, status text, payload text)')
    registry={'schema_version':VERSION,'family':family,'series':{},'captures':{}}
    rejected=[];accepted=[]
    try:
        for path,m in captures(root,family):
            db.execute('savepoint capture');count=0
            try:
                capture_meta={k:m[k] for k in ('source_url','sha256','captured_at_utc','capture_id','http_status')}
                for row in parse_capture(path,m,as_of):
                    count+=1
                    db.execute('insert or replace into obs values (?,?,?,?,?)',
                        (row['observation_id'],row['series_id'],row['fecha'],row['value_status'],json.dumps(row,ensure_ascii=False,separators=(',',':'))))
                if not count:raise r.Error('Captura histórica sin filas')
                db.execute('release capture');db.commit();accepted.append(m['capture_id'])
                registry['captures'][m['capture_id']]=capture_meta
            except (r.Error,ValueError,KeyError,TypeError,OverflowError) as exc:
                db.execute('rollback to capture');db.execute('release capture')
                rejected.append(dict(source_url=m['source_url'],capture_id=m['capture_id'],status=getattr(exc,'status','QUARANTINED'),reason=str(exc)))
        if not accepted:raise r.Error('No hay capturas históricas válidas; salida anterior conservada')
        published=root/'dashboard/commodities/history/index.json'
        if rejected and published.exists():
            old=json.loads(published.read_bytes()).get('families',{}).get(family)
            if old:
                from scripts.magyp.grains.history_validate import read
                previous=json.loads(read(published.parent/family,old['registry']))
                valid_urls={x['source_url'] for x in previous['captures'].values()}
                if any(x['source_url'] in valid_urls for x in rejected):
                    raise r.Error('Revisión de archivo antes válido rechazada; histórico publicado conservado')
        db.execute('create index by_series on obs(series,day)');db.commit()
        normalized=root/'normalized/commodities/history'/f'{family}.jsonl.gz'
        normalized.parent.mkdir(parents=True,exist_ok=True)
        # Base completa local: incluye cero, S/C, etiquetas y celdas originales.
        with gzip.open(normalized.with_suffix('.stage'),'wt',encoding='utf-8') as out:
            for payload, in db.execute('select payload from obs order by series,day'):out.write(payload+'\n')
        normalized.with_suffix('.stage').replace(normalized)
        folder=root/'dashboard/commodities/history'/family
        monthly=[];daily=defaultdict(list);counts=Counter();years=defaultdict(Counter)
        dates=[];products=set();markets=set();currencies=set();units=set()
        for series, in db.execute('select distinct series from obs order by series').fetchall():
            rows=[json.loads(x[0]) for x in db.execute('select payload from obs where series=? order by day',(series,))]
            sample=rows[0];key=series[:16]
            if key in registry['series'] and registry['series'][key]['series_id']!=series:raise r.Error('Colisión de ID compacto')
            registry['series'][key]={k:sample.get(k,'') for k in SERIES_FIELDS}
            positive={x['fecha']:x for x in rows if x['value_status']=='positive'}
            groups=defaultdict(list)
            for row in rows:
                counts[row['value_status']]+=1;years[row['fecha'][:4]][row['value_status']]+=1
                if row['value_status']!='positive':continue
                dates.append(row['fecha']);products.add(row['commodity']);markets.add(row['mercado'])
                currencies.add(row['moneda']);units.add(row['unidad']);groups[row['periodo_ym']].append(row)
                if family!='internal':
                    item={**row,'operaciones':1,'precio_promedio':row['price'],'precio_min':row['price'],'precio_max':row['price']}
                    for days in (7,30):
                        prior=positive.get((date.fromisoformat(row['fecha'])-timedelta(days=days)).isoformat())
                        item[f'variacion_{days}d_pct']=r.pct(row['price'],Decimal(prior['price'])) if prior and method_key(prior)==method_key(row) else ''
                    daily[row['fecha'][:4]].append(compact(item))
            aggregates={}
            for period,part in groups.items():
                prices=[Decimal(x['price']) for x in part];last=part[-1]
                item={**last,'price':str(median(prices)),'operaciones':len(part),'precio_promedio':str(sum(prices)/len(prices)),
                    'precio_min':str(min(prices)),'precio_max':str(max(prices)),
                    'aggregation_captures':'|'.join(sorted({x['capture_id'] for x in part}))}
                item['quality_flags']=sorted({f for x in part for f in x.get('quality_flags',[])})
                item['quality_flags'].append('official_monthly_value' if family=='internal' else 'derived_median_observed_days_no_interpolation')
                aggregates[period]=item
            for period,item in aggregates.items():
                for months,field in ((1,'variacion_mensual_pct'),(12,'variacion_interanual_pct')):
                    prior=aggregates.get(r.shifted(period,-months))
                    item[field]=r.pct(item['price'],Decimal(prior['price'])) if prior and method_key(item)==method_key(prior) else ''
                monthly.append(compact(item))
        if not dates:raise r.Error('Histórico sin precios positivos')
        monthly.sort(key=lambda x:(x['fecha'],x['series_key']))
        monthly_file=shard(folder,'monthly.csv',csv_bytes(monthly),len(monthly))
        daily_files={}
        for year,rows in sorted(daily.items()):
            rows.sort(key=lambda x:(x['fecha'],x['series_key']))
            daily_files[year]=shard(folder,f'daily-{year}.csv',csv_bytes(rows),len(rows))
        registry_file=shard(folder,'registry.json',r.encoded(registry),len(registry['series']))
        inventory=dict(family=family,oldest_verified_date=min(dates),latest_verified_date=max(dates),
            frequency='mensual publicada' if family=='internal' else
                'índice calendario diario; mensual derivada' if family=='fob' else 'diaria cuando publica; mensual derivada',
            products=sorted(products),markets=sorted(markets),currency=sorted(currencies),unit=sorted(units),
            rows=sum(counts.values()),positive_rows=counts['positive'],value_status_counts=dict(counts),
            monthly_rows=len(monthly),coverage_by_year={y:dict(v) for y,v in sorted(years.items())},
            accepted_files=len(accepted),rejected_files=rejected,coverage_status='VERIFIED_WITH_GAPS',
            files_endpoints_count=len(accepted)+len(rejected),source_catalog='COMMODITIES_HISTORY_LINKS.json',
            traceability_registry=registry_file['path'],
            automation_status='REPRODUCIBLE_BACKFILL; current workflow unchanged',schema_version=VERSION,
            last_successful_capture=max(x['captured_at_utc'] for x in registry['captures'].values()))
        entry=dict(schema_version=VERSION,family=family,registry=registry_file,monthly=monthly_file,daily=daily_files,
            coverage=inventory,columns=list(COLUMNS),source_priority='current exact series/date > historical exact series/date',
            monthly_method='Published monthly value' if family=='internal' else
                'Median of published SSPM calendar-index values, including weekends; not an official monthly price' if family=='fob' else
                'Median of observed daily values per exact series; no interpolation')
        db.close();stage.replace(work/(family+'.sqlite'))
        return entry
    finally:
        db.close()


def compare_legacy(root,entry):
    """Se compara por dimensiones económicas, nunca sólo por producto/fecha."""
    db=sqlite3.connect(root/'analytical/commodities/history/internal.sqlite')
    official={}
    for payload, in db.execute("select payload from obs where status='positive'"):
        row=json.loads(payload)
        official[(row['periodo_ym'],h.label(row['commodity']),h.label(row['mercado']),row['moneda'],row['unidad'],row['tipo_precio'])]=row
    # El bundle corriente tiene prioridad incluso si publica S/C para una celda.
    for row in r.csv_read((root/'dashboard/commodities/internal.csv').read_bytes()):
        if row['row_kind']=='observation':
            key=(row['periodo_ym'],h.label(row['commodity']),h.label(row['mercado']),row['moneda'],row['unidad'],row['tipo_precio'])
            if row['value_status']=='positive':official[key]=row
            else:official.pop(key,None)
    db.close()
    path=ROOT/'data/commodities_local_mensual/dashboard/COMMODITIES_LOCAL_MENSUAL_DASHBOARD_MENSUAL.csv'
    legacy=r.csv_read(path.read_bytes());comparison=[];gaps=[]
    for old in legacy:
        market=old['mercado'].split(' — ')[-1]
        key=(old['periodo_ym'],h.label(old['commodity']),h.label(market),old['moneda'],old['unidad'],old['tipo_precio'])
        new=official.get(key)
        item=dict(period=key[0],product=old['commodity'],market=market,currency=key[3],unit=key[4],
            legacy_price=old['precio_mediana'],official_price=new['price'] if new else None,
            covered=bool(new),absolute_difference=str(Decimal(new['price'])-Decimal(old['precio_mediana'])) if new else None)
        comparison.append(item)
        if not new:gaps.append(old)
    result=dict(schema_version=VERSION,legacy_rows=len(legacy),covered_rows=sum(x['covered'] for x in comparison),
        gap_rows=len(gaps),legacy_still_needed_pct=round(100*len(gaps)/len(legacy),2),
        can_retire_legacy=not gaps,legacy_file_sha256=r.digest(path.read_bytes()),comparison=comparison,
        rule='Exact period/product/market/type/currency/unit; official positives replace, legacy only genuine uncovered cells; no currency conversion')
    result['price_difference_rows']=sum(Decimal(x['absolute_difference'])!=0 for x in comparison if x['covered'])
    result['max_absolute_price_difference']=str(max((abs(Decimal(x['absolute_difference'])) for x in comparison if x['covered']),default=Decimal(0)))
    result['can_retire_legacy']=not gaps and result['price_difference_rows']==0
    entry['legacy_comparison']={k:v for k,v in result.items() if k!='comparison'}
    r.atomic(root/'reports/COMMODITIES_HISTORY_LEGACY_COMPARISON.json',r.encoded(result))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',choices=list(FAMILIES)+['all'],default='all')
    p.add_argument('--as-of',type=date.fromisoformat,default=date.today())
    p.add_argument('--data-root',type=Path,default=ROOT/'data/magyp')
    p.add_argument('--reports-only',action='store_true',help='Regenerar inventario desde shards publicados validados, sin RAW/red')
    a=p.parse_args();folder=a.data_root/'dashboard/commodities/history'
    index_path=folder/'index.json'
    index=json.loads(index_path.read_bytes()) if index_path.exists() else dict(schema_version=VERSION,families={})
    if a.reports_only:
        from scripts.magyp.grains.history_validate import validate
        validate(folder)
        inventory_reports(a.data_root,index)
        r.atomic(index_path,r.encoded(index))
        return 0
    for family in FAMILIES if a.source=='all' else [a.source]:
        entry=build_family(a.data_root,family,a.as_of)
        if family=='internal':compare_legacy(a.data_root,entry)
        # Ninguna familia válida depende de que la siguiente pueda normalizarse.
        with r.lock(folder):
            index=json.loads(index_path.read_bytes()) if index_path.exists() else dict(schema_version=VERSION,families={})
            index['families'][family]=entry
            r.atomic(index_path,r.encoded(index))
        print('[HISTORY PUBLISH]',family,entry['coverage']['positive_rows'],'precios',flush=True)
    inventory_reports(a.data_root,index)
    return 0


if __name__=='__main__':raise SystemExit(main())
