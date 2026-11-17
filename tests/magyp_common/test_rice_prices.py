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


def rate_document():
    return {
        "schema_version": "bcra-a3500-v1", "source": rice.BCRA_LANDING,
        "source_url": rice.BCRA_URL, "raw_sha256": "a" * 64,
        "rates": [["2022-05-17", 100], ["2022-05-31", 110],
                  ["2022-06-01", 120], ["2022-06-30", 180],
                  ["2022-07-01", 200], ["2022-07-31", 300]],
    }


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

    def test_a3500_monthly_average_excludes_partial_start_and_in_progress_month(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bcra.json"
            path.write_text(json.dumps(rate_document()), encoding="utf-8")
            averages, metadata = rice.monthly_a3500(path, date(2022, 7, 31))
        self.assertEqual(list(averages), ["2022-06"])
        self.assertEqual(averages["2022-06"]["average"], rice.Decimal("150.0000"))
        self.assertEqual(averages["2022-06"]["count"], 2)
        self.assertEqual((metadata["first_month"], metadata["latest_month"]), ("2022-05", "2022-07"))

    def test_conversion_retains_original_ars_qq_and_applies_exact_unit_and_a3500_rules(self):
        cell = {"fecha": "2022-06-01", "periodo_ym": "2022-06",
                "source_locator": "table[1]/row[2]/2022/06", "duplicate_source_rows": [],
                "values": [("LARGO FINO", "15.000,00*", "15000.00", "positive"),
                           ("LARGO ANCHO", "20.000,00", "20000.00", "positive")]}
        capture = {"captured_at_utc": "2026-11-17T12:00:00Z", "raw_sha256": "b" * 64,
                   "capture_id": "fixture", "source_url": rice.INTERNAL_URL}
        fx = {"2022-06": {"average": rice.Decimal("150.0000"), "count": 2,
                           "first_date": "2022-06-01", "last_date": "2022-06-30"}}
        rows = rice._internal_rows([cell], capture, fx,
            {"sha256": "c" * 64, "url": rice.BCRA_URL})
        largo_fino = [row for row in rows if row["rice_variety_raw"] == "LARGO FINO"]
        values = {(row["moneda"], row["unidad"]): row["price"] for row in largo_fino}
        self.assertEqual(values, {("ARS", "QQ"): "15000.00", ("ARS", "KG"): "150.00",
                                   ("USD", "QQ"): "100.0000"})
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

    def test_internal_no_publication_and_source_outage_preserve_last_valid_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "magyp"
            rates = Path(temp) / "bcra.json"
            rates.write_text(json.dumps(rate_document()), encoding="utf-8")
            cells = rice.parse_internal(internal_html(), date(2026, 11, 17))
            fx, metadata = rice.monthly_a3500(rates, date(2026, 11, 17))
            capture = {"captured_at_utc": "2026-11-17T12:00:00Z", "raw_sha256": "d" * 64,
                       "capture_id": "initial", "source_url": rice.INTERNAL_URL}
            valid = rice.build_bundle(rice._internal_rows(cells, capture, fx, metadata))
            output = root / "dashboard" / "commodities" / "rice_internal.csv.gz"
            packed = rice.gzip_bundle(valid)
            rice.atomic_write(output, packed)
            fetcher = lambda url: rice.Download(internal_html(), 200, "text/html", url)
            status, _ = rice.update_internal(root, date(2026, 11, 17), fetcher, rates)
            self.assertEqual(status, "NO_PUBLICATION")
            self.assertEqual(output.read_bytes(), packed)

            def unavailable(_url):
                raise rice.SourceUnavailable("test outage")

            status, record = rice.update_internal(root, date(2026, 11, 17), unavailable, rates)
            self.assertEqual(status, "SOURCE_UNAVAILABLE")
            self.assertEqual(record["last_valid_date"], "2026-07-01")
            self.assertEqual(output.read_bytes(), packed)

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
