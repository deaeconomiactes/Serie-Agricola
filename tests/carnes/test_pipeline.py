import csv
import io
import json
import tempfile
import unittest
from datetime import date
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from scripts.carnes import csv_sources as c, pipeline as p
from scripts.carnes.model import DataError, observation
from scripts.carnes.validate import validate

ASOF=date(2026,10,22)
SPEC=dict(source_id='test_sspm',source='SAGyP / SSPM',url='https://infra.datos.gob.ar/test.csv',
    kind='sspm_faena',frequency='monthly',units={k:'Cabezas' if k.endswith('cabezas') else 'Toneladas' for k in c.SSPM_COLUMNS[1:]})


def payload(rows=None,columns=c.SSPM_COLUMNS):
    stream=io.StringIO();writer=csv.writer(stream,lineterminator='\n');writer.writerow(columns)
    writer.writerows(rows or [['1980-01-01','100.25','','0','50','20','','']])
    return stream.getvalue().encode()


class Response:
    status=200
    headers=Message();headers['Content-Type']='text/csv; charset=UTF-8'
    def __init__(self,body):self.body=body
    def read(self,limit):return self.body[:limit]
    def __enter__(self):return self
    def __exit__(self,*args):pass


class CSVTests(unittest.TestCase):
    def test_missing_zero_fractional_values_and_original_units(self):
        rows=c.parse_csv(payload(),SPEC,ASOF)
        self.assertEqual(rows[0]['value'],'100.25')
        self.assertIn('fractional_count_published',rows[0]['quality_flags'])
        self.assertEqual(rows[1]['value'],None)
        self.assertEqual(rows[2]['value'],'0')
        self.assertEqual(rows[1]['unit'],'Toneladas')
        self.assertEqual(rows[1]['weight_basis'],'NOT_IDENTIFIED')

    def test_strict_schema_future_duplicate_invalid_numbers(self):
        for body in [payload(columns=[*c.SSPM_COLUMNS,'new']),
                payload([['2027-01-01']+['1']*7]),payload([['2026-10-02']+['1']*7]),
                payload([['2026-01-01']+['1']*7]*2),payload([['2026-01-01','NaN']+['1']*6]),
                payload([['2026-01-01','-1']+['1']*6]),payload([['2026-01-01','12x']+['1']*6])]:
            with self.subTest(body=body),self.assertRaises(DataError):c.parse_csv(body,SPEC,ASOF)

    def test_historical_prices_exports_and_weights_remain_separate_without_conversion(self):
        body=payload([['1998-01']+['10.50']*13],c.INDICATOR_COLUMNS)
        rows=c.parse_csv(body,{'kind':'bovine_indicators'},ASOF)
        self.assertEqual(len(rows),10)
        prices=[r for r in rows if r['family']=='livestock_price']
        self.assertEqual({r['currency'] for r in prices},{'ARS','USD'})
        self.assertEqual({r['value'] for r in rows},{'10.50'})
        exports=[r for r in rows if r['family']=='exports']
        self.assertEqual(len(exports),3)
        self.assertEqual({r['weight_basis'] for r in exports},{'NOT_APPLICABLE','carcass_equivalent_with_bone'})
        self.assertFalse(any('consumo' in r['metric'] for r in rows))


class PipelineTests(unittest.TestCase):
    def capture(self,root,body):
        with patch.object(p,'build_opener') as opener:
            opener.return_value.open.return_value=Response(body)
            return p.CaptureClient(root).get(SPEC['source_id'],SPEC['url'],'csv')

    def test_immutable_capture_manifest_and_replay_idempotence(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            _,first=self.capture(root,payload());_,second=self.capture(root,payload())
            self.assertNotEqual(first['capture_id'],second['capture_id'])
            self.assertEqual(first['raw_sha256'],second['raw_sha256'])
            self.assertNotIn('headers',first)
            self.assertEqual(p.build_source(root,SPEC,ASOF),'UPDATED')
            index=(root/'dashboard/index.json').read_bytes()
            self.assertEqual(validate(root/'dashboard'),6)
            self.assertEqual(p.build_source(root,SPEC,ASOF),'NO_OP_ALREADY_CURRENT')
            self.assertEqual(index,(root/'dashboard/index.json').read_bytes())

    def test_broken_new_schema_and_raw_hash_keep_last_valid_dashboard(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.capture(root,payload());p.build_source(root,SPEC,ASOF)
            path=root/'dashboard/index.json';prior=path.read_bytes()
            self.capture(root,b'unknown,columns\n1,2\n')
            with self.assertRaises(DataError):p.build_source(root,SPEC,ASOF)
            self.assertEqual(path.read_bytes(),prior)
            manifest=sorted((root/'raw/test_sspm').glob('*/manifest.json'))[-1]
            (manifest.parent/'response.csv').write_bytes(b'tampered')
            with self.assertRaises(DataError):p.build_source(root,SPEC,ASOF)
            self.assertEqual(path.read_bytes(),prior)

    def test_corrupt_prepared_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.capture(root,payload());p.build_source(root,SPEC,ASOF)
            index=json.loads((root/'dashboard/index.json').read_bytes())
            filename=index['sources']['test_sspm']['files'][0]['path']
            (root/'dashboard'/filename).write_bytes(b'bad')
            with self.assertRaises(DataError):validate(root/'dashboard')

    def test_url_allowlist_and_private_parameters(self):
        for url in ['http://infra.datos.gob.ar/test','https://evil.test/a','https://www.magyp.gob.ar/a?token=x',
                'https://user:secret@infra.datos.gob.ar/a','https://infra.datos.gob.ar/a#fragment']:
            with self.assertRaises(DataError):p.public_url(url)

    def test_duplicate_observations_never_publish(self):
        manifest=dict(capture_id='c1',capture_date='2026-10-22T12:00:00Z',raw_sha256='a'*64)
        rows=c.parse_csv(payload(),SPEC,ASOF)
        with self.assertRaises(DataError):p.enrich([rows[0],dict(rows[0])],SPEC,manifest,ASOF)

    def test_value_and_status_must_agree(self):
        manifest=dict(capture_id='c1',capture_date='2026-10-22T12:00:00Z',raw_sha256='a'*64)
        for value,status in [('', 'observed'),(None,'observed'),('1','missing'),('1','unknown')]:
            row=c.parse_csv(payload(),SPEC,ASOF)[0]
            row.update(value=value,value_status=status)
            with self.subTest(value=value,status=status),self.assertRaises(DataError):
                p.enrich([row],SPEC,manifest,ASOF)

    def test_prepared_observed_empty_is_rejected_even_with_valid_hash(self):
        import gzip
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.capture(root,payload());p.build_source(root,SPEC,ASOF)
            path=root/'dashboard/index.json';index=json.loads(path.read_bytes())
            item=index['sources']['test_sspm']['files'][0];shard=root/'dashboard'/item['path']
            rows=list(csv.DictReader(io.StringIO(gzip.decompress(shard.read_bytes()).decode())))
            rows[0].update(value='',value_status='observed')
            for row in rows:row['quality_flags']=json.loads(row['quality_flags'])
            body=gzip.compress(p.csv_bytes(rows),mtime=0);shard.write_bytes(body)
            item.update(bytes=len(body),sha256=p.digest(body));path.write_bytes(p.encoded(index))
            with self.assertRaisesRegex(DataError,'nonempty'):validate(root/'dashboard')

    def test_discovery_outage_uses_validated_catalog_and_continues_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'catalog').mkdir()
            (root/'catalog/sources.json').write_bytes(p.encoded({'schema_version':p.VERSION,'sources':[SPEC]}))
            with patch('sys.argv',['pipeline','run','--data-root',temp,'--allow-web']),\
                    patch.object(p,'discover',side_effect=p.SourceUnavailable('HTTP 503')),\
                    patch.object(p.CaptureClient,'get'),patch.object(p,'build_source',return_value='UPDATED') as build,\
                    patch.object(p,'inventory'):
                self.assertEqual(p.main(),0);build.assert_called_once()
            state=json.loads((root/'reports/CARNES_UPDATE_STATUS.json').read_bytes())
            self.assertEqual(state['discovery']['status'],'SOURCE_UNAVAILABLE')
            self.assertTrue(state['discovery']['used_existing_catalog'])
            self.assertEqual(state['sources']['test_sspm']['status'],'UPDATED')

    def test_discovery_outage_without_cache_and_invalid_cache(self):
        for cached,expected in [(None,0),({'schema_version':'unknown','sources':[]},1)]:
            with self.subTest(cached=cached),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)
                if cached:
                    (root/'catalog').mkdir();(root/'catalog/sources.json').write_bytes(p.encoded(cached))
                with patch('sys.argv',['pipeline','run','--data-root',temp,'--allow-web']),\
                        patch.object(p,'discover',side_effect=p.SourceUnavailable('timeout')),\
                        patch.object(p,'build_source') as build:
                    self.assertEqual(p.main(),expected);build.assert_not_called()
                state=json.loads((root/'reports/CARNES_UPDATE_STATUS.json').read_bytes())
                self.assertEqual(state['discovery']['status'],'PIPELINE_ERROR' if expected else 'SOURCE_UNAVAILABLE')

    def test_discovery_schema_error_never_silently_reuses_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'catalog').mkdir()
            path=root/'catalog/sources.json';prior=p.encoded({'schema_version':p.VERSION,'sources':[SPEC]})
            path.write_bytes(prior)
            with patch('sys.argv',['pipeline','run','--data-root',temp,'--allow-web']),\
                    patch.object(p,'discover',side_effect=DataError('official schema changed')),\
                    patch.object(p,'build_source') as build:
                self.assertEqual(p.main(),1);build.assert_not_called()
            self.assertEqual(path.read_bytes(),prior)
            state=json.loads((root/'reports/CARNES_UPDATE_STATUS.json').read_bytes())
            self.assertEqual(state['discovery']['status'],'PIPELINE_ERROR')

    def test_dry_run_never_accesses_network(self):
        with patch('sys.argv',['pipeline','run']),patch.object(p.CaptureClient,'get') as get:
            self.assertEqual(p.main(),0);get.assert_not_called()

    def test_only_one_writer_can_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with p.writer_lock(root):
                with self.assertRaises(DataError):
                    with p.writer_lock(root):pass
            self.assertFalse((root/'.writer.lock').exists())

    def test_one_source_failure_does_not_stop_independent_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);other={**SPEC,'source_id':'other'}
            catalog={'schema_version':p.VERSION,'sources':[SPEC,other]}
            with patch('sys.argv',['pipeline','run','--data-root',temp,'--allow-web']),\
                    patch.object(p,'discover',return_value=catalog),patch.object(p.CaptureClient,'get'),\
                    patch.object(p,'build_source',side_effect=[DataError('schema changed'),'UPDATED']) as build,\
                    patch.object(p,'inventory'):
                self.assertEqual(p.main(),1)
            self.assertEqual(build.call_count,2)
            state=json.loads((root/'reports/CARNES_UPDATE_STATUS.json').read_bytes())['sources']
            self.assertEqual(state['test_sspm']['status'],'PIPELINE_ERROR')
            self.assertEqual(state['other']['status'],'UPDATED')

    def test_source_outage_is_explicit_and_does_not_build_or_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);catalog={'schema_version':p.VERSION,'sources':[SPEC]}
            with patch('sys.argv',['pipeline','run','--data-root',temp,'--allow-web']),\
                    patch.object(p,'discover',return_value=catalog),\
                    patch.object(p.CaptureClient,'get',side_effect=p.SourceUnavailable('HTTP 503')),\
                    patch.object(p,'build_source') as build,patch.object(p,'inventory'):
                self.assertEqual(p.main(),0);build.assert_not_called()
            state=json.loads((root/'reports/CARNES_UPDATE_STATUS.json').read_bytes())['sources']['test_sspm']
            self.assertEqual(state['status'],'SOURCE_UNAVAILABLE')
            self.assertTrue(state['last_valid_preserved'])
