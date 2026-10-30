import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from scripts.mayoristas.build_dashboard import build, INPUTS, ROOT
from scripts.ci.prepare_pages import prepare


class DeliveryBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)/'repo';self.root.mkdir()
        for name in INPUTS:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text('a;b\n1;2\n' if name.endswith('.csv') else '{}',encoding='utf-8')
        row=dict(fecha='2026-01-01',year=2026,mercado='Mercado de Corrientes',data_source='LEGACY',
                 fechaPrecision='diaria',precioObservado=100,unidadPrecioObservado='$/bulto',precioKgEstimado=None)
        self.source={'views':{f:[row] for f in ['diaria','mensual','anual']},'metadata':{'magypPriceInfo':{'updated_at':'2026-01-01'}}}

    def generate(self):
        with patch('scripts.mayoristas.build_dashboard.subprocess.run',return_value=SimpleNamespace(stdout=json.dumps(self.source))):
            return build(self.root)

    def test_deterministic_build_preserves_types_counts_currency_unknown_and_originals(self):
        before={n:(self.root/n).read_bytes() for n in INPUTS}
        first=self.generate();folder=self.root/'data/mayoristas/dashboard'
        contents={p.name:p.read_bytes() for p in folder.iterdir()}
        self.assertEqual(first,self.generate())
        self.assertEqual(contents,{p.name:p.read_bytes() for p in folder.iterdir()})
        for f in first['fragments']:
            body=(folder/f['path']).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(),f['sha256'])
            self.assertEqual(len(body),f['bytes'])
            self.assertEqual(f['currency'],['Sin identificar'])
            rows=json.loads(gzip.decompress(body));self.assertIsNone(rows[0]['precioKgEstimado'])
            self.assertEqual(rows[0]['precioObservado'],100)
        self.assertEqual(before,{n:(self.root/n).read_bytes() for n in INPUTS})

    def test_invalid_or_empty_source_preserves_previous_index(self):
        self.generate();index=self.root/'data/mayoristas/dashboard/index.json';previous=index.read_bytes()
        self.source['views']['mensual']=[]
        with self.assertRaises(ValueError):self.generate()
        self.assertEqual(previous,index.read_bytes())

    def test_temporary_candidate_does_not_modify_active_index_or_inventory(self):
        self.generate()
        active=self.root/'data/mayoristas/dashboard/index.json'
        inventory=self.root/'data/mayoristas/reports/LOAD_INVENTORY.json'
        before=(active.read_bytes(),inventory.read_bytes())
        output=Path(self.temporary.name)/'candidate'
        self.source['views']['mensual'][0]['precioObservado']=125
        with patch('scripts.mayoristas.build_dashboard.subprocess.run',return_value=SimpleNamespace(stdout=json.dumps(self.source))):
            result=build(self.root, output=output, write_inventory=False)
        self.assertEqual((active.read_bytes(),inventory.read_bytes()),before)
        self.assertTrue((output/'index.json').exists())
        self.assertEqual(result['row_counts']['mensual'],1)

    def test_builder_reads_complete_node_output_from_temporary_file(self):
        def run(*args, **kwargs):
            if 'stdout' in kwargs:
                kwargs['stdout'].write(json.dumps(self.source).encode('utf-8'))
            return SimpleNamespace(stdout=None)
        with patch('scripts.mayoristas.build_dashboard.subprocess.run',side_effect=run):
            result=build(self.root, write_inventory=False)
        self.assertEqual(result['row_counts'],{'diaria':1,'mensual':1,'anual':1})

    def test_atomic_index_replace_failure_preserves_last_valid(self):
        self.generate();index=self.root/'data/mayoristas/dashboard/index.json';previous=index.read_bytes()
        import os
        real=os.replace
        def replace(a,b):
            if Path(b)==index:raise OSError('fixture disk failure')
            return real(a,b)
        with patch('scripts.mayoristas.build_dashboard.os.replace',side_effect=replace),self.assertRaises(OSError):self.generate()
        self.assertEqual(previous,index.read_bytes())
        self.assertFalse(list(index.parent.glob('.index-*')))

    def test_candidate_browser_contract_failure_does_not_activate_new_index(self):
        self.generate();index=self.root/'data/mayoristas/dashboard/index.json';previous=index.read_bytes()
        import subprocess
        with patch('scripts.mayoristas.build_dashboard.subprocess.run',side_effect=[
            SimpleNamespace(stdout=json.dumps(self.source)),subprocess.CalledProcessError(1,['validate_delivery'])
        ]),self.assertRaises(subprocess.CalledProcessError):
            build(self.root)
        self.assertEqual(index.read_bytes(),previous)
        self.assertFalse(list(index.parent.glob('.index-*')))

    def test_pages_only_publishes_referenced_shards_and_keeps_build_inputs_in_repo(self):
        result=self.generate();folder=self.root/'data/mayoristas/dashboard'
        (folder/'obsolete.json.gz').write_bytes(b'old')
        other=self.root/'data/magyp/dashboard/commodities/internal.csv';other.parent.mkdir(parents=True,exist_ok=True);other.write_text('untouched')
        destination=Path(self.temporary.name)/'pages';prepare(self.root,destination)
        self.assertFalse((destination/'PRECIOS_MAYORISTAS_INTEGRADO.csv').exists())
        self.assertFalse((destination/'data/magyp/dashboard/mcba').exists())
        self.assertFalse((destination/'data/mercado_central').exists())
        self.assertFalse((destination/'data/mayoristas/dashboard/obsolete.json.gz').exists())
        self.assertEqual((destination/other.relative_to(self.root)).read_text(),'untouched')
        self.assertTrue((self.root/'PRECIOS_MAYORISTAS_INTEGRADO.csv').exists())
        for f in result['fragments']:self.assertTrue((destination/'data/mayoristas/dashboard'/f['path']).exists())

    def test_real_index_and_all_shards_reconcile(self):
        folder=ROOT/'data/mayoristas/dashboard';index=json.loads((folder/'index.json').read_text('utf-8'))
        for frequency,count in index['row_counts'].items():
            total=0;orders=[]
            for f in index['fragments']:
                if f['frequency']!=frequency:continue
                body=(folder/f['path']).read_bytes()
                self.assertEqual(hashlib.sha256(body).hexdigest(),f['sha256'])
                rows=json.loads(gzip.decompress(body));self.assertEqual(len(rows),f['row_count']);total+=len(rows)
                orders.extend(r['_runtime_order'] for r in rows)
            self.assertEqual(total,count);self.assertEqual(len(set(orders)),count)
        self.assertTrue({2024,2025,2026}.issubset(index['years']))

    def test_pages_excludes_sio_audit_evidence_without_removing_sources(self):
        reports=self.root/'data/commodities_sio/reports';reports.mkdir(parents=True)
        names=('SIO_GRAIN_AUDIT.json','CASOS_PRECIOS_CERO_SIO.csv')
        for name in names:(reports/name).write_text('audit evidence',encoding='utf-8')
        (reports/'runtime.json').write_text('{}',encoding='utf-8')
        destination=Path(self.temporary.name)/'pages';prepare(self.root,destination)
        for name in names:
            self.assertTrue((reports/name).exists())
            self.assertFalse((destination/'data/commodities_sio/reports'/name).exists())
        self.assertTrue((destination/'data/commodities_sio/reports/runtime.json').exists())


if __name__=='__main__':unittest.main()
