"""Cobertura histórica y decisión de cutover MCBA; nunca publica precios nuevos."""
from __future__ import annotations
import csv
import io
import json
import math
import statistics
import sys
import unicodedata
from collections import defaultdict
from datetime import date
from functools import lru_cache
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import atomic_write, csv_bytes, sha256
from scripts.magyp.mcba.labels import normalized_label, load_rules
from scripts.mercado_central.update_mcba_monthly import read_published, MONTHS, VERSION, CODES


def label(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value or '')).upper()
                   if not unicodedata.combining(c)).strip().rstrip('.')


def candidate_usd(payload, manifest):
    if sha256(payload) != manifest['sha256']:
        raise ValueError('SHA del candidato histórico inválido')
    rows = list(csv.DictReader(io.StringIO(payload.decode('cp1252'))))
    required = {'pais_id', 'pais', 'mercado', 'año', 'mes', 'producto', 'variedad',
                'origen', 'precio_usd_kg', 'moneda_cod', 'moneda'}
    if not rows or set(rows[0]) != required:
        raise ValueError('Schema del candidato USD desconocido')
    normalized = []
    for index, row in enumerate(rows, 2):
        month = MONTHS.get(label(row['mes']))
        price = float(row['precio_usd_kg']) if row['precio_usd_kg'].strip() else None
        if (row['moneda_cod'] != 'USD' or row['mercado'] != 'Mercado Central de Buenos Aires'
                or not month or (price is not None and (not math.isfinite(price) or price < 0))):
            raise ValueError('Candidato USD inválido; no se convierte a ARS')
        day = date(int(row['año']), month, 1).isoformat()
        normalized.append(dict(date=day, date_precision='monthly', price=price,
                               currency='USD', unit='kg', source='MAGyP catálogo histórico MCBA',
                               product_raw=row['producto'], variety_raw=row['variedad'],
                               origin_raw=row['origen'], raw_fields=row, row_number=index,
                               schema_version='magyp-mcba-usd-monthly-archive-v1',
                               source_url=manifest['url'], raw_sha256=manifest['sha256'],
                               captured_at_utc=manifest['captured_at_utc'],
                               quality_status='EXCLUDED_FROM_ARS_RUNTIME',
                               price_available=price is not None and price > 0,
                               reason='USD/kg y menor granularidad; no equivale a ARS/kg modal diario'))
    return normalized


def compare_daily(official, legacy):
    rules = load_rules()
    @lru_cache(maxsize=None)
    def norm(dimension, value):
        return normalized_label(dimension, value, rules) or ''
    def key(day, kind, product, variety, origin, package):
        return tuple(label(v) for v in (day, kind, product, variety, origin, package))
    left, right = defaultdict(set), defaultdict(set)
    for r in official:
        left[key(r['date'], r['type'], r['product_normalized'], r['variety_normalized'],
                 r['origin_normalized'], r['package_normalized'])].add(float(r['price']))
    for r in legacy:
        if r.get('fecha_precision') == 'mensual':
            continue
        unit = r.get('unidad_precio_observado') or r.get('unidad')
        if unit != '$/kg':
            continue
        try:
            price = float(r['precio_kg_estimado'])
        except (ValueError, TypeError):
            continue
        if not math.isfinite(price) or price <= 0:
            continue
        package = CODES['package'].get(label(r['envase']), r['envase'])
        right[key(r['fecha'], r['rubro'], norm('product', r['especie']), norm('variety', r['variedad']),
                  norm('origin', r['procedencia']), norm('package', package))].add(price)
    common = left.keys() & right.keys()
    ratios = [next(iter(left[k]))/next(iter(right[k])) for k in common
              if len(left[k]) == len(right[k]) == 1]
    return dict(shared_keys=len(common), unambiguous_pairs=len(ratios),
                ambiguous_keys=sum(len(left[k]) != 1 or len(right[k]) != 1 for k in common),
                within_one_percent=sum(abs(v-1) <= .01 for v in ratios),
                median_ratio=statistics.median(ratios) if ratios else None,
                missing_legacy_keys=len(right.keys()-left.keys()),
                notes='Cotejo diagnóstico fecha/rubro/producto/variedad/origen/envase; alias explícitos config/mcba_aliases.json, códigos oficiales de envase, etiquetas sin tildes/punto final. Calidad/tamaño/grado no estructurados en la carga manual diaria: claves ambiguas excluidas. No prueba igualdad metodológica.')


def audit(root=ROOT):
    data = root/'data/mercado_central'
    monthly = read_published(data)
    prior_validation = json.loads((data/'reports/MCBA_MONTHLY_VALIDATION.json').read_text(encoding='utf-8'))
    discovery = json.loads((data/'reports/MCBA_HISTORY_DISCOVERY.json').read_text(encoding='utf-8'))
    daily = [json.loads(line) for line in (data/'analytical/mcba/daily.jsonl').open(encoding='utf-8')]
    if len(daily) != prior_validation['daily_rows']:
        raise ValueError('Detalle analítico no coincide con el reporte validado')
    for capture in prior_validation['zip_catalog']:
        path = data/'raw/mcba'/capture['capture_id']/'response.zip'
        if sha256(path.read_bytes()) != capture['raw_sha256']:
            raise ValueError('RAW ZIP modificado; auditoría cancelada')
    detail = [r for r in daily if r['observation_level'] == 'detail' and float(r['price']) > 0]
    with (root/'PRECIOS_MAYORISTAS_INTEGRADO.csv').open(encoding='utf-8-sig', newline='') as stream:
        legacy = [r for r in csv.DictReader(stream, delimiter=';') if r['mercado'] == 'Mercado Central de Buenos Aires']
    candidates = []
    for manifest in discovery['requests']:
        if manifest.get('raw_file'):
            folder = data/'raw/history'/discovery['capture_id']
            part = candidate_usd((folder/manifest['raw_file']).read_bytes(), manifest)
            candidates.extend(part)
            atomic_write(data/'normalized/history'/discovery['capture_id']/'usd_candidate.jsonl',
                         ''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in part).encode())
    covered = {(r['period'], r['type']) for r in monthly}
    retained = [r for r in legacy if (r['fecha'][:7], r['rubro']) not in covered]
    years = sorted({r['date'][:4] for r in daily} | {r['fecha'][:4] for r in legacy}
                   | {r['date'][:4] for r in candidates})
    inventory, comparisons = [], []
    for year in range(int(min(years)), int(max(years))+1):
        y = str(year)
        rows = [r for r in daily if r['date'][:4] == y]
        quotes = [r for r in detail if r['date'][:4] == y]
        old = [r for r in legacy if r['fecha'][:4] == y]
        candidate = [r for r in candidates if r['date'][:4] == y]
        books = {(r['type'], r['member']) for r in rows}
        dates = sorted({r['date'] for r in rows+candidate})
        inventory.append(dict(year=year, months_available=sorted({r['period'] for r in rows} | {r['date'][:7] for r in candidate}),
            compatible_months_available=sorted({r['period'] for r in rows}),
            fruit_files=sum(kind == 'Frutas' for kind, _ in books),
            vegetable_files=sum(kind == 'Hortalizas' for kind, _ in books),
            zip_files=sum(p['period'][:4] == y for p in discovery['current_zip_publications']),
            first_observation=dates[0] if dates else None, last_observation=dates[-1] if dates else None,
            rows=len(rows)+len(candidate), detail_rows=len(quotes), monthly_rows=sum(r['period'][:4] == y for r in monthly),
            schema_version=VERSION if rows else 'magyp-mcba-usd-monthly-archive-v1' if candidate else None,
            currency='ARS' if rows else 'USD' if candidate else None,
            frequency='diaria, vista mensual derivada' if rows else 'mensual, candidato excluido' if candidate else None,
            quality_status='VALIDATED_OBSERVED_DAYS' if rows else 'INCOMPATIBLE_USD_CANDIDATE' if candidate else 'NO_EQUIVALENT_LINK_FOUND',
            usd_candidate_rows=len(candidate), usd_candidate_periods=sorted({r['date'][:7] for r in candidate}),
            usd_candidate_rows_without_price=sum(not r['price_available'] for r in candidate),
            notes='Ausencia de enlace encontrado no demuestra inexistencia de archivos históricos. No se construyeron URLs por año.'))
        missing = sorted({r['fecha'][:7] for r in old} - {r['period'] for r in rows})
        old_products, products = {label(r['especie']) for r in old}, {label(r['product_normalized']) for r in quotes}
        old_varieties, varieties = {label(r['variedad']) for r in old}, {label(r['variety_normalized']) for r in quotes}
        old_origins, origins = {label(r['procedencia']) for r in old}, {label(r['origin_normalized']) for r in quotes}
        comparisons.append(dict(year=year, official_daily_rows=len(rows), legacy_rows=len(old),
            legacy_monthly_rows=sum(r.get('fecha_precision') == 'mensual' for r in old),
            legacy_periods=sorted({r['fecha'][:7] for r in old}), missing_periods=missing,
            shared_products=sorted(old_products & products), legacy_products_not_found=sorted(old_products-products),
            shared_varieties=sorted(old_varieties & varieties), legacy_varieties_not_found=sorted(old_varieties-varieties),
            shared_origins=sorted(old_origins & origins), legacy_origins_not_found=sorted(old_origins-origins),
            legacy_units=sorted({r.get('unidad_precio_observado') or r['unidad'] for r in old}),
            official_unit='ARS/kg' if rows else None,
            monthly_price_comparison='NO_COMMON_MONTHLY_PERIOD' if not any(r.get('fecha_precision') == 'mensual' and r['fecha'][:7] in {q['period'] for q in rows} for r in old) else 'REQUIRES_METHOD_REVIEW',
            daily_price_comparison=compare_daily(quotes, old)))
    old_monthly = [r for r in legacy if r.get('fecha_precision') == 'mensual']
    old_monthly_retained = [r for r in retained if r.get('fecha_precision') == 'mensual']
    result = dict(schema_version='mcba-history-audit-v1', source='Mercado Central de Buenos Aires',
        discovery_capture_id=discovery['capture_id'],
        oldest_verified_compatible_year=min(int(r['date'][:4]) for r in daily),
        oldest_verified_official_candidate_year=min((int(r['date'][:4]) for r in candidates), default=None),
        inventory=inventory, comparisons=comparisons,
        official_rows=len(daily), official_detail_rows=len(detail), monthly_rows=len(monthly),
        excluded_usd_candidate_rows=len(candidates),
        cutover=dict(can_retire_mcba_legacy=False, status='BLOCKED_BY_SOURCE',
            reason='No se encontraron enlaces reproducibles a XLS equivalentes anteriores a 2026; el candidato 2017–2018 está en USD y tiene menor granularidad.',
            official_monthly_periods=sorted({r['period'] for r in monthly}),
            replaced_legacy_periods_in_monthly_view=sorted({r['fecha'][:7] for r in legacy if (r['fecha'][:7], r['rubro']) in covered}),
            remaining_legacy_monthly_periods=sorted({r['fecha'][:7] for r in old_monthly_retained}),
            original_legacy_monthly_rows=len(old_monthly), remaining_legacy_monthly_rows=len(old_monthly_retained),
            legacy_monthly_history_still_needed_pct=round(100*len(old_monthly_retained)/len(old_monthly), 2) if old_monthly else 0,
            legacy_input_rows_retained_in_monthly_view_pct=round(100*len(retained)/len(legacy), 2),
            percentage_scope='El segundo porcentaje sólo describe el enrutamiento mensual actual; no autoriza retirar la carga manual del diario ni del anual.',
            daily='MAGyP conserva su circuito separado; no sustituido por agregación mensual ni por CSV USD.',
            annual='Sin cutover anual: publicación y métodos no equivalentes.'),
        validation_report='MCBA_MONTHLY_VALIDATION.json',
        comparison_alias_rules_sha256=sha256((root/'config/mcba_aliases.json').read_bytes()),
        zip_catalog_sha256=sha256((data/'reports/MCBA_MONTHLY_VALIDATION.json').read_bytes()))
    atomic_write(data/'reports/MCBA_HISTORY_INVENTORY.json', (json.dumps(result, ensure_ascii=False, indent=2)+'\n').encode())
    flat = [{**r, 'months_available': '|'.join(r['months_available']),
             'compatible_months_available': '|'.join(r['compatible_months_available']),
             'usd_candidate_periods': '|'.join(r['usd_candidate_periods'])} for r in inventory]
    atomic_write(data/'reports/MCBA_HISTORY_INVENTORY.csv', csv_bytes(flat, list(flat[0])))
    return result


if __name__ == '__main__':
    report = audit()
    print(json.dumps({k: report[k] for k in ('oldest_verified_compatible_year', 'oldest_verified_official_candidate_year', 'official_rows', 'excluded_usd_candidate_rows', 'cutover')}, ensure_ascii=True))
