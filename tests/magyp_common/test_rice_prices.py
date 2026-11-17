import csv
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.magyp import rice_prices as rice


def internal_html():
    return b"""<!doctype html><html><body><p>$/QQ: Pesos Argentinos por Quintal</p>
    <table><tr><th>Ano/Mes</th><th>LARGO FINO</th><th>LARGO ANCHO</th></tr>
    <tr><td>2026/06</td><td>13.500,00*</td><td>20.000,00</td></tr>
    <tr><td>2026/06</td><td>13.500,00*</td><td>20.000,00</td></tr>
    <tr><td>2026/07</td><td>14.000,50</td><td></td></tr></table></body></html>"""


def labels_for(year):
    return rice.FOB_LABELS_2017_2024 if year <= 2024 else rice.FOB_LABELS_2025_ON


def fob_html(year, labels=None, options=False, omit_month=None):
    labels = labels or labels_for(year)
    rows = ["<html><body><h1>Arroz - Serie Precios Internacionales (U$S/Ton FOB)</h1><table>",
            "<tr><td>ARROZ - SERIE PRECIOS INTERNACIONALES (U$S/Ton FOB)</td></tr>",
            "<tr><td>" + str(year) + "</td>" + "".join(f"<td>{label}</td>" for label in labels) + "</tr>"]
    for month, name in enumerate(rice.MONTHS, start=1):
        if month == omit_month:
            continue
        month_label = f"{name} {year % 100:02d}" if year <= 2024 else name
        values = ["-" if month == 2 and index == 0 else str(300 + month + index)
                  for index, _ in enumerate(labels)]
        rows.append(f"<tr><td>{month_label}</td>" + "".join(f"<td>{value}</td>" for value in values) + "</tr>")
    rows.append("<tr><td colspan='20'>Fuente: Osiriz/InfoArro</td></tr></table>")
    if options:
        rows.append("<select name='jumpMenu'>")
        for year_option in range(2017, year + 1):
            filename = f"{900000 + year - year_option}_{year_option}.php"
            url = ("https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/areas/regionales/"
                   "_archivos/000020_Precios%20Internacionales/000052_Arroz/000002_Hist%C3%B3ricos/" + filename)
            rows.append(f"<option value='{url}'>{year_option}</option>")
        rows.append("</select>")
    rows.append("</body></html>")
    return "".join(rows).encode("utf-8")


class RicePricesTests(unittest.TestCase):
    def test_internal_months_duplicates_and_original_markers_are_preserved(self):
        cells = rice.parse_internal(internal_html(), date(2026, 11, 17))
        self.assertEqual([row["periodo_ym"] for row in cells], ["2026-06", "2026-07"])
        self.assertEqual(cells[0]["values"][0], ("LARGO FINO", "13.500,00*", "13500.00", "positive"))
        self.assertEqual(len(cells[0]["duplicate_source_rows"]), 1)
        self.assertEqual(cells[1]["values"][1][3], "missing")
        with self.assertRaisesRegex(rice.RiceError, "posterior"):
            rice.parse_internal(internal_html().replace(b"2026/07", b"2026/12"), date(2026, 11, 17))
        conflict = internal_html().replace(b"2026/06</td><td>13.500,00*</td><td>20.000,00</td></tr>\n    <tr><td>2026/07", b"2026/06</td><td>13.500,00*</td><td>21.000,00</td></tr>\n    <tr><td>2026/07")
        with self.assertRaisesRegex(rice.RiceError, "conflictivas"):
            rice.parse_internal(conflict, date(2026, 11, 17))

    def test_fob_history_keeps_year_specific_quality_labels_and_does_not_fill_months(self):
        historical = rice.parse_fob_page(fob_html(2017, options=False, omit_month=7), 2017)
        year, values, _options, labels = historical
        self.assertEqual(year, 2017)
        self.assertIn("Thai5", labels)
        self.assertEqual(len(set(row["periodo_ym"] for row in values)), 11)
        self.assertNotIn("2017-07", {row["periodo_ym"] for row in values})
        current = rice.parse_fob_page(fob_html(2026, options=True))
        self.assertEqual(current[0], 2026)
        self.assertNotIn("Thai5", current[3])
        self.assertEqual([year for year, _ in current[2]], list(range(2017, 2027)))

    def test_internal_conversion_retains_ars_qq_and_applies_only_simple_unit_conversion(self):
        cell = {"fecha": "2022-06-01", "periodo_ym": "2022-06",
                "source_locator": "table[1]/row[2]/2022/06", "duplicate_source_rows": [],
                "values": [("LARGO FINO", "15.000,00*", "15000.00", "positive"),
                           ("LARGO ANCHO", "20.000,00", "20000.00", "positive")]}
        capture = {"captured_at_utc": "2026-11-17T12:00:00Z", "raw_sha256": "b" * 64,
                   "capture_id": "fixture", "source_url": rice.INTERNAL_URL}
        rows = rice._internal_rows([cell], capture)
        largo_fino = [row for row in rows if row["rice_variety_raw"] == "LARGO FINO"]
        values = {(row["moneda"], row["unidad"]): row["price"] for row in largo_fino}
        self.assertEqual(values, {("ARS", "QQ"): "15000.00", ("ARS", "KG"): "150.00"})
        base = next(row for row in largo_fino if row["moneda"] == "ARS" and row["unidad"] == "QQ")
        self.assertEqual(base["price_raw_source"], "15.000,00*")
        self.assertEqual(base["source_marker"], "*")
        self.assertEqual(base["duplicate_source_rows"], "")
        self.assertIn("100 KG", next(row for row in largo_fino if row["unidad"] == "KG")["conversion_method"])
        expected_rows = 3 * len(rows) + len({row["series_id"] for row in rows}) + 1
        self.assertEqual(len(rice.validate_bundle(rice.build_bundle(rows))), expected_rows)

    def test_history_reductions_and_conflicting_observation_values_fail_closed(self):
        base = {"row_kind": "observation", "tipo_precio": rice.INTERNAL_BASE_TYPE,
                "periodo_ym": "2026-06", "rice_variety_raw": "LARGO FINO",
                "fob_origin_quality_raw": "", "value_status": "positive", "price": "100"}
        with self.assertRaisesRegex(rice.RiceError, "reduce períodos"):
            rice._check_history([base], [], "rice_internal")
        reduced = {**base, "value_status": "missing", "price": ""}
        with self.assertRaisesRegex(rice.RiceError, "celda vacía"):
            rice._check_history([base], [reduced], "rice_internal")

    def test_internal_update_ignores_missing_or_invalid_bcra_and_records_positive_revisions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "magyp"
            project_root = Path(temp) / "project"
            output = root / "dashboard" / "commodities" / "rice_internal.csv.gz"
            fetcher = lambda url: rice.Download(internal_html(), 200, "text/html", url)
            # No BCRA file exists in the project root; the internal MAGyP publication stands alone.
            with patch.object(rice, "ROOT", project_root):
                status, record = rice.update_internal(root, date(2026, 11, 17), fetcher)
            self.assertEqual(status, "UPDATED")
            observations = [row for row in rice.read_bundle(output) if row["row_kind"] == "observation"]
            self.assertEqual({row["moneda"] for row in observations}, {"ARS"})
            self.assertEqual({row["unidad"] for row in observations}, {"QQ", "KG"})
            self.assertTrue(all(not row["fx_a3500_monthly_avg"] for row in observations))
            initial = output.read_bytes()

            # An invalid A3500 document also has no bearing on the internal source.
            invalid_bcra = project_root / "data" / "carnes" / "dashboard" / "bcra_a3500.json"
            invalid_bcra.parent.mkdir(parents=True)
            invalid_bcra.write_text("not-json", encoding="utf-8")
            revised_html = internal_html().replace(b"13.500,00*", b"16.500,00*")
            revised_fetcher = lambda url: rice.Download(revised_html, 200, "text/html", url)
            with patch.object(rice, "ROOT", project_root):
                status, revised_state = rice.update_internal(root, date(2026, 11, 17), revised_fetcher)
            self.assertEqual(status, "UPDATED")
            self.assertEqual(revised_state["historical_revisions_recorded"], 1)
            ledger_path = root / "reports" / "RICE_INTERNAL_REVISIONS.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["schema_version"], rice.REVISION_LEDGER_VERSION)
            self.assertEqual(len(ledger["revisions"]), 1)
            revision = ledger["revisions"][0]
            self.assertEqual(revision["periodo_ym"], "2026-06")
            self.assertEqual(revision["rice_variety_raw"], "LARGO FINO")
            self.assertEqual(revision["previous"]["price_ars_qq"], "13500.00")
            self.assertEqual(revision["current"]["price_ars_qq"], "16500.00")
            self.assertNotEqual(revision["previous"]["raw_sha256"], revision["current"]["raw_sha256"])
            self.assertNotEqual(revision["previous"]["capture_id"], revision["current"]["capture_id"])
            self.assertTrue(revision["previous"]["raw_artifact"].endswith("/response.html"))
            rice._validate_revision_ledger(ledger)

            # Identical republication is a no-op and keeps the revision history append-only.
            status, _ = rice.update_internal(root, date(2026, 11, 17), revised_fetcher)
            self.assertEqual(status, "NO_PUBLICATION")
            self.assertEqual(len(json.loads(ledger_path.read_text(encoding="utf-8"))["revisions"]), 1)

            # If the audit ledger cannot be persisted, roll the bundle back to its last valid version.
            stable_bundle = output.read_bytes()
            second_revision = internal_html().replace(b"13.500,00*", b"17.500,00*")
            second_fetcher = lambda url: rice.Download(second_revision, 200, "text/html", url)
            atomic_write = rice.atomic_write
            def fail_revision_ledger(path, payload):
                if Path(path) == ledger_path:
                    raise OSError("simulated ledger write failure")
                return atomic_write(path, payload)
            with patch.object(rice, "atomic_write", side_effect=fail_revision_ledger), \
                    patch.object(rice.traceback, "print_exc"):
                status, failed_state = rice.update_internal(root, date(2026, 11, 17), second_fetcher)
            self.assertEqual(status, "PIPELINE_ERROR")
            self.assertIn("simulated ledger write failure", failed_state["diagnostic_note"])
            self.assertEqual(output.read_bytes(), stable_bundle)
            self.assertEqual(len(json.loads(ledger_path.read_text(encoding="utf-8"))["revisions"]), 1)

            def unavailable(_url):
                raise rice.SourceUnavailable("test outage")

            packed = output.read_bytes()
            status, record = rice.update_internal(root, date(2026, 11, 17), unavailable)
            self.assertEqual(status, "SOURCE_UNAVAILABLE")
            self.assertEqual(record["last_valid_date"], "2026-07-01")
            self.assertEqual(output.read_bytes(), packed)
            self.assertNotEqual(initial, packed)

    def test_fob_no_publication_and_source_outage_preserve_last_valid_bundle(self):
        current = fob_html(2026, options=True)
        page = rice.parse_page(current)
        mapping = {rice.FOB_URL: current}
        for value, label in page.options:
            year = int(label)
            mapping[rice.canonical_historical_url(value)] = fob_html(year)

        def fetcher(url):
            return rice.Download(mapping[url], 200, "text/html", url)

        with tempfile.TemporaryDirectory() as temp, patch.object(rice.time, "sleep"):
            root = Path(temp) / "magyp"
            status, first = rice.update_fob(root, date(2026, 12, 31), fetcher)
            self.assertEqual(status, "UPDATED")
            output = root / "dashboard" / "commodities" / "rice_fob.csv.gz"
            valid = output.read_bytes()
            observations = [row for row in rice.read_bundle(output) if row["row_kind"] == "observation"]
            self.assertTrue(any(row["fob_origin_quality_raw"] == "Thai5" for row in observations))
            self.assertTrue(any(row["fob_origin_quality_raw"] == "Thai100" for row in observations))
            status, _ = rice.update_fob(root, date(2026, 12, 31), fetcher)
            self.assertEqual(status, "NO_PUBLICATION")
            self.assertEqual(output.read_bytes(), valid)

            def unavailable(_url):
                raise rice.SourceUnavailable("test outage")

            status, record = rice.update_fob(root, date(2026, 12, 31), unavailable)
            self.assertEqual(status, "SOURCE_UNAVAILABLE")
            self.assertEqual(record["last_valid_date"], "2026-12-01")
            self.assertEqual(output.read_bytes(), valid)

    def test_fob_prices_after_control_date_are_rejected(self):
        current = fob_html(2026, options=True)
        page = rice.parse_page(current)
        mapping = {rice.FOB_URL: current}
        for value, label in page.options:
            mapping[rice.canonical_historical_url(value)] = fob_html(int(label))

        with tempfile.TemporaryDirectory() as temp, patch.object(rice.time, "sleep"):
            status, record = rice.update_fob(
                Path(temp) / "magyp", date(2026, 11, 17),
                lambda url: rice.Download(mapping[url], 200, "text/html", url))
        self.assertEqual(status, "PIPELINE_ERROR")
        self.assertIn("posterior", record["diagnostic_note"])


if __name__ == "__main__":
    unittest.main()
