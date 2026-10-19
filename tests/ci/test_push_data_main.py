"""Real local Git remotes: racing writers, bounded retries and conflict abort."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from shlex import quote

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/ci/push_data_main.sh'
BASH = shutil.which('bash') or ('C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else None)


@unittest.skipUnless(BASH and Path(BASH).exists(), 'Bash required for publication integration tests')
class PushTests(unittest.TestCase):
    def git(self, *args, cwd=None):
        return subprocess.check_output(['git', *args], cwd=cwd or self.work,
            env=self.env, stderr=subprocess.DEVNULL, text=True).strip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='data-writer-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote.git'
        self.work = self.root / 'writer'
        self.side = self.root / 'other-writer'
        self.env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_AUTHOR_NAME': 'Fixture',
            'GIT_AUTHOR_EMAIL': 'fixture@example.invalid', 'GIT_COMMITTER_NAME': 'Fixture',
            'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}
        self.git('init', '--bare', '--initial-branch=main', self.remote.as_posix(), cwd=self.root)
        self.git('clone', self.remote.as_posix(), self.work.as_posix(), cwd=self.root)
        self.git('config', 'core.autocrlf', 'false')
        (self.work / 'seed.txt').write_text('seed\n', encoding='utf8')
        self.git('add', 'seed.txt'); self.git('commit', '-m', 'seed'); self.git('push', 'origin', 'HEAD:main')
        self.git('clone', self.remote.as_posix(), self.side.as_posix(), cwd=self.root)
        self.git('config', 'core.autocrlf', 'false', cwd=self.side)
        (self.work / 'candidate.csv').write_text('approved\n', encoding='utf8')
        self.git('add', 'candidate.csv'); self.git('commit', '-m', 'candidate')
        self.candidate = self.git('rev-parse', 'HEAD')
        self.counter = self.root / 'push-count'

    def advance(self, conflict=False):
        name = 'candidate.csv' if conflict else 'other.txt'
        (self.side / name).write_text('remote-data\n', encoding='utf8')
        self.git('add', name, cwd=self.side); self.git('commit', '-m', 'other writer', cwd=self.side)
        self.git('push', 'origin', 'HEAD:main', cwd=self.side)

    def hook(self, races=0, reject=False):
        side = quote(self.side.as_posix()); counter = quote(self.counter.as_posix())
        body = f'''#!/bin/sh
n=$(cat {counter} 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" > {counter}
if [ "$n" -le {races} ]; then
  echo "$n" > {side}/race.txt
  git -C {side} add race.txt || exit 1
  git -C {side} commit -m "other-writer-$n" >/dev/null || exit 1
  git -C {side} push origin HEAD:main >/dev/null || exit 1
fi
exit {1 if reject else 0}
'''
        path = self.work / '.git/hooks/pre-push'
        path.write_text(body, encoding='utf8', newline='\n'); path.chmod(0o755)

    def run_publish(self):
        return subprocess.run([BASH, SCRIPT.as_posix()], cwd=self.work,
            env=self.env, capture_output=True, text=True, timeout=90)

    def remote_file(self, name):
        return self.git('--git-dir=' + self.remote.as_posix(), 'show', 'main:' + name)

    def test_success_without_remote_advance(self):
        self.hook()
        result = self.run_publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.counter.read_text().strip(), '1')
        self.assertEqual(self.remote_file('candidate.csv'), 'approved')

    def test_rebase_preserves_other_writer_before_push(self):
        self.advance(); self.hook()
        result = self.run_publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.remote_file('other.txt'), 'remote-data')
        self.assertEqual(self.remote_file('candidate.csv'), 'approved')

    def test_one_race_retries_once_and_preserves_both_writers(self):
        self.hook(races=1)
        result = self.run_publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.counter.read_text().strip(), '2')
        self.assertEqual(self.remote_file('race.txt'), '1')
        self.assertEqual(self.remote_file('candidate.csv'), 'approved')

    def test_two_races_stop_after_second_push_without_force(self):
        self.hook(races=2)
        result = self.run_publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.counter.read_text().strip(), '2')
        self.assertEqual(self.remote_file('race.txt'), '2')
        files = self.git('--git-dir=' + self.remote.as_posix(), 'ls-tree', '--name-only', 'main')
        self.assertNotIn('candidate.csv', files)
        self.assertEqual((self.work / 'candidate.csv').read_text(), 'approved\n')

    def test_conflict_aborts_and_preserves_candidate_for_diagnostics(self):
        self.advance(conflict=True); self.hook()
        result = self.run_publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.counter.exists())
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.candidate)
        self.assertFalse((self.work / '.git/rebase-merge').exists())
        self.assertFalse((self.work / '.git/rebase-apply').exists())
        self.assertEqual(self.remote_file('candidate.csv'), 'remote-data')
        self.assertEqual((self.work / 'candidate.csv').read_text(), 'approved\n')

    def test_rejection_without_remote_advance_does_not_retry(self):
        self.hook(reject=True)
        result = self.run_publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.counter.read_text().strip(), '1')


if __name__ == '__main__':
    unittest.main()
