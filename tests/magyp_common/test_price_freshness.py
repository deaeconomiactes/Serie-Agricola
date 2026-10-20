import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from scripts.magyp import build_price_freshness as freshness
from scripts.magyp.grains import references

class FreshnessTests(unittest.TestCase):
    def test_report_separates_families_and_static_future_dates(self):
        original=freshness.read_csv
        def read(path,delimiter=';'):
            if path.name=='PRECIOS_MAYORISTAS_INTEGRADO.csv':
                return [{'mercado':'Mercado de Corrientes','fecha':'2025-10-05'},
                        {'mercado':'Mercado de Corrientes','fecha':'2099-12-25'},
                        {'mercado':'Mercado Central de Buenos Aires','fecha':'2025-10-01','fecha_precision':'mensual'}]
            return original(path,delimiter)
        with patch.object(freshness,'read_csv',side_effect=read),patch.object(freshness,'atomic_write') as write:
            result=freshness.build()
        sources={r['source_family']:r for r in result['sources']}
        self.assertEqual(len(sources),10)
        self.assertEqual(sources['corrientes']['last_observation_date'],'2025-10-05')
        self.assertEqual(sources['corrientes']['status'],'STATIC')
        self.assertFalse(sources['corrientes']['automatic_update'])
        self.assertIsNone(sources['corrientes']['last_successful_update'])
        self.assertEqual(sources['magyp_internal']['frequency'],'mensual')
        self.assertEqual(sources['magyp_fob']['currency'],['Sin identificar'])
        self.assertNotEqual(sources['mcba']['source_family'],sources['mcba_monthly']['source_family'])
        self.assertEqual(json.loads(write.call_args.args[1])['schema_version'],'price-freshness-v1')

    def test_explicit_failure_preserves_successful_dates(self):
        with patch.object(freshness,'atomic_write'):
            initial=freshness.build()
            state={'status':'SOURCE_UNAVAILABLE','requested_date':'2026-10-20','attempted_at':'2099-01-01T00:00:00Z'}
            result=freshness.build(mcba_status=state)
        previous=next(r for r in initial['sources'] if r['source_family']=='mcba')
        current=next(r for r in result['sources'] if r['source_family']=='mcba')
        self.assertEqual(current['status'],'SOURCE_UNAVAILABLE')
        self.assertEqual(current['last_successful_update'],previous['last_successful_update'])
        self.assertEqual(current['last_observation_date'],previous['last_observation_date'])

    def test_reference_states_are_independent_and_outputs_preserved(self):
        unavailable=references.Error('HTTP unavailable');unavailable.source_unavailable=True
        with TemporaryDirectory() as folder:
            root=Path(folder); target=root/'dashboard/commodities/fob.csv'
            target.parent.mkdir(parents=True); target.write_bytes(b'previous valid bundle')
            args=['references','--date','2026-10-20','--data-root',folder,'--source','all']
            with patch('sys.argv',args),patch.object(references,'run',side_effect=[
                'UPDATED',unavailable,'UPDATED','NO_PUBLICATION',references.Error('Schema changed')]):
                self.assertEqual(references.main(),1)
            actual=[json.loads((root/f'reports/PRICE_STATE_{source}.json').read_bytes())['status'] for source in references.SOURCES]
            self.assertEqual(actual,['UPDATED','SOURCE_UNAVAILABLE','UPDATED','NO_PUBLICATION','PIPELINE_ERROR'])
            self.assertEqual(target.read_bytes(),b'previous valid bundle')
