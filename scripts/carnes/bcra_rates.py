"""Capture the official BCRA A3500 daily workbook and publish a bounded series.

RAW captures are kept outside Git. A failed fetch or validation never replaces the
last valid dashboard file. This series is not the TCNPM monthly average.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import tempfile
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import xlrd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data' / 'carnes'
URL = 'https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/com3500.xls'
LANDING = 'https://www.bcra.gob.ar/tipo-cambio-referencia-comunicacion-a-3500-tcnpm/'
START = date(2022, 5, 17)
VERSION = 'bcra-a3500-v1'


def parse_workbook(payload, today=None):
    today = today or date.today()
    if len(payload) > 4_000_000 or not payload.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        raise ValueError('El archivo no es un XLS BCRA válido')
    book = xlrd.open_workbook(file_contents=payload)
    sheet = book.sheet_by_name('TCR diario y TCNPM')
    if '3500' not in str(sheet.cell_value(1, 2)) or sheet.cell_value(3, 2) != 'Fecha' or 'Referencia' not in str(sheet.cell_value(3, 3)):
        raise ValueError('Encabezado BCRA desconocido')
    rows = []
    previous = None
    for index in range(4, sheet.nrows):
        day, value = sheet.cell_value(index, 2), sheet.cell_value(index, 3)
        if not isinstance(day, (int, float)) or isinstance(day, bool) or not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f'Fecha o cotización inválida en fila {index + 1}')
        current = xlrd.xldate_as_datetime(day, book.datemode).date()
        if current > today or (previous and current <= previous) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'Serie BCRA inválida en fila {index + 1}')
        previous = current
        if current >= START:
            rows.append([current.isoformat(), value])
    if not rows or rows[0][0] > START.isoformat():
        raise ValueError('Cobertura BCRA insuficiente para MAG')
    return rows


def atomic_json(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.bcra-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as file:
            json.dump(obj, file, ensure_ascii=False, separators=(',', ':')); file.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def update(data_root=DATA, fetch=None, today=None):
    data_root = Path(data_root); now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    out = data_root / 'dashboard/bcra_a3500.json'; status_path = data_root / 'reports/BCRA_A3500_STATUS.json'
    status = {'source': LANDING, 'url': URL, 'checked_at': now}
    try:
        if fetch is None:
            def fetch():
                request = Request(URL, headers={'User-Agent': 'Mozilla/5.0 (compatible; SerieAgricola/1.0)'})
                with urlopen(request, timeout=40) as response:
                    if response.status != 200: raise OSError(f'HTTP {response.status}')
                    return response.read(4_000_001)
        payload = fetch()
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        status.update(status='SOURCE_UNAVAILABLE', message=str(error)); atomic_json(status_path, status); return status
    digest = hashlib.sha256(payload).hexdigest()
    capture = now.replace(':', '').replace('-', '') + '_' + uuid.uuid4().hex[:12]
    raw = data_root / 'raw/bcra_a3500' / capture; raw.mkdir(parents=True, exist_ok=False)
    (raw / 'response.xls').write_bytes(payload)
    atomic_json(raw / 'manifest.json', {'source_url': URL, 'capture_date': now, 'sha256': digest, 'bytes': len(payload), 'capture_id': capture})
    try:
        rows = parse_workbook(payload, today)
        if out.exists():
            old = json.loads(out.read_text('utf-8'))
            if old.get('schema_version') != VERSION or not old.get('rates') or rows[-1][0] < old['rates'][-1][0] or rows[0][0] > old['rates'][0][0]:
                raise ValueError('La nueva captura reduce la cobertura válida')
            if old.get('raw_sha256') == digest:
                status.update(status='NO_PUBLICATION', last_observation=rows[-1][0], capture_id=capture, raw_sha256=digest)
                atomic_json(status_path, status); return status
        document = {'schema_version': VERSION, 'source': LANDING, 'source_url': URL, 'capture_date': now, 'capture_id': capture, 'raw_sha256': digest, 'rates': rows}
        atomic_json(out, document)
        status.update(status='UPDATED', last_observation=rows[-1][0], capture_id=capture, raw_sha256=digest)
    except Exception as error:
        status.update(status='PIPELINE_ERROR', message=f'{type(error).__name__}: {error}', capture_id=capture, raw_sha256=digest)
    atomic_json(status_path, status); return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--allow-web', action='store_true'); args = parser.parse_args()
    if not args.allow_web: raise SystemExit('Use --allow-web para consultar BCRA')
    result = update(); print(json.dumps(result, ensure_ascii=False)); raise SystemExit(1 if result['status'] == 'PIPELINE_ERROR' else 0)
