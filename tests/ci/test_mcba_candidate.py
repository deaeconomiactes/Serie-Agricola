import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ci import mcba_candidate as candidate
from scripts.magyp.common.platform import PipelineError, publish_bundle
from scripts.magyp.mcba.update_mcba_dashboard import outputs_for

ROOT = Path(__file__).resolve().parents[2]


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.root = self.folder / 'main'
        self.published = self.root / candidate.PUBLISHED
        shutil.copytree(ROOT / candidate.PUBLISHED, self.published)
        # Minimal current-main inputs for the real freshness builder.
        inputs = [candidate.build_price_freshness.REPORT, 'PRECIOS_MAYORISTAS_INTEGRADO.csv',
            'data/commodities_local_mensual/dashboard/COMMODITIES_LOCAL_MENSUAL_DASHBOARD_RESUMEN.csv',
            'data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_RESUMEN.csv']
        inputs += [f'data/magyp/dashboard/commodities/{family}.csv' for family in
                   ('internal', 'board', 'fas', 'fob', 'futures')]
        for name in inputs:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        self.base = self.folder / 'baseline.json'
        # Real legacy marker also covers MONTHLY; baseline still exports five hashes.
        candidate.baseline(self.published, self.base)
        self.windows = self.folder / 'windows'
        shutil.copytree(self.published, self.windows)
        rows = candidate.read_bundle(self.windows)
        self.requested = max(r['date'] for r in rows)
        # Synthetic revision preserves the actual published schema and complete history.
        for row in rows:
            if row['date'] == self.requested:
                row['capture_timestamp'] = row['last_update'] = '2098-01-01T00:00:00Z'
                row['price'] = str(float(row['price']) + 1)
        publish_bundle(self.windows, outputs_for(rows), len(rows))
        self.state = {'result': 'UPDATED', 'source': 'MAGyP', 'source_url': candidate.URL,
            'source_status': 'MAGYP', 'requested_date': self.requested,
            'attempted_at': '2098-01-02T00:00:00Z', 'last_observation_date': self.requested,
            'last_successful_update': max(r['capture_timestamp'] for r in rows)}
        self.status = self.folder / 'MCBA_RUN_STATUS.json'
        self.artifact = self.folder / 'candidate'

    def pack(self):
        self.status.write_text(json.dumps(self.state), encoding='utf-8')
        candidate.pack(self.windows, self.base, self.status, self.artifact)

    def reject_unchanged(self):
        before = snapshot(self.root)
        with patch.object(candidate.build_price_freshness, 'build') as build:
            with self.assertRaises(PipelineError):
                candidate.apply(self.root, self.artifact)
            build.assert_not_called()
        self.assertEqual(snapshot(self.root), before)

    def test_baseline_conflict_writes_nothing(self):
        self.pack()
        marker = self.published / '_SUCCESS.json'
        marker.write_bytes(marker.read_bytes() + b'\n')
        self.reject_unchanged()

    def test_old_candidate_rejected_by_each_published_state(self):
        for place in ('status', 'freshness'):
            with self.subTest(place=place):
                if self.artifact.exists():
                    shutil.rmtree(self.artifact)
                self.pack()
                if place == 'status':
                    target = self.published / candidate.STATUS
                    old = target.read_bytes() if target.exists() else None
                    target.write_text(json.dumps({'attempted_at': '2099-01-01T00:00:00Z'}))
                else:
                    target = self.root / candidate.build_price_freshness.REPORT
                    old = target.read_bytes()
                    report = json.loads(old)
                    next(r for r in report['sources'] if r['source_family'] == 'mcba')['attempted_at'] = '2099-01-01T00:00:00Z'
                    target.write_text(json.dumps(report))
                self.reject_unchanged()
                if old is None:
                    target.unlink()
                else:
                    target.write_bytes(old)

    def test_corrupt_artifact_writes_nothing(self):
        self.pack()
        (self.artifact / 'payload' / candidate.BUNDLE[0]).write_bytes(b'corrupt')
        self.reject_unchanged()

    def test_mismatched_status_writes_nothing(self):
        self.pack()
        manifest_path = self.artifact / 'candidate.json'
        manifest = json.loads(manifest_path.read_bytes())
        manifest['run_status']['last_observation_date'] = '2000-01-01'
        manifest_path.write_text(json.dumps(manifest))
        self.reject_unchanged()

    def test_updated_only_bundle_status_and_freshness_change(self):
        # Another source was updated after Windows captured its baseline.
        report_path = self.root / candidate.build_price_freshness.REPORT
        report = json.loads(report_path.read_bytes())
        sio = next(r for r in report['sources'] if r['source_family'] == 'sio')
        sio.update(status='UPDATED', attempted_at='2099-01-01T00:00:00Z')
        report_path.write_text(json.dumps(report))
        self.pack()
        before = snapshot(self.root)
        candidate.apply(self.root, self.artifact)  # real build, real read_bundle
        after = snapshot(self.root)
        allowed = {(candidate.PUBLISHED / name).as_posix() for name in candidate.BUNDLE + (candidate.STATUS,)}
        allowed.add(candidate.build_price_freshness.REPORT)
        self.assertEqual({p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}, allowed)
        final = candidate.read_bundle(self.published)
        self.assertEqual(max(r['capture_timestamp'] for r in final), self.state['last_successful_update'])
        fresh = json.loads(report_path.read_bytes())
        preserved = next(r for r in fresh['sources'] if r['source_family'] == 'sio')
        self.assertEqual(preserved['status'], 'UPDATED')
        self.assertEqual(preserved['attempted_at'], '2099-01-01T00:00:00Z')
        self.assertEqual(json.loads((self.published / candidate.STATUS).read_bytes()), self.state)

    def test_build_failure_restores_every_byte_including_freshness(self):
        self.pack()
        before = snapshot(self.root)
        def fail(root, mcba_status):
            (root / candidate.build_price_freshness.REPORT).write_bytes(b'partial build')
            raise RuntimeError('synthetic failure')
        with patch.object(candidate.build_price_freshness, 'build', side_effect=fail):
            with self.assertRaises(RuntimeError):
                candidate.apply(self.root, self.artifact)
        self.assertEqual(snapshot(self.root), before)

    def test_nonupdated_is_status_only_and_preserves_bundle(self):
        rows = candidate.read_bundle(self.published)
        self.state.update(result='SOURCE_UNAVAILABLE', source_status='MAGYP_LAST_VALID',
            last_successful_update=max(r['capture_timestamp'] for r in rows))
        self.pack()
        self.assertEqual(set(snapshot(self.artifact)), {'candidate.json'})
        before = {name: (self.published / name).read_bytes() for name in candidate.BUNDLE}
        output = self.folder / 'github-output'
        with patch.dict('os.environ', {'GITHUB_OUTPUT': str(output)}):
            candidate.apply(self.root, self.artifact)
        self.assertEqual(output.read_text(), 'result=SOURCE_UNAVAILABLE\n')
        self.assertEqual({name: (self.published / name).read_bytes() for name in candidate.BUNDLE}, before)

    def test_unknown_result_and_unexpected_files_rejected(self):
        self.pack()
        (self.artifact / 'RAW.xlsx').write_bytes(b'not public')
        self.reject_unchanged()
        (self.artifact / 'RAW.xlsx').unlink()
        path = self.artifact / 'candidate.json'
        manifest = json.loads(path.read_bytes())
        manifest['run_status']['result'] = 'STATIC'
        path.write_text(json.dumps(manifest))
        self.reject_unchanged()


if __name__ == '__main__':
    unittest.main()
