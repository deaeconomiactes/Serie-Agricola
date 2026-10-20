import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from scripts.magyp.common.platform import sha256
from scripts.mercado_central import audit_history as audit, discover_history as discovery


class HistoryTests(unittest.TestCase):
    def candidate(self, price='1.22', currency='USD'):
        headers = ['pais_id','pais','mercado','año','mes','producto','variedad','origen',
                   'precio_usd_kg','moneda_cod','moneda']
        out = io.StringIO(); writer = csv.writer(out)
        writer.writerow(headers)
        writer.writerow(['32','Argentina','Mercado Central de Buenos Aires','2017','Enero',
                         'Ananá','Perola','Brasil',price,currency,'Dolares'])
        payload = out.getvalue().encode('cp1252')
        manifest = dict(sha256=sha256(payload), url='https://datos.magyp.gob.ar/file.csv',
                        captured_at_utc='2026-10-20T12:00:00Z')
        return payload, manifest

    def test_usd_history_preserves_originals_and_is_never_relabelled_ars(self):
        body, manifest = self.candidate()
        row = audit.candidate_usd(body, manifest)[0]
        self.assertEqual(row['date'], '2017-01-01')
        self.assertEqual(row['currency'], 'USD')
        self.assertEqual(row['raw_fields']['precio_usd_kg'], '1.22')
        self.assertEqual(row['quality_status'], 'EXCLUDED_FROM_ARS_RUNTIME')
        self.assertEqual(row['raw_sha256'], sha256(body))

    def test_missing_and_zero_candidate_prices_are_preserved_not_invented(self):
        for value, expected in [('', None), ('0', 0.)]:
            row = audit.candidate_usd(*self.candidate(value))[0]
            self.assertEqual(row['price'], expected)
            self.assertFalse(row['price_available'])

    def test_candidate_schema_currency_and_hash_changes_fail_closed(self):
        body, manifest = self.candidate(currency='ARS')
        with self.assertRaises(ValueError): audit.candidate_usd(body, manifest)
        body, manifest = self.candidate()
        with self.assertRaises(ValueError): audit.candidate_usd(body+b'x', manifest)

    def test_comparison_excludes_ambiguous_quotes_and_keeps_daily_semantics(self):
        base = dict(date='2026-01-02',type='Frutas',product_normalized='MANZANA',
                    variety_normalized='',origin_normalized='BRASIL',package_normalized='CAJA',price='10')
        old = dict(fecha='2026-01-02',rubro='Frutas',especie='Manzana',variedad='',
                   procedencia='Brasil',envase='CA',unidad='$/kg',precio_kg_estimado='10')
        result = audit.compare_daily([base], [old])
        self.assertEqual(result['unambiguous_pairs'], 1)
        self.assertEqual(result['within_one_percent'], 1)
        result = audit.compare_daily([base, {**base,'price':'20'}], [old])
        self.assertEqual(result['ambiguous_keys'], 1)
        self.assertEqual(result['unambiguous_pairs'], 0)
        self.assertEqual(audit.compare_daily([base], [{**old,'fecha_precision':'mensual'}])['shared_keys'], 0)

    def test_discovery_rejects_external_links_and_session_parameters(self):
        for url in ['https://other.invalid/data.zip', discovery.PAGE+'?token=secret',
                    'https://mercadocentral.gob.ar/%2e%2e/data.zip']:
            with self.assertRaises(ValueError): discovery.safe(url)
        self.assertEqual(discovery.safe(discovery.SITEMAP), discovery.SITEMAP)

    def test_bounded_discovery_follows_links_and_never_retries_directory_403(self):
        zip_url = 'https://mercadocentral.gob.ar/sites/default/files/precios_mayoristas/FRUTAS_ENERO_2026.zip'
        bodies = {
            discovery.PAGE: f'<a href="{zip_url}">ZIP</a>'.encode(),
            discovery.SITEMAP: b'<sitemapindex><sitemap><loc>https://mercadocentral.gob.ar/sitemap.xml?page=1</loc></sitemap></sitemapindex>',
            'https://mercadocentral.gob.ar/sitemap.xml?page=1': b'<urlset/>',
            discovery.PORTAL: b'<html>Sin recurso</html>',
        }
        calls = []
        class Response(io.BytesIO):
            status = 200
            headers = {'Content-Type':'text/html'}
        def request(req, **kwargs):
            url = req.full_url; calls.append(url)
            if url.endswith('/precios_mayoristas/'):
                raise HTTPError(url,403,'Forbidden',None,None)
            result = Response(bodies[url]); result.url = url
            return result
        with tempfile.TemporaryDirectory() as tmp, patch.object(discovery,'urlopen',side_effect=request), patch.object(discovery.time,'sleep'):
            result = discovery.collect(Path(tmp), True)
        self.assertEqual(len(result['current_zip_publications']), 1)
        self.assertEqual(result['request_count'], 5)
        self.assertEqual(sum(u.endswith('/precios_mayoristas/') for u in calls), 1)
        self.assertFalse(any(u.endswith('.zip') for u in calls))
        self.assertTrue(any(r['http_status']==403 for r in result['requests']))

    def test_real_inventory_does_not_authorize_cutover_without_coverage(self):
        report = json.loads((audit.ROOT/'data/mercado_central/reports/MCBA_HISTORY_INVENTORY.json').read_text(encoding='utf-8'))
        self.assertFalse(report['cutover']['can_retire_mcba_legacy'])
        self.assertEqual(report['cutover']['legacy_monthly_history_still_needed_pct'],100.)
        self.assertTrue(all(not y['compatible_months_available'] for y in report['inventory'] if y['year']<2026))
        self.assertEqual(len(report['cutover']['remaining_legacy_monthly_periods']),24)
