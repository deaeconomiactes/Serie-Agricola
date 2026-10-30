import csv
import unittest
from collections import Counter
from pathlib import Path

from scripts.mayoristas.auditar_dimensiones import abbreviation_candidate, key

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'data/mayoristas/reports'


def read(name):
    with (REPORT / name).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


class DimensionInventoryTest(unittest.TestCase):
    def test_inventory_accounts_for_each_dimension_and_view(self):
        rows = read('DIMENSIONES_MAYORISTAS_INVENTARIO.csv')
        totals = Counter()
        for row in rows:
            totals[(row['dimension'], row['frecuencia_vista'])] += int(row['count'])
        dimensions = {'producto', 'variedad', 'procedencia', 'mercado', 'unidad',
                      'envase', 'tamanio', 'calidad', 'grado'}
        self.assertEqual({dimension for dimension, _ in totals}, dimensions)
        # This is an audit snapshot, not a live delivery index. Every dimension
        # must account for the same snapshot rows in each frequency.
        for frequency in {'diaria','mensual','anual'}:
            counts = {totals[dimension, frequency] for dimension in dimensions}
            self.assertEqual(len(counts), 1)
            self.assertGreater(next(iter(counts)), 0)

    def test_ambiguous_abbreviations_are_candidates_not_equivalences(self):
        self.assertTrue(abbreviation_candidate('Ctes.', 'Corrientes'))
        self.assertTrue(abbreviation_candidate('E. Rios', 'Entre Ríos'))
        self.assertFalse(abbreviation_candidate('Corrientes', 'Corrientes'))
        self.assertEqual(key('Entre Ríos'), key('Entre Rios'))
        rows = read('PROCEDENCIAS_ABREVIATURAS_CANDIDATAS.csv')
        self.assertTrue(all(row['status'] == 'REVIEW_REQUIRED' for row in rows))

    def test_product_candidates_have_cross_row_evidence_and_review_status(self):
        rows = read('PRODUCTO_VARIEDAD_CANDIDATOS.csv')
        products = {row['producto_candidato'] for row in rows}
        self.assertGreaterEqual(len(products), 10)
        self.assertTrue(all(row['status'] == 'REVIEW_REQUIRED' and row['fuentes_evidencia'] for row in rows))


if __name__ == '__main__':
    unittest.main()
