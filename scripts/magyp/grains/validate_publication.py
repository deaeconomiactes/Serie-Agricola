"""Guardia de publicación: sólo cinco CSV de dashboard, válidos y livianos."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.magyp.grains import references as r

MAX_DASHBOARD_BYTES = 5 * 1024 * 1024
PUBLICATION_FILES = tuple(f'data/magyp/dashboard/commodities/{source}.csv' for source in r.SOURCES if source != 'fob') + ('data/magyp/dashboard/commodities/fob.csv.gz',)


def validate_outputs(root, max_bytes=MAX_DASHBOARD_BYTES):
    for source in r.SOURCES:
        path = r.dashboard_path(root, source)
        if not path.is_file() or path.is_symlink():
            raise r.Error(f'{source}: output ausente o enlace; publicación rechazada')
        size=path.stat().st_size
        if not 0 < size <= max_bytes:
            raise r.Error(f'{source}: tamaño {size} fuera del límite {max_bytes}; publicación rechazada')
        try: r.validate_bundle(r.read_dashboard(root, source), source)
        except r.Error as error: raise r.Error(f'{source}: {error}') from error
    report=root/'reports/PRICE_FRESHNESS_STATUS.json'
    if report.exists():
        from scripts.magyp.build_price_freshness import validate_report
        validate_report(json.loads(report.read_text(encoding='utf-8')))


def validate_staged_paths(paths):
    if not set(paths).issubset((*PUBLICATION_FILES, 'data/magyp/reports/PRICE_FRESHNESS_STATUS.json')):
        raise r.Error('Archivo fuera del allowlist dashboard; publicación rechazada')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=r.ROOT / 'data' / 'magyp')
    parser.add_argument('--check-staged', action='store_true')
    args = parser.parse_args()
    try:
        validate_outputs(args.data_root)
        if args.check_staged:
            paths = subprocess.check_output(['git', 'diff', '--cached', '--name-only', '-z'], cwd=r.ROOT)
            validate_staged_paths(paths.decode('utf-8').rstrip('\0').split('\0') if paths else [])
        print('[VALIDATE] Cinco CSV dashboard válidos; publicación limitada al allowlist')
        return 0
    except (r.Error, OSError, UnicodeError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        detail=str(error) if isinstance(error,r.Error) else type(error).__name__
        print(f'[VALIDATE] Publicación rechazada ({detail}); conservar última versión publicada')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
