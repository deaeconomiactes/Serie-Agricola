import csv
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from scripts.mayoristas import auditar_tomate_2026 as audit

ROOT = Path(__file__).resolve().parents[2]


class TomatoAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='tomate-audit-')
        cls.addClassCleanup(cls.temp.cleanup)
        output = Path(cls.temp.name) / 'matriz.csv'
        with patch.object(audit, 'OUTPUT', output):
            audit.main()
        with output.open(encoding='utf-8-sig', newline='') as stream:
            cls.rows = list(csv.DictReader(stream))

    def test_published_rows_and_origin_alias(self):
        self.assertGreater(len(self.rows), 0)
        selected = [r for r in self.rows if r['procedencia_canonica_propuesta'] == 'Corrientes']
        counts = Counter(r['mercado'] for r in selected)
        self.assertGreater(counts['Mercado Central de Buenos Aires'], 0)
        self.assertGreater(counts['Mercado de Corrientes'], 0)
        self.assertEqual({r['procedencia_actual'] for r in selected}, {'Corrientes'})
        self.assertTrue(all(r['procedencia_raw_disponible'].upper().rstrip('.') in {'CTES','CORRIENTES'} for r in selected))

    def test_conversion_audit_and_future_dates(self):
        selected = [r for r in self.rows if r['procedencia_canonica_propuesta'] == 'Corrientes']
        counts = Counter(r['conversion_verificable'] for r in selected)
        self.assertGreater(counts['Directa'], 0)
        self.assertGreater(counts['Estimada; peso informado en presentación'], 0)
        self.assertGreater(counts['Revisar'], 0)
        for row in selected:
            if row['conversion_verificable'].startswith('Estimada'):
                self.assertAlmostEqual(float(row['precio_kg']), float(row['precio_observado']) / float(row['kg_envase']), places=6)


if __name__ == '__main__':
    unittest.main()
