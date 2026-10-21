"""Stage Pages without the retired internal-price manual archive."""
import argparse
import shutil
from pathlib import Path


def prepare(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination == source or source in destination.parents:
        raise ValueError('Pages destination must be outside the checkout')

    def ignore(folder, names):
        if Path(folder).resolve() == source / 'data':
            return ['commodities_local_mensual'] if 'commodities_local_mensual' in names else []
        if Path(folder).resolve() == source:
            return ['.git'] if '.git' in names else []
        return []

    shutil.copytree(source, destination, ignore=ignore)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path.cwd())
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.destination)
    print('[PAGES] Paquete preparado; archivo manual de precios internos excluido')
