import csv
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TomatoAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, 'scripts/mayoristas/auditar_tomate_2026.py'], cwd=ROOT, check=True)
        with (ROOT / 'data/mayoristas/reports/TOMATE_2026_MATRIZ.csv').open(encoding='utf-8-sig', newline='') as stream:
            cls.rows = list(csv.DictReader(stream))

    def test_published_rows_and_origin_alias(self):
        self.assertEqual(len(self.rows), 1665)
        selected = [r for r in self.rows if r['procedencia_canonica_propuesta'] == 'Corrientes']
        self.assertEqual(Counter(r['mercado'] for r in selected), {
            'Mercado Central de Buenos Aires': 55, 'Mercado de Corrientes': 970})
        self.assertEqual({r['procedencia_actual'] for r in selected}, {'Corrientes'})
        self.assertEqual({r['procedencia_raw_disponible'].upper() for r in selected}, {'CTES.', 'CORRIENTES'})

    def test_conversion_audit_and_future_dates(self):
        selected = [r for r in self.rows if r['procedencia_canonica_propuesta'] == 'Corrientes']
        counts = Counter(r['conversion_verificable'] for r in selected)
        self.assertEqual(counts['Directa'], 55)
        self.assertEqual(counts['Estimada; peso informado en presentación'], 877)
        self.assertEqual(counts['Revisar'], 93)
        self.assertEqual(sum(r['fecha'] > '2026-10-29' for r in selected), 3)
        for row in selected:
            if row['conversion_verificable'].startswith('Estimada'):
                self.assertAlmostEqual(float(row['precio_kg']), float(row['precio_observado']) / float(row['kg_envase']), places=6)


if __name__ == '__main__':
    unittest.main()
