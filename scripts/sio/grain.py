"""Homogeneous SIO event groups and fail-closed publication. No acquisition."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median

VERSION = 'sio-transactions-v2'
SOURCE_URL = 'https://www.siogranos.com.ar/consulta_publica/operaciones_informadas.aspx'
# Raw economic dimensions, including the event class; not a contract-state model.
DIMENSIONS = ('commodity', 'moneda', 'unidad', 'tipo_precio', 'condicion_comercial',
              'lugar_entrega', 'precio_puesto_en', 'procedencia', 'condicion_pago',
              'tipo_operacion', 'operacion', 'calidad', 'fecha_entrega', 'fuera_de_termino', 'fuente')
OPTIONAL = ('condicion_comercial', 'condicion_pago', 'tipo_operacion', 'precio_puesto_en',
            'procedencia', 'lugar_entrega', 'calidad', 'fecha_entrega')
REQUIRED = {'fecha', 'commodity', 'moneda', 'unidad', 'tipo_precio', 'precio', 'fuente', 'precio_valido_para_serie'}
COMMON = ['schema_version', 'series_id', *DIMENSIONS, 'lugar_entrega_raw', 'delivery_status',
          'delivery_basis', 'condicion_serie', 'source_url', 'capture_ids', 'event_ids',
          'capture_timestamps', 'raw_sha256s', 'input_sha256', 'quality_flags']
STATS = ['operaciones', 'precio_promedio', 'precio_mediana', 'precio_min', 'precio_max',
         'volumen_total', 'volumen_conocido', 'volumen_registros_validos', 'precio_ponderado_volumen']


def text(row, field):
    value = row.get(field)
    return '' if value is None else str(value).strip()


def number(raw):
    raw = str(raw if raw is not None else '').strip()
    if not raw:
        return None
    if re.fullmatch(r'[-+]?\d+(?:\.\d+)?[eE][-+]?\d+', raw):
        pass
    elif ',' in raw and '.' in raw:
        raw = raw.replace('.', '').replace(',', '.')
    else:
        raw = raw.replace(',', '.')
    try:
        result = float(raw)
        return result if math.isfinite(result) else None
    except ValueError:
        return None


def fmt(value):
    return '' if value is None else f'{value:.6f}'.rstrip('0').rstrip('.') or '0'


def yes(value):
    return str(value).strip().casefold() in {'sí', 'si', 'true', '1'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode()).hexdigest()


def missing(value):
    return value.casefold() in {'', 'sin especificar', 'sin informar', 'no informado', 'sin identificar'}


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter=';')
        return list(reader.fieldnames or []), list(reader)


def identity(row):
    raw_id = text(row, 'id_operacion_sio')
    return 'id:' + raw_id if raw_id else 'fingerprint:' + digest({k: text(row, k) for k in (*DIMENSIONS, 'fecha', 'precio', 'volumen', 'volumen_unidad')})


def condition_label(row):
    labels = [('condicion_comercial', 'Comercial'), ('condicion_pago', 'Pago'),
              ('tipo_operacion', 'Tipo'), ('operacion', 'Evento'), ('calidad', 'Calidad'),
              ('fecha_entrega', 'Entrega'), ('precio_puesto_en', 'Precio puesto en'),
              ('fuera_de_termino', 'Fuera de término')]
    parts = [f'{label}: {row[field]}' for field, label in labels if row[field]]
    if not row['condicion_comercial']:
        parts.insert(0, 'Comercial no informada')
    if not row['condicion_pago']:
        parts.insert(1, 'Pago no informado')
    return ' · '.join(parts)


def normalize(rows):
    events = []
    seen = {}
    rejected = Counter()
    duplicates = 0
    for original in rows:
        key = identity(original)
        signature = {k: text(original, k) for k in (*DIMENSIONS, 'fecha', 'precio', 'volumen', 'volumen_unidad')}
        if key in seen:
            if seen[key] != signature:
                raise ValueError('ID de evento repetido con contenido incompatible; última salida conservada')
            duplicates += 1
            continue
        seen[key] = signature
        raw_price = text(original, 'precio')
        price = number(raw_price)
        if price is None or price <= 0 or yes(original.get('precio_cero_flag', '')) or not yes(original.get('precio_valido_para_serie', '')):
            rejected['zero_price' if price == 0 else 'missing_price' if not raw_price else 'invalid_or_ineligible_price'] += 1
            continue
        try:
            day = date.fromisoformat(text(original, 'fecha'))
        except ValueError as error:
            raise ValueError('Fecha SIO inválida; última salida conservada') from error
        if any(missing(text(original, f)) for f in ('commodity', 'moneda', 'unidad', 'tipo_precio', 'fuente')) or ('moneda_explicitamente_informada' in original and not yes(original['moneda_explicitamente_informada'])):
            rejected['unidentified_economic_dimensions'] += 1
            continue
        row = {f: '' if missing(text(original, f)) else text(original, f) for f in DIMENSIONS}
        flags = {f'MISSING_{field.upper()}' for field in OPTIONAL if not row[field]}
        if key.startswith('fingerprint:'):
            flags.add('NO_SOURCE_EVENT_ID')
        if row['operacion'].casefold() != 'contrato':
            flags.add('EVENT_NOT_CONFIRMED_ACTIVE_CONTRACT')
        if not text(original, 'raw_sha256'):
            flags.add('RAW_HASH_NOT_RECORDED')
        if not text(original, 'fecha_descarga_snapshot'):
            flags.add('CAPTURE_NOT_RECORDED')
        basis = re.search(r'(En\s+(?:origen|destino))\s*$', row['lugar_entrega'], re.I)
        # This is a suffix explicitly present in the published delivery text,
        # not an inference that it equals the separate precio_puesto_en field.
        row.update(event_id=key, price=price, day=day, flags=flags,
                   volume=number(original.get('volumen')), volume_unit=text(original, 'volumen_unidad'),
                   capture=text(original, 'fecha_descarga_snapshot'), raw_hash=text(original, 'raw_sha256'),
                   capture_id=text(original, 'capture_id'), delivery_basis=basis.group(1) if basis else '',
                   source_url=text(original, 'source_url') or SOURCE_URL)
        row['series_id'] = digest([row[f] for f in DIMENSIONS])
        events.append(row)
    if not events:
        raise ValueError('Sin eventos de precio válidos; última salida conservada')
    return events, dict(rejected), duplicates


def aggregate(group, input_hash):
    base = group[0]
    if any(len({row[field] for row in group}) != 1 for field in DIMENSIONS):
        raise ValueError('Agregado con dimensiones heterogéneas; última salida conservada')
    flags = set().union(*(row['flags'] for row in group))
    volumes = [row['volume'] for row in group]
    comparable = [v is not None and v >= 0 and row['volume_unit'] == row['unidad'] for row, v in zip(group, volumes)]
    complete = all(comparable)
    known_volume = sum(v for v, valid in zip(volumes, comparable) if valid)
    if not complete:
        flags.add('INCOMPLETE_OR_INCOMPARABLE_VOLUME')
    prices = [row['price'] for row in group]
    result = {field: base[field] for field in DIMENSIONS}
    result.update(schema_version=VERSION, series_id=base['series_id'], lugar_entrega_raw=base['lugar_entrega'],
                  delivery_status='UNIQUE' if base['lugar_entrega'] else 'MISSING', delivery_basis=base['delivery_basis'],
                  condicion_serie=condition_label(base), source_url=base['source_url'], input_sha256=input_hash,
                  operaciones=str(len(group)), precio_promedio=fmt(sum(prices)/len(prices)),
                  precio_mediana=fmt(median(prices)), precio_min=fmt(min(prices)), precio_max=fmt(max(prices)),
                  volumen_total=fmt(known_volume if complete else None), volumen_conocido=fmt(known_volume if any(comparable) else None),
                  volumen_registros_validos=str(sum(comparable)),
                  precio_ponderado_volumen=fmt(sum(row['price']*row['volume'] for row in group)/known_volume if complete and known_volume>0 else None))
    for field, values in [('event_ids', [r['event_id'] for r in group]),
                          ('capture_timestamps', [r['capture'] for r in group]),
                          ('capture_ids', [r['capture_id'] for r in group]),
                          ('raw_sha256s', [r['raw_hash'] for r in group]), ('quality_flags', flags)]:
        result[field] = json.dumps(sorted(set(v for v in values if v)), ensure_ascii=False)
    return result


def change(current, previous):
    return fmt((number(current)/number(previous)-1)*100) if number(current) is not None and number(previous) is not None and number(previous)>0 else ''


def state(value):
    v = number(value)
    return 'Sin dato' if v is None else 'Revisar' if abs(v)>50 else 'Baja' if v < -5 else 'Estable' if v<=5 else 'Suba moderada' if v<=20 else 'Suba fuerte'


def views(events, input_hash):
    groups = {'diario':defaultdict(list), 'mensual':defaultdict(list)}
    for row in events:
        groups['diario'][(row['day'].isoformat(), row['series_id'])].append(row)
        groups['mensual'][(row['day'].isoformat()[:7], row['series_id'])].append(row)
    daily=[];monthly=[];latest=[]
    for name, store in groups.items():
        for (period, _), group in sorted(store.items()):
            row = aggregate(group, input_hash)
            row.update(año=period[:4], mes=str(int(period[5:7])))
            if name=='diario':
                row['fecha']=period;daily.append(row)
            else:
                row.update(periodo_ym=period, dias_con_datos=str(len({r['day'] for r in group})));monthly.append(row)
    month_index={(r['series_id'],r['periodo_ym']):r for r in monthly}
    for row in monthly:
        year,month=map(int,row['periodo_ym'].split('-'))
        previous=f'{year-1}-12' if month==1 else f'{year}-{month-1:02d}'
        row['variacion_mensual_pct']=change(row['precio_mediana'],month_index.get((row['series_id'],previous),{}).get('precio_mediana'))
        row['variacion_interanual_pct']=change(row['precio_mediana'],month_index.get((row['series_id'],f'{year-1}-{month:02d}'),{}).get('precio_mediana'))
    by_series=defaultdict(list)
    for row in daily:
        by_series[row['series_id']].append(row)
    for series in by_series.values():
        series.sort(key=lambda r:r['fecha']);row=dict(series[-1]);day=date.fromisoformat(row['fecha'])
        for days in (7,30):
            prior=[r for r in series if date.fromisoformat(r['fecha'])<=day-timedelta(days=days)]
            row[f'variacion_{days}d_pct']=change(row['precio_mediana'],prior[-1]['precio_mediana'] if prior else None)
        row.update(fecha_ultima=row['fecha'], precio_mediana_ultimo_dia=row['precio_mediana'],
                   precio_promedio_ultimo_dia=row['precio_promedio'], operaciones_ultimo_dia=row['operaciones'],
                   volumen_ultimo_dia=row['volumen_total'], estado=state(row['variacion_30d_pct'] or row['variacion_7d_pct']))
        latest.append(row)
    semaphore=[dict(r,estado=state(r['variacion_mensual_pct'])) for r in monthly]
    return {'diario':daily,'mensual':monthly,'ultimos':latest,'semaforo':semaphore}


def profile(rows):
    return {field:{'missing':sum(missing(text(r,field)) for r in rows),
                   'distinct_nonmissing':len({text(r,field) for r in rows if not missing(text(r,field))})}
            for field in ('fecha',*DIMENSIONS,'volumen','volumen_unidad','precio','id_operacion_sio','fecha_descarga_snapshot')}


def audit(rows, events, outputs, baseline, input_hash, rejected, duplicates):
    def maize(value):
        return ''.join(c for c in unicodedata.normalize('NFD',value.casefold()) if not unicodedata.combining(c))=='maiz'
    control=[r for r in events if maize(r['commodity']) and r['moneda']=='USD' and r['unidad']=='TN' and r['day'].isoformat()=='2026-09-09']
    control_rows=[r for r in outputs['diario'] if maize(r['commodity']) and r['moneda']=='USD' and r['unidad']=='TN' and r['fecha']=='2026-09-09']
    return {'schema_version':VERSION,'input_sha256':input_hash,'input_rows':len(rows),'eligible_events':len(events),
            'exact_repeated_events_omitted':duplicates,'rejected':rejected,'dimensions':list(DIMENSIONS),
            'profile':profile(rows),'baseline_public':baseline,'homogeneous_series':len(outputs['ultimos']),
            'rows_by_output':{k:len(v) for k,v in outputs.items()},
            'multi_delivery_groups_after':0,'multi_condition_groups_after':0,
            'control':{'date':'2026-09-09','commodity':'Maíz','currency':'USD','unit':'TN',
                       'documented_previous_median':193.45,'recomputed_previous_median':median(r['price'] for r in control) if control else None,
                       'events':len(control),'separated_groups':[{k:r[k] for k in ('series_id',*DIMENSIONS,'operaciones','precio_mediana','quality_flags','event_ids')} for r in control_rows]},
            'limitations':['Snapshots observados, no censo de contratos ni reconstrucción de última instancia.',
                           'Condición/pago/tipo/calidad/entrega ausentes en memoria histórica no se reconstruyen ni se infieren.',
                           'Origen/destino es el sufijo literal del lugar; no se equipara a precio_puesto_en.',
                           'La variación describe cambios de composición de eventos dentro de las mismas dimensiones.',
                           'SHA de entrada permite trazar al CSV de eventos; no sustituye un hash RAW ausente.']}


def publish(files):
    """Validate all candidates first; restore the prior bundle if replacement fails."""
    with tempfile.TemporaryDirectory(prefix='sio-publish-') as temporary:
        temp=Path(temporary);staged=[];backups={};replaced=[]
        for index,(path,body) in enumerate(files.items()):
            path.parent.mkdir(parents=True,exist_ok=True)
            # Stage beside the destination so os.replace stays on one filesystem.
            fd,name=tempfile.mkstemp(prefix='.sio-',dir=path.parent)
            os.close(fd);candidate=Path(name);candidate.write_bytes(body);staged.append((path,candidate))
            if path.exists():
                backup=temp/str(index);shutil.copy2(path,backup);backups[path]=backup
        try:
            for path,candidate in staged:
                os.replace(candidate,path);replaced.append(path)
        except Exception:
            for path in reversed(replaced):
                if path in backups:
                    shutil.copy2(backups[path],path)
                else:
                    path.unlink(missing_ok=True)
            raise
        finally:
            for _,candidate in staged:
                candidate.unlink(missing_ok=True)


def csv_bytes(rows, fields):
    import io
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,delimiter=';',extrasaction='ignore',lineterminator='\n')
    writer.writeheader();writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')


def build(source_path, paths, report_path, latest_capture=''):
    headers,rows=read_csv(source_path)
    if not REQUIRED.issubset(headers):
        raise ValueError('Schema SIO desconocido; última salida conservada')
    input_hash=hashlib.sha256(source_path.read_bytes()).hexdigest()
    events,rejected,duplicates=normalize(rows)
    output=views(events,input_hash)
    audit_path=report_path.parent/'SIO_GRAIN_AUDIT.json'
    previous=json.loads(audit_path.read_text('utf-8')) if audit_path.exists() else {}
    old_daily=read_csv(paths['diario'])[1] if paths['diario'].exists() else []
    baseline=previous.get('baseline_public') or {'daily_rows':len(old_daily),
        'rows_multiple_delivery':sum('|' in text(r,'lugares_entrega') for r in old_daily),
        'rows_multiple_conditions':None,
        'condition_completeness_note':'El mensual anterior no conserva condición; no permite cuantificar mezclas a partir del agregado.',
        'daily_sha256':hashlib.sha256(paths['diario'].read_bytes()).hexdigest() if paths['diario'].exists() else None}
    captures=[r['capture'] for r in events if r['capture']]
    capture=max([*captures,latest_capture],default='')
    dates=[r['day'].isoformat() for r in events]
    updates=[text(r,'fecha_actualizacion_dashboard') for r in rows if text(r,'fecha_actualizacion_dashboard')]
    summary={'schema_version':VERSION,'fecha_actualizacion':date.today().isoformat(),
        'fecha_actualizacion_dashboard':max(updates,default=''),'fecha_ultima_captura_sio':capture,
        'fecha_ultima_operacion_sio':max(dates),'fecha_min_operacion_sio':min(dates),'fecha_max_operacion_sio':max(dates),
        'fecha_min':min(dates),'fecha_max':max(dates),'filas_analiticas':str(len(events)),'operaciones':str(len(events)),
        'commodities':'|'.join(sorted({r['commodity'] for r in events})),
        'monedas':'|'.join(sorted({r['moneda'] for r in events})),'unidades':'|'.join(sorted({r['unidad'] for r in events})),
        'fuente':'SIO Granos / Secretaría de Agricultura','modo':'histórico_snapshots',
        'nota_metodologica_corta':'Agregación derivada de eventos SIO por dimensiones homogéneas; no precio mensual oficial ni spot de plaza. No reconstruye contratos vigentes. Campos históricos ausentes señalados; sin imputación.'}
    output['resumen']=[summary]
    report=audit(rows,events,output,baseline,input_hash,rejected,duplicates)
    common=[*COMMON,*STATS,'año','mes']
    monthly_fields=[*common,'periodo_ym','dias_con_datos','variacion_mensual_pct','variacion_interanual_pct']
    fields={'diario':[*common,'fecha'],'mensual':monthly_fields,'semaforo':[*monthly_fields,'estado'],
        'ultimos':[*common,'fecha','fecha_ultima','precio_mediana_ultimo_dia','precio_promedio_ultimo_dia',
                   'operaciones_ultimo_dia','volumen_ultimo_dia','variacion_7d_pct','variacion_30d_pct','estado'],
        'resumen':list(summary)}
    for name,records in output.items():
        if not records:
            raise ValueError(f'Salida {name} vacía; última salida conservada')
        if name!='resumen':
            keys=[(r['series_id'],r.get('fecha') or r.get('periodo_ym') or r.get('fecha_ultima')) for r in records]
            if len(keys)!=len(set(keys)) or any(not number(r['precio_mediana']) for r in records):
                raise ValueError('Salida SIO inválida; última salida conservada')
    files={paths[k]:csv_bytes(v,fields[k]) for k,v in output.items()}
    files[audit_path]=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()
    files[report_path]=(f'# SIO: grano transaccional\n\nSchema: {VERSION}.\n\n'
        f'Eventos elegibles: {len(events)}. Series homogéneas: {len(output["ultimos"])}.\n\n'
        'Diario y mensual preservan lugar, condición comercial, pago, origen, modalidad, tipo y clase de evento, calidad y entrega. '
        'Mensual: agregación derivada de operaciones; no precio mensual oficial.\n\n'
        'Los campos ausentes no se infieren. No se reconstruye la última instancia contractual. '
        'Ver SIO_GRAIN_AUDIT.json y docs/SIO_TRANSACTIONAL_GRAIN.md.\n').encode()
    publish(files)
    return {'source_path':source_path,'valid_rows':len(events),'rows_by_output':{k:len(v) for k,v in output.items()},'series':len(output['ultimos'])}
