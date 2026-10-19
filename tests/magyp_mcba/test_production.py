import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.magyp.common.platform import PipelineError, publish_bundle
from scripts.magyp.mcba import validate_production_mcba as guard
from scripts.magyp.mcba.update_mcba_dashboard import outputs_for, update
from test_publication import daily


class ProductionTests(unittest.TestCase):
    def seed(self, folder):
        publish_bundle(folder, outputs_for(daily()), len(daily()))
        state = {'source_status': 'MAGYP', 'requested_date': '2026-08-24',
                 'attempted_at': '2026-10-19T12:00:00Z'}
        (folder / guard.STATUS_FILE).write_text(json.dumps(state), encoding='utf8')

    def test_valid_bundle_and_explicit_publication_allowlist(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); self.seed(folder)
            self.assertEqual(guard.validate(folder, requested_date='2026-08-24'), len(daily()))
            guard.validate_staged([guard.PREFIX + name for name in guard.PUBLISH_FILES])
            for path in ['app.js', 'data/magyp/raw/mcba/response.xlsx',
                         guard.PREFIX + 'MCBA_MAGYP_MONTHLY.csv', '.env']:
                with self.subTest(path=path), self.assertRaises(PipelineError):
                    guard.validate_staged([path])

    def test_unavailable_magyp_preserves_all_csv_and_allows_only_last_valid_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'published'; self.seed(folder)
            before = {path.name: path.read_bytes() for path in folder.iterdir() if path.name != guard.STATUS_FILE}
            with patch('scripts.magyp.mcba.update_mcba_dashboard.browser_fetch', side_effect=PipelineError('HTTP unavailable')):
                with self.assertRaises(PipelineError):
                    update('2026-10-19', Path(temp) / 'capture', folder, True)
            self.assertTrue(all((folder / name).read_bytes() == body for name, body in before.items()))
            self.assertEqual(guard.validate(folder, True, '2026-10-19'), len(daily()))
            guard.validate_staged([guard.PREFIX + guard.STATUS_FILE], True)
            for name in (*guard.DATA_FILES, '_SUCCESS.json'):
                with self.subTest(name=name), self.assertRaises(PipelineError):
                    guard.validate_staged([guard.PREFIX + name], True)
            with self.assertRaises(PipelineError): guard.validate(folder, False)

    def test_invalid_bundle_status_or_limits_block_publication(self):
        for failure in ['empty', 'corrupt', 'missing_marker_entry', 'wrong_date', 'non_utc', 'oversized']:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp); self.seed(folder)
                marker = folder / '_SUCCESS.json'; status = folder / guard.STATUS_FILE
                if failure == 'empty': (folder / guard.DATA_FILES[0]).write_bytes(b'')
                elif failure == 'corrupt': (folder / guard.DATA_FILES[1]).write_bytes(b'corrupt')
                elif failure == 'missing_marker_entry':
                    obj = json.loads(marker.read_bytes()); del obj['files'][guard.DATA_FILES[1]]
                    marker.write_text(json.dumps(obj), encoding='utf8')
                elif failure in ['wrong_date', 'non_utc']:
                    obj = json.loads(status.read_bytes())
                    obj['requested_date' if failure == 'wrong_date' else 'attempted_at'] = '2026-10-18' if failure == 'wrong_date' else '2026-10-19T12:00:00'
                    status.write_text(json.dumps(obj), encoding='utf8')
                with patch.object(guard, 'MAX_FILE_BYTES', 1 if failure == 'oversized' else guard.MAX_FILE_BYTES):
                    with self.assertRaises(PipelineError): guard.validate(folder, requested_date='2026-08-24')


if __name__ == '__main__':
    unittest.main()
