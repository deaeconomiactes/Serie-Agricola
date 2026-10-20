"""Coverage and controlled comparisons; never substitutes missing prices between sources."""
import csv
import json
import statistics
import unicodedata
import zipfile
import sys
from collections import defaultdict,Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.mercado_central.update_mcba_monthly import read_published,VERSION,inventory
from scripts.magyp.mcba.labels import normalized_label,load_rules
from scripts.magyp.common.platform import atomic_write

def report(root=ROOT):
    data=root/'data/mercado_central'
    monthly=read_published(data)
    daily=[]
    with (data/'analytical/mcba/daily.jsonl').open(encoding='utf-8') as stream:
        for line in stream:daily.append(json.loads(line))
    detail=[r for r in daily if r['observation_level']=='detail' and float(r['price'])>0]
    coverage=[]
    for period in sorted({r['period'] for r in detail}):
        for kind in ['Frutas','Hortalizas']:
            part=[r for r in detail if r['period']==period and r['type']==kind]
            coverage.append({'period':period,'type':kind,'daily_rows':len(part),
                'days':len({r['date'] for r in part}),'first_date':min((r['date'] for r in part),default=None),
                'last_date':max((r['date'] for r in part),default=None),
                'monthly_series':sum(r['period']==period and r['type']==kind for r in monthly)})
    with (root/'PRECIOS_MAYORISTAS_INTEGRADO.csv').open(encoding='utf-8-sig',newline='') as stream:
        legacy=[r for r in csv.DictReader(stream,delimiter=';') if r['mercado']=='Mercado Central de Buenos Aires' and r.get('fecha_precision','').lower()=='mensual']
    with (root/'data/magyp/dashboard/mcba/MCBA_MAGYP_DAILY.csv').open(encoding='utf-8') as stream:
        magyp=[r for r in csv.DictReader(stream) if r['observation_level']=='detail']
    rules=load_rules()
    def key(r):
        return tuple(''.join(c for c in unicodedata.normalize('NFKD',str(r.get(k,''))).upper() if not unicodedata.combining(c)).strip().rstrip('.') for k in ['date','type','product_normalized','variety_normalized','origin_normalized','package_normalized','quality','size','grade'])
    left=defaultdict(set);right=defaultdict(set)
    for r in detail:left[key(r)].add(float(r['price']))
    for r in magyp:right[key(r)].add(float(r['price']))
    common=set(left)&set(right);ratios=[];samples=[];ambiguous=0
    for k in sorted(common):
        if len(left[k])!=1 or len(right[k])!=1:ambiguous+=1;continue
        a=next(iter(left[k]));b=next(iter(right[k]));ratios.append(a/b)
        if len(samples)<8:samples.append({'date':k[0],'type':k[1],'product':k[2],'variety':k[3],
            'origin':k[4],'package':k[5],'quality':k[6],'size':k[7],'grade':k[8],
            'central_modal_kg':a,'magyp_published_kg':b,'ratio':a/b})
    legacy_periods={r['fecha'][:7] for r in legacy};new_periods={r['period'] for r in monthly}
    norm=lambda x:normalized_label('product',x,rules) or ''
    old_products={norm(r['especie']) for r in legacy};new_products={r['product_normalized'] for r in monthly}
    catalog=[]
    captures={r['capture_id'] for r in daily}
    for capture in sorted(captures):
        folder=data/'raw/mcba'/capture
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        members,excluded=inventory((folder/'response.zip').read_bytes())
        part=[r for r in daily if r['capture_id']==capture]
        catalog.append({'source_url':manifest['url'],'original_name':manifest['original_name'],
            'captured_at_utc':manifest['captured_at_utc'],'capture_id':capture,'raw_sha256':manifest['sha256'],
            'size_bytes':manifest['size_bytes'],'members':[m['name'] for m in members],
            'excluded_members':excluded,'format':'XLS BIFF2','observed_periods':sorted({r['period'] for r in part}),
            'first_date':min(r['date'] for r in part),'last_date':max(r['date'] for r in part)})
    result={'schema_version':VERSION,'zip_catalog':catalog,'format':'ZIP with daily XLS BIFF2, 14 columns',
        'source_frequency':'daily observations in monthly archives','dashboard_frequency':'derived monthly',
        'daily_rows':len(daily),'detail_price_rows':len(detail),'species_summary_rows':sum(r['observation_level']=='species_summary' for r in daily),
        'monthly_series':len(monthly),'coverage':coverage,
        'cross_period_members':sorted({r['member'] for r in daily if r['cross_period_member']}),
        'multiple_quote_monthly_series':sum(int(r['multiple_quotes_days'])>0 for r in monthly),
        'legacy_comparison':{'last_period':max(legacy_periods),'common_periods':sorted(legacy_periods&new_periods),
            'shared_products':sorted(old_products&new_products),
            'status':'NO_COMMON_MONTHLY_PERIOD' if not legacy_periods&new_periods else 'COMMON_PERIOD_AVAILABLE',
            'notes':'No se fuerza equivalencia de precios entre períodos distintos ni entre grados de detalle distintos.'},
        'magyp_daily_comparison':{'shared_dimension_keys':len(common),'unambiguous_pairs':len(ratios),
            'ambiguous_keys_not_matched':ambiguous,'median_ratio':statistics.median(ratios) if ratios else None,
            'within_one_percent':sum(abs(v-1)<=.01 for v in ratios),'samples':samples,
            'notes':'Matching fecha/rubro/especie/variedad/procedencia/envase/calidad/tamaño/grado; códigos expandidos según leyenda oficial, comparación de etiquetas sin tildes/punto final. KG no se equipara entre fuentes. MOPK modal y Promedio x Kg MAGyP son etiquetas diferentes.'}}
    target=root/'data/mercado_central/reports/MCBA_MONTHLY_VALIDATION.json'
    atomic_write(target,(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    return result
if __name__=='__main__':
    r=report()
    print(json.dumps({k:r[k] for k in ['daily_rows','detail_price_rows','monthly_series','magyp_daily_comparison']},ensure_ascii=True))
