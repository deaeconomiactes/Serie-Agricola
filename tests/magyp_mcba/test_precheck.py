import json
import socket
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.magyp.common.platform import PipelineError, publish_bundle
from scripts.magyp.mcba.acquisition import AcquisitionResult, browser_fetch, connectivity_precheck, navigation_snapshot, URL
from scripts.magyp.mcba.update_mcba_dashboard import update, outputs_for
from test_publication import daily
from test_mcba import DAY, export
import test_initial_get as browser_fixtures


class PrecheckTests(unittest.TestCase):
    def connection(self):
        connection = MagicMock()
        connection._create_connection.return_value = MagicMock()
        connection.connect.side_effect = lambda: connection._create_connection(('ssma.magyp.gob.ar', 443))
        connection.getresponse.return_value.status = 200
        return connection

    def test_one_get_200_no_cookies_and_no_response_body(self):
        connection = self.connection()
        with patch('socket.getaddrinfo', return_value=[('fixture',)]), \
                patch('http.client.HTTPSConnection', return_value=connection), redirect_stdout(StringIO()):
            result = connectivity_precheck()
        self.assertTrue(result['dns_resolves'])
        self.assertTrue(result['tcp_connected'])
        self.assertTrue(result['https_connected'])
        self.assertEqual(result['http_status'], 200)
        self.assertEqual(connection.request.call_count, 1)
        self.assertEqual(connection.request.call_args.args, ('GET', '/frutas.precios.aspx'))
        self.assertNotIn('Cookie', connection.request.call_args.kwargs['headers'])
        connection.getresponse.return_value.read.assert_not_called()
        connection.close.assert_called_once()

    def test_precheck_timeout_connection_or_dns_failure_still_starts_edge(self):
        for error in (socket.gaierror('SECRET'), TimeoutError('SECRET'), ConnectionError('SECRET')):
            connection = self.connection()
            dns_failure = isinstance(error, socket.gaierror)
            connection.connect.side_effect = error
            logs = StringIO()
            with self.subTest(kind=type(error).__name__), \
                    patch('socket.getaddrinfo', side_effect=error if dns_failure else None), \
                    patch('http.client.HTTPSConnection', return_value=connection), \
                    patch('scripts.magyp.mcba.acquisition._browser_fetch_once',
                          return_value=AcquisitionResult(export(), 'BROWSER_AUTOMATION_REQUIRED')) as browser, \
                    patch('scripts.magyp.mcba.acquisition.time.sleep') as sleep, redirect_stdout(logs):
                acquisition = browser_fetch(DAY, DAY, channel='msedge')
                browser.assert_called_once_with(DAY, DAY, 60, 80, 'msedge'); sleep.assert_not_called()
                result = acquisition.diagnostics['precheck']
                self.assertEqual(result['dns_resolves'], not dns_failure)
                self.assertFalse(result['https_connected'])
                self.assertIsNone(result['http_status'])
                self.assertNotIn('SECRET', logs.getvalue())
                self.assertEqual(result['classification'], 'PRECHECK_INCONCLUSIVE')
                self.assertEqual(len(acquisition.diagnostics['acquisition_attempts']), 1)

    def test_precheck_5xx_and_other_nonblocking_statuses_still_start_edge(self):
        for status in (500, 503, 599, 302, 429):
            connection = self.connection(); connection.getresponse.return_value.status = status
            with self.subTest(status=status), patch('socket.getaddrinfo'), \
                    patch('http.client.HTTPSConnection', return_value=connection), \
                    patch('scripts.magyp.mcba.acquisition._browser_fetch_once',
                          return_value=AcquisitionResult(export(), 'BROWSER_AUTOMATION_REQUIRED')) as browser, \
                    redirect_stdout(StringIO()):
                result = browser_fetch(DAY, DAY, channel='msedge')
                browser.assert_called_once_with(DAY, DAY, 60, 80, 'msedge')
                self.assertEqual(result.diagnostics['precheck']['http_status'], status)
                self.assertEqual(result.diagnostics['precheck']['classification'],
                                 'PRECHECK_TRANSIENT' if status >= 500 else 'PRECHECK_INCONCLUSIVE')

    def test_precheck_http_rejection_never_starts_playwright(self):
        for status in (401, 403, 404):
            connection = self.connection(); connection.getresponse.return_value.status = status
            with self.subTest(status=status), patch('socket.getaddrinfo'), \
                    patch('http.client.HTTPSConnection', return_value=connection), \
                    patch('scripts.magyp.mcba.acquisition._browser_fetch_once') as browser, redirect_stdout(StringIO()):
                with self.assertRaises(PipelineError) as error: browser_fetch(DAY, DAY)
                self.assertEqual(error.exception.diagnostics['precheck']['http_status'], status)
                browser.assert_not_called()

    def test_validated_xlsx_success_after_inconclusive_precheck(self):
        fixture = browser_fixtures.InitialGetTests(methodName='runTest')
        with fixture.scenario([200]) as (sessions, audit, sleep, logs), \
                patch('scripts.magyp.mcba.acquisition.connectivity_precheck', wraps=connectivity_precheck), \
                patch('socket.getaddrinfo', side_effect=socket.gaierror('SECRET')):
            result = browser_fetch(DAY, DAY, channel='msedge')
            self.assertTrue(result.diagnostics['xlsx_valid'])
            self.assertGreater(result.diagnostics['validated_rows'], 0)
            self.assertEqual(result.diagnostics['precheck']['classification'], 'PRECHECK_INCONCLUSIVE')
            self.assertEqual(result.label_evidence[0]['date'], '24/08/2026')
            self.assertEqual(result.diagnostics['acquisition_attempts'][0]['acquisition_stage'], 'completed')
            sleep.assert_not_called()

    def test_three_edge_failures_after_inconclusive_precheck_preserve_last_valid(self):
        fixture = browser_fixtures.InitialGetTests(methodName='runTest')
        with tempfile.TemporaryDirectory() as temp, fixture.scenario([TimeoutError(), TimeoutError(), TimeoutError()]) as (sessions, audit, sleep, logs), \
                patch('scripts.magyp.mcba.acquisition.connectivity_precheck', wraps=connectivity_precheck), \
                patch('socket.getaddrinfo', side_effect=socket.gaierror()):
            target, raw = Path(temp) / 'published', Path(temp) / 'capture'
            publish_bundle(target, outputs_for(daily()), len(daily()))
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            with self.assertRaises(PipelineError): update(DAY, raw, target, True, browser_channel='msedge')
            self.assertTrue(all((target / name).read_bytes() == value for name, value in before.items()))
            self.assertEqual(json.loads((target / 'MCBA_MAGYP_UPDATE_STATUS.json').read_bytes())['source_status'],
                             'MAGYP_LAST_VALID')
            diagnostic = json.loads((raw / 'reports/MCBA_INTEGRATION_ATTEMPT.json').read_bytes())['diagnostics']
            self.assertEqual(len(diagnostic['acquisition_attempts']), 3)
            self.assertEqual(diagnostic['precheck']['classification'], 'PRECHECK_INCONCLUSIVE')
            self.assertEqual(sleep.call_count, 2)
            for browser, context, page in sessions:
                browser.close.assert_called_once(); context.close.assert_called_once()

    def test_navigation_snapshot_is_only_safe_public_metadata(self):
        page = MagicMock()
        page.url = URL + '?token=SECRET'
        page.evaluate.return_value = {'ready_state': 'loading', 'date_from_exists': True,
                                      'date_to_exists': False, 'GXState': 'SECRET'}
        result = navigation_snapshot(page, 200, 1)
        self.assertEqual(result['final_url'], URL)
        self.assertEqual(result['ready_state'], 'loading')
        self.assertTrue(result['date_from_exists'])
        self.assertFalse(result['date_to_exists'])
        self.assertNotIn('SECRET', json.dumps(result))

    def test_precheck_failure_preserves_last_valid_and_persists_exact_probe_result(self):
        connection = self.connection(); connection.getresponse.return_value.status = 403
        with tempfile.TemporaryDirectory() as temp, patch('socket.getaddrinfo'), \
                patch('http.client.HTTPSConnection', return_value=connection), \
                patch('scripts.magyp.mcba.acquisition._browser_fetch_once') as browser, redirect_stdout(StringIO()):
            target, raw = Path(temp) / 'published', Path(temp) / 'capture'
            publish_bundle(target, outputs_for(daily()), len(daily()))
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            with self.assertRaises(PipelineError): update(DAY, raw, target, True)
            self.assertTrue(all((target / name).read_bytes() == value for name, value in before.items()))
            status = json.loads((target / 'MCBA_MAGYP_UPDATE_STATUS.json').read_bytes())
            self.assertEqual(status['source_status'], 'MAGYP_LAST_VALID')
            diagnostic = json.loads((raw / 'reports/MCBA_INTEGRATION_ATTEMPT.json').read_bytes())
            self.assertEqual(diagnostic['diagnostics']['precheck']['http_status'], 403)
            browser.assert_not_called()


if __name__ == '__main__':
    unittest.main()
