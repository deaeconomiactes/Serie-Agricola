import json
import socket
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.magyp.common.platform import PipelineError, publish_bundle
from scripts.magyp.mcba.acquisition import browser_fetch, connectivity_precheck, navigation_snapshot, URL
from scripts.magyp.mcba.update_mcba_dashboard import update, outputs_for
from test_publication import daily
from test_mcba import DAY


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

    def test_precheck_timeout_or_dns_failure_never_starts_playwright(self):
        for dns_failure in (True, False):
            connection = self.connection()
            connection.connect.side_effect = TimeoutError('SECRET')
            logs = StringIO()
            with self.subTest(dns_failure=dns_failure), \
                    patch('socket.getaddrinfo', side_effect=socket.gaierror('SECRET') if dns_failure else None), \
                    patch('http.client.HTTPSConnection', return_value=connection), \
                    patch('scripts.magyp.mcba.acquisition._browser_fetch_once') as browser, \
                    patch('scripts.magyp.mcba.acquisition.time.sleep') as sleep, redirect_stdout(logs):
                with self.assertRaises(PipelineError) as error: browser_fetch(DAY, DAY)
                browser.assert_not_called(); sleep.assert_not_called()
                result = error.exception.diagnostics['precheck']
                self.assertEqual(result['dns_resolves'], not dns_failure)
                self.assertFalse(result['https_connected'])
                self.assertIsNone(result['http_status'])
                self.assertNotIn('SECRET', logs.getvalue())
                self.assertEqual(error.exception.diagnostics['acquisition_attempts'], [])

    def test_precheck_http_rejection_never_starts_playwright(self):
        for status in (401, 403, 404, 503):
            connection = self.connection(); connection.getresponse.return_value.status = status
            with self.subTest(status=status), patch('socket.getaddrinfo'), \
                    patch('http.client.HTTPSConnection', return_value=connection), \
                    patch('scripts.magyp.mcba.acquisition._browser_fetch_once') as browser, redirect_stdout(StringIO()):
                with self.assertRaises(PipelineError) as error: browser_fetch(DAY, DAY)
                self.assertEqual(error.exception.diagnostics['precheck']['http_status'], status)
                browser.assert_not_called()

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
        with tempfile.TemporaryDirectory() as temp, patch('socket.getaddrinfo', side_effect=socket.gaierror()), \
                patch('scripts.magyp.mcba.acquisition._browser_fetch_once') as browser, redirect_stdout(StringIO()):
            target, raw = Path(temp) / 'published', Path(temp) / 'capture'
            publish_bundle(target, outputs_for(daily()), len(daily()))
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            with self.assertRaises(PipelineError): update(DAY, raw, target, True)
            self.assertTrue(all((target / name).read_bytes() == value for name, value in before.items()))
            status = json.loads((target / 'MCBA_MAGYP_UPDATE_STATUS.json').read_bytes())
            self.assertEqual(status['source_status'], 'MAGYP_LAST_VALID')
            diagnostic = json.loads((raw / 'reports/MCBA_INTEGRATION_ATTEMPT.json').read_bytes())
            self.assertFalse(diagnostic['diagnostics']['precheck']['dns_resolves'])
            browser.assert_not_called()


if __name__ == '__main__':
    unittest.main()
