import re
import unittest
from pathlib import Path

from scripts.carnes.mag_prices import pipeline_exit_code


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/update-carnes-mag.yml'


def step_block(workflow, name):
    marker = f'- name: {name}'
    return workflow.split(marker, 1)[1].split('\n      - name:', 1)[0]


def step_condition(workflow, name):
    step = step_block(workflow, name)
    match = re.search(r'^\s*if:\s*(.+)$', step, re.MULTILINE)
    if not match:
        raise AssertionError(f'Workflow step has no condition: {name}')
    return match.group(1).strip()


def evaluate_condition(condition, *, ref, outcomes, outputs=None):
    outputs = outputs or {}
    for clause in re.split(r'\s*&&\s*', condition):
        clause = clause.strip()
        if clause == 'always()':
            continue
        match = re.fullmatch(r"github\.ref\s*==\s*'([^']+)'", clause)
        if match:
            if ref != match.group(1):
                return False
            continue
        match = re.fullmatch(r"steps\.([a-z0-9_-]+)\.outcome\s*==\s*'([^']+)'", clause)
        if match:
            if outcomes.get(match.group(1)) != match.group(2):
                return False
            continue
        match = re.fullmatch(r"steps\.([a-z0-9_-]+)\.outputs\.([a-z0-9_-]+)\s*==\s*'([^']+)'", clause)
        if match:
            if outputs.get((match.group(1), match.group(2))) != match.group(3):
                return False
            continue
        raise AssertionError(f'Unsupported workflow condition clause: {clause}')
    return True


class CarnesWorkflowPublicationTests(unittest.TestCase):
    def test_pinned_carnes_test_dependencies_are_installed_before_unittest(self):
        workflow = WORKFLOW.read_text(encoding='utf-8')
        test_step = step_block(workflow, 'Test Carnes transformations and interface')
        dependency_install = 'python -m pip install --disable-pip-version-check -r scripts/carnes/requirements.txt'
        test_suite = 'python -m unittest discover -s tests/carnes -v'
        self.assertIn(dependency_install, test_step)
        self.assertLess(test_step.index(dependency_install), test_step.index(test_suite))

    def test_failed_capture_cannot_publish_after_successful_validation_and_tests(self):
        workflow = WORKFLOW.read_text(encoding='utf-8')
        publish = step_condition(workflow, 'Publish only light Carnes outputs')
        deploy = step_condition(workflow, 'Deploy updated dashboard explicitly')
        outcomes = {'update': 'failure', 'validate': 'success', 'tests': 'success'}

        publish_runs = evaluate_condition(publish, ref='refs/heads/main', outcomes=outcomes)
        outputs = {('publication', 'changed'): 'true' if publish_runs else 'false'}
        deploy_runs = evaluate_condition(deploy, ref='refs/heads/main', outcomes=outcomes, outputs=outputs)
        side_effects = ['commit/push'] if publish_runs else []
        if deploy_runs:
            side_effects.append('deploy')

        self.assertFalse(publish_runs)
        self.assertFalse(deploy_runs)
        self.assertEqual(side_effects, [])
        self.assertIn("steps.update.outcome == 'failure'", workflow)
        failure_step = workflow.split('- name: Fail visibly on a pipeline, validation, or test error', 1)[1]
        self.assertIn("steps.update.outcome == 'failure'", failure_step)
        self.assertIn('run: exit 1', failure_step)

    def test_source_statuses_remain_successful_publication_states(self):
        workflow = WORKFLOW.read_text(encoding='utf-8')
        publish = step_condition(workflow, 'Publish only light Carnes outputs')
        for source_status in ('NO_PUBLICATION', 'SOURCE_UNAVAILABLE'):
            with self.subTest(source_status=source_status):
                # Only PIPELINE_ERROR fails the pipeline; expected source states still pass the workflow gate.
                self.assertEqual(0, pipeline_exit_code([source_status]))
                outcomes = {'update': 'success', 'validate': 'success', 'tests': 'success'}
                self.assertTrue(evaluate_condition(publish, ref='refs/heads/main', outcomes=outcomes))


if __name__ == '__main__':
    unittest.main()
