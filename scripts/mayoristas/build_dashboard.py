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
}

def packed(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()

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

def build(root=ROOT, output=None, node='node'):
    root=Path(root).resolve();output=Path(output or root/'data/mayoristas/dashboard').resolve()
    result=subprocess.run([node,str(root/'scripts/mayoristas/source_rows.cjs'),str(root)],capture_output=True,text=True,encoding='utf-8',check=True)
    source=json.loads(result.stdout)
    output.mkdir(parents=True,exist_ok=True)
    descriptors=[];bodies={};counts={}
    for frequency,rows in source['views'].items():
        if not rows: raise ValueError('Empty wholesale view')
        groups=defaultdict(list)
        for order,row in enumerate(rows):
            if not row.get('mercado') or not isinstance(row.get('year'),int): raise ValueError('Invalid market/year')
            groups[(row['mercado'],row['year'],row['data_source'])].append(dict(row,_runtime_order=order))
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
    report=root/'data/mayoristas/reports';report.mkdir(parents=True,exist_ok=True)
    (report/'LOAD_INVENTORY.json').write_bytes(packed(inventory(root))+b'\n')
    print(f'[BUILD] Mayoristas: {len(descriptors)} shards, {sum(len(b) for b in bodies.values())} compressed bytes')
    return index

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--node',default=shutil.which('node') or 'node')
    args=parser.parse_args();build(args.root,args.output,args.node)
