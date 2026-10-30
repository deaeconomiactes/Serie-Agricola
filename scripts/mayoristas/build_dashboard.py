"""Deterministic delivery shards from published wholesale outputs. No acquisition."""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from collections import defaultdict

VERSION = 'mayoristas-shards-v1'
ROOT = Path(__file__).resolve().parents[2]
INPUTS = {
    'PRECIOS_MAYORISTAS_INTEGRADO.csv': ('historical_mcba_and_corrientes', ';', 'history and Corrientes'),
    'RESUMEN_SERIES_UTILIZABLES_PRECIOS_2026.csv': ('quality', ';', 'series quality flags'),
    'data/magyp/dashboard/mcba/MCBA_MAGYP_DAILY.csv': ('mcba_daily', ',', 'published daily detail and species summary'),
    'data/magyp/dashboard/mcba/MCBA_MAGYP_SUMMARY.csv': ('metadata', ',', 'daily source coverage'),
    'data/magyp/dashboard/mcba/_SUCCESS.json': ('metadata', None, 'daily bundle integrity'),
    'data/magyp/dashboard/mcba/MCBA_MAGYP_UPDATE_STATUS.json': ('metadata', None, 'daily current status'),
    'data/mercado_central/dashboard/mcba/MCBA_MC_MONTHLY_DERIVED.csv': ('mcba_monthly', ',', 'monthly derived official daily observations'),
    'data/mercado_central/dashboard/mcba/_SUCCESS.json': ('metadata', None, 'monthly bundle integrity'),
    'data/magyp/reports/PRICE_FRESHNESS_STATUS.json': ('freshness', None, 'shared freshness loaded at boot'),
    'data/mayoristas/config/procedencia_aliases.json': ('metadata', None, 'approved provenance aliases'),
    'data/mayoristas/config/producto_variedad_aliases.json': ('metadata', None, 'approved product and variety aliases'),
    'data/mayoristas/config/fuentes.json': ('metadata', None, 'source currency confirmation'),
}

def packed(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()

def compact_dimensions(row):
    """Omit reconstructible fields, keeping values that differ from their fallback."""
    row = dict(row)
    if row.get('_normalization_schema') != 'v1':
        return row
    raw = {
        'producto_raw': row.get('product_raw', row.get('especie', '')),
        'variedad_raw': row.get('variety_raw', row.get('variedad', '')),
        'procedencia_raw': row.get('origin_raw', row.get('procedencia', '')),
        'mercado_raw': row.get('mercado', ''),
        'envase_raw': row.get('package_raw', row.get('envase', '')),
        'unidad_raw': row.get('price_unit', row.get('unidadPrecioObservado', '')),
        'tamanio_raw': row.get('size_raw', row.get('tamanoMCBA', '')),
        'calidad_raw': row.get('quality_raw', row.get('calidadMCBA', '')),
        'grado_raw': row.get('grade_raw', row.get('gradoMCBA', '')),
        'fuente_original': row.get('fuente', ''),
        'moneda_original': str(row.get('currency') or '').strip(),
    }
    for field, fallback in raw.items():
        if row.get(field) == fallback:
            row.pop(field, None)
    for field in ('producto_normalizado', 'variedad_normalizada', 'procedencia_normalizada',
                  'mercado_normalizado', 'envase_normalizado', 'tamanio_normalizado', 'calidad_normalizada', 'grado_normalizado',
                  'unidad_normalizada', 'moneda_normalizada',
                  'factor_conversion', 'peso_utilizado', 'conversion_validada'):
        row.pop(field, None)
    return row

def inventory(root):
    result=[]
    for name,(family,delimiter,purpose) in INPUTS.items():
        path=root/name
        with path.open(encoding='utf-8-sig',newline='') as stream:
            rows=sum(1 for _ in csv.DictReader(stream,delimiter=delimiter)) if delimiter else None
        result.append(dict(file=name,bytes=path.stat().st_size,rows=rows,purpose=purpose,
                           source_family=family,loaded_initially=True,
                           can_fragment=family not in ('metadata','freshness','quality'),can_lazy_load=family!='freshness'))
    return result

def build(root=ROOT, output=None, node='node', write_inventory=True):
    root=Path(root).resolve();output=Path(output or root/'data/mayoristas/dashboard').resolve()
    # A file avoids a huge stdout pipe and allows Node to finish writing before parsing.
    with tempfile.TemporaryFile(mode='w+b') as stream:
        result=subprocess.run([node,str(root/'scripts/mayoristas/source_rows.cjs'),str(root)],stdout=stream,stderr=subprocess.PIPE,check=True)
        stream.seek(0)
        # Unit tests may supply a small simulated subprocess result.
        if result.stdout is not None:
            source=json.loads(result.stdout)
        else:
            with io.TextIOWrapper(stream,encoding='utf-8') as text_stream:
                source=json.load(text_stream)
    output.mkdir(parents=True,exist_ok=True)
    descriptors=[];bodies={};counts={}
    for frequency,rows in source['views'].items():
        if not rows: raise ValueError('Empty wholesale view')
        groups=defaultdict(list)
        for order,row in enumerate(rows):
            if not row.get('mercado') or not isinstance(row.get('year'),int): raise ValueError('Invalid market/year')
            groups[(row['mercado'],row['year'],row['data_source'])].append(dict(compact_dimensions(row),_runtime_order=order))
        counts[frequency]=len(rows)
        for (market,year,origin),group in sorted(groups.items()):
            expanded=packed(group)
            buffer=io.BytesIO()
            with gzip.GzipFile(filename='',mode='wb',fileobj=buffer,compresslevel=9,mtime=0) as stream: stream.write(expanded)
            body=buffer.getvalue()
            if len(body)>12000000 or len(expanded)>120000000:
                raise ValueError('Delivery shard exceeds browser limits; subdivide before publication')
            sha=hashlib.sha256(body).hexdigest()
            prefix='mcba' if market=='Mercado Central de Buenos Aires' else 'corrientes' if market=='Mercado de Corrientes' else hashlib.sha256(market.encode()).hexdigest()[:8]
            name=f'{prefix}-{frequency}-{year}-{origin.lower()}-{sha[:16]}.json.gz'
            if json.loads(gzip.decompress(body))!=group: raise ValueError('Roundtrip mismatch')
            bodies[name]=body
            dates=sorted(r['fecha'] for r in group if r.get('fecha'))
            descriptors.append(dict(source=origin,market=market,frequency=frequency,year=year,
                row_count=len(group),first_observation=dates[0] if dates else None,last_observation=dates[-1] if dates else None,
                schema_version=VERSION,sha256=sha,bytes=len(body),expanded_bytes=len(expanded),path=name,
                currency=sorted({r.get('currency') or 'Sin identificar' for r in group}),
                unit=sorted({r.get('unidadPrecioObservado') or 'Sin identificar' for r in group}),
                source_frequency=sorted({r['fechaPrecision'] for r in group}),
                status='STATIC' if origin=='LEGACY' else 'PUBLISHED',
                fields=sorted(set().union(*(r.keys() for r in group)))))
    index=dict(schema_version=VERSION,format='json+gzip',fragments=descriptors,
               years=sorted({f['year'] for f in descriptors}),markets=sorted({f['market'] for f in descriptors}),
               row_counts=counts,metadata=source['metadata'],
               inputs=[dict(path=name,sha256=hashlib.sha256((root/name).read_bytes()).hexdigest()) for name in INPUTS if 'FRESHNESS' not in name])
    # Content addressed files first, index last. A failed build never changes the active index.
    for name,body in bodies.items():
        path=output/name
        if path.exists():
            if path.read_bytes()!=body: raise ValueError('Content-address collision')
        else:
            fd,temp=tempfile.mkstemp(prefix='.candidate-',dir=output)
            try:
                with os.fdopen(fd,'wb') as stream: stream.write(body)
                os.replace(temp,path)
            finally:
                if os.path.exists(temp): os.unlink(temp)
    fd,temp=tempfile.mkstemp(prefix='.index-',dir=output)
    try:
        with os.fdopen(fd,'wb') as stream: stream.write(packed(index)+b'\n')
        subprocess.run([node,str(root/'scripts/mayoristas/validate_delivery.cjs'),str(root),temp],check=True)
        os.replace(temp,output/'index.json')
    finally:
        if os.path.exists(temp): os.unlink(temp)
    # Obsolete shards may remain for an open tab; Pages stages only index-referenced files.
    if write_inventory:
        report=root/'data/mayoristas/reports';report.mkdir(parents=True,exist_ok=True)
        (report/'LOAD_INVENTORY.json').write_bytes(packed(inventory(root))+b'\n')
    print(f'[BUILD] Mayoristas: {len(descriptors)} shards, {sum(len(b) for b in bodies.values())} compressed bytes')
    return index

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--node',default=shutil.which('node') or 'node')
    parser.add_argument('--skip-inventory',action='store_true',help='Build a temporary candidate without changing repository reports')
    args=parser.parse_args();build(args.root,args.output,args.node,not args.skip_inventory)
