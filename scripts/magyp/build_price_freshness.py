"""Audit published price outputs; operational states are explicit, never calendar guesses."""
from __future__ import annotations
import argparse
import csv
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.magyp.common.platform import atomic_write
STATES={'UPDATED','NO_OP_ALREADY_CURRENT','NO_PUBLICATION','SOURCE_UNAVAILABLE','MAGYP_LAST_VALID','LAST_VALID','PIPELINE_ERROR','STATIC','NOT_REPORTED'}
REPORT='data/magyp/reports/PRICE_FRESHNESS_STATUS.json'

def read_csv(path,delimiter=';'):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream,delimiter=delimiter))

def read_json(path,default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def validate_report(report):
    required={'mcba','mcba_monthly','corrientes','local_mensual','sio','magyp_internal','magyp_board','magyp_fas','magyp_fob','magyp_futures'}
    sources=report.get('sources',[])
    if report.get('schema_version')!='price-freshness-v1' or len(sources)!=len(required) or {r['source_family'] for r in sources}!=required:
        raise ValueError('Incomplete price freshness report')
    for row in sources:
        if row['status'] not in STATES or not isinstance(row['automatic_update'],bool):
            raise ValueError('Invalid price freshness state')
        if row['last_observation_date']:
            datetime.strptime(row['last_observation_date'],'%Y-%m-%d')
        if row['last_successful_update']:
            datetime.fromisoformat(row['last_successful_update'].replace('Z','+00:00'))
    return report


def add_commodities_history(report,root):
    """Cobertura histórica explícita; no altera fuentes ajenas a Commodities."""
    catalog=read_json(root/'data/magyp/dashboard/commodities/history/index.json',{})
    if not catalog:return report
    if catalog.get('schema_version')!='magyp-history-v1':raise ValueError('Unknown commodities history schema')
    for row in report['sources']:
        family=row['source_family'].removeprefix('magyp_')
        entry=catalog.get('families',{}).get(family) if row['source_family'].startswith('magyp_') else None
        if entry:
            coverage=entry['coverage']
            row['historical_coverage']={k:coverage[k] for k in ('oldest_verified_date','latest_verified_date','positive_rows',
                'monthly_rows','products','markets','currency','unit','coverage_status','last_successful_capture')}
            row['effective_sources']=['MAGyP / SSPM series 358.1; separate from position API'] if family=='fob' else ['MAGyP official historical publications','MAGyP current publication']
            row['history_automation']='Reproducible CLI; periodic current-family workflow remains independent'
            row['historical_coverage']['status']='VALIDATED_BACKFILL'
            # El éxito de un archivo histórico no acredita éxito del workflow actual.
            row['effective_data_last_observation_date']=max(row.get('last_observation_date') or '',coverage['latest_verified_date'])
            row['effective_data_last_capture']=max(row.get('last_successful_update') or '',coverage['last_successful_capture'])
        if row['source_family']=='local_mensual':
            cutover=catalog.get('families',{}).get('internal',{}).get('legacy_comparison',{})
            row['runtime_active']=not cutover.get('can_retire_legacy',False)
            if not row['runtime_active']:
                row['notes']=f"Retirado del runtime habitual: {cutover['covered_rows']}/{cutover['legacy_rows']} observaciones cubiertas y comparadas con publicaciones oficiales. Original conservado para auditoría."
    return report

def build(root=ROOT,mcba_status=None,sio_status=None):
    old=read_json(root/REPORT,{'sources':[]})
    prior={r['source_family']:r for r in old['sources']}
    records=[]
    def add(key,source,market,frequency,day,stamp,auto,workflow,notes,currency,unit,state=None):
        before=prior.get(key,{})
        state=state or {}
        if (before.get('attempted_at') or '') > (state.get('attempted_at') or ''):
            state=before
        status=state.get('result') or state.get('status') or ('STATIC' if not auto else before.get('status','NOT_REPORTED'))
        if status not in STATES: raise ValueError('Unknown price freshness status')
        records.append(dict(source_family=key,source=source,market=market,frequency=frequency,
            last_observation_date=day or None,last_successful_update=stamp or None,status=status,
            automatic_update=auto,workflow=workflow,notes=notes + (' ' + state['diagnostic_note'] if state.get('diagnostic_note') else ''),currency=currency,unit=unit,
            requested_date=state.get('requested_date',before.get('requested_date')),
            attempted_at=state.get('attempted_at',before.get('attempted_at')),
            diagnostic_note=state.get('diagnostic_note'),evidence=state.get('evidence',before.get('evidence'))))
    for family,file,frequency in [('magyp_internal','internal','mensual'),('magyp_board','board','diaria'),
        ('magyp_fas','fas','diaria cuando publica'),('magyp_fob','fob','diaria cuando publica'),('magyp_futures','futures','diaria cuando publica')]:
        from scripts.magyp.grains.references import validate_bundle
        rows=validate_bundle((root/f'data/magyp/dashboard/commodities/{file}.csv').read_bytes(),file)
        summary=next(r for r in rows if r['row_kind']=='resumen')
        observations=[r for r in rows if r['row_kind']=='observation' and (file!='fas' or r['regime']=='D.E.C.')]
        # D.E.R. is retained in its CSV but never sets freshness of D.E.C.
        if file=='fas' and not observations:
            observations=[r for r in rows if r['row_kind']=='observation' and 'D.E.C' in r.get('tipo_precio','')]
        def values(field): return sorted({r.get(field) or 'Sin identificar' for r in observations})
        day=max((r['fecha'] for r in observations),default=summary['fecha_max'])
        stamp=max((r['updated_at_utc'] for r in observations),default=summary['fecha_actualizacion_dashboard'])
        state=read_json(root/f'data/magyp/reports/PRICE_STATE_{file}.json',{})
        add(family,'MAGyP',values('mercado'),frequency,day,stamp,True,'magyp-commodities-review.yml',
            'Familia independiente; sin interpolación. D.E.R. sólo histórico.' if file=='fas' else 'Familia independiente; sin interpolación.',values('moneda'),values('unidad'),state)
    from scripts.magyp.mcba.published_bundle import read_bundle
    read_bundle(root/'data/magyp/dashboard/mcba')
    summary=read_csv(root/'data/magyp/dashboard/mcba/MCBA_MAGYP_SUMMARY.csv',',')[0]
    state=mcba_status or read_json(root/'data/magyp/dashboard/mcba/MCBA_MAGYP_UPDATE_STATUS.json',{})
    if not (state.get('result') or state.get('status')) and state.get('source_status')=='MAGYP_LAST_VALID':
        state={**state,'status':'MAGYP_LAST_VALID'}
    add('mcba','MAGyP','Mercado Central de Buenos Aires','diaria cuando publica',summary['date_max'],summary['updated_at'],True,
        'update-magyp-mcba.yml','Edge Windows; fecha civil argentina; último bundle válido ante indisponibilidad.',['ARS'],['kg'],state)
    legacy=read_csv(root/'PRECIOS_MAYORISTAS_INTEGRADO.csv')
    for key,market,note in [('corrientes','Mercado de Corrientes','Fuente legacy principal, actualización manual.'),
        ('mcba_monthly','Mercado Central de Buenos Aires','Mensual legacy; no se deriva del diario MAGyP.')]:
        subset=[r for r in legacy if r.get('mercado')==market and (key!='mcba_monthly' or r.get('fecha_precision','').lower()=='mensual')]
        dates=[]
        today=datetime.now(timezone(timedelta(hours=-3))).date().isoformat()
        for row in subset:
            value=row.get('fecha','')
            for fmt in ('%Y-%m-%d','%d/%m/%Y'):
                try: dates.append(datetime.strptime(value[:10],fmt).date().isoformat()); break
                except ValueError: pass
        future=sum(d>today for d in dates)
        dates=[d for d in dates if d<=today]
        if future: note+=f' {future} filas futuras excluidas del indicador, igual que en el dashboard; originales conservados.'
        if key=='mcba_monthly' and (root/'data/mercado_central/dashboard/mcba/_SUCCESS.json').exists():
            from scripts.mercado_central.update_mcba_monthly import read_published as central_read
            monthly=central_read(root/'data/mercado_central')
            state=read_json(root/'data/mercado_central/dashboard/mcba/UPDATE_STATUS.json',{})
            add(key,'Mercado Central de Buenos Aires',market,'mensual derivada de observaciones diarias',
                max(r['last_observation_date'] for r in monthly),max(r['capture_timestamp'] for r in monthly),True,
                'update-mcba-monthly-central.yml',
                'Media mensual de modales diarios por serie y días observados; no es promedio mensual oficial MAGyP. Legacy en períodos/categorías sin cobertura.',
                ['ARS'],['kg'],state)
        else:
            add(key,'Legacy',market,'mensual' if key=='mcba_monthly' else 'según planilla',max(dates,default=None),None,False,None,note,sorted({r.get('moneda') or 'Sin identificar' for r in subset}),
                sorted({r.get('unidad_precio_observado') or r.get('unidad') or 'Sin identificar' for r in subset}))
    cutover=read_json(root/'data/magyp/dashboard/commodities/history/index.json',{}).get('families',{}).get('internal',{}).get('legacy_comparison',{})
    if cutover.get('can_retire_legacy'):
        # Audit-only metadata: production no longer reads manual price CSVs.
        archive=prior.get('local_mensual',{})
        local={'fecha_max':archive.get('last_observation_date'),
            'monedas':'|'.join(archive.get('currency') or ['ARS']),
            'unidades':'|'.join(archive.get('unit') or ['TN'])}
    else:
        local=read_csv(root/'data/commodities_local_mensual/dashboard/COMMODITIES_LOCAL_MENSUAL_DASHBOARD_RESUMEN.csv')[0]
    add('local_mensual','Legacy precios internos','plazas informadas','mensual',local.get('fecha_max'),None,False,None,
        'Histórico local mensual disponible por separado; sin reemplazar MAGyP.',
        local.get('monedas','Sin identificar').split('|'),local.get('unidades','Sin identificar').split('|'),{'status':'STATIC'})
    sio=read_csv(root/'data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_RESUMEN.csv')[0]
    state={'status':sio_status,'attempted_at':datetime.now(timezone.utc).isoformat()} if sio_status else {}
    add('sio',sio.get('fuente','SIO Granos'),'plazas informadas','transaccional / snapshot diario',sio.get('fecha_max'),sio.get('fecha_ultima_captura_sio'),True,
        'update-sio-commodities.yml','Operaciones transaccionales; snapshot reciente, no reconstrucción de contratos.',sio.get('monedas','').split('|'),sio.get('unidades','').split('|'),state)
    report=add_commodities_history({'schema_version':'price-freshness-v1','sources':records},root)
    validate_report(report)
    atomic_write(root/REPORT,(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--mcba-status',type=Path)
    p.add_argument('--sio-status',choices=sorted(STATES))
    p.add_argument('--commodities-history-only',action='store_true',help='Enriquece el reporte publicado sin recalcular otros módulos')
    a=p.parse_args()
    if a.commodities_history_only:
        report=add_commodities_history(validate_report(read_json(a.root/REPORT)),a.root)
        validate_report(report)
        atomic_write(a.root/REPORT,(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    else:
        report=build(a.root,read_json(a.mcba_status) if a.mcba_status else None,a.sio_status)
    for r in report['sources']:
        print(f"[FRESHNESS] {r['source_family']} {r['status']} last={r['last_observation_date']} updated={r['last_successful_update']}")
if __name__=='__main__': main()
