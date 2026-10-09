import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from test_mcba import row, export, normalized, DAY
from scripts.magyp.common.platform import PipelineError, RawManifest, sha256
from scripts.magyp.mcba.acquisition import (AcquisitionResult, browser_fetch, describe_genexus,
                                           public_endpoint, select_fetcher, validate_window)
from scripts.magyp.mcba.labels import normalized_label
from scripts.magyp.mcba.matching import mutual_unique_matches
from scripts.magyp.mcba.model import build_analytical, dashboard_rows, normalize, parse_export
from scripts.magyp.mcba.compare_mcba_current_vs_magyp import compare, run


def current(label="MANZANA", price="1500"):
    return {"fecha": DAY, "fecha_precision": "", "archivo_origen": "zip/RF240826.XLS",
            "rubro": "Frutas", "especie": label, "variedad": "RED DELICI", "procedencia": "R. NEGRO",
            "envase": "CAJA", "unidad": "ARS/kg", "precio": price, "moneda": "ARS"}


class Phase2Tests(unittest.TestCase):
    def test_genexus_description_never_returns_hidden_values(self):
        d = describe_genexus('<input name="GXState" value="private-session-state">'
                             '<input name="vDDO_FRUTAS_PRECIOS_FECHAAUXDATE" value="24/08/2026">'
                             '<input name="vDDO_FRUTAS_PRECIOS_FECHAAUXDATETO" value="24/08/2026">')
        self.assertTrue(d["has_gxstate"])
        self.assertTrue(d["has_date_controls"])
        self.assertNotIn("private-session-state", json.dumps(d))

    def test_http_simulation_selected_without_browser(self):
        result = AcquisitionResult(export(), "HTTP_AUTONOMOUS", 200)
        http = MagicMock(return_value=result)
        browser = MagicMock()
        self.assertIs(select_fetcher(DAY, DAY, "http", browser, http), result)
        browser.assert_not_called()

    def test_simulated_http_fallback_to_browser(self):
        result = AcquisitionResult(export(), "BROWSER_AUTOMATION_REQUIRED")
        http = MagicMock(side_effect=PipelineError("HTTP unsupported"))
        browser = MagicMock(return_value=result)
        self.assertIs(select_fetcher(DAY, DAY, "auto", browser, http), result)
        browser.assert_called_once_with(DAY, DAY)

    def test_explicit_http_never_silently_uses_browser(self):
        browser = MagicMock()
        with self.assertRaises(PipelineError):
            select_fetcher(DAY, DAY, "http", browser)
        browser.assert_not_called()

    def test_browser_protocol_simulated_download_on_popup_and_no_secrets(self):
        # Adquisición completa simulada, ninguna red ni navegador real.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.xlsx"
            path.write_bytes(export())
            browser, probe, context, page = [MagicMock() for _ in range(4)]
            probe.new_page.return_value.evaluate.return_value = "Mozilla/5.0 HeadlessChrome"
            browser.new_context.side_effect = [probe, context]
            context.new_page.return_value = page
            context.cookies.return_value = [{"name": "ASP.NET_SessionId", "value": "private-cookie"}]
            page.goto.return_value.status = 200
            page.content.return_value = '<input name="GXState" value="private-state">'
            page.expect_response.return_value.__enter__.return_value.value.status = 200
            tr = MagicMock()
            tr.locator.return_value.all_text_contents.return_value = ["24/08/2026", "Frutas", "MANZANA",
                "RED DELICI", "R. NEGRO", "CAJA", "Elegido", "GRANDE", "", "0,00", "1.500,00"]
            download = MagicMock()
            download.path.return_value = str(path)
            download.failure.return_value = None
            handlers = {}
            page.on.side_effect = lambda event, handler: handlers.update({event: handler})
            popup = MagicMock()
            popup.on.side_effect = lambda event, handler: handlers.update({"popup_" + event: handler})
            context.on.side_effect = lambda event, handler: handlers.update({"context_" + event: handler})
            def locator(selector):
                item = MagicMock()
                if selector.startswith("#GridContainerTbl"):
                    item.all.return_value = [tr]
                if selector == "#EXPORT":
                    def click():
                        handlers["context_page"](popup)
                        handlers["popup_download"](download)
                    item.click.side_effect = click
                return item
            page.locator.side_effect = locator
            fake = MagicMock()
            fake.return_value.__enter__.return_value.chromium.launch.return_value = browser
            with patch.dict(sys.modules, {"playwright": MagicMock(),
                                           "playwright.sync_api": SimpleNamespace(sync_playwright=fake)}):
                result = browser_fetch(DAY, DAY)
            self.assertEqual(result.payload, path.read_bytes())
            self.assertEqual(result.classification, "BROWSER_AUTOMATION_REQUIRED")
            self.assertNotIn("private-cookie", json.dumps(result.diagnostics))
            self.assertNotIn("private-state", json.dumps(result.diagnostics))
            download.delete.assert_called_once()
            context.close.assert_called_once()
            browser.close.assert_called_once()

    def test_window_limit_and_range_parser(self):
        validate_window("2026-08-19", "2026-08-24")
        with self.assertRaises(PipelineError):
            validate_window("2026-08-01", "2026-08-24")
        body = export([row(), row(Fecha=datetime(2026, 8, 25))])
        self.assertEqual(len(parse_export(body, DAY, "2026-08-25")), 2)
        with self.assertRaises(PipelineError):
            parse_export(body, DAY)

    def test_temporary_url_has_no_ids_or_tokens_in_diagnostics(self):
        endpoint = public_endpoint("https://ssma.magyp.gob.ar/PublicTempStorage/export-session.xlsx?secret=private")
        self.assertNotIn("session", endpoint)
        self.assertNotIn("private", endpoint)

    def test_observation_level_and_kg_unknown(self):
        result = normalized([row(), row(Variedad="Prom.Esp.", Procedencia=None), row(Especie=None)])
        self.assertEqual([r["observation_level"] for r in result], ["detail", "species_summary", "unknown"])
        self.assertTrue(all(r["kg_semantics_status"] == "unknown" and r["volume"] is None for r in result))

    def test_documented_and_contextual_currency_are_distinct(self):
        legacy = normalized()[0]
        self.assertEqual(legacy["currency_evidence"], "contextual")
        body = export()
        from scripts.magyp.mcba.model import PARSER_VERSION, SCHEMA_VERSION, ENDPOINT
        m = RawManifest("mcba", "market_price_observation", ENDPOINT, "GET",
            {"date_from": DAY, "date_to": DAY}, "2026-10-06T12:00:00Z", 200, None, None,
            len(body), sha256(body), SCHEMA_VERSION, PARSER_VERSION, 1, "validated", "test", "browser_automation",
            "ARS", "ARS/kg", currency_evidence="documented")
        self.assertEqual(normalize(parse_export(body, DAY), m)[0]["currency_evidence"], "documented")

    def test_encoding_rule_is_exact_and_manual_review_not_applied(self):
        rules = [{"dimension": "variety", "source_value": "PI¥A", "canonical_value": "PIÑA", "status": "validated"}]
        self.assertEqual(normalized_label("variety", "PI¥A", rules), "PIÑA")
        self.assertEqual(normalized_label("variety", "OTHER¥LABEL", rules), "OTHER¥LABEL")
        rules[0]["status"] = "manual_review"
        self.assertEqual(normalized_label("variety", "PI¥A", rules, True), "PI¥A")

    def test_observed_alias_only_probable_not_normalized(self):
        rules = [{"dimension": "package", "source_value": "Ca", "canonical_value": "CAJA", "status": "observed"}]
        self.assertEqual(normalized_label("package", "Ca", rules), "CA")
        self.assertEqual(normalized_label("package", "Ca", rules, True), "CAJA")

    def test_multiple_candidates_have_no_assigned_match(self):
        m = normalized()
        result = mutual_unique_matches([current(), current()], m, [])
        self.assertTrue(all(r["status"] == "ambiguous" for r in result))
        self.assertFalse(any(r["magyp_index"] is not None and r["current_index"] is not None for r in result))

    def test_reverse_multiple_candidates_are_ambiguous(self):
        m = normalized([row(), row(Calidad="Comercial")])
        result = mutual_unique_matches([current()], m, [])
        self.assertEqual(len(result), 3)
        self.assertTrue(all(r["status"] == "ambiguous" for r in result))

    def test_partial_period_coverage_days_unknown_expected_calendar(self):
        r = normalized()
        second = dict(r[0], observation_id="second-day", observation_date="2026-08-25")
        data = dashboard_rows(build_analytical(r + [second]))
        self.assertEqual(data["MONTHLY"][0]["coverage_days"], 2)
        self.assertEqual(data["MONTHLY"][0]["aggregation_status"], "partial_period")
        self.assertIsNone(data["MONTHLY"][0]["expected_days"])
        self.assertIsNone(data["MONTHLY"][0]["coverage_ratio"])

    def test_nonoverlap_dates_not_marked_as_missing_coverage(self):
        r = normalized()
        r[0]["observation_date"] = "2026-10-05"
        result, daily, monthly = compare([current()], build_analytical(r))
        self.assertEqual(result, [])
        self.assertEqual(daily, [])

    def test_empty_overlap_report_has_schema_and_no_missing_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('scripts.magyp.mcba.compare_mcba_current_vs_magyp.current_rows', return_value=[current()]), \
                 patch('scripts.magyp.mcba.compare_mcba_current_vs_magyp.read_jsonl', return_value=[]):
                stats = run(Path(folder), Path('unused.csv'))
            self.assertEqual(sum(stats['matches'].values()), 0)
            report = (Path(folder) / 'reports/MCBA_CURRENT_VS_MAGYP.csv').read_text(encoding='utf-8-sig')
            self.assertEqual(len(report.splitlines()), 1)
            self.assertIn('matching_rule', report)


if __name__ == "__main__":
    unittest.main()
