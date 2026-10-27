import unittest,subprocess,os,shutil,tempfile,textwrap,sys,json
from pathlib import Path
from scripts.ci.workflow_status import requires_deploy
class WorkflowStatusTests(unittest.TestCase):
    def test_branch_guard_blocks_before_any_git_operation(self):
        bash=shutil.which('bash') or 'C:/Program Files/Git/bin/bash.exe'
        result=subprocess.run([bash,str(Path(__file__).resolve().parents[2]/'scripts/ci/push_data_main.sh')],env={**os.environ,'GITHUB_ACTIONS':'true','GITHUB_REF':'refs/heads/review'},capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('requiere refs/heads/main',result.stdout)
    def test_sio_capture_preserves_failure_through_tee(self):
        root=Path(__file__).resolve().parents[2]
        workflow=(root/'.github/workflows/update-sio-commodities.yml').read_text(encoding='utf-8')
        step=workflow.split('- name: Capturar snapshot latest',1)[1].split('- name: Integrar snapshot',1)[0]
        command=textwrap.dedent(step.split('        run: |\n',1)[1]).strip()
        bash=shutil.which('bash') or 'C:/Program Files/Git/bin/bash.exe'
        with tempfile.TemporaryDirectory() as folder:
            fake="python() { printf 'No se pudo actualizar SIO: URLError\\n'; return 1; }\n"
            result=subprocess.run([bash,'-c',fake+command],env={**os.environ,'RUNNER_TEMP':Path(folder).as_posix()},capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('No se pudo actualizar SIO:',(Path(folder)/'sio-capture.log').read_text())
    def test_failed_publication_logs_requested_date_and_last_published_observation(self):
        root=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as folder:
            candidate=Path(folder)/'candidate.json';candidate.write_text(json.dumps({'run_status':{'requested_date':'2026-10-27','last_observation_date':'2026-10-27'}}))
            published=Path(folder)/'summary.csv';published.write_text('date_max\n2026-10-05\n')
            result=subprocess.run([sys.executable,str(root/'scripts/ci/workflow_status.py'),'summary','--source','MAGyP_MCBA','--status','PIPELINE_ERROR','--status-file',str(candidate),'--last-csv',str(published)],capture_output=True,text=True,check=True)
            self.assertIn('REQUESTED_DATE=2026-10-27',result.stdout);self.assertIn('LAST_OBSERVATION=2026-10-05',result.stdout);self.assertIn('FINAL_STATUS=PIPELINE_ERROR',result.stdout)
    def test_attempt_only_no_op_does_not_redeploy(self):
        old=b'{"status":"SOURCE_UNAVAILABLE","attempted_at":"old","last_successful_update":"valid"}'
        new=b'{"status":"SOURCE_UNAVAILABLE","attempted_at":"new","last_successful_update":"valid"}'
        self.assertFalse(requires_deploy('data/magyp/reports/PRICE_FRESHNESS_STATUS.json',old,new))
    def test_source_state_transition_is_visible_without_new_csv(self):
        self.assertTrue(requires_deploy('data/magyp/reports/PRICE_FRESHNESS_STATUS.json',b'{"status":"UPDATED"}',b'{"status":"SOURCE_UNAVAILABLE"}'))
    def test_observation_capture_and_csv_changes_deploy(self):
        for field in ['last_observation_date','last_successful_update']:
            self.assertTrue(requires_deploy('data/magyp/reports/PRICE_FRESHNESS_STATUS.json',('{"'+field+'":"old"}').encode(),('{"'+field+'":"new"}').encode()))
        self.assertTrue(requires_deploy('data/a/dashboard/a.csv',b'1',b'2'))
    def test_audit_only_does_not_deploy(self):
        for path in ['data/a/reports/a.md','data/a/reports/a.json','data/a/dashboard/SOURCE_INDEX.json']:
            self.assertFalse(requires_deploy(path,b'old',b'new'))
if __name__=='__main__':unittest.main()
