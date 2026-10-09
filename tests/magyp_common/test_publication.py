import tempfile
import unittest
from pathlib import Path
from scripts.magyp.grains import references as r
from scripts.magyp.grains import validate_publication as p


class PublicationTests(unittest.TestCase):
    def seed(self, root):
        for source in r.SOURCES:
            row = r.observation(source, '2026-10-08', 'Fixture', 'Fixture plaza',
                'Fixture reference', 'Sin identificar', 'Sin identificar', '100', 'json')
            row.update(capture_id='fixture', updated_at_utc='2026-10-09T12:00:00Z',
                raw_sha256='a' * 64, record_id=r.identity([source, 'fixture']))
            r.atomic(root / 'dashboard' / 'commodities' / f'{source}.csv', r.bundle([row], source))

    def test_all_five_outputs_validated_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.seed(root)
            before = {path: path.read_bytes() for path in root.rglob('*.csv')}
            p.validate_outputs(root)
            self.assertEqual(before, {path: path.read_bytes() for path in root.rglob('*.csv')})

    def test_one_missing_empty_corrupt_wrong_family_or_large_output_blocks_publication(self):
        for failure in ['missing', 'empty', 'schema', 'wrong_family', 'oversized']:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); self.seed(root)
                path = root / 'dashboard' / 'commodities' / 'fob.csv'
                if failure == 'missing': path.unlink()
                elif failure == 'empty': path.write_bytes(b'')
                elif failure == 'schema': path.write_bytes(b'unknown')
                elif failure == 'wrong_family': path.write_bytes((path.parent / 'board.csv').read_bytes())
                before = {file: file.read_bytes() for file in root.rglob('*.csv')}
                with self.assertRaises(r.Error):
                    p.validate_outputs(root, max_bytes=1 if failure == 'oversized' else p.MAX_DASHBOARD_BYTES)
                self.assertEqual(before, {file: file.read_bytes() for file in root.rglob('*.csv')})

    def test_allowlist_never_stages_raw_secrets_frontend_or_other_modules(self):
        p.validate_staged_paths([])
        p.validate_staged_paths(p.PUBLICATION_FILES)
        for path in ['data/magyp/raw/commodities/fob/response.json', '.env', 'app.js',
                'data/magyp/dashboard/mcba/MCBA_MAGYP_DAILY.csv', 'temp.csv']:
            with self.subTest(path=path), self.assertRaises(r.Error):
                p.validate_staged_paths([*p.PUBLICATION_FILES, path])


if __name__ == '__main__':
    unittest.main()
