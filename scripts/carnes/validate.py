"""Offline validation of prepared Carnes files; never needs RAW or a browser."""
import argparse
import csv
import gzip
import io
import json
import re
from datetime import date
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.carnes.model import DataError,FIELDS,VERSION,digest
from scripts.carnes.csv_sources import decimal_value


def validate_entry(folder,entry):
    from scripts.carnes.pipeline import public_url
    public_url(entry['source_url']);total=0;seen=set()
    for item in entry['files']:
        if not re.fullmatch(r'[a-z0-9_-]+-[a-f0-9]{16}\.csv\.gz',item['path']):raise DataError('Invalid prepared path')
        path=folder/item['path']
        if path.is_symlink():raise DataError('Prepared symlink rejected')
        body=path.read_bytes()
        if len(body)>5_000_000 or len(body)!=item['bytes'] or digest(body)!=item['sha256']:
            raise DataError('Prepared file hash/size mismatch')
        with gzip.GzipFile(fileobj=io.BytesIO(body)) as zipped:decoded=zipped.read(45_000_001)
        if len(decoded)>45_000_000:raise DataError('Decoded output too large')
        reader=csv.DictReader(io.StringIO(decoded.decode('utf-8')),strict=True)
        if reader.fieldnames!=FIELDS:raise DataError('Prepared schema changed')
        count=0
        for row in reader:
            if None in row or any(v is None for v in row.values()):raise DataError('Incomplete prepared row')
            if row['schema_version']!=VERSION or row['source_id']!=entry['source_id'] or row['source_url']!=entry['source_url']:
                raise DataError('Prepared source mismatch')
            if row['family']!=item['family'] or row['frequency']!=item['frequency'] or row['observation_date'][:4]!=item['year']:
                raise DataError('Prepared partition mismatch')
            date.fromisoformat(row['observation_date']);date.fromisoformat(row['period_end'])
            if row['raw_sha256']!=entry['raw_sha256'] or row['capture_id']!=entry['capture_id']:
                raise DataError('Prepared RAW provenance mismatch')
            if row['observation_id'] in seen:raise DataError('Duplicate prepared observation')
            seen.add(row['observation_id'])
            if any(not re.fullmatch('[a-f0-9]{64}',row[k]) for k in ['observation_id','record_id','raw_sha256']):raise DataError('Invalid technical ID')
            if not row['unit'] or not row['currency'] or not row['source_locator']:raise DataError('Missing economic/provenance dimension')
            if row['value_status']=='missing':
                if row['value']!='':raise DataError('Missing flag conceals value')
            elif row['value_status']=='observed':
                if decimal_value(row['value']) is None:raise DataError('Observed value must be a nonempty number')
            else:raise DataError('Unknown value status')
            flags=json.loads(row['quality_flags'])
            if not isinstance(flags,list) or any(not isinstance(f,str) for f in flags):raise DataError('Invalid quality flags')
            count+=1
        if count!=item['rows']:raise DataError('Prepared count mismatch')
        total+=count
    if total!=entry['dashboard_rows'] or not total:raise DataError('Empty/incomplete prepared source')
    return total


def validate(folder):
    index=json.loads((folder/'index.json').read_bytes())
    if index['schema_version']!=VERSION or not index['sources']:raise DataError('Invalid Carnes index')
    return sum(validate_entry(folder,entry) for entry in index['sources'].values())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dashboard-root',type=Path,default=ROOT/'data/carnes/dashboard')
    print('[VALIDATE] Carnes',validate(parser.parse_args().dashboard_root),'prepared rows valid')
