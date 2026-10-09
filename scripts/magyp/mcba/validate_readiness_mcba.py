"""Controles offline de mes solicitado, comparaciones y duplicados; nunca adquiere datos."""
import argparse
import calendar
import json
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import PipelineError, atomic_write, csv_bytes, load_raw, sha256
from scripts.magyp.mcba.model import normalize, parse_export, build_analytical, stable_id
from scripts.magyp.mcba.labels import load_rules, canonical, normalized_label
from scripts.magyp.mcba.matching import mutual_unique_matches, price_current
from scripts.magyp.mcba.compare_mcba_current_vs_magyp import current_rows, precision, report_row
from scripts.magyp.mcba.validate_acquisition_mcba import export_attempts


def month_days(month):
    first = date.fromisoformat(month+'-01')
    return [(first+timedelta(days=i)).isoformat() for i in range(calendar.monthrange(first.year,first.month)[1])]


def plan_month(month):
    days = month_days(month)
    return [(days[i], days[min(i+6,len(days)-1)]) for i in range(0,len(days),7)]


def write_csv(path, rows, fields):
    atomic_write(path,csv_bytes(rows,fields))


def duplicate_groups(rows):
    groups = defaultdict(list)
    fields = ('fecha','rubro','especie','variedad','procedencia','envase','moneda',
              'unidad_precio_observado','unidad','observaciones')
    for r in rows:
        key = tuple(r.get(k,'') for k in fields)+(price_current(r),)
        groups[key].append(r)
    return [g for g in groups.values() if len(g)>1]


def audit_current(rows, input_file, folder):
    original = [r for r in rows if r['fecha']=='2026-08-19' and precision(r)=='day']
    groups = duplicate_groups(original)
    excluded = {id(r) for g in groups for r in g[1:]}
    diagnostic_unique = [r for r in original if id(r) not in excluded]
    # Vista contrafactual sólo para medir impacto; nunca se publica como base corregida.
    def avg(rs):
        prices = [price_current(r) for r in rs if price_current(r) is not None]
        return mean(prices) if prices else None
    records = [{'group_id':stable_id([g[0]['fecha'],g[0].get('especie'),g[0].get('variedad'),
                  g[0].get('procedencia'),g[0].get('envase'),price_current(g[0]),g[0].get('observaciones')]),
                'classification':'economic_duplicate', 'source_file_duplicate_status':'inferred_same_RF_nested_archive_not_byte_verified',
                'rows':len(g),'excess_rows':len(g)-1,'product':g[0].get('especie'),
                'price':price_current(g[0]),'current_row_references':[r.get('_current_row') for r in g],
                'source_files':[r.get('archivo_origen') for r in g], 'source_file_sha256':None} for g in groups]
    write_csv(folder/'MCBA_CURRENT_DUPLICATE_GROUPS.csv',records,
              ['group_id','classification','source_file_duplicate_status','rows','excess_rows','product',
               'price','current_row_references','source_files','source_file_sha256'])
    counts = Counter(r.get('especie') for r in original)
    unique_counts = Counter(r.get('especie') for r in diagnostic_unique)
    metrics = {'date':'2026-08-19','classification':'economic_duplicate','rows_original':len(original),
               'duplicate_groups':len(groups),'excess_rows':sum(len(g)-1 for g in groups),
               'rows_diagnostic_unique':len(diagnostic_unique),'input_sha256':sha256(input_file.read_bytes()),
               'source_file_hash_status':'unavailable_original_XLS_and_ZIP_not_in_workspace',
               'arithmetic_mean_original':avg(original),'arithmetic_mean_diagnostic_unique':avg(diagnostic_unique),
               'mean_method':'diagnostic_row_mean_all_products_not_economic_index',
               'source_counts':dict(Counter(r.get('archivo_origen') for r in original))}
    table = '\n'.join(f"| {p} | {counts[p]} | {unique_counts[p]} |" for p in sorted(counts) if counts[p]!=unique_counts[p])
    report = f"""# Auditoría de duplicados actuales MCBA

Fecha: 2026-08-19. Clasificación confirmada a nivel de filas: **economic_duplicate**.
Hipótesis de archivo: source_file_duplicate por copia RF en ZIP anidado, **inferida**,
sin hash de originales XLS/ZIP disponibles en el workspace. No equivalencia binaria comprobada.

Clave literal: fecha/rubro/especie/variedad/procedencia/envase/moneda/unidades/
observaciones (atributos CAL/TAM/GRADO disponibles)/precio parseado. No se eliminan aliases.
Referencias de filas/archivos y clasificación por grupo en MCBA_CURRENT_DUPLICATE_GROUPS.csv.

```json
{json.dumps(metrics,ensure_ascii=False,indent=2)}
```

Los conteos por producto se inflan. El ranking por número de filas puede cambiar;
no es un ranking de volumen. Medias por producto de una copia completa idéntica de RF
no cambian por replicación uniforme, pero mezclar frutas y hortalizas aumenta el peso
relativo de frutas. La media global anterior es sólo diagnóstico, no índice publicable.
Sumas de precios/conteos se inflan; nunca inferir cantidades de estos registros.

| Producto con conteo afectado | Original | Vista diagnóstica sin repetición |
|---|---:|---:|
{table}

No se modifica PRECIOS_MAYORISTAS_INTEGRADO.csv. La vista sin repeticiones existe sólo
en memoria para impacto; una corrección futura debe auditar originales y autorizaciones.
"""
    atomic_write(folder/'MCBA_CURRENT_DUPLICATE_AUDIT.md',report.encode('utf-8'))
    return metrics


def coverage(month, attempts, raw_loader):
    days = month_days(month)
    selected = [r for r in attempts if r['purpose']=='month_validation' and r['date'][:7]==month]
    requested, verified = set(),set()
    latest = {}
    canonical_rows = []
    for attempt in selected:
        window = [d for d in days if attempt['date']<=d<=attempt['date_to']]
        requested.update(window)
        if attempt['result']=='success':
            payload,manifest = raw_loader(attempt['capture_id'])
            records = parse_export(payload,attempt['date'],attempt['date_to'])
            if len(records)!=manifest.record_count:
                raise ValueError('Conteo RAW no coincide con manifest')
            canonical_rows.extend(normalize(records,manifest))
            verified.update(window)
            for d in window:
                previous = latest.get(d)
                if not previous or attempt['captured_at_utc']>previous['captured_at_utc'] or previous['result']!='success':
                    latest[d]=attempt
        else:
            for d in window:
                if d not in verified:
                    latest[d]=attempt
    analytical = build_analytical(canonical_rows) if canonical_rows else []
    analytical = [r for r in analytical if latest.get(r['observation_date'],{}).get('capture_id')==r['capture_id']]
    records=[]
    for day in days:
        att = latest.get(day)
        day_rows = [r for r in analytical if r['observation_date']==day] if day in verified else []
        prices = [r['price'] for r in day_rows if r['price'] is not None]
        success = day in verified
        r={'date':day,'capture_id':att.get('capture_id') if att else None,
           'rows':len(day_rows) if success else None,
           **{field+'s':len({r[field] for r in day_rows if r[field]}) if success else None
              for field in ('product','variety','origin','package','quality','size','grade')},
           'price_min':min(prices) if prices else None,'price_max':max(prices) if prices else None,
           'acquisition_status':'success' if success else 'failed' if att else 'not_requested',
           'coverage_status':'observed_rows' if day_rows else 'observed_rows_0' if success else 'unverified',
           'calendar_status':'unknown'}
        # Plurales públicos del contrato (no varietys/qualitys).
        r['varieties']=r.pop('varietys');r['qualities']=r.pop('qualitys')
        records.append(r)
    with_data = {r['date'] for r in records if r['rows'] and r['rows']>0}
    status = ('complete_requested_window' if len(verified)==len(days) else
              'partial_requested_window' if verified else 'failed' if selected else 'unknown')
    metrics={'month':month,'calendar_days':len(days),'days_requested':len(requested),
             'days_with_data':len(with_data),'days_without_data':len(verified-with_data),
             'days_unverified':len(set(days)-verified),'successful_exports':sum(r['result']=='success' for r in selected),
             'failed_exports':sum(r['result']!='success' for r in selected),
             'coverage_ratio_requested':len(verified)/len(requested) if requested else None,
             'coverage_ratio_definition':'days_in_validated_export_windows / unique_days_requested',
             'month_coverage_status':status,'rows_magyp':len(analytical),
             'calendar_status':'unknown','official_monthly_equivalence':False}
    return records,metrics,analytical


def aggregate_observed(rows, magyp):
    rules=load_rules()
    buckets=defaultdict(list)
    for r in rows:
        if magyp and (r['observation_level']!='detail' or not r['valid_for_price_series']): continue
        mapping={'product':'product' if magyp else 'especie','variety':'variety' if magyp else 'variedad',
                 'origin':'origin' if magyp else 'procedencia','package':'package' if magyp else 'envase'}
        dims={k:normalized_label(k,r.get(v),rules) for k,v in mapping.items()}
        dims.update(type=r.get('type' if magyp else 'rubro'),currency=r.get('currency' if magyp else 'moneda'),
                    quality=r.get('quality') if magyp else None,size=r.get('size') if magyp else None,
                    grade=r.get('grade') if magyp else None)
        price=r.get('price') if magyp else price_current(r)
        unit=r.get('price_unit') if magyp else r.get('unidad_precio_observado') or r.get('unidad')
        if dims['currency']!='ARS' or canonical(unit) not in {'KG','ARS/KG','$/KG'}:
            raise PipelineError('Agregado MCBA requiere pesos/kg documentados, sin conversión implícita')
        day=r['observation_date' if magyp else 'fecha']
        if price is not None: buckets[(tuple(dims.items()),day[:7])].append((day,price,r))
    result=[]
    for (pairs,month),group in sorted(buckets.items(),key=str):
        daily=defaultdict(list)
        for d,p,_ in group:daily[d].append(p)
        result.append({**dict(pairs),'observation_date':month+'-01','price':mean(mean(p) for p in daily.values()),
                       'price_unit':'kg','observation_level':'detail','period':month,
                       'method':'mean_of_daily_means_observed_days','observed_days':len(daily),
                       'observation_count':len(group),'source':'mcba' if magyp else 'mcba_current',
                       'observation_id':stable_id([pairs,month]),'capture_id':None,
                       'source_url':group[0][2].get('source_url'),
                       'raw_sha256':None,'aggregation_status':'observed_days_aggregate_not_official_monthly',
                       'input_references':[r.get('observation_id',r.get('_current_row')) for _,_,r in group]})
    return result


def matches(current, magyp, comparison_kind):
    result=[]
    for match in mutual_unique_matches(current,magyp):
        m=magyp[match['magyp_index']] if match['magyp_index'] is not None else None
        c=current[match['current_index']] if match['current_index'] is not None else None
        out=report_row(match['status'],m,c,len(match['candidate_indices']))
        difference=out['price_difference'];base=price_current(c) if c else None
        out.update(comparison_kind=comparison_kind,matching_rule=match['rule'],
                   absolute_price_difference=abs(difference) if difference is not None else None,
                   relative_price_difference=difference/base if difference is not None and base else None,
                   candidate_references=[current[i].get('_current_row',current[i].get('observation_id')) for i in match['candidate_indices']] if m
                   else [magyp[i]['observation_id'] for i in match['candidate_indices']],
                   aliases_used=[])
        if m and c:
            mapping=(('product','especie'),('variety','variedad'),('origin','procedencia'),('package','envase'))
            for dim,field in mapping:
                if canonical(m.get(dim))!=canonical(c.get(field)):
                    out['aliases_used'].append({'dimension':dim,'magyp':m.get(dim),'current':c.get(field),
                         'canonical_magyp':normalized_label(dim,m.get(dim),allow_observed=match['status']=='probable'),
                         'canonical_current':normalized_label(dim,c.get(field),allow_observed=match['status']=='probable')})
        result.append(out)
    return result


def matching_metrics(rows):
    categories=('exact','normalized_exact','probable','ambiguous','current_only','magyp_only')
    counts=Counter(r['match_status'] for r in rows)
    denominator=len(rows)
    matched=[r for r in rows if r['match_status'] in categories[:3]]
    return {'report_entities_or_pairs':denominator,'denominator_definition':'unique_pairs_plus_unpaired_entities_ambiguous_counted_per_side',
            'magyp_entities':sum(r['date_magyp'] is not None for r in rows),
            'current_entities':sum(r['date_current'] is not None for r in rows),
            'ambiguous_magyp_entities':sum(r['match_status']=='ambiguous' and r['date_magyp'] is not None for r in rows),
            'ambiguous_current_entities':sum(r['match_status']=='ambiguous' and r['date_current'] is not None for r in rows),
            'counts':{k:counts[k] for k in categories},
            'percentages':{k:100*counts[k]/denominator if denominator else None for k in categories},
            'paired_price_differences_over_0_011':sum(abs(r['price_difference'])>0.011 for r in matched),
            'max_absolute_price_difference':max((r['absolute_price_difference'] for r in matched),default=None),
            'max_absolute_relative_price_difference':max((abs(r['relative_price_difference']) for r in matched if r['relative_price_difference'] is not None),default=None)}


def run(data_root, current_file, month):
    folder=data_root/'reports'
    attempts=export_attempts(data_root)
    records,metrics,magyp=coverage(month,attempts,lambda i:load_raw(data_root/'raw/mcba'/i))
    write_csv(folder/'MCBA_MAGYP_MONTH_VALIDATION.csv',records,
              ['date','capture_id','rows','products','varieties','origins','packages','qualities','sizes',
               'grades','price_min','price_max','acquisition_status','coverage_status','calendar_status'])
    current=current_rows(current_file)
    period=[r for r in current if r['fecha'][:7]==month]
    daily=[r for r in period if precision(r)=='day']
    historical=[r for r in period if precision(r)=='month']
    dates={r['observation_date'] for r in magyp}
    daily=[r for r in daily if r['fecha'] in dates]
    common={r['fecha'] for r in daily}
    details=[r for r in magyp if r['observation_level']=='detail' and r['observation_date'] in common and r['valid_for_price_series']]
    a=matches(daily,details,'A_daily_detail_vs_detail') if common else []
    magyp_month=aggregate_observed(magyp,True)
    current_month=aggregate_observed(daily,False)
    # B: mismos días de ambas bases; dimensiones perdidas actuales no se reconstruyen.
    b_magyp=aggregate_observed(details,True) if common else []
    current_b=[dict(r,fecha=r['observation_date'],rubro=r['type'],especie=r['product'],variedad=r['variety'],
                    procedencia=r['origin'],envase=r['package'],moneda=r['currency'],unidad='kg',precio=r['price'])
               for r in current_month]
    b=matches(current_b,b_magyp,'B_observed_days_aggregates') if common else []
    # C: etiquetas/candidatos y diferencias descriptivas; NO equivalencia de fórmula.
    c=matches(historical,magyp_month,'C_historical_monthly_formula_unverified') if magyp_month and historical else []
    fields=list(report_row('',None,None,0))+['comparison_kind','matching_rule','absolute_price_difference',
              'relative_price_difference','candidate_references','aliases_used']
    for suffix,rows in [('DAILY',a),('OBSERVED_AGGREGATES',b),('HISTORICAL_MONTHLY',c)]:
        write_csv(folder/f'MCBA_MONTH_MATCHING_{suffix}.csv',rows,fields)
    aggregate_fields=['product','variety','origin','package','type','currency','quality','size','grade',
                      'observation_date','price','price_unit','observation_level','period','method','observed_days',
                      'observation_count','source','observation_id','capture_id','source_url','raw_sha256','aggregation_status','input_references']
    write_csv(folder/'MCBA_MONTH_OBSERVED_AGGREGATES.csv',magyp_month,aggregate_fields)
    metrics.update(rows_current=len(period),rows_current_daily_comparable=len(daily),rows_current_historical_monthly=len(historical),
                   common_daily_dates=sorted(common),
                   magyp_dimensions={k:len({r[k] for r in magyp if r[k]}) for k in ('product','variety','origin','package','quality','size','grade')},
                   current_month_duplicate_groups=len(duplicate_groups(period)),
                   matching_A=matching_metrics(a),matching_B=matching_metrics(b),matching_C=matching_metrics(c),
                   historical_comparison_status='diagnostic_formula_unverified' if c else 'not_comparable_no_acquired_data_or_no_historical_source')
    atomic_write(folder/'MCBA_MONTH_READINESS_METRICS.json',(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n').encode())
    audit_current(current,current_file,folder)
    print(f"[VALIDATE] {month} {metrics['month_coverage_status']}: {metrics['days_requested']} solicitados; {metrics['days_with_data']} con datos")
    return metrics


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--month',required=True)
    p.add_argument('--data-root',type=Path,default=ROOT/'data/magyp')
    p.add_argument('--current',type=Path,default=ROOT/'PRECIOS_MAYORISTAS_INTEGRADO.csv')
    args=p.parse_args()
    run(args.data_root,args.current,args.month)
