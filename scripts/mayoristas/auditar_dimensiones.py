"""Inventario sin mutaciones de todas las dimensiones de los shards activos.

Cada frecuencia de vista se cuenta por separado: las vistas reutilizan registros.
Las propuestas son candidatos de revisión, no reglas de normalización.
"""
from __future__ import annotations

import csv
import gzip
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'data/mayoristas/dashboard'
REPORT = ROOT / 'data/mayoristas/reports'
DIMENSIONS = {
    'producto': ('product_raw', 'especie'),
    'variedad': ('variety_raw', 'variedad'),
    'procedencia': ('origin_raw', 'procedencia'),
    'mercado': ('mercado_raw', 'mercado'),
    'unidad': ('price_unit', 'unidadPrecioObservado'),
    'envase': ('package_raw', 'envase'),
    'tamanio': ('size_raw', 'tamanoMCBA'),
    'calidad': ('quality_raw', 'calidadMCBA'),
    'grado': ('grade_raw', 'gradoMCBA'),
}
WRAPPED_RAW = {'producto': 'producto_raw', 'variedad': 'variedad_raw', 'procedencia': 'procedencia_raw',
               'mercado': 'mercado_raw', 'unidad': 'unidad_raw', 'envase': 'envase_raw',
               'tamanio': 'tamanio_raw', 'calidad': 'calidad_raw', 'grado': 'grado_raw'}


def key(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    text = ''.join(c for c in text if not unicodedata.combining(c)).casefold()
    return re.sub(r'[^\w]+', ' ', text).strip()


def available_raw(row, field, current, wrapped):
    # The legacy adapter has already discarded some upstream raw columns.
    # Label the fallback as available data, never as a verified source original.
    return (str(row[field]), 'fuente') if row.get(field) not in (None, '') else (str(row.get(wrapped, row.get(current)) or ''), 'adaptador')


def abbreviation_candidate(short, long):
    """Find possible abbreviations only; a match never establishes equivalence."""
    if '.' not in short:
        return False
    a, b = key(short).replace(' ', ''), key(long).replace(' ', '')
    if len(a) < 3 or len(b) <= len(a) or len(b) > 4 * len(a):
        return False
    remaining = iter(b)
    return all(any(char == candidate for candidate in remaining) for char in a)


def write(name, fields, rows):
    with (REPORT / name).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    index = json.loads((FOLDER / 'index.json').read_text(encoding='utf-8'))
    counts = Counter()
    variants = defaultdict(set)
    product_rows = Counter()
    pair_sources = defaultdict(set)
    fragment_totals = Counter()
    for fragment in index['fragments']:
        frequency = fragment['frequency']
        with gzip.open(FOLDER / fragment['path'], 'rt', encoding='utf-8') as stream:
            rows = json.load(stream)
        fragment_totals[frequency] += len(rows)
        for row in rows:
            source = row.get('data_source', '')
            for dimension, (raw_field, current_field) in DIMENSIONS.items():
                raw, provenance = available_raw(row, raw_field, current_field, WRAPPED_RAW[dimension])
                current = str(row.get(current_field) or '')
                counts[(dimension, raw, current, provenance, source, frequency)] += 1
                if raw:
                    variants[(dimension, key(raw))].add(raw)
            product = str(row.get('especie') or '')
            variety = str(row.get('variedad') or '')
            product_rows[(product, variety, source, frequency)] += 1
            if product and variety and key(variety) not in ('sin variedad', 'sin especificar'):
                pair_sources[(key(product), key(variety))].add((product, variety, source))
    REPORT.mkdir(parents=True, exist_ok=True)
    inventory = []
    for (dimension, raw, current, provenance, source, frequency), count in sorted(counts.items()):
        candidates = sorted(variants[(dimension, key(raw))]) if raw else []
        inventory.append(dict(dimension=dimension, raw_disponible=raw, raw_proveniencia=provenance,
            normalizado_actual=current, fuente=source, frecuencia_vista=frequency, count=count,
            clave_candidata=key(raw), variantes_candidatas=' | '.join(candidates) if len(candidates) > 1 else '',
            confianza='sin evaluar', status='REVIEW_REQUIRED' if len(candidates) > 1 else 'SIN_CAMBIO'))
    write('DIMENSIONES_MAYORISTAS_INVENTARIO.csv', list(inventory[0]), inventory)

    origins = sorted({r['raw_disponible'] for r in inventory
                      if r['dimension'] == 'procedencia' and r['raw_disponible']})
    origin_candidates = [dict(raw=short, candidato=long, confianza='sin evaluar',
                              status='REVIEW_REQUIRED', motivo='abreviatura posible; requiere evidencia')
                         for short in origins for long in origins
                         if abbreviation_candidate(short, long)]
    write('PROCEDENCIAS_ABREVIATURAS_CANDIDATAS.csv',
          ['raw', 'candidato', 'confianza', 'status', 'motivo'], origin_candidates)

    # Evidence for possible embedded variety: a separate-column product/variety
    # pair with the same complete words in another row. Candidate, not equality.
    candidates = []
    for (product, variety, source, frequency), count in sorted(product_rows.items()):
        if variety and key(variety) not in ('sin variedad', 'sin especificar'):
            continue
        product_key = key(product)
        for (base, suffix), evidence in pair_sources.items():
            if product_key == base + ' ' + suffix:
                candidates.append(dict(raw_value=product, variedad_actual=variety,
                    producto_candidato=sorted(evidence)[0][0], variedad_candidata=sorted(evidence)[0][1],
                    fuente=source, frecuencia_vista=frequency, count=count,
                    fuentes_evidencia=' | '.join(sorted({e[2] for e in evidence})),
                    confidence='sin evaluar', reason='coincidencia textual con producto y variedad separados',
                    status='REVIEW_REQUIRED'))
    fields = ['raw_value', 'variedad_actual', 'producto_candidato', 'variedad_candidata', 'fuente',
              'frecuencia_vista', 'count', 'fuentes_evidencia', 'confidence', 'reason', 'status']
    write('PRODUCTO_VARIEDAD_CANDIDATOS.csv', fields, candidates)
    print(json.dumps(dict(fragment_rows=dict(fragment_totals), inventory_rows=len(inventory),
                          product_candidates=len(candidates), origin_candidates=len(origin_candidates)),
                     ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
