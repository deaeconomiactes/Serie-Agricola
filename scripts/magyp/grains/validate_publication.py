"""Guardia de publicación: sólo cinco CSV de dashboard, válidos y livianos."""
import argparse
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.magyp.grains import references as r

MAX_DASHBOARD_BYTES = 5 * 1024 * 1024
PUBLICATION_FILES = tuple(f'data/magyp/dashboard/commodities/{source}.csv' for source in r.SOURCES)


def validate_outputs(root, max_bytes=MAX_DASHBOARD_BYTES):
    for source in r.SOURCES:
        path = root / 'dashboard' / 'commodities' / f'{source}.csv'
        if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= max_bytes:
            raise r.Error('Output ausente, vacío o demasiado pesado; publicación rechazada')
        r.validate_bundle(path.read_bytes(), source)


def validate_staged_paths(paths):
    if not set(paths).issubset(PUBLICATION_FILES):
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
    except (r.Error, OSError, UnicodeError, subprocess.CalledProcessError):
        print('[VALIDATE] Publicación rechazada; conservar última versión publicada')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
