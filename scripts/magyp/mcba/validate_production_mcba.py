"""Guardia de publicación MCBA: bundle íntegro, estado explícito y allowlist cerrado."""
import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import PipelineError
from scripts.magyp.mcba.update_mcba_dashboard import read_bundle

DATA_FILES = ('MCBA_MAGYP_DAILY.csv', 'MCBA_MAGYP_DETAIL.csv',
              'MCBA_MAGYP_LATEST.csv', 'MCBA_MAGYP_SUMMARY.csv')
STATUS_FILE = 'MCBA_MAGYP_UPDATE_STATUS.json'
PUBLISH_FILES = (*DATA_FILES, '_SUCCESS.json', STATUS_FILE)
PREFIX = 'data/magyp/dashboard/mcba/'
MAX_FILE_BYTES = 10 * 1024 * 1024


def validate(folder, capture_failed=False, requested_date=None):
    for name in PUBLISH_FILES:
        path = folder / name
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_FILE_BYTES:
            raise PipelineError('Output MCBA ausente, vacío o demasiado pesado')
    marker = json.loads((folder / '_SUCCESS.json').read_bytes())
    files = set(marker['files'])
    if not set(DATA_FILES).issubset(files) or files - set(DATA_FILES) - {'MCBA_MAGYP_MONTHLY.csv'}:
        raise PipelineError('Marcador MCBA incompleto o fuera del contrato')
    rows = read_bundle(folder)
    state = json.loads((folder / STATUS_FILE).read_bytes())
    expected = 'MAGYP_LAST_VALID' if capture_failed else 'MAGYP'
    if state.get('source_status') != expected:
        raise PipelineError('Estado MCBA incompatible con el resultado de captura')
    day = date.fromisoformat(state['requested_date']).isoformat()
    if requested_date and day != requested_date:
        raise PipelineError('Estado MCBA de otra fecha solicitada')
    stamp = datetime.fromisoformat(state['attempted_at'].replace('Z', '+00:00'))
    if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
        raise PipelineError('Timestamp MCBA sin UTC')
    return len(rows)


def validate_staged(paths, capture_failed=False):
    allowed = {PREFIX + name for name in ((STATUS_FILE,) if capture_failed else PUBLISH_FILES)}
    if not set(paths).issubset(allowed):
        raise PipelineError('Archivo staged fuera del allowlist MCBA')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--published-dir', type=Path, default=ROOT / PREFIX)
    parser.add_argument('--capture-failed', action='store_true')
    parser.add_argument('--requested-date')
    parser.add_argument('--check-staged', action='store_true')
    args = parser.parse_args()
    try:
        count = validate(args.published_dir, args.capture_failed, args.requested_date)
        if args.check_staged:
            body = subprocess.check_output(['git', 'diff', '--cached', '--name-only', '-z'], cwd=ROOT)
            validate_staged(body.decode('utf-8').rstrip('\0').split('\0') if body else [], args.capture_failed)
        print(f'[VALIDATE] MCBA {count} filas; ' + ('MAGYP_LAST_VALID; sólo metadata publicable' if args.capture_failed else 'MAGYP; bundle publicable'))
        return 0
    except (PipelineError, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError):
        print('[VALIDATE] ERROR: no publicar; conservar último bundle válido')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
