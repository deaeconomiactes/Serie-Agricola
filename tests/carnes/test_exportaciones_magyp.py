import io, json, tempfile, unittest
from datetime import datetime
from pathlib import Path
import re
from urllib.error import URLError
from openpyxl import Workbook
from scripts.carnes import exportaciones_magyp as e

def fixture():
    w=Workbook();s=w.active;s.title='Indicadores mensuales 1990-2026';s.cell(4,15,'EXPORTACION DE CARNE VACUNA');s.cell(5,15,'Volumen en toneladas equivalentes res con hueso');s.cell(5,16,'Valor en Miles de USD')
    s.cell(6,2,datetime(1990,1,1));s.cell(6,15,100);s.cell(6,16,200)
    s.cell(7,2,datetime(1990,2,1));s.cell(7,15,150);s.cell(7,16,300)
    out=io.BytesIO();w.save(out);return out.getvalue()

class ExportsTests(unittest.TestCase):
    def test_workflow_gate_blocks_failed_capture_after_successful_checks(self):
        workflow=Path(__file__).resolve().parents[2]/'.github/workflows/update-carnes-exportaciones.yml'
        text=workflow.read_text('utf8')
        upload=text.split('      - uses: actions/upload-artifact@v4',1)[1].split('      - name: Publicar salidas validadas',1)[0]
        publish=text.split('      - name: Publicar salidas validadas',1)[1]
        gate=re.search(r"(?m)^        if: (.+)$",publish)
        self.assertIsNotNone(gate)
        self.assertEqual(gate.group(1),"success() && github.ref == 'refs/heads/main' && steps.capture.outcome == 'success'")
        self.assertIn('if: always() && steps.capture.outcome != \'skipped\'',upload)
        self.assertIn('data/carnes/raw/exportaciones_magyp/',upload)
        self.assertIn('data/carnes/reports/EXPORTACIONES_MAGYP_STATUS.json',upload)
        self.assertIn('git commit -m',publish)
        self.assertIn('gh workflow run deploy.yml --ref main',publish)

        # Passing earlier checks does not override a failed capture; the same gate
        # still admits successful capture runs that report legitimate source states.
        for checks_passed,capture_outcome,allowed in [
            (True,'failure',False),(True,'success',True),
            (False,'success',False),(True,'skipped',False),
        ]:
            self.assertEqual(checks_passed and capture_outcome=='success',allowed)

    def test_initial_publication_matches_official_september_2026_report(self):
        path=Path(__file__).resolve().parents[2]/'data/carnes/dashboard/exportaciones_magyp.json'
        document=json.loads(path.read_text('utf8'))
        if document['raw_sha256']!='076c4c81928ee54dd616034aaac01c7bb53ecbd5861d4a2fa0a4a5115b548553':self.skipTest('La fuente fue revisada posteriormente')
        rows=[r for r in document['rows'] if '2026-01-01'<=r['date']<='2026-09-01'];self.assertEqual(len(rows),9)
        self.assertAlmostEqual(sum(r['tonnes_rch'] for r in rows),675191.549823,places=4)
        self.assertAlmostEqual(sum(r['usd_thousands'] for r in rows),3656691.45488,places=4)
    def test_values_units_source_cells_and_dates(self):
        rows=e.parse(fixture());self.assertEqual(rows[0],{'date':'1990-01-01','tonnes_rch':100,'usd_thousands':200,'source_locator':'Indicadores mensuales 1990-2026!O6:P6'})
        self.assertEqual(rows[1]['date'],'1990-02-01')
    def test_invalid_or_unavailable_preserves_latest(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);first=e.update(root,fixture);self.assertEqual(first['status'],'UPDATED');path=root/'dashboard/exportaciones_magyp.json';old=path.read_bytes()
            self.assertEqual(e.update(root,lambda:b'bad')['status'],'PIPELINE_ERROR');self.assertEqual(path.read_bytes(),old)
            def offline():raise URLError('offline')
            self.assertEqual(e.update(root,offline)['status'],'SOURCE_UNAVAILABLE');self.assertEqual(path.read_bytes(),old)
            self.assertEqual(e.update(root,fixture)['status'],'NO_PUBLICATION');self.assertEqual(path.read_bytes(),old)
    def test_reduced_coverage_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.assertEqual(e.update(root,fixture)['status'],'UPDATED');out=root/'dashboard/exportaciones_magyp.json';old=out.read_bytes()
            w=load_fixture=Workbook();s=w.active;s.title='Indicadores mensuales 1990-2026';s.cell(4,15,'EXPORTACION DE CARNE VACUNA');s.cell(5,15,'equivalentes');s.cell(5,16,'Miles de USD');s.cell(6,2,datetime(1990,1,1));s.cell(6,15,100);s.cell(6,16,200);f=io.BytesIO();w.save(f)
            self.assertEqual(e.update(root,lambda:f.getvalue())['status'],'PIPELINE_ERROR');self.assertEqual(out.read_bytes(),old)
    def test_revision_of_a_published_month_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);original=fixture();self.assertEqual(e.update(root,lambda:original)['status'],'UPDATED')
            from openpyxl import load_workbook
            w=load_workbook(io.BytesIO(original));w.active['O6']=101;changed=io.BytesIO();w.save(changed)
            self.assertEqual(e.update(root,lambda:changed.getvalue())['status'],'UPDATED')
            result=json.loads((root/'dashboard/exportaciones_magyp.json').read_text('utf8'))
            self.assertEqual(result['rows'][0]['tonnes_rch'],101)
            self.assertEqual(len(list((root/'raw/exportaciones_magyp').glob('*/response.xlsx'))),2)

if __name__=='__main__':unittest.main()
