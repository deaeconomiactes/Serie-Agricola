"""Valida todos los shards sin red ni RAW; ejecutable también en GitHub/Linux."""
import argparse
import csv
import gzip
import io
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.magyp.grains import references as r


def read(folder,descriptor):
    name=descriptor['path']
    if not re.fullmatch(r'[a-z0-9.-]+-[a-f0-9]{16}\.gz',name):raise r.Error('Nombre de shard inválido')
    path=folder/name
    if path.is_symlink():raise r.Error('Symlink público no permitido')
    body=path.read_bytes()
    if len(body)!=descriptor['bytes'] or len(body)>5_000_000 or r.digest(body)!=descriptor['sha256']:
        raise r.Error('Hash/tamaño de shard no coincide')
    # Descompresión acotada incluso si el archivo comprimido está mal formado.
    with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:decoded=stream.read(45_000_001)
    if len(decoded)!=descriptor['decoded_bytes'] or len(decoded)>45_000_000:raise r.Error('Tamaño decodificado incorrecto')
    return decoded


def validate(root,require_all=True):
    index=json.loads((root/'index.json').read_bytes())
    if index['schema_version']!='magyp-history-v1':raise r.Error('Índice histórico incompatible')
    if require_all and set(index['families'])!=set(r.SOURCES):raise r.Error('Faltan familias históricas')
    total=0
    for family,entry in index['families'].items():
        if family not in r.SOURCES or entry['family']!=family:raise r.Error('Familia desconocida')
        folder=root/family;dictionary=json.loads(read(folder,entry['registry']))
        if dictionary['family']!=family or dictionary['schema_version']!=index['schema_version']:raise r.Error('Diccionario de otra familia')
        for key,series in dictionary['series'].items():
            if series['series_id'][:16]!=key or not re.fullmatch('[a-f0-9]{64}',series['series_id']):raise r.Error('ID histórico incompatible')
            if not series['moneda'] or not series['unidad']:raise r.Error('Moneda/unidad vacía')
        for frequency,descriptors in [('mensual',{'all':entry['monthly']}),('diaria',entry['daily'])]:
            for year,descriptor in descriptors.items():
                stream=csv.DictReader(io.StringIO(read(folder,descriptor).decode()),delimiter=';')
                if stream.fieldnames!=entry['columns']:raise r.Error('Columnas de shard cambiaron')
                seen=set();count=0
                for row in stream:
                    key=(row['series_key'],row['fecha'][:7] if frequency=='mensual' else row['fecha'])
                    if key in seen:raise r.Error('ID público duplicado')
                    seen.add(key);count+=1
                    if row['series_key'] not in dictionary['series'] or row['capture_key'] not in dictionary['captures']:raise r.Error('Trazabilidad incompleta')
                    if r.number(row['price'],'json')[1]!='positive' or row['value_status']!='positive':raise r.Error('Precio público inválido')
                    if frequency=='diaria' and row['fecha'][:4]!=year:raise r.Error('Fecha en shard de otro año')
                if count!=descriptor['rows']:raise r.Error('Conteo de shard incorrecto')
                total+=count
    return total


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dashboard-root',type=Path,default=ROOT/'data/magyp/dashboard/commodities/history')
    args=p.parse_args();print('[HISTORY VALIDATE]',validate(args.dashboard_root),'filas de vistas válidas')


if __name__=='__main__':main()
