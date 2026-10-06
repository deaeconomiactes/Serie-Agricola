"""Una sesión explícita por invocación; ledger público, sin reintentos automáticos."""
import argparse
import json
import platform
import sys
import time
import uuid
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import PipelineError, atomic_write, csv_bytes, utc_now
from scripts.magyp.mcba.acquisition import browser_fetch, validate_window
from scripts.magyp.mcba.fetch_mcba import capture
from scripts.magyp.mcba.model import parse_export


def attempt(start, end, data_root, purpose, channel='chromium', timeout=40, max_requests=80,
            fetcher=None, explicit_retry=False):
    validate_window(start, end)
    previous=[json.loads(f.read_text(encoding='utf-8'))['attempt']
              for f in (data_root/'reports').glob('MCBA_PHASE3_ATTEMPT_*.json')]
    previous=[r for r in previous if (r['date'],r['date_to'],r['purpose'])==(start,end,purpose)]
    if len(previous)>=2 or bool(previous)!=explicit_retry:
        raise PipelineError('Un intento inicial y un retry explícito como máximo por ventana')
    started = utc_now()
    clock = time.monotonic()
    record = dict(attempt_id=uuid.uuid4().hex, date=start, date_to=end, purpose=purpose,
                  captured_at_utc=started, result='failed', failure_stage=None, duration_seconds=None,
                  request_count=0, rows=0, xlsx_valid=False, error_category=None, capture_id=None,
                  browser_channel=channel, python_version=platform.python_version(),
                  platform=platform.system(), playwright_version=version('playwright'),
                  timeout_seconds=timeout, max_requests=max_requests,
                  attempt_type='explicit_retry' if explicit_retry else 'initial')
    diagnostics = {}
    stage = 'acquisition'
    try:
        result = (fetcher or browser_fetch)(start, end, timeout=timeout, max_requests=max_requests, channel=channel)
        diagnostics = result.diagnostics
        record['request_count'] = diagnostics.get('request_count', len(diagnostics.get('requests', [])))
        stage = 'validate_xlsx'
        rows = parse_export(result.payload, start, end)
        record.update(rows=len(rows), xlsx_valid=True)
        stage = 'store_raw'
        folder = capture(result.payload, start, data_root, 'browser_automation', result.http_status,
                         result.content_type, date_to=end, request_method=result.request_method,
                         request_count=record['request_count'], acquisition_classification=result.classification)
        record.update(result='success', capture_id=folder.name)
    except Exception as error:
        diagnostics = getattr(error, 'diagnostics', diagnostics)
        record.update(failure_stage=diagnostics.get('stage', stage),
                      request_count=len(diagnostics.get('requests', [])),
                      error_category='timeout' if 'TimeoutError' in str(error) else type(error).__name__)
        # Nunca persistir repr/str de excepciones con URLs transitorias o valores privados.
    record['duration_seconds'] = round(time.monotonic() - clock, 3)
    reports = data_root / 'reports'
    atomic_write(reports / ('MCBA_PHASE3_ATTEMPT_' + record['attempt_id'] + '.json'),
                 (json.dumps({'attempt': record, 'diagnostics': diagnostics}, ensure_ascii=False, indent=2)+'\n').encode())
    export_attempts(data_root)
    print(f"[FETCH] {start}..{end} {record['result']} requests={record['request_count']} rows={record['rows']} stage={record['failure_stage']}")
    return record


def export_attempts(data_root):
    attempts = sorted([json.loads(f.read_text(encoding='utf-8'))['attempt']
                       for f in (data_root/'reports').glob('MCBA_PHASE3_ATTEMPT_*.json')],
                      key=lambda r: (r['captured_at_utc'], r['attempt_id']))
    seen=set()
    for r in attempts:
        key=(r['date'],r['date_to'],r['purpose'])
        r.setdefault('attempt_type','legacy_repeat' if key in seen else 'initial')
        seen.add(key)
    if attempts:
        atomic_write(data_root/'reports/MCBA_PHASE3_ACQUISITION_ATTEMPTS.csv', csv_bytes(attempts, list(attempts[0])))
    year = [r for r in attempts if r['purpose'] == 'validation_2025']
    if year:
        atomic_write(data_root/'reports/MCBA_2025_ACQUISITION_VALIDATION.csv', csv_bytes(year, list(year[0])))
    return attempts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--date-from', required=True)
    p.add_argument('--date-to')
    p.add_argument('--purpose', choices=('validation_2025','month_validation','clean_smoke'), required=True)
    p.add_argument('--allow-web', action='store_true')
    p.add_argument('--data-root', type=Path, default=ROOT/'data/magyp')
    p.add_argument('--browser-channel', choices=('chromium','msedge'), default='chromium')
    p.add_argument('--timeout', type=int, default=40)
    p.add_argument('--max-requests', type=int, default=80)
    p.add_argument('--explicit-retry',action='store_true',help='Segundo y último intento para esta ventana')
    args = p.parse_args()
    if not args.allow_web:
        p.error('Red requiere --allow-web; una sesión, sin retry')
    result = attempt(args.date_from, args.date_to or args.date_from, args.data_root, args.purpose,
                     args.browser_channel, args.timeout, args.max_requests, explicit_retry=args.explicit_retry)
    raise SystemExit(0 if result['result']=='success' else 1)


if __name__ == '__main__':
    main()
