"""Stage Pages without the retired internal-price manual archive."""
import argparse
import json
import shutil
from pathlib import Path


def prepare(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination == source or source in destination.parents:
        raise ValueError('Pages destination must be outside the checkout')

    # Upstream publications remain build/audit inputs in Git, not browser payloads.
    wholesale_index = source / 'data/mayoristas/dashboard/index.json'
    wholesale = json.loads(wholesale_index.read_text('utf-8')) if wholesale_index.exists() else None
    runtime = {'index.json', *(f['path'] for f in wholesale['fragments'])} if wholesale else set()
    retired = {
        source / 'PRECIOS_MAYORISTAS_INTEGRADO.csv',
        source / 'PRECIOS_MAYORISTAS_2026_INTEGRADO.csv',
        source / 'RESUMEN_SERIES_UTILIZABLES_PRECIOS_2026.csv',
        source / 'data/magyp/dashboard/mcba',
        source / 'data/mercado_central',
    } if wholesale else set()

    def ignore(folder, names):
        folder = Path(folder).resolve()
        if wholesale and folder == wholesale_index.parent:
            return [name for name in names if name not in runtime]
        excluded = [name for name in names if folder / name in retired]
        if folder == source / 'data' and 'commodities_local_mensual' in names:
            excluded.append('commodities_local_mensual')
        if folder == source and '.git' in names:
            excluded.append('.git')
        return excluded

    shutil.copytree(source, destination, ignore=ignore)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path.cwd())
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.destination)
    print('[PAGES] Paquete preparado; archivo manual de precios internos excluido')
