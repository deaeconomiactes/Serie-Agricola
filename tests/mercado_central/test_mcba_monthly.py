import io
import json
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from scripts.mercado_central import update_mcba_monthly as m
from scripts.magyp.common.platform import csv_bytes, publish_bundle, sha256

URL='https://mercadocentral.gob.ar/sites/default/files/precios_mayoristas/FRUTAS%20%20ENERO-26_0.zip'
DAY=date(2026,1,2)

def manifest(period='2026-01'):
    return {'type':'Frutas','period':period,'url':URL,'sha256':'a'*64,'capture_id':'capture-one',
        'captured_at_utc':'2026-10-20T12:00:00Z'}

def rows(price=100,name='RF020126.XLS',period='2026-01'):
    digits=name[2:8]
    values=[['ESP','VAR','PROC','ENV','KG','CAL','TAM','GRADO','MA'+digits,'MO'+digits,'MI'+digits,'MAPK','MOPK','MIPK'],
            ['MANZANA','RED DELICI','R. NEGRO','CA',18.,'EL','GRANDE','',price*20.,price*18.,price*16.,price+10.,float(price),price-10.]]
    sheet=SimpleNamespace(ncols=14,nrows=2,name='Sheet 1',row_values=lambda i:values[i])
    book=SimpleNamespace(nsheets=1,sheet_by_index=lambda i:sheet,release_resources=lambda:None)
    with patch('xlrd.open_workbook',return_value=book):
        return m.normalize_book(b'fixture',name,manifest(period),[])

def seed(root):
    month=m.monthly_view(rows(),date(2026,10,20))
    publish_bundle(root/'dashboard/mcba',{m.FILE:csv_bytes(month,list(m.MONTH_FIELDS))},len(month))
    return month

class MonthlyTests(unittest.TestCase):
    def test_discovery_uses_only_published_urls_and_typo_evidence(self):
        source='<a href="'+URL+'">January</a><a href="/sites/default/files/precios_mayoristas/HORTALIZA_SEPTIENBRE_26_0.zip">September</a>'
        links=m.discover(source,2026)
        self.assertEqual([(r['period'],r['type']) for r in links],[('2026-01','Frutas'),('2026-09','Hortalizas')])
        self.assertEqual(links[0]['url'],URL)
        self.assertEqual(m.discover(source,2025),[])
        with self.assertRaises(m.InvalidSource):m.discover('<a href="https://attacker.invalid/FRUTAS_ENERO_2026.zip">bad</a>',2026)
        with self.assertRaises(m.InvalidSource):m.allowed('https://mercadocentral.gob.ar/../../evil.zip')

    def test_archive_does_not_extract_or_process_unrelated_members(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            archive.writestr('RF020126.XLS',b'fixture')
            archive.writestr('../../evil.XLS',b'ignored')
            archive.writestr('Links/private.html',b'not inspected')
            archive.writestr('shortcut.lnk',b'not executed')
        members,ignored=m.inventory(stream.getvalue())
        self.assertEqual([r['name'] for r in members],['RF020126.XLS'])
        self.assertEqual(ignored,3)
        with self.assertRaises(m.InvalidSource):m.inventory(b'not a zip')

    def test_xls_preserves_raw_and_expands_only_official_codes(self):
        row=rows()[0]
        self.assertEqual(row['package_raw'],'CA');self.assertEqual(row['package_normalized'],'CAJA')
        self.assertEqual(row['quality_raw'],'EL');self.assertEqual(row['quality'],'Elegido')
        self.assertEqual(row['raw_fields']['MOPK'],100)
        self.assertEqual(row['price'],'100.0')
        self.assertEqual(row['price_unit'],'kg')
        self.assertEqual(row['currency_raw'],'')
        self.assertEqual(row['raw_sha256'],'a'*64)
        self.assertEqual(row['row_number'],2)

    def test_wrong_header_date_and_wrong_category_fail(self):
        with self.assertRaises(m.InvalidSource):rows(name='RH020126.XLS')
        with patch('xlrd.open_workbook',return_value=SimpleNamespace(nsheets=1,sheet_by_index=lambda i:SimpleNamespace(ncols=1,row_values=lambda i:['bad']))):
            with self.assertRaises(m.InvalidSource):m.normalize_book(b'bad','RF020126.XLS',manifest(),[])

    def test_cross_period_book_is_not_relabelled_by_zip_name(self):
        row=rows(name='RF040526.XLS',period='2026-04')[0]
        self.assertEqual(row['date'],'2026-05-04');self.assertEqual(row['period'],'2026-05')
        self.assertTrue(row['cross_period_member'])

    def test_monthly_is_day_balanced_mean_with_all_dimensions(self):
        first=rows()[0]; second={**first,'date':'2026-01-05','price':'200','raw_fields':{'MOPK':200},'member':'RF050126.XLS'}
        other={**first,'grade':'INV','grade_raw':'INV','price':'999','raw_fields':{'MOPK':999}}
        result=m.monthly_view([first,first,second,other],date(2026,1,20))
        common=next(r for r in result if not r['grade'])
        self.assertEqual(float(common['price']),150)
        self.assertEqual(common['observed_days'],2)
        self.assertEqual(len(result),2)
        self.assertIn('no volume weights',common['method'])
        self.assertEqual(common['period_status'],'observed_days_only')

    def test_multiple_quotes_and_summary_are_not_silently_lost_or_mixed(self):
        a=rows()[0]; b={**a,'price':'200','raw_fields':{'MOPK':200}}; c={**a,'date':'2026-01-05','price':'300','raw_fields':{'MOPK':300}}
        summary={**a,'observation_level':'species_summary','price':'9999'}
        result=m.monthly_view([a,b,c,summary],date(2026,1,20))[0]
        self.assertEqual(float(result['price']),225)
        self.assertEqual(result['multiple_quotes_days'],1)
        self.assertEqual(result['observation_count'],3)
        self.assertEqual(result['observed_days'],2)

    def test_future_dates_never_published(self):
        a=rows()[0];future={**a,'date':'2026-01-21','price':'9999','raw_fields':{'MOPK':9999}}
        result=m.monthly_view([a,future],date(2026,1,20))[0]
        self.assertEqual(float(result['price']),100)

    def test_failures_preserve_last_bundle_and_status(self):
        for error,status in [(m.SourceUnavailable('timeout'),'SOURCE_UNAVAILABLE'),(m.InvalidSource('schema'),'PIPELINE_ERROR')]:
            with self.subTest(status=status),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);seed(root)
                before={p.name:p.read_bytes() for p in (root/'dashboard/mcba').iterdir()}
                with patch.object(m,'request',side_effect=error):
                    with self.assertRaises(type(error)):m.run(root,2026,date(2026,10,20),True)
                self.assertTrue(all((root/'dashboard/mcba'/name).read_bytes()==body for name,body in before.items()))
                self.assertEqual(json.loads((root/'dashboard/mcba/UPDATE_STATUS.json').read_bytes())['status'],status)

    def test_no_links_is_no_publication_and_never_an_empty_csv(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'request',return_value=(b'<html></html>',{},200)):
            root=Path(temp);seed(root);before=(root/'dashboard/mcba'/m.FILE).read_bytes()
            self.assertEqual(m.run(root,2026,date(2026,10,20),True)['status'],'NO_PUBLICATION')
            self.assertEqual((root/'dashboard/mcba'/m.FILE).read_bytes(),before)

    def test_published_hash_is_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);seed(root);(root/'dashboard/mcba'/m.FILE).write_bytes(b'corrupt')
            with self.assertRaises(m.InvalidSource):m.read_published(root)

    def test_known_zip_fingerprints_noop_without_normalizing(self):
        payload=io.BytesIO()
        with zipfile.ZipFile(payload,'w') as z:z.writestr('RF020126.XLS',b'fixture')
        raw=payload.getvalue()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);seed(root);before=(root/'dashboard/mcba'/m.FILE).read_bytes()
            (root/'dashboard/mcba/SOURCE_INDEX.json').write_text(json.dumps({'fingerprints':{URL:sha256(raw)},'parser_version':m.PARSER_VERSION}))
            with patch.object(m,'request',side_effect=[(('<a href="'+URL+'">zip</a>').encode(),{},200),(raw,{},200)]),patch.object(m,'normalize_book') as normalize,patch.object(m.time,'sleep'):
                result=m.run(root,2026,date(2026,10,20),True)
                self.assertEqual(result['status'],'NO_OP_ALREADY_CURRENT');normalize.assert_not_called()
            self.assertEqual((root/'dashboard/mcba'/m.FILE).read_bytes(),before)
