"""End-to-end regression for a monthly publication newer than committed shards."""
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts.mayoristas.build_dashboard import build, INPUTS, ROOT
from scripts.mercado_central.update_mcba_monthly import FILE, read_published


class CandidateUpdateTests(unittest.TestCase):
    def test_changed_monthly_publication_requires_and_passes_candidate_rebuild(self):
        with tempfile.TemporaryDirectory(prefix='mcba-candidate-') as temp:
            root = Path(temp) / 'repo'
            files = [*INPUTS, 'app.js', 'mcba-prices.js', 'mcba-monthly.js', 'mayoristas-loader.js',
                     'scripts/mayoristas/source_rows.cjs', 'scripts/mayoristas/normalize.cjs',
                     'scripts/mayoristas/validate_delivery.cjs', 'tests/magyp_frontend/mayoristas-delivery.test.cjs']
            for name in files:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, target)
            old = root / 'candidate-old'
            build(root, old, write_inventory=False)

            folder = root / 'data/mercado_central/dashboard/mcba'
            csv_path = folder / FILE
            with csv_path.open(encoding='utf-8', newline='') as stream:
                reader = csv.DictReader(stream)
                columns, rows = reader.fieldnames, list(reader)
            extra = dict(rows[0], product_raw='PRODUCTO CONTROL', product_normalized='PRODUCTO CONTROL',
                         observation_id=hashlib.sha256(b'candidate-update-regression').hexdigest())
            rows.append(extra)
            with csv_path.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
                writer.writeheader(); writer.writerows(rows)
            marker_path = folder / '_SUCCESS.json'
            marker = json.loads(marker_path.read_text(encoding='utf-8'))
            marker['record_count'] = len(rows)
            marker['files'][FILE] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
            marker_path.write_text(json.dumps(marker), encoding='utf-8')
            self.assertEqual(len(read_published(root / 'data/mercado_central')), len(rows))

            def check(candidate):
                env = dict(os.environ, MAYORISTAS_DELIVERY_ROOT=str(candidate), MAYORISTAS_CANDIDATE_SMOKE='1')
                return subprocess.run(['node', '--test', '--test-name-pattern=exact economic equivalence',
                    str(root / 'tests/magyp_frontend/mayoristas-delivery.test.cjs')], cwd=root,
                    env=env, capture_output=True, text=True, encoding='utf-8', timeout=360)

            stale = check(old)
            self.assertNotEqual(stale.returncode, 0, stale.stdout + stale.stderr)
            self.assertIn('exact row order/content', stale.stdout + stale.stderr)
            current = root / 'candidate-new'
            build(root, current, write_inventory=False)
            updated = check(current)
            self.assertEqual(updated.returncode, 0, updated.stdout + updated.stderr)


if __name__ == '__main__':
    unittest.main()
