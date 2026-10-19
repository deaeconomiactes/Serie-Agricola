import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.magyp.mcba.acquisition import preferred_browser_channel, wait_for_genexus_controls


class GeneXusReadyTests(unittest.TestCase):
    def test_installed_edge_is_preferred_on_windows_and_absence_uses_chromium(self):
        with tempfile.TemporaryDirectory() as temp:
            edge = Path(temp) / 'Microsoft/Edge/Application/msedge.exe'
            edge.parent.mkdir(parents=True)
            with patch('sys.platform', 'win32'), patch.dict(os.environ, {
                    'PROGRAMFILES(X86)': temp, 'PROGRAMFILES': temp, 'LOCALAPPDATA': temp}):
                self.assertEqual(preferred_browser_channel(), 'chromium')
                edge.write_bytes(b'fixture')
                self.assertEqual(preferred_browser_channel(), 'msedge')
            with patch('sys.platform', 'linux'):
                self.assertEqual(preferred_browser_channel(), 'chromium')

    def page(self):
        page = MagicMock()
        controls = {}
        def locator(selector):
            item = controls.setdefault(selector, MagicMock())
            item.is_visible.return_value = False
            return item
        page.locator.side_effect = locator
        return page, controls

    def test_delayed_controls_are_explicitly_waited_before_use(self):
        page, controls = self.page()
        wait_for_genexus_controls(page, 60)
        for selector in ('#GridContainerTbl', '#EXPORT', '#DDO_GRIDContainer_TF_1_btnGroupDrop',
                         '#vDDO_FRUTAS_PRECIOS_FECHAAUXDATE', '#vDDO_FRUTAS_PRECIOS_FECHAAUXDATETO'):
            args = controls[selector].wait_for.call_args.kwargs
            self.assertEqual(args['state'], 'visible')
            self.assertTrue(0 < args['timeout'] <= 60000)
        page.wait_for_load_state.assert_called_once()
        page.remove_listener.assert_called_once()

    def test_initial_reload_relocates_controls_within_same_deadline(self):
        page, controls = self.page()
        grid = page.locator('#GridContainerTbl')
        def reload():
            page.on.call_args.args[1](page.main_frame)
            raise RuntimeError('Execution context was destroyed')
        grid.wait_for.side_effect = lambda **kwargs: reload() if grid.wait_for.call_count == 1 else None
        wait_for_genexus_controls(page, 60)
        self.assertEqual(grid.wait_for.call_count, 2)
        self.assertEqual(page.wait_for_load_state.call_count, 2)
        self.assertLessEqual(grid.wait_for.call_args_list[1].kwargs['timeout'],
                             grid.wait_for.call_args_list[0].kwargs['timeout'])

    def test_repeated_reloads_cannot_extend_timeout(self):
        page, controls = self.page()
        page.wait_for_load_state.side_effect = RuntimeError('Execution context was destroyed')
        with patch('scripts.magyp.mcba.acquisition.time.monotonic', side_effect=[0, 1, 61]):
            with self.assertRaises(TimeoutError): wait_for_genexus_controls(page, 60)
        page.remove_listener.assert_called_once()


if __name__ == '__main__':
    unittest.main()
