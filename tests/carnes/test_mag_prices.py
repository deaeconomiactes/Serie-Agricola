import gzip
import json
import tempfile
import unittest
from datetime import date
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from scripts.carnes import mag_prices as mag
from scripts.carnes.model import DataError, digest
from scripts.carnes.validate import validate_entry


ASOF = date(2026, 11, 11)
CAPTURE_ID = '20261111T130000Z_0123456789ab'


def manifest(body=b'official response'):
    return {
        'capture_id': CAPTURE_ID,
        'capture_date': '2026-11-11T13:00:00Z',
        'raw_sha256': digest(body),
    }


def detail_html(status='PRECIOS DEFINITIVOS', median='4.200,00', day='17/05/2022'):
    return f'''<!doctype html><html><h2>{status}</h2>
    <h3>PRECIOS POR CATEGORIA ENTRE EL MARTES {day} AL MARTES {day}</h3>
    <table>
      <tr><th>Categoría</th><th>Precios</th><th>Totales</th><th>Prom.</th></tr>
      <tr><th></th><th>Mínimo</th><th>Máximo</th><th>Promedio</th><th>Mediana</th><th>Cabezas</th><th>Importe</th><th>Kgs</th><th>Kgs</th></tr>
      <tr><td>NOVILLOS Esp.Joven + 430</td><td>3.500,00</td><td>4.600,00</td><td>4.194,276</td><td>{median}</td><td>655</td><td>$1.369.619.800,00</td><td>326.545</td><td>499</td></tr>
      <tr><td></td><td></td><td></td><td>4.194,276</td><td></td><td>655</td><td>$1.369.619.800,00</td><td>326.545</td><td>499</td></tr>
      <tr><td>TOTALES</td><td></td><td></td><td></td><td></td><td>655</td><td>$1.369.619.800,00</td><td>326.545</td><td>499</td></tr>
    </table></html>'''.encode('windows-1252')


def totals_html():
    return '''<html><h6>TOTALES POR DIA ENTRE EL MARTES 17/05/2022 AL MIÉRCOLES 18/05/2022</h6>
    <table><tr><th>Fecha</th><th>Cab. ingresadas</th><th>Importe</th><th>I.N.M.A.G.</th><th>Variación</th></tr>
    <tr><td>Ma&nbsp;17/05/2022</td><td>10.442</td><td>972.865.940,00</td><td>281,022</td><td><table><tr><td>sin texto</td></tr></table></td></tr>
    <tr><td>Mi 18/05/2022</td><td>14</td><td></td><td>- *</td><td></td></tr>
    <tr><td>Totales</td><td>10.456</td><td>972.865.940,00</td><td>-</td><td></td></tr></table></html>'''.encode('windows-1252')


def chart_json():
    return json.dumps({
        'title': 'Evolución Precios Promedio NOVILLOS',
        'type': 'bar',
        'labels': ['MAG 17/05/22', 'MAG 18/05/22'],
        'data': [
            {'label': 'Precio Promedio', 'vals': [4194.276, 4201.5]},
            {'label': 'Cabezas', 'vals': [655, 401]},
        ],
        'scale': 'linear',
    }).encode()


class MAGPricesTests(unittest.TestCase):
    def test_argentine_decimals_and_unrecognized_values_fail_closed(self):
        self.assertEqual(mag.argentine_number('1.234.567,89'), mag.Decimal('1234567.89'))
        self.assertEqual(mag.argentine_number('3.500,000'), mag.Decimal('3500.000'))
        self.assertIsNone(mag.argentine_number('Falta Cerrar'))
        self.assertIsNone(mag.argentine_number('- *'))
        self.assertEqual(mag.argentine_signed_number('-2,50 %'), mag.Decimal('-2.50'))
        for value in ('1,2,3', '12.34,00', 'NaN', '1O0'):
            with self.subTest(value=value), self.assertRaises(DataError):
                mag.argentine_number(value)

    def test_detail_report_preserves_classification_provenance_and_condition(self):
        body = detail_html()
        rows, condition = mag.parse_detail(body, date(2022, 5, 17), 'mag_prices_detail', manifest(body))
        self.assertEqual(condition, 'DEFINITIVE')
        self.assertEqual(len(rows), 24)
        average = next(r for r in rows if r['metric'] == 'price_average' and r['entity_type'] == 'category')
        self.assertEqual(average['category'], 'Novillos')
        self.assertEqual(average['category_raw'], 'NOVILLOS Esp.Joven + 430')
        self.assertEqual(average['age_class'], 'Esp.Joven + 430')
        self.assertEqual(average['value'], '4194.276')
        self.assertEqual(average['unit'], 'ARS/kg vivo')
        self.assertEqual(average['value_raw'], '4.194,276')
        self.assertEqual(average['unit'], 'ARS/kg vivo')
        self.assertEqual(average['unit_raw'], '')
        self.assertIn('unit_inferred_from_sagyp_reference', average['quality_flags'])
        self.assertEqual(average['capture_id'], CAPTURE_ID)
        self.assertEqual(average['raw_sha256'], digest(body))
        self.assertTrue(any(r['entity_type'] == 'category_rollup' for r in rows))

    def test_provisional_missing_stat_is_flagged_and_definitive_missing_fails(self):
        body = detail_html('PRECIOS PROVISORIOS', median='')
        rows, condition = mag.parse_detail(body, date(2022, 5, 17), 'mag_prices_detail', manifest(body))
        self.assertEqual(condition, 'PROVISIONAL')
        median = next(r for r in rows if r['metric'] == 'price_median' and r['entity_type'] == 'category')
        self.assertEqual(median['value_status'], 'missing')
        self.assertIn('published_value_missing', median['quality_flags'])
        definitive = detail_html(median='')
        with self.assertRaises(DataError):
            mag.parse_detail(definitive, date(2022, 5, 17), 'mag_prices_detail', manifest(definitive))

    def test_detail_date_and_report_state_are_strict(self):
        with self.assertRaises(DataError):
            mag.parse_detail(detail_html(), date(2022, 5, 18), 'mag_prices_detail', manifest())
        both = detail_html().replace(b'<h2>PRECIOS DEFINITIVOS</h2>', b'<h2>PRECIOS PROVISORIOS</h2><h2>PRECIOS DEFINITIVOS</h2>')
        with self.assertRaises(DataError):
            mag.parse_detail(both, date(2022, 5, 17), 'mag_prices_detail', manifest(both))
        empty = detail_html()
        empty = empty[:empty.index(b'<tr><td>NOVILLOS')] + b'</table></html>'
        with self.assertRaises(mag.NoPublication):
            mag.parse_detail(empty, date(2022, 5, 17), 'mag_prices_detail', manifest(empty))

    def test_chart_history_contract_filters_pre_canuelas_rows(self):
        body = chart_json()
        rows = mag.parse_chart(body, '1', 'mag_prices_history_novillos', manifest(body), date(2022, 5, 18))
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]['observation_date'], '2022-05-17')
        self.assertEqual(rows[0]['value'], '4194.276')
        self.assertEqual(rows[0]['methodology'], mag.CHART_METHOD)
        self.assertEqual(rows[0]['unit'], 'ARS/kg vivo')
        old = chart_json().replace(b'17/05/22', b'16/05/22')
        with self.assertRaises(DataError):
            mag.parse_chart(old, '1', 'mag_prices_history_novillos', manifest(old), date(2022, 5, 18))
        changed = json.loads(body); changed['data'][0]['vals'].pop()
        with self.assertRaises(DataError):
            mag.parse_chart(json.dumps(changed).encode(), '1', 'mag_prices_history_novillos', manifest(), ASOF)

    def test_totals_parse_nested_table_and_keep_missing_as_missing(self):
        body = totals_html()
        rows = mag.parse_totals(body, 'mag_inmag', manifest(body), date(2022, 5, 18))
        self.assertEqual(len(rows), 6)
        first = [r for r in rows if r['observation_date'] == '2022-05-17']
        self.assertEqual(next(r for r in first if r['metric'] == 'inmag_index')['value'], '281.022')
        day_two = [r for r in rows if r['observation_date'] == '2022-05-18']
        missing_amount = next(r for r in day_two if r['metric'] == 'market_amount_ARS')
        self.assertEqual(missing_amount['value_status'], 'missing')
        self.assertEqual(missing_amount['value_raw'], '')
        missing_index = next(r for r in day_two if r['metric'] == 'inmag_index')
        self.assertEqual(missing_index['value_status'], 'missing')
        self.assertIn('index_not_calculated', missing_index['quality_flags'])

    def test_raw_capture_is_immutable_and_has_response_hashes(self):
        body = chart_json()
        metadata = {'status': 200, 'content_type': 'application/json', 'encoding': 'utf-8', 'size_bytes': len(body), 'raw_sha256': digest(body)}
        with tempfile.TemporaryDirectory() as temp, patch.object(mag, 'request_body', return_value=(body, metadata)), patch.object(mag.time, 'sleep'):
            folder, captured, bodies = mag.capture_bundle(temp, 'mag_prices_history_novillos', [
                {'name': 'response.json', 'url': mag.CHART_URL, 'params': {'txtCLASE': '1'}}
            ])
            self.assertEqual((folder / 'response.json').read_bytes(), body)
            self.assertEqual(bodies['response.json'], body)
            recorded = json.loads((folder / 'manifest.json').read_bytes())
            self.assertEqual(recorded['response_files'][0]['raw_sha256'], digest(body))
            self.assertEqual(captured['raw_sha256'], mag.digest([{
                k: recorded['response_files'][0][k] for k in ('name', 'request_url', 'parameters', 'raw_sha256', 'size_bytes')
            }]))
            with self.assertRaises(FileExistsError):
                (folder / 'response.json').open('xb')

    def test_public_requests_are_spaced_at_least_one_second(self):
        self.assertEqual(mag.MAX_RUN_REQUESTS, 10)
        class Response:
            status = 200
            headers = Message()
            def __init__(self):
                self.headers['Content-Type'] = 'application/json; charset=utf-8'
            def read(self, limit):
                return b'{}'
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False

        class Client:
            def open(self, *_args, **_kwargs):
                return Response()

        mag._last_request_at = None
        mag._requests_this_run = 0
        with patch.object(mag, 'build_opener', return_value=Client()), \
                patch.object(mag.time, 'monotonic', side_effect=[100.0, 100.0, 100.2, 100.2]), \
                patch.object(mag.time, 'sleep') as sleep:
            mag.request_body(mag.CHART_URL)
            mag.request_body(mag.CHART_URL)
        sleep.assert_called_once()
        self.assertAlmostEqual(sleep.call_args.args[0], 0.8)
        mag._requests_this_run = mag.MAX_RUN_REQUESTS
        with self.assertRaises(DataError):
            mag.request_body(mag.CHART_URL)
        mag._requests_this_run = 0

    def test_dashboard_upsert_is_multicapture_and_invalid_update_preserves_index(self):
        body = chart_json(); captured = manifest(body)
        rows = mag.parse_chart(body, '1', 'mag_prices_history_novillos', captured, date(2022, 5, 18))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'dashboard').mkdir()
            entry_status, _ = mag.publish_source(root, 'mag_prices_history_novillos', mag.CHART_URL,
                'mag_daily_category_average', rows, captured)
            self.assertEqual(entry_status, 'UPDATED')
            raw_folder = root / 'raw/mag_prices_history_novillos' / CAPTURE_ID
            raw_folder.mkdir(parents=True)
            raw_manifest = {**captured, 'source_id': 'mag_prices_history_novillos', 'response_files': []}
            (raw_folder / 'manifest.json').write_bytes(mag.encoded(raw_manifest))
            self.assertTrue(mag.apply_detail_conditions_to_chart(root, 'mag_prices_history_novillos', {'2022-05-17': 'PROVISIONAL'}))
            index_path = root / 'dashboard/index.json'; prior = index_path.read_bytes()
            index = json.loads(prior); entry = index['sources']['mag_prices_history_novillos']
            self.assertEqual(entry['capture_mode'], 'multi_capture')
            self.assertEqual(validate_entry(root / 'dashboard', entry), len(rows))
            stored, _ = mag.read_entry_rows(root, 'mag_prices_history_novillos')
            self.assertIn('provisional_source_statement', next(r for r in stored.values() if r['metric'] == 'price_average' and r['observation_date'] == '2022-05-17')['quality_flags'])
            self.assertTrue(mag.apply_detail_conditions_to_chart(root, 'mag_prices_history_novillos', {'2022-05-17': 'DEFINITIVE'}))
            cleared, _ = mag.read_entry_rows(root, 'mag_prices_history_novillos')
            self.assertNotIn('provisional_source_statement', next(r for r in cleared.values() if r['metric'] == 'price_average' and r['observation_date'] == '2022-05-17')['quality_flags'])
            prior = index_path.read_bytes()
            invalid = [dict(row) for row in rows]; invalid[0]['value'] = 'NaN'
            with self.assertRaises(DataError):
                mag.publish_source(root, 'mag_prices_history_novillos', mag.CHART_URL,
                    'mag_daily_category_average', invalid, manifest(b'new capture'))
            self.assertEqual(index_path.read_bytes(), prior)

    def test_detail_snapshot_replaces_previous_report_day(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'dashboard').mkdir()
            first_body = detail_html(day='17/05/2022')
            first_rows, _ = mag.parse_detail(first_body, date(2022, 5, 17), 'mag_prices_detail', manifest(first_body))
            mag.publish_source(root, 'mag_prices_detail', mag.DETAIL_URL,
                'mag_daily_category_detail_latest', first_rows, manifest(first_body), replace_source=True)
            second_body = detail_html(day='18/05/2022')
            second_rows, _ = mag.parse_detail(second_body, date(2022, 5, 18), 'mag_prices_detail', manifest(second_body))
            status, _entry = mag.publish_source(root, 'mag_prices_detail', mag.DETAIL_URL,
                'mag_daily_category_detail_latest', second_rows, manifest(second_body), replace_source=True)
            stored, _entry = mag.read_entry_rows(root, 'mag_prices_detail')
            self.assertEqual(status, 'UPDATED')
            self.assertEqual(len(stored), len(second_rows))
            self.assertEqual({row['observation_date'] for row in stored.values()}, {'2022-05-18'})

    def test_status_codes_preserve_last_valid_bundle_on_nonupdate_states(self):
        for state in ('NO_PUBLICATION', 'SOURCE_UNAVAILABLE', 'PIPELINE_ERROR'):
            with self.subTest(state=state):
                row = mag.status_record(state, 'source condition', True)
                self.assertEqual(row['status'], state)
                self.assertTrue(row['last_valid_preserved'])

    def test_source_outage_records_status_without_replacing_last_valid_bundle(self):
        body = chart_json(); captured = manifest(body)
        rows = mag.parse_chart(body, '1', 'mag_prices_history_novillos', captured, date(2022, 5, 18))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'dashboard').mkdir()
            mag.publish_source(root, 'mag_prices_history_novillos', mag.CHART_URL, 'mag_daily_category_average', rows, captured)
            index_path = root / 'dashboard/index.json'; prior = index_path.read_bytes()
            with patch.object(mag, 'capture_bundle', side_effect=mag.SourceUnavailable('test HTTP outage')):
                result = mag.update(root, ASOF, allow_web=True)
            self.assertEqual(result, 0)
            self.assertEqual(index_path.read_bytes(), prior)
            status = json.loads((root / 'reports/CARNES_UPDATE_STATUS.json').read_bytes())['sources']
            self.assertEqual(status['mag_prices_history_novillos']['status'], 'SOURCE_UNAVAILABLE')
            self.assertTrue(status['mag_prices_history_novillos']['last_valid_preserved'])
            self.assertEqual(status['mag_prices_history_vacas']['status'], 'SOURCE_UNAVAILABLE')
            self.assertFalse(status['mag_prices_history_vacas']['last_valid_preserved'])
            with patch.object(mag, 'capture_bundle', side_effect=DataError('changed source schema')):
                result = mag.update(root, ASOF, allow_web=True)
            self.assertEqual(result, 1)
            self.assertEqual(index_path.read_bytes(), prior)
            status = json.loads((root / 'reports/CARNES_UPDATE_STATUS.json').read_bytes())['sources']
            self.assertEqual(status['mag_prices_history_novillos']['status'], 'PIPELINE_ERROR')
            self.assertTrue(status['mag_prices_history_novillos']['last_valid_preserved'])


if __name__ == '__main__':
    unittest.main()
