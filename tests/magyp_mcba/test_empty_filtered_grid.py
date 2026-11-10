import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from scripts.magyp.mcba.acquisition import confirmed_empty_filtered_grid, initial_grid_has_rows


class EmptyFilteredGridTests(unittest.TestCase):
    def setUp(self):
        self.page = MagicMock()
        self.grid, self.rows, self.start, self.end, self.bar, self.notice = (MagicMock() for _ in range(6))
        self.grid.count.return_value = 1
        self.rows.count.return_value = 0
        self.start.input_value.return_value = self.end.input_value.return_value = '10/11/2026'
        self.bar.get_by_text.return_value = self.notice
        self.notice.count.return_value = 1
        self.notice.is_visible.return_value = True
        mapping = {'#GridContainerTbl': self.grid,
                   "#GridContainerTbl tr[id^='GridContainerRow_']": self.rows,
                   '#vDDO_FRUTAS_PRECIOS_FECHAAUXDATE': self.start,
                   '#vDDO_FRUTAS_PRECIOS_FECHAAUXDATETO': self.end,
                   '#GRIDPAGINATIONBARContainer_DVPaginationBar': self.bar}
        self.page.locator.side_effect = mapping.__getitem__
        self.response = SimpleNamespace(status=200, request=SimpleNamespace(
            post_data_json={'events': ['DDO_GRID.ONOPTIONCLICKED'], 'parms': ['10/11/2026', '10/11/2026']}))

    def confirmed(self, had_rows=True, errors=()):
        return confirmed_empty_filtered_grid(self.page, '2026-11-10', '2026-11-10',
                                             had_rows, self.response, errors)

    def test_explicit_empty_result_requires_transition_and_all_evidence(self):
        self.assertTrue(self.confirmed())
        self.assertFalse(self.confirmed(had_rows=False))
        self.assertFalse(self.confirmed(errors=['http_error']))
        self.rows.count.return_value = 1
        self.assertFalse(self.confirmed())
        self.rows.count.return_value = 0
        self.end.input_value.return_value = '09/11/2026'
        self.assertFalse(self.confirmed())
        self.end.input_value.return_value = '10/11/2026'
        self.notice.is_visible.return_value = False
        self.assertFalse(self.confirmed())
        self.notice.is_visible.return_value = True
        self.response.request.post_data_json = {'events': ['OTHER']}
        self.assertFalse(self.confirmed())
        self.response.request.post_data_json = {'events': ['DDO_GRID.ONOPTIONCLICKED'], 'parms': ['09/11/2026']}
        self.assertFalse(self.confirmed())
        self.response.request.post_data_json = {'events': ['DDO_GRID.ONOPTIONCLICKED'], 'parms': ['10/11/2026', '10/11/2026']}
        self.response.status = 503
        self.assertFalse(self.confirmed())

    def test_initial_rows_must_not_have_an_existing_empty_notice(self):
        self.rows.count.return_value = 10
        self.assertFalse(initial_grid_has_rows(self.page))
        self.notice.count.return_value = 0
        self.assertTrue(initial_grid_has_rows(self.page))


if __name__ == '__main__':
    unittest.main()
