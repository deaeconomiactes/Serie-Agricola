"""Capture and publish official daily prices and INMAG observations from MAG.

RAW responses are immutable. The dashboard retains the latest value for each
economic observation while keeping the capture ID and raw hash on every row.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import html
import io
import json
import re
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.carnes.model import DataError, FIELDS, VERSION, digest, observation
from scripts.magyp.common.platform import atomic_write
from scripts.carnes.pipeline import csv_bytes, encoded, now, read_json, writer_lock
from scripts.carnes.validate import validate_entry

DATA = ROOT / 'data/carnes'
CATALOG = DATA / 'catalog/mag_prices.json'
INDEX_URL = 'https://mercadoagroganadero.com.ar/dll/hacienda1.dll/haciinfo000001'
DETAIL_URL = 'https://mercadoagroganadero.com.ar/dll/hacienda1.dll/haciinfo000502'
TOTALS_URL = 'https://mercadoagroganadero.com.ar/dll/hacienda2.dll/haciinfo000011'
CHART_URL = 'https://mercadoagroganadero.com.ar/php/hacigraf000110.chartjs.php'
SOURCE = 'Mercado Agroganadero S.A. (MAG)'
MARKET = 'Mercado Agroganadero de Cañuelas'
MAG_START = date(2022, 5, 17)
PRICE_FAMILY = 'livestock_price'
INDEX_FAMILY = 'livestock_index'
ACTIVITY_FAMILY = 'market_activity'
PRICE_METHOD = 'resolution_2018_32_detailed_categories'
CHART_METHOD = 'mag_category_average_chart'
INDEX_METHOD = 'mag_inmag_official_index'
CHART_CATEGORIES = {
    '1': ('Novillos', 'NOVILLOS'),
    '2': ('Novillitos', 'NOVILLITOS'),
    '3': ('Vaquillonas', 'VAQUILLONAS'),
    '4': ('Terneros', 'TERNEROS'),
    '5': ('Vacas', 'VACAS'),
    '6': ('Toros', 'TOROS'),
}
DETAIL_CATEGORIES = {
    'NOVILLOS': 'Novillos', 'NOVILLO': 'Novillos',
    'NOVILLITOS': 'Novillitos', 'VAQUILLONAS': 'Vaquillonas',
    'TERNEROS': 'Terneros', 'VACAS': 'Vacas', 'TOROS': 'Toros',
    'M.E.J.': 'M.E.J.', 'M.E.J': 'M.E.J.', 'MEJ': 'M.E.J.',
}
PRICE_FIELDS = [
    ('price_min', 'Precio mínimo', 'ARS/kg vivo', 'ARS'),
    ('price_max', 'Precio máximo', 'ARS/kg vivo', 'ARS'),
    ('price_average', 'Precio promedio', 'ARS/kg vivo', 'ARS'),
    ('price_median', 'Precio mediano', 'ARS/kg vivo', 'ARS'),
    ('heads', 'Cabezas', 'cabezas', 'NOT_APPLICABLE'),
    ('amount_ARS', 'Importe', 'ARS', 'ARS'),
    ('kilos', 'Kilos publicados', 'kg', 'NOT_APPLICABLE'),
    ('average_kilos', 'Kilos promedio publicados', 'kg/cabeza', 'NOT_APPLICABLE'),
]
IDENTITY = ['source_id','table_id','family','metric','species','observation_date','period_end','frequency',
    'category','age_class','geography','geography_level','market','entity_type','entity_id',
    'entity_name','entity_tax_id','entity_activity','currency','unit','weight_basis','methodology']
PRICE_SOURCE_IDS = {f'mag_prices_history_{name.lower()}' for name, _ in CHART_CATEGORIES.values()}
DETAIL_SOURCE_ID = 'mag_prices_detail'
INMAG_SOURCE_ID = 'mag_inmag'
REQUEST_INTERVAL_SECONDS = 1.0
MAX_RUN_REQUESTS = 10
_last_request_at = None
_requests_this_run = 0


class SourceUnavailable(RuntimeError):
    pass


class NoPublication(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def local_today():
    # Argentina observes UTC-3 year-round; avoid an OS-dependent timezone database.
    return (datetime.now(timezone.utc) + timedelta(hours=-3)).date()


def encoded_query(params):
    return urlencode(params, quote_via=quote, safe='')


def read_catalog(path=CATALOG):
    catalog = json.loads(Path(path).read_bytes())
    if catalog.get('schema_version') != 'mag-carnes-v1' or catalog.get('market_start') != MAG_START.isoformat():
        raise DataError('Unknown MAG cattle-price catalog contract')
    if catalog.get('sources', {}).get('category_history', {}).get('categories') != {k: v[0] for k, v in CHART_CATEGORIES.items()}:
        raise DataError('MAG category catalog changed')
    return catalog


class TableParser(HTMLParser):
    """Read table rows/cells without depending on a browser or HTML library."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.table_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'table':
            if self.table_depth == 0:
                self.table = []
            self.table_depth += 1
            return
        if self.table_depth != 1:
            return
        if tag == 'tr' and self.table is not None:
            self.row = []
        elif tag in {'td', 'th'} and self.row is not None:
            self.cell = []
        elif tag == 'br' and self.cell is not None:
            self.cell.append(' ')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'table' and self.table_depth:
            self.table_depth -= 1
            if self.table_depth == 0 and self.table is not None:
                self.tables.append(self.table)
                self.table = None
                self.row = None
                self.cell = None
            return
        if self.table_depth != 1:
            return
        if tag in {'td', 'th'} and self.cell is not None:
            text = re.sub(r'\s+', ' ', ''.join(self.cell).replace('\xa0', ' ')).strip()
            self.row.append(html.unescape(text))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.table_depth == 1 and self.cell is not None:
            self.cell.append(data)


def page_text(body):
    return body.decode('windows-1252', errors='strict')


def clean_text(value):
    return re.sub(r'\s+', ' ', html.unescape(value).replace('\xa0', ' ')).strip()


def page_headings(source):
    matches = re.findall(r'<h[1-6]\b[^>]*>(.*?)</h[1-6]>', source, re.I | re.S)
    return [clean_text(re.sub(r'<[^>]+>', ' ', item)) for item in matches]


def argentine_number(raw, *, missing_ok=True):
    """Parse the MAG Spanish numeric formats while retaining raw text separately."""
    value = clean_text(str(raw or '')).replace('$', '').replace(' ', '')
    if not value or value in {'-', '–', '—', '-*', '-**', '- *', '- **'} or re.fullmatch(r'-{2,}', value) or value.casefold().startswith('faltacerrar'):
        if missing_ok:
            return None
        raise DataError(f'Empty published number: {raw!r}')
    if not re.fullmatch(r'\d+(?:\.\d{3})*(?:,\d+)?', value):
        raise DataError(f'Invalid Argentine decimal: {raw!r}')
    normalized = value.replace('.', '').replace(',', '.')
    try:
        result = Decimal(normalized)
    except InvalidOperation:
        raise DataError(f'Invalid Argentine decimal: {raw!r}') from None
    if not result.is_finite() or result < 0:
        raise DataError(f'Negative or nonfinite MAG value: {raw!r}')
    return result


def argentine_signed_number(raw):
    value = clean_text(str(raw or '')).replace('%', '').replace('$', '').replace(' ', '')
    if not value or value in {'-', '–', '—'}:
        return None
    sign = -1 if value.startswith('-') else 1
    unsigned = value[1:] if value[:1] in {'-', '+'} else value
    return argentine_number(unsigned, missing_ok=False) * sign


def decimal_text(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DataError(f'Unexpected JSON numeric value: {value!r}')
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise DataError(f'Negative or nonfinite MAG value: {value!r}')
    return format(result, 'f')


def date_from_label(label, year_digits=2):
    match = re.search(r'(\d{2}/\d{2}/\d{' + str(year_digits) + r'})\s*$', clean_text(label))
    if not match:
        raise DataError(f'Unknown MAG date label: {label!r}')
    fmt = '%d/%m/%y' if year_digits == 2 else '%d/%m/%Y'
    try:
        return datetime.strptime(match.group(1), fmt).date()
    except ValueError:
        raise DataError(f'Invalid MAG date label: {label!r}') from None


def make_observation(*, source_id, source_url, manifest, family, metric, category,
        category_raw, age_class='', value, value_raw, unit, unit_raw=None, currency='NOT_APPLICABLE',
        weight_basis='NOT_IDENTIFIED', methodology, table_id, locator, flags=None,
        entity_type='category', date_value, geography=MARKET, geography_level='market'):
    if date_value > local_today():
        raise DataError('Future MAG observation')
    row = observation(family=family, metric=metric, species='bovinos',
        observation_date=date_value.isoformat(), period_end=date_value.isoformat(), frequency='daily',
        category=category, category_raw=category_raw, age_class=age_class,
        geography=geography, geography_raw=geography, geography_level=geography_level,
        market=MARKET, table_id=table_id, entity_type=entity_type, currency=currency, unit=unit,
        unit_raw=unit if unit_raw is None else unit_raw, weight_basis=weight_basis,
        value=decimal_text(value), value_raw=str(value_raw or ''),
        value_status='missing' if value is None else 'observed', methodology=methodology,
        quality_flags=list(flags or []), source_locator=locator)
    row.update(source_id=source_id, source=SOURCE, source_url=source_url,
        capture_date=manifest['capture_date'], capture_id=manifest['capture_id'],
        raw_sha256=manifest['raw_sha256'])
    row['observation_id'] = digest([row[k] for k in IDENTITY])
    row['record_id'] = digest([row['observation_id'], row['capture_id'], row['raw_sha256']])
    return row


def find_table(tables, required, *, strict_header=True):
    required_norm = [clean_text(v).casefold() for v in required]
    matches = []
    for table in tables:
        flat = [[clean_text(cell).casefold() for cell in row] for row in table]
        if any(len(row) == len(required_norm) and row == required_norm for row in flat):
            matches.append(table)
        elif strict_header and required_norm[0] in [cell for row in flat for cell in row]:
            # Header-like table changed shape; the parser must fail closed.
            if any('categoria' in cell or 'fecha' in cell for row in flat for cell in row):
                raise DataError('MAG result table header changed')
    if len(matches) != 1:
        raise DataError(f'Expected one MAG table with headers {required!r}; found {len(matches)}')
    return matches[0]


def find_detail_table(tables):
    for table in tables:
        rows = [[clean_text(cell).casefold() for cell in row] for row in table]
        has_group_header = any(row and row[0] == 'categoría' and len(row) == 4 for row in rows)
        has_measure_header = any(len(row) == 9 and row[1:] ==
            ['mínimo','máximo','promedio','mediana','cabezas','importe','kgs','kgs'] for row in rows)
        if has_group_header and has_measure_header:
            return table
    raise DataError('MAG category result table headers changed')


def report_status(headings):
    text = ' '.join(headings).upper()
    provisional = 'PRECIOS PROVISORIOS' in text
    definitive = 'PRECIOS DEFINITIVOS' in text
    if provisional == definitive:
        raise DataError('MAG report has no unique definitive/provisional status')
    return provisional


def detail_category(label):
    normalized = clean_text(label).upper()
    for original, category in sorted(DETAIL_CATEGORIES.items(), key=lambda item: len(item[0]), reverse=True):
        if normalized == original or normalized.startswith(original + ' '):
            classification = clean_text(label)[len(original):].strip()
            if original in {'M.E.J.', 'M.E.J'} and classification.startswith('.'):
                classification = classification[1:].strip()
            return category, classification, clean_text(label)
    raise DataError(f'Unknown MAG classification label: {label!r}')


def parse_detail(body, query_date, source_id, manifest):
    source = page_text(body)
    headings = page_headings(source)
    title = next((h for h in headings if 'PRECIOS POR CATEGORIA' in h.upper()), None)
    if not title:
        raise DataError('MAG category report title missing')
    dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', title)
    if len(dates) != 2:
        raise DataError('MAG category report date range changed')
    start, end = (datetime.strptime(value, '%d/%m/%Y').date() for value in dates)
    if start != query_date or end != query_date:
        raise DataError('MAG report does not match requested observation date')
    provisional = report_status(headings)
    parser = TableParser(); parser.feed(source)
    table = find_detail_table(parser.tables)
    rows = []
    current_category = None
    has_detail = False
    flags_base = ['provisional_source_statement'] if provisional else []
    for row_index, cells in enumerate(table):
        if len(cells) != 9:
            continue
        raw_label = clean_text(cells[0])
        normalized = raw_label.upper()
        if any(value in {'mínimo','máximo','promedio','mediana','cabezas','importe','kgs'} for value in
                [clean_text(c).casefold() for c in cells[1:]]):
            continue
        values_raw = cells[1:]
        if not raw_label:
            numeric = [argentine_number(v) for v in values_raw]
            if not any(v is not None for v in numeric):
                continue
            if not current_category:
                raise DataError('MAG category subtotal without category heading')
            category, age_class = current_category, 'Total de categoría (publicado)'
            category_raw = f'{category} · Total publicado'
            entity_type = 'category_rollup'
        elif normalized in {'TOTALES', 'TOTAL', 'TOTAL GENERAL'}:
            numeric = [argentine_number(v) for v in values_raw]
            category, age_class, category_raw, entity_type = 'Total MAG', '', raw_label, 'total'
        else:
            category, age_class, category_raw = detail_category(raw_label)
            numeric = [argentine_number(v) for v in values_raw]
            current_category = category
            entity_type = 'category'
            has_detail = True
        for (metric, _label, unit, currency), value, raw_value in zip(PRICE_FIELDS, numeric, values_raw):
            if value is None and not provisional and entity_type == 'category':
                raise DataError(f'Definitive MAG category has a missing {metric}: {raw_label!r}')
            flags = list(flags_base)
            raw_unit = {'heads':'Cabezas', 'amount_ARS':'$', 'kilos':'Kgs', 'average_kilos':'Kgs'}.get(metric, '')
            if metric.startswith('price_'):
                flags.append('unit_inferred_from_sagyp_reference')
            if value is None:
                flags.append('published_value_missing')
            rows.append(make_observation(source_id=source_id, source_url=DETAIL_URL, manifest=manifest,
                family=PRICE_FAMILY, metric=metric, category=category, category_raw=category_raw,
                age_class=age_class, value=value, value_raw=raw_value, unit=unit, unit_raw=raw_unit, currency=currency,
                weight_basis='live' if metric.startswith('price_') else 'NOT_IDENTIFIED',
                methodology=PRICE_METHOD if entity_type != 'total' else 'mag_daily_market_total',
                table_id='mag/category_prices', locator=f'response-{query_date.isoformat()}.html#result/tr[{row_index}]/td',
                flags=flags, entity_type=entity_type, date_value=query_date))
    if not has_detail:
        raise NoPublication(f'No category rows for {query_date.isoformat()}')
    # A report with rows for another date or an all-zero completed sheet is invalid.
    observed_prices = [r for r in rows if r['metric'] == 'price_average' and r['value_status'] == 'observed']
    if not observed_prices:
        raise DataError('MAG category report contains no observed averages')
    return rows, 'PROVISIONAL' if provisional else 'DEFINITIVE'


def parse_chart(body, category_code, source_id, manifest, as_of):
    expected_category, raw_category = CHART_CATEGORIES[category_code]
    try:
        data = json.loads(body.decode('utf-8-sig'), parse_float=Decimal, parse_int=int)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise DataError('MAG evolution chart is not valid JSON') from None
    if not isinstance(data, dict) or set(data) != {'title', 'type', 'labels', 'data', 'scale'}:
        raise DataError('MAG evolution chart JSON schema changed')
    if data['title'] != f'Evolución Precios Promedio {raw_category}' or data['type'] != 'bar':
        raise DataError('MAG evolution chart identity changed')
    labels, series = data['labels'], data['data']
    if not isinstance(labels, list) or not labels or len(series) != 2:
        raise DataError('MAG evolution chart is empty or incomplete')
    if [item.get('label') for item in series] != ['Precio Promedio', 'Cabezas']:
        raise DataError('MAG evolution chart series labels changed')
    if any(not isinstance(item.get('vals'), list) or len(item['vals']) != len(labels) for item in series):
        raise DataError('MAG evolution chart series lengths differ')
    dates = [date_from_label(label) for label in labels]
    if dates != sorted(set(dates)) or dates[0] < MAG_START or dates[-1] > as_of:
        raise DataError('MAG evolution chart dates are duplicated, unordered, outside coverage or future')
    rows = []
    price_values, head_values = series[0]['vals'], series[1]['vals']
    for i, (label, day, price, heads) in enumerate(zip(labels, dates, price_values, head_values)):
        for metric, raw, family, unit, currency, weight, method in [
            ('price_average', price, PRICE_FAMILY, 'ARS/kg vivo', 'ARS', 'live', CHART_METHOD),
            ('heads_by_category', heads, ACTIVITY_FAMILY, 'cabezas', 'NOT_APPLICABLE', 'NOT_IDENTIFIED', CHART_METHOD),
        ]:
            if raw is None:
                value = None; raw_value = ''
            else:
                value = Decimal(str(raw)) if isinstance(raw, (Decimal, int)) and not isinstance(raw, bool) else None
                if value is None or not value.is_finite() or value < 0:
                    raise DataError(f'Invalid MAG chart point for {metric}: {raw!r}')
                raw_value = str(raw)
            rows.append(make_observation(source_id=source_id, source_url=CHART_URL, manifest=manifest,
                family=family, metric=metric, category=expected_category, category_raw=raw_category,
                value=value, value_raw=raw_value, unit=unit,
                unit_raw='' if metric == 'price_average' else 'Cabezas', currency=currency, weight_basis=weight,
                methodology=method, table_id='mag/evolution_prices_by_category',
                locator=f'response.json#/data/{0 if metric == "price_average" else 1}/vals/{i}; label={label}',
                flags=['daily_average_published_by_MAG','unit_inferred_from_sagyp_reference'] if metric == 'price_average' else ['daily_heads_published_by_MAG'],
                entity_type='category', date_value=day))
    return rows


def summary_table(source):
    parser = TableParser(); parser.feed(source)
    required = ['Fecha', 'Cab. ingresadas', 'Importe', 'I.N.M.A.G.', 'Variación']
    return find_table(parser.tables, required)


def parse_totals(body, source_id, manifest, as_of):
    source = page_text(body)
    headings = page_headings(source)
    title = next((h for h in headings if 'TOTALES POR DIA' in h.upper()), None)
    if not title:
        raise DataError('MAG totals report title missing')
    parser = TableParser(); parser.feed(source)
    required = ['Fecha', 'Cab. ingresadas', 'Importe', 'I.N.M.A.G.', 'Variación']
    table = find_table(parser.tables, required)
    rows = []
    previous_date = None
    for row_index, cells in enumerate(table):
        if len(cells) != 5:
            continue
        raw_date = clean_text(cells[0])
        if not raw_date or raw_date.casefold() == 'fecha':
            continue
        if raw_date.casefold().startswith('totales'):
            continue
        day = date_from_label(raw_date, 4)
        if day < MAG_START:
            continue
        if day > as_of or previous_date is not None and day <= previous_date:
            raise DataError('MAG totals dates are unordered, duplicated or future')
        previous_date = day
        raw_heads, raw_amount, raw_index, raw_change = cells[1:]
        heads = argentine_number(raw_heads, missing_ok=False)
        amount = argentine_number(raw_amount)
        index_value = argentine_number(raw_index)
        change = clean_text(raw_change).replace('%', '').strip()
        change_value = argentine_signed_number(change) if change else None
        if raw_index and raw_index.casefold() in {'falta cerrar', 'falta cerrar*'}:
            index_value = None
        common = dict(source_id=source_id, source_url=TOTALS_URL, manifest=manifest, date_value=day,
            category='MAG', category_raw='Mercado Agroganadero', methodology=INDEX_METHOD,
            table_id='mag/daily_totals_inmag', entity_type='market_total')
        rows.extend([
            make_observation(**common, family=ACTIVITY_FAMILY, metric='market_heads', value=heads,
                value_raw=raw_heads, unit='cabezas', unit_raw='Cab. ingresadas', weight_basis='NOT_APPLICABLE',
                locator=f'response.html#totals/tr[{row_index}]/td[1]'),
            make_observation(**common, family=ACTIVITY_FAMILY, metric='market_amount_ARS', value=amount,
                value_raw=raw_amount, unit='ARS', unit_raw='$', currency='ARS', weight_basis='NOT_APPLICABLE',
                locator=f'response.html#totals/tr[{row_index}]/td[2]',
                flags=['published_value_missing'] if amount is None else []),
            make_observation(**common, family=INDEX_FAMILY, metric='inmag_index', value=index_value,
                value_raw=raw_index, unit='puntos I.N.M.A.G.', unit_raw='I.N.M.A.G.', weight_basis='NOT_APPLICABLE',
                locator=f'response.html#totals/tr[{row_index}]/td[3]',
                flags=['index_not_calculated'] if clean_text(raw_index).startswith('-') else ['index_not_closed'] if index_value is None else []),
        ])
        if raw_change:
            rows.append(make_observation(**common, family=INDEX_FAMILY, metric='inmag_variation_percent',
                value=change_value, value_raw=raw_change, unit='%', unit_raw='Variación', weight_basis='NOT_APPLICABLE',
                locator=f'response.html#totals/tr[{row_index}]/td[4]'))
    if not rows:
        raise NoPublication('MAG totals page has no market days in the requested period')
    return rows


def expected_base_url(url):
    from urllib.parse import urlsplit
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'mercadoagroganadero.com.ar' or parsed.port not in (None, 443):
        raise DataError('MAG URL is outside the official HTTPS origin')
    if parsed.path not in {DETAIL_URL.split('.ar', 1)[1], TOTALS_URL.split('.ar', 1)[1], CHART_URL.split('.ar', 1)[1]}:
        raise DataError('MAG endpoint is not in the approved catalog')
    return url


def request_body(url, max_bytes=8_000_000):
    global _last_request_at, _requests_this_run
    expected_base_url(url.split('?', 1)[0])
    if _requests_this_run >= MAX_RUN_REQUESTS:
        raise DataError('MAG run request budget exhausted')
    _requests_this_run += 1
    current = time.monotonic()
    if _last_request_at is not None:
        remaining = REQUEST_INTERVAL_SECONDS - (current - _last_request_at)
        if remaining > 0:
            time.sleep(remaining)
    _last_request_at = time.monotonic()
    request = Request(url, headers={'User-Agent': 'Serie-Agricola MAG public-source pipeline/1.0',
        'Accept': 'text/html,application/json;q=0.9,*/*;q=0.5'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=30) as response:
            body = response.read(max_bytes + 1)
            status = response.status
            content_type = response.headers.get('Content-Type', '')
            encoding = response.headers.get_content_charset()
    except (HTTPError, URLError, OSError) as error:
        raise SourceUnavailable(f'HTTP/service unavailable ({getattr(error, "code", type(error).__name__)})') from None
    if status != 200:
        raise SourceUnavailable(f'HTTP {status}')
    if len(body) > max_bytes:
        raise DataError('MAG response exceeds size limit')
    return body, {'status': status, 'content_type': content_type, 'encoding': encoding,
        'size_bytes': len(body), 'raw_sha256': digest(body)}


def capture_bundle(root, source_id, requests):
    if not re.fullmatch(r'[a-z0-9_]+', source_id):
        raise DataError('Invalid MAG source ID')
    if len(requests) > 10:
        raise DataError('MAG request budget exceeded')
    responses = {}
    for item in requests:
        url = item['url'] + ('?' + encoded_query(item['params']) if item.get('params') else '')
        body, metadata = request_body(url)
        responses[item['name']] = (body, dict(metadata, request_url=url, parameters=item.get('params', {})))
    stamp = utc_now()
    capture_id = stamp.replace(':', '').replace('.', '') + '_' + uuid.uuid4().hex[:12]
    folder = Path(root) / 'raw' / source_id / capture_id
    folder.mkdir(parents=True, exist_ok=False)
    response_records = []
    for name, (body, metadata) in responses.items():
        if not re.fullmatch(r'[a-z0-9_-]+\.(?:json|html)', name):
            raise DataError('Invalid MAG response filename')
        with (folder / name).open('xb') as stream:
            stream.write(body)
        response_records.append(dict(name=name, **metadata))
    raw_sha = digest([{k: item[k] for k in ('name','request_url','parameters','raw_sha256','size_bytes')}
        for item in response_records])
    manifest = dict(source_id=source_id, source_url=requests[0]['url'], method='GET',
        capture_date=stamp, capture_id=capture_id, status=200, raw_sha256=raw_sha,
        size_bytes=sum(item['size_bytes'] for item in response_records), parser_version='mag-carnes-v1',
        schema_version=VERSION, response_files=response_records)
    with (folder / 'manifest.json').open('xb') as stream:
        stream.write(encoded(manifest))
    print(f'[RAW] {source_id} capture={capture_id} responses={len(response_records)} sha256={raw_sha}', flush=True)
    return folder, manifest, {name: body for name, (body, _) in responses.items()}


def read_entry_rows(root, source_id):
    index = read_json(Path(root) / 'dashboard/index.json', {'schema_version': VERSION, 'sources': {}})
    entry = index.get('sources', {}).get(source_id)
    if not entry:
        return {}, None
    validate_entry(Path(root) / 'dashboard', entry)
    rows = {}
    for descriptor in entry['files']:
        with gzip.open(Path(root) / 'dashboard' / descriptor['path'], 'rt', encoding='utf-8', newline='') as stream:
            for row in csv.DictReader(stream):
                row['quality_flags'] = json.loads(row['quality_flags'])
                if row['observation_id'] in rows:
                    raise DataError(f'Duplicate existing MAG row in {source_id}')
                rows[row['observation_id']] = row
    return rows, entry


def row_content(row):
    ignored = {'observation_id','record_id','capture_date','capture_id','raw_sha256'}
    result = {key: row[key] for key in FIELDS if key not in ignored}
    flags = row.get('quality_flags', [])
    result['quality_flags'] = json.loads(flags) if isinstance(flags, str) else flags
    return result


def publish_source(root, source_id, source_url, kind, new_rows, manifest, *, replace_source=False):
    root = Path(root)
    existing, previous_entry = read_entry_rows(root, source_id)
    merged = {} if replace_source else dict(existing)
    changed = False
    for row in new_rows:
        if set(row) != set(FIELDS):
            raise DataError('MAG normalizer observation contract changed')
        if row['family'] not in {'livestock_price','livestock_index','market_activity'} or row['frequency'] != 'daily':
            raise DataError('Unknown MAG family/frequency')
        if row['value_status'] == 'observed' and (row['value'] is None or not re.fullmatch(r'\d+(?:\.\d*)?', row['value'])):
            raise DataError('Invalid normalized MAG value')
        if row['value_status'] == 'missing' and row['value'] is not None:
            raise DataError('MAG missing value conceals a value')
        if row['observation_id'] in merged and row_content(merged[row['observation_id']]) == row_content(row):
            continue
        merged[row['observation_id']] = row
        changed = True
    if not merged or not any(row['value_status'] == 'observed' for row in merged.values()):
        raise DataError('MAG output is empty; last valid bundle preserved')
    rows = sorted(merged.values(), key=lambda row: (row['observation_date'], row['metric'], row['category'], row['age_class']))
    groups = {}
    for row in rows:
        groups.setdefault((row['family'], row['frequency'], row['observation_date'][:4]), []).append(row)
    descriptors = []
    for (family, frequency, year), part in sorted(groups.items()):
        body = gzip.compress(csv_bytes(part), mtime=0)
        if len(body) > 5_000_000:
            raise DataError('MAG dashboard shard too large')
        filename = f'{source_id}-{family}-{frequency}-{year}-{digest(body)[:16]}.csv.gz'
        atomic_write(root / 'dashboard' / filename, body)
        descriptors.append(dict(path=filename, sha256=digest(body), bytes=len(body), rows=len(part),
            family=family, frequency=frequency, year=year))
    entry = dict(source=SOURCE, source_url=source_url, source_id=source_id, kind=kind,
        capture_mode='multi_capture', capture_id=manifest['capture_id'], raw_sha256=manifest['raw_sha256'],
        last_successful_capture=manifest['capture_date'],
        first_observation=min(row['observation_date'] for row in rows),
        last_observation=max(row['observation_date'] for row in rows), rows=len(rows),
        observed_rows=sum(row['value_status'] == 'observed' for row in rows), dashboard_rows=len(rows),
        source_lifecycle='CURRENT_PUBLICATION', license='NOT_SPECIFIED', files=descriptors)
    validate_entry(root / 'dashboard', entry)
    index_path = root / 'dashboard/index.json'
    index = read_json(index_path, dict(schema_version=VERSION, sources={}))
    if index.get('schema_version') != VERSION or not isinstance(index.get('sources'), dict):
        raise DataError('Unknown Carnes prepared index')
    index['sources'][source_id] = entry
    atomic_write(index_path, encoded(index))
    # Drop only superseded, unreferenced shards belonging to this MAG source.
    keep = {item['path'] for item in descriptors}
    for path in (root / 'dashboard').glob(f'{source_id}-*.csv.gz'):
        if path.name not in keep:
            path.unlink()
    return 'UPDATED' if changed or previous_entry is None else 'NO_PUBLICATION', entry


def load_detail_latest(root):
    existing, _entry = read_entry_rows(root, DETAIL_SOURCE_ID)
    provisional = [row for row in existing.values() if 'provisional_source_statement' in row.get('quality_flags', [])]
    return max((date.fromisoformat(row['observation_date']) for row in provisional), default=None)


def apply_detail_conditions_to_chart(root, source_id, conditions):
    """Carry MAG's report header status onto matching chart averages without relabelling history."""
    if not conditions:
        return False
    existing, entry = read_entry_rows(root, source_id)
    if not entry:
        return False
    changed = False
    for row in existing.values():
        condition = conditions.get(row['observation_date'])
        if row['metric'] != 'price_average' or condition not in {'PROVISIONAL', 'DEFINITIVE'}:
            continue
        flags = list(row['quality_flags'])
        if condition == 'PROVISIONAL' and 'provisional_source_statement' not in flags:
            flags.append('provisional_source_statement'); changed = True
        elif condition == 'DEFINITIVE' and 'provisional_source_statement' in flags:
            flags.remove('provisional_source_statement'); changed = True
        row['quality_flags'] = flags
    if not changed:
        return False
    capture_id = entry['capture_id']
    manifest = read_json(Path(root) / 'raw' / source_id / capture_id / 'manifest.json')
    if not manifest or manifest.get('capture_id') != capture_id or manifest.get('raw_sha256') != entry['raw_sha256']:
        raise DataError('MAG chart RAW manifest is unavailable for report-status propagation')
    publish_source(root, source_id, CHART_URL, 'mag_daily_category_average', list(existing.values()), manifest)
    return True


def status_record(status, reason=None, last_valid_preserved=False):
    return dict(status=status, attempted_at=utc_now(), reason=reason,
        last_valid_preserved=bool(last_valid_preserved))


def pipeline_exit_code(outcomes):
    """Only technical pipeline errors fail Actions; publication states remain data states."""
    return int('PIPELINE_ERROR' in outcomes)


def update(root=DATA, as_of=None, allow_web=False):
    global _last_request_at, _requests_this_run
    root = Path(root); as_of = as_of or local_today()
    if not allow_web:
        print('[FETCH] DRY-RUN; pass --allow-web for controlled public HTTP', flush=True)
        return 0
    _last_request_at = None; _requests_this_run = 0
    root.mkdir(parents=True, exist_ok=True)
    states = read_json(root / 'reports/CARNES_UPDATE_STATUS.json', dict(schema_version=VERSION, sources={}))
    states.setdefault('sources', {})
    if states.get('schema_version') != VERSION:
        raise DataError('Unknown Carnes status schema')
    outcomes = []

    def record(source_id, status, reason=None):
        preserved = False
        if status in {'SOURCE_UNAVAILABLE','PIPELINE_ERROR','NO_PUBLICATION'}:
            try:
                _rows, previous_entry = read_entry_rows(root, source_id)
                preserved = previous_entry is not None
            except (DataError, ValueError, KeyError, TypeError, OSError):
                preserved = False
        states['sources'][source_id] = status_record(status, reason, preserved)
        atomic_write(root / 'reports/CARNES_UPDATE_STATUS.json', encoded(states))
        print(f'[STATE] {source_id}: {status}' + (f' ({reason})' if reason else ''), flush=True)
        outcomes.append(status)

    detail_conditions = {}
    try:
        read_catalog()
    except (DataError, ValueError, KeyError, TypeError, OSError) as error:
        record('mag_prices_catalog', 'PIPELINE_ERROR', f'{type(error).__name__}: {error}')
        return 1

    # Six official category charts, using the historical range after MAG began in Cañuelas.
    for code, (category, raw_category) in CHART_CATEGORIES.items():
        source_id = f'mag_prices_history_{category.lower()}'
        params = {'txtFECHAINI': MAG_START.strftime('%d/%m/%Y'), 'txtFECHAFIN': as_of.strftime('%d/%m/%Y'), 'txtCLASE': code}
        try:
            folder, manifest, bodies = capture_bundle(root, source_id,
                [dict(name='response.json', url=CHART_URL, params=params)])
            rows = parse_chart(bodies['response.json'], code, source_id, manifest, as_of)
            publish_source(root, source_id, CHART_URL, 'mag_daily_category_average', rows, manifest)
            latest_price = max((date.fromisoformat(row['observation_date']) for row in rows
                if row['metric'] == 'price_average' and row['value_status'] == 'observed'), default=None)
            if latest_price == as_of:
                record(source_id, 'UPDATED')
            else:
                record(source_id, 'NO_PUBLICATION', f'No hay promedio de {category} para {as_of.isoformat()}; último dato {latest_price or "sin fecha"}')
        except SourceUnavailable as error:
            record(source_id, 'SOURCE_UNAVAILABLE', str(error))
        except (DataError, ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
            record(source_id, 'PIPELINE_ERROR', f'{type(error).__name__}: {error}')
        except Exception as error:
            record(source_id, 'PIPELINE_ERROR', f'{type(error).__name__}: {error}')

    # Refresh today's report and re-check the latest provisional report so its final version replaces it.
    try:
        dates = {as_of, date.fromordinal(as_of.toordinal() - 1)}
        previous_provisional = load_detail_latest(root)
        if previous_provisional:
            dates.add(previous_provisional)
        requests = [dict(name=f'response-{day.isoformat()}.html', url=DETAIL_URL,
            params={'txtFechaIni': day.strftime('%d/%m/%Y'), 'txtFechaFin': day.strftime('%d/%m/%Y')}) for day in sorted(dates)]
        folder, manifest, bodies = capture_bundle(root, DETAIL_SOURCE_ID, requests)
        rows = []; date_status = {}
        for item in requests:
            day = date.fromisoformat(item['name'][9:19])
            try:
                parsed, condition = parse_detail(bodies[item['name']], day, DETAIL_SOURCE_ID, manifest)
                rows.extend(parsed); date_status[day.isoformat()] = condition
            except NoPublication as error:
                date_status[day.isoformat()] = 'NO_PUBLICATION'
                print(f'[SOURCE] {DETAIL_SOURCE_ID} {day}: NO_PUBLICATION ({error})', flush=True)
        if rows:
            # Detailed classification statistics are a compact latest-report snapshot.
            # Full daily evolution stays in the smaller official category-average series.
            latest_detail_day = max(date.fromisoformat(row['observation_date']) for row in rows)
            rows = [row for row in rows if row['observation_date'] == latest_detail_day.isoformat()]
            publication_state, _entry = publish_source(root, DETAIL_SOURCE_ID, DETAIL_URL,
                'mag_daily_category_detail_latest', rows, manifest, replace_source=True)
            if date_status.get(as_of.isoformat()) == 'NO_PUBLICATION' and publication_state != 'UPDATED':
                record(DETAIL_SOURCE_ID, 'NO_PUBLICATION', json.dumps(date_status, ensure_ascii=False, sort_keys=True))
            else:
                record(DETAIL_SOURCE_ID, 'UPDATED', json.dumps(date_status, ensure_ascii=False, sort_keys=True))
        else:
            record(DETAIL_SOURCE_ID, 'NO_PUBLICATION', json.dumps(date_status, ensure_ascii=False, sort_keys=True))
        detail_conditions = {day: state for day, state in date_status.items() if state in {'PROVISIONAL', 'DEFINITIVE'}}
    except SourceUnavailable as error:
        record(DETAIL_SOURCE_ID, 'SOURCE_UNAVAILABLE', str(error))
    except (DataError, ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        record(DETAIL_SOURCE_ID, 'PIPELINE_ERROR', f'{type(error).__name__}: {error}')
    except Exception as error:
        record(DETAIL_SOURCE_ID, 'PIPELINE_ERROR', f'{type(error).__name__}: {error}')

    # The price chart omits a provisional/definitive label; inherit it only from the
    # matching official detailed report date and retain the chart's own RAW lineage.
    for category, _raw_category in CHART_CATEGORIES.values():
        source_id = f'mag_prices_history_{category.lower()}'
        try:
            apply_detail_conditions_to_chart(root, source_id, detail_conditions)
        except Exception as error:
            record(source_id, 'PIPELINE_ERROR', f'{type(error).__name__}: {error}')

    # MAG publishes daily totals and the separately identified INMAG index in one official table.
    try:
        params = {'txtFechaIni': MAG_START.strftime('%d/%m/%Y'), 'txtFechaFin': as_of.strftime('%d/%m/%Y')}
        folder, manifest, bodies = capture_bundle(root, INMAG_SOURCE_ID,
            [dict(name='response.html', url=TOTALS_URL, params=params)])
        rows = parse_totals(bodies['response.html'], INMAG_SOURCE_ID, manifest, as_of)
        publish_source(root, INMAG_SOURCE_ID, TOTALS_URL, 'mag_daily_totals_inmag', rows, manifest)
        latest_index = max((row for row in rows if row['metric'] == 'inmag_index'), key=lambda row: row['observation_date'])
        if latest_index['value_status'] == 'missing':
            condition = 'pendiente de cierre' if 'index_not_closed' in latest_index['quality_flags'] else 'no calculado según el marcador publicado'
            record(INMAG_SOURCE_ID, 'NO_PUBLICATION', f'I.N.M.A.G. {condition} al {latest_index["observation_date"]} ({latest_index["value_raw"]})')
        else:
            record(INMAG_SOURCE_ID, 'UPDATED')
    except SourceUnavailable as error:
        record(INMAG_SOURCE_ID, 'SOURCE_UNAVAILABLE', str(error))
    except (DataError, ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        record(INMAG_SOURCE_ID, 'PIPELINE_ERROR', f'{type(error).__name__}: {error}')
    except Exception as error:
        record(INMAG_SOURCE_ID, 'PIPELINE_ERROR', f'{type(error).__name__}: {error}')

    # Validate the complete published index without contacting any source.
    try:
        from scripts.carnes.validate import validate
        validate(root / 'dashboard')
    except (DataError, ValueError, KeyError, TypeError, OSError) as error:
        record('mag_prices_validation', 'PIPELINE_ERROR', f'{type(error).__name__}: {error}')
    except Exception as error:
        record('mag_prices_validation', 'PIPELINE_ERROR', f'{type(error).__name__}: {error}')
    return pipeline_exit_code(outcomes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['update'])
    parser.add_argument('--data-root', type=Path, default=DATA)
    parser.add_argument('--as-of', type=date.fromisoformat, default=local_today())
    parser.add_argument('--allow-web', action='store_true')
    args = parser.parse_args()
    with writer_lock(args.data_root):
        return update(args.data_root, args.as_of, args.allow_web)


if __name__ == '__main__':
    raise SystemExit(main())
