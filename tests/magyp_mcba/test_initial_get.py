import json
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from scripts.magyp.common.platform import PipelineError, publish_bundle
from scripts.magyp.mcba.acquisition import URL, browser_fetch, safe_initial_url
from scripts.magyp.mcba.update_mcba_dashboard import outputs_for, update
from test_mcba import DAY, row, export
from test_publication import daily


class InitialGetTests(unittest.TestCase):
    def session(self, outcome, folder, audit, number, final_url=URL):
        browser, probe, context, page = (MagicMock() for _ in range(4))
        browser.new_context.side_effect = [probe, context]
        probe.new_page.return_value.evaluate.return_value = 'HeadlessChrome'
        context.new_page.return_value = page
        context.close.side_effect = lambda: audit.append(('context_closed', number))
        browser.close.side_effect = lambda: audit.append(('browser_closed', number))
        browser.version = 'fixture'
        handlers = {}
        page.on.side_effect = lambda event, callback: handlers.update({event: callback})
        page.url = final_url
        def goto(*args, **kwargs):
            request = SimpleNamespace(url=URL, method='GET', resource_type='document')
            route = MagicMock(); route.request = request
            context.route.call_args.args[1](route)
            if isinstance(outcome, Exception): raise outcome
            response = SimpleNamespace(status=outcome, url=final_url, headers={}, request=request)
            handlers['response'](response)
            return response
        page.goto.side_effect = goto
        page.content.return_value = '<input name="GXState" value="private-state">'
        page.expect_response.return_value.__enter__.return_value.value.status = 200
        tr = MagicMock()
        tr.locator.return_value.all_text_contents.return_value = [
            '24/08/2026', 'Frutas', 'MANZANA', 'RED DELICI', 'R. NEGRO', 'CAJA',
            'Elegido', 'GRANDE', '', '0,00', '1.500,00']
        path = folder / f'export-{number}.xlsx'; path.write_bytes(export([row()]))
        download = MagicMock(); download.path.return_value = str(path); download.failure.return_value = None
        page.fixture_download = download
        def locator(selector):
            item = MagicMock()
            if selector.startswith('#GridContainerTbl'): item.all.return_value = [tr]
            if selector == '#EXPORT': item.click.side_effect = lambda: handlers['download'](download)
            return item
        page.locator.side_effect = locator
        return browser, context, page

    @contextmanager
    def scenario(self, outcomes, final_url=URL):
        with tempfile.TemporaryDirectory() as temp:
            audit = []; sessions = [self.session(o, Path(temp), audit, n, final_url)
                                    for n, o in enumerate(outcomes, 1)]
            fake = MagicMock()
            fake.return_value.__enter__.return_value.chromium.launch.side_effect = [s[0] for s in sessions]
            logs = StringIO()
            with patch.dict(sys.modules, {'playwright': MagicMock(),
                    'playwright.sync_api': SimpleNamespace(sync_playwright=fake)}),\
                    patch.dict('os.environ', {'GITHUB_ACTIONS': 'true'}),\
                    patch('scripts.magyp.mcba.acquisition.time.sleep',
                        side_effect=lambda seconds: audit.append(('sleep', seconds))) as sleep,\
                    redirect_stdout(logs):
                yield sessions, audit, sleep, logs

    def test_initial_get_200_safe_metadata_and_no_retry(self):
        with self.scenario([200]) as (sessions, audit, sleep, logs):
            result = browser_fetch(DAY, DAY, channel='chromium')
            self.assertTrue(result.payload.startswith(b'PK'))
            record = result.diagnostics['initial_get_attempts'][0]
            self.assertEqual(record['http_status'], 200)
            self.assertEqual(record['final_url'], URL)
            self.assertEqual(record['requested_date'], DAY)
            self.assertEqual(record['browser_channel'], 'chromium')
            self.assertEqual(record['acquisition_stage'], 'initial_get')
            self.assertEqual(record['request_count'], 1)
            self.assertGreaterEqual(record['duration_seconds'], 0)
            self.assertIsNone(record['error_type'])
            self.assertFalse(result.diagnostics['retry_performed']); sleep.assert_not_called()
            self.assertNotIn('private-state', json.dumps(result.diagnostics))
            sessions[0][1].cookies.assert_not_called()

    def assert_retry_succeeds(self, first):
        with self.scenario([first, 200]) as (sessions, audit, sleep, logs):
            result = browser_fetch(DAY, DAY, channel='chromium')
            sleep.assert_called_once_with(10)
            self.assertEqual(audit[:3], [('context_closed', 1), ('browser_closed', 1), ('sleep', 10)])
            self.assertEqual(len(result.diagnostics['initial_get_attempts']), 2)
            self.assertTrue(result.diagnostics['retry_performed'])
            self.assertEqual(result.diagnostics['request_count'], 2)
            for browser, context, page in sessions:
                browser.close.assert_called_once(); context.close.assert_called_once()
                page.goto.assert_called_once_with(URL, wait_until='load')
            self.assertNotIn('private-session', logs.getvalue())

    def test_timeout_then_success_clean_session(self):
        self.assert_retry_succeeds(TimeoutError('private-session?GXState=SECRET'))

    def test_http_500_then_success_clean_session(self):
        self.assert_retry_succeeds(500)

    def test_connection_then_success_clean_session(self):
        self.assert_retry_succeeds(ConnectionResetError('private-session'))

    def test_three_failures_are_visible_and_never_fourth_attempt(self):
        with self.scenario([500, TimeoutError('private-session'), 503]) as (sessions, audit, sleep, logs):
            with self.assertRaises(PipelineError) as error:
                browser_fetch(DAY, DAY, channel='chromium')
            self.assertEqual(sleep.call_count, 2)
            self.assertEqual(error.exception.diagnostics['error_type'], 'HTTP_5XX')
            self.assertEqual(len(error.exception.diagnostics['initial_get_attempts']), 3)
            self.assertEqual(error.exception.diagnostics['request_count'], 3)
            self.assertEqual(audit[-2:], [('context_closed', 3), ('browser_closed', 3)])
            self.assertEqual([a['attempt'] for a in error.exception.diagnostics['acquisition_attempts']], [1, 2, 3])
            for browser, context, page in sessions:
                browser.close.assert_called_once(); context.close.assert_called_once()

    def fail_control(self, page, selector, error):
        original = page.locator.side_effect
        def locator(value):
            item = original(value)
            if value == selector:
                item.click.side_effect = error
            return item
        page.locator.side_effect = locator

    def assert_later_timeout_restarts_session(self, selector, stage):
        with self.scenario([200, 200]) as (sessions, audit, sleep, logs):
            self.fail_control(sessions[0][2], selector, TimeoutError('private-session GXState=SECRET'))
            result = browser_fetch(DAY, DAY, channel='chromium')
            attempts = result.diagnostics['acquisition_attempts']
            self.assertEqual([a['acquisition_stage'] for a in attempts], [stage, 'completed'])
            self.assertEqual([a['error_type'] for a in attempts], ['TIMEOUT', None])
            self.assertEqual([a['request_count'] for a in attempts], [1, 1])
            for a in attempts:
                self.assertEqual(a['requested_date'], DAY)
                self.assertIn('http_status', a)
                self.assertGreaterEqual(a['duration_seconds'], 0)
            self.assertEqual(audit[:3], [('context_closed', 1), ('browser_closed', 1), ('sleep', 10)])
            sleep.assert_called_once_with(10)
            for browser, context, page in sessions:
                browser.close.assert_called_once(); context.close.assert_called_once()
                page.goto.assert_called_once_with(URL, wait_until='load')
            self.assertNotIn('SECRET', logs.getvalue() + json.dumps(result.diagnostics))

    def test_date_controls_timeout_then_new_session_success(self):
        self.assert_later_timeout_restarts_session('#DDO_GRIDContainer_TF_1_btnGroupDrop', 'date_controls')

    def test_export_timeout_then_new_session_success(self):
        self.assert_later_timeout_restarts_session('#EXPORT', 'export_download')

    def test_download_timeout_then_new_session_success(self):
        with self.scenario([200, 200]) as (sessions, audit, sleep, logs):
            sessions[0][2].fixture_download.path.side_effect = TimeoutError('SECRET')
            result = browser_fetch(DAY, DAY, channel='chromium')
            self.assertEqual(result.diagnostics['acquisition_attempts'][0]['acquisition_stage'], 'export_download')
            self.assertEqual(result.diagnostics['acquisition_attempts'][0]['error_type'], 'TIMEOUT')
            sleep.assert_called_once_with(10)

    def test_export_http_error_classification_and_retry_policy(self):
        for status in (401, 403, 404, 503):
            with self.subTest(status=status), self.scenario([200, 200] if status == 503 else [200]) as (sessions, _, sleep, logs):
                page = sessions[0][2]
                response = SimpleNamespace(status=status, url=URL, headers={},
                                           request=SimpleNamespace(resource_type='document', method='GET'))
                original = page.locator.side_effect
                def locator(value):
                    item = original(value)
                    if value == '#EXPORT':
                        on_response = next(call.args[1] for call in page.on.call_args_list if call.args[0] == 'response')
                        item.click.side_effect = lambda: on_response(response)
                    return item
                page.locator.side_effect = locator
                if status == 503:
                    result = browser_fetch(DAY, DAY, channel='chromium')
                    record = result.diagnostics['acquisition_attempts'][0]
                    sleep.assert_called_once_with(10)
                else:
                    with self.assertRaises(PipelineError) as caught:
                        browser_fetch(DAY, DAY, channel='chromium')
                    record = caught.exception.diagnostics['acquisition_attempts'][0]
                    sleep.assert_not_called()
                self.assertEqual(record['http_status'], status)
                self.assertEqual(record['error_type'], 'HTTP_5XX' if status == 503 else f'HTTP_{status}')

    def test_invalid_xlsx_never_retries_and_preserves_last_valid(self):
        with tempfile.TemporaryDirectory() as temp, self.scenario([200]) as (sessions, _, sleep, logs):
            Path(sessions[0][2].fixture_download.path.return_value).write_bytes(b'invalid XLSX')
            target, capture_root = Path(temp) / 'published', Path(temp) / 'capture'
            publish_bundle(target, outputs_for(daily()), len(daily()))
            before = {path.name: path.read_bytes() for path in target.iterdir()}
            with self.assertRaises(PipelineError): update(DAY, capture_root, target, True)
            sleep.assert_not_called()
            self.assertTrue(all((target / name).read_bytes() == body for name, body in before.items()))
            status = json.loads((target / 'MCBA_MAGYP_UPDATE_STATUS.json').read_bytes())
            self.assertEqual(status['source_status'], 'MAGYP_LAST_VALID')

    def test_third_complete_attempt_can_succeed(self):
        with self.scenario([TimeoutError(), 200, 200]) as (sessions, audit, sleep, logs):
            self.fail_control(sessions[1][2], '#EXPORT', TimeoutError())
            result = browser_fetch(DAY, DAY, channel='chromium')
            self.assertTrue(result.payload.startswith(b'PK'))
            self.assertEqual(sleep.call_count, 2)
            self.assertEqual([a['acquisition_stage'] for a in result.diagnostics['acquisition_attempts']],
                             ['initial_get', 'export_download', 'completed'])

    def test_three_transient_failures_preserve_last_valid(self):
        with tempfile.TemporaryDirectory() as temp, self.scenario([200, 200, 200]) as (sessions, audit, sleep, logs):
            for _, _, page in sessions:
                self.fail_control(page, '#DDO_GRIDContainer_TF_1_btnGroupDrop', TimeoutError('SECRET'))
            target, capture_root = Path(temp) / 'published', Path(temp) / 'capture'
            publish_bundle(target, outputs_for(daily()), len(daily()))
            before = {path.name: path.read_bytes() for path in target.iterdir()}
            with self.assertRaises(PipelineError): update(DAY, capture_root, target, True)
            self.assertTrue(all((target / name).read_bytes() == body for name, body in before.items()))
            status = json.loads((target / 'MCBA_MAGYP_UPDATE_STATUS.json').read_bytes())
            self.assertEqual(status['source_status'], 'MAGYP_LAST_VALID')
            diag = json.loads((capture_root / 'reports/MCBA_INTEGRATION_ATTEMPT.json').read_bytes())
            attempts = diag['diagnostics']['acquisition_attempts']
            self.assertEqual(len(attempts), 3)
            self.assertTrue(all(a['error_type'] == 'TIMEOUT' and a['acquisition_stage'] == 'date_controls'
                                for a in attempts))
            self.assertEqual(sleep.call_count, 2)
            self.assertNotIn('SECRET', json.dumps(diag))

    def test_wrong_grid_date_never_retries(self):
        with self.scenario([200]) as (sessions, _, sleep, logs):
            original = sessions[0][2].locator.side_effect
            def locator(value):
                item = original(value)
                if value.startswith('#GridContainerTbl'):
                    item.all.return_value[0].locator.return_value.all_text_contents.return_value[0] = '25/08/2026'
                return item
            sessions[0][2].locator.side_effect = locator
            with self.assertRaises(PipelineError): browser_fetch(DAY, DAY, channel='chromium')
            sleep.assert_not_called()

    def test_retry_never_exceeds_total_request_budget(self):
        with self.scenario([500]) as (_, _, sleep, logs):
            with self.assertRaises(PipelineError) as error:
                browser_fetch(DAY, DAY, max_requests=1, channel='chromium')
            self.assertEqual(error.exception.diagnostics['request_count'], 1)
            self.assertFalse(error.exception.diagnostics['retry_performed'])
            sleep.assert_not_called()

    def test_403_401_blocked_404_429_and_redirect_never_retry(self):
        for status in [403, 401, 404, 429]:
            with self.subTest(status=status), self.scenario([status]) as (_, audit, sleep, logs):
                with self.assertRaises(PipelineError) as error:
                    browser_fetch(DAY, DAY, channel='chromium')
                sleep.assert_not_called()
                self.assertEqual(error.exception.diagnostics['http_status'], status)
                self.assertEqual(error.exception.diagnostics['error_type'], f'HTTP_{status}')
                if status in {401, 403}:
                    self.assertEqual(error.exception.diagnostics['classification'], 'GITHUB_RUNNER_ACCESS_BLOCKED')
        with self.scenario([200], final_url='https://other.invalid/(S(private-session))/login?token=SECRET') as (_, _, sleep, logs):
            with self.assertRaises(PipelineError) as error:
                browser_fetch(DAY, DAY, channel='chromium')
            sleep.assert_not_called()
            text = json.dumps(error.exception.diagnostics) + logs.getvalue()
            self.assertNotIn('private-session', text); self.assertNotIn('SECRET', text)
            self.assertEqual(error.exception.diagnostics['error_type'], 'UNEXPECTED_REDIRECT')
        self.assertNotIn('private-session', safe_initial_url('https://ssma.magyp.gob.ar/(S(private-session))/x?token=SECRET'))

    def test_dns_navigation_abort_and_post_get_schema_errors_never_retry(self):
        for error, kind in [(RuntimeError('net::ERR_NAME_NOT_RESOLVED private-session'), 'DNS'),
                            (RuntimeError('net::ERR_ABORTED private-session'), 'NAVIGATION_ABORTED')]:
            with self.subTest(kind=kind), self.scenario([error]) as (_, _, sleep, logs):
                with self.assertRaises(PipelineError) as caught: browser_fetch(DAY, DAY, channel='chromium')
                self.assertEqual(caught.exception.diagnostics['error_type'], kind)
                sleep.assert_not_called()
        with self.scenario([200]) as (sessions, _, sleep, logs):
            sessions[0][2].locator.side_effect = PipelineError('Unexpected schema')
            with self.assertRaises(PipelineError): browser_fetch(DAY, DAY, channel='chromium')
            sleep.assert_not_called()

    def test_403_preserves_last_valid_csv_and_persists_safe_diagnostic(self):
        with tempfile.TemporaryDirectory() as temp, self.scenario([403]) as (_, _, sleep, logs):
            target, capture_root = Path(temp) / 'published', Path(temp) / 'capture'
            publish_bundle(target, outputs_for(daily()), len(daily()))
            before = {path.name: path.read_bytes() for path in target.iterdir()}
            with self.assertRaises(PipelineError): update(DAY, capture_root, target, True)
            self.assertTrue(all((target / name).read_bytes() == body for name, body in before.items()))
            status = json.loads((target / 'MCBA_MAGYP_UPDATE_STATUS.json').read_bytes())
            self.assertEqual(status['source_status'], 'MAGYP_LAST_VALID')
            diag = json.loads((capture_root / 'reports/MCBA_INTEGRATION_ATTEMPT.json').read_bytes())
            self.assertEqual(diag['diagnostics']['http_status'], 403)
            self.assertEqual(diag['diagnostics']['classification'], 'GITHUB_RUNNER_ACCESS_BLOCKED')
            self.assertFalse((capture_root / 'raw').exists())
            sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
