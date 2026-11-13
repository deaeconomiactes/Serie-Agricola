import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from scripts.carnes import bcra_rates as b


class Sheet:
    nrows = 6
    def cell_value(self, row, col):
        values = {(1, 2): 'Comunicación A 3500', (3, 2): 'Fecha', (3, 3): 'Referencia',
                  (4, 2): 44698.0, (4, 3): 117.0, (5, 2): 44699.0, (5, 3): 118.0}
        return values.get((row, col), '')


class Book:
    datemode = 0
    def sheet_by_name(self, name):
        if name != 'TCR diario y TCNPM': raise KeyError(name)
        return Sheet()


class BCRARatesTests(unittest.TestCase):
    def test_parse_official_layout_and_reject_wrong_signature(self):
        with patch.object(b.xlrd, 'open_workbook', return_value=Book()):
            rows = b.parse_workbook(bytes.fromhex('d0cf11e0a1b11ae1'), date(2026, 11, 13))
        self.assertEqual(rows, [['2022-05-17', 117.0], ['2022-05-18', 118.0]])
        with self.assertRaises(ValueError): b.parse_workbook(b'not xls')

    def test_unavailable_or_invalid_capture_preserves_last_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); target = root / 'dashboard/bcra_a3500.json'
            target.parent.mkdir(parents=True); target.write_text('last valid', encoding='utf-8')
            def unavailable(): raise URLError('offline')
            self.assertEqual(b.update(root, unavailable)['status'], 'SOURCE_UNAVAILABLE')
            self.assertEqual(target.read_text('utf-8'), 'last valid')
            self.assertEqual(b.update(root, lambda: b'invalid')['status'], 'PIPELINE_ERROR')
            self.assertEqual(target.read_text('utf-8'), 'last valid')
            raw = list((root / 'raw/bcra_a3500').glob('*/manifest.json'))
            self.assertEqual(len(raw), 1)
            self.assertEqual(json.loads(raw[0].read_text('utf-8'))['bytes'], 7)


if __name__ == '__main__': unittest.main()
