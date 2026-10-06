import io
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from scripts.magyp.common.platform import PipelineError, RawManifest, load_raw, sha256
from scripts.magyp.mcba.fetch_mcba import capture, fetch_export
from scripts.magyp.mcba.model import (FIELDS, HEADERS, PARSER_VERSION, SCHEMA_VERSION,
    ENDPOINT, build_analytical, dashboard_rows, normalize, parse_export, validate_canonical)
from scripts.magyp.mcba.normalize_mcba import run as normalize_run
from scripts.magyp.mcba.build_analytical_mcba import run as analytical_run
from scripts.magyp.mcba.build_dashboard_mcba import run as dashboard_run
from scripts.magyp.mcba.compare_mcba_current_vs_magyp import compare

DAY = "2026-08-24"


def row(**overrides):
    r = dict(zip(HEADERS, [datetime(2026, 8, 24), "Frutas", "MANZANA", "RED DELICI", "R. NEGRO",
                           "CAJA", "Elegido", "GRANDE", "GRADO A", 0, 1500]))
    r.update(overrides)
    return r


def export(records=None, headers=None):
    w = Workbook()
    s = w.active
    s.append([None] * 11)
    s.append(["Fecha", datetime(2026, 8, 24), "Hasta", datetime(2026, 8, 24)])
    s.append([None] * 11)
    s.append(headers or HEADERS)
    for r in records if records is not None else [row()]:
        s.append([r[h] for h in HEADERS])
    b = io.BytesIO()
    w.save(b)
    return b.getvalue()


def normalized(records=None, currency="ARS", unit="ARS/kg"):
    body = export(records)
    m = RawManifest("mcba", "market_price_observation", ENDPOINT, None,
                    {"date_from": DAY, "date_to": DAY}, "2026-10-06T12:00:00Z", None, None, None,
                    len(body), sha256(body), SCHEMA_VERSION, PARSER_VERSION, 1, "validated",
                    "fixture-capture", "browser_export_import", currency, unit)
    return normalize(parse_export(body, DAY), m)


class McbaTests(unittest.TestCase):
    def test_complete_canonical_fields_and_dimensions(self):
        r = normalized()[0]
        self.assertEqual(set(r), set(FIELDS))
        self.assertEqual([r[k] for k in ("product", "variety", "origin", "package", "quality", "size", "grade")],
                         ["MANZANA", "RED DELICI", "R. NEGRO", "CAJA", "Elegido", "GRANDE", "GRADO A"])
        self.assertEqual(r["observation_date"], DAY)
        self.assertEqual(r["price_average"], 1500)
        self.assertEqual(r["currency"], "ARS")
        self.assertEqual(r["price_unit"], "ARS/kg")
        self.assertIsNone(r["source_record_id"])
        self.assertIsNone(r["volume"])
        self.assertEqual(r["kg_raw"], 0)
        self.assertIsNone(r["price_min"])
        self.assertEqual(r["original_dimensions"]["Calidad"], "Elegido")

    def test_invalid_date_preserved_flagged(self):
        rows = normalized([row(), row(Fecha="31/02/2026")])
        self.assertIsNone(rows[1]["observation_date"])
        self.assertIn("date_missing", rows[1]["quality_flags"])
        self.assertFalse(build_analytical(rows)[1]["valid_for_price_series"])

    def test_invalid_price_preserved_flagged(self):
        r = normalized([row(**{"Promedio x Kg.": "no disponible"})])[0]
        self.assertIsNone(r["price"])
        self.assertEqual(r["price_raw"], "no disponible")
        self.assertIn("price_missing", r["quality_flags"])

    def test_null_dimensions_and_currency_unit(self):
        r = normalized([row(Especie=None, Variedad=None, Procedencia=None, Envase=None)], None, None)[0]
        self.assertIsNone(r["product_normalized"])
        self.assertIsNone(r["package_normalized"])
        self.assertTrue({"product_missing", "origin_missing", "currency_missing", "unit_missing"}.issubset(r["quality_flags"]))

    def test_zero_and_negative_prices(self):
        for price, flag in ((0, "price_zero"), (-1, "price_negative")):
            with self.subTest(price=price):
                r = normalized([row(**{"Promedio x Kg.": price})])
                self.assertIn(flag, r[0]["quality_flags"])
                self.assertFalse(build_analytical(r)[0]["valid_for_price_series"])

    def test_locale_decimal_and_nonfinite(self):
        r = normalized([row(**{"Promedio x Kg.": "1.234,56"})])[0]
        self.assertEqual(r["price"], 1234.56)
        r = normalized([row(**{"Promedio x Kg.": "NaN"})])[0]
        self.assertIsNone(r["price"])

    def test_exact_duplicates_retained_with_distinct_technical_ids(self):
        rows = normalized([row(), row()])
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["observation_id"], rows[1]["observation_id"])
        self.assertEqual(rows[0]["dimension_key"], rows[1]["dimension_key"])
        self.assertTrue(all("duplicate_candidate" in r["quality_flags"] for r in rows))
        self.assertTrue(all(not r["valid_for_price_series"] for r in build_analytical(rows)))

    def test_dimension_duplicate_with_different_price_is_candidate(self):
        rows = normalized([row(), row(**{"Promedio x Kg.": 1600})])
        self.assertTrue(all("duplicate_candidate" in r["quality_flags"] for r in rows))

    def test_extreme_value_candidate_is_not_silently_deleted(self):
        rows = normalized([row(Variedad=str(i), **{"Promedio x Kg.": v}) for i, v in enumerate([10, 11, 10, 10, 1000])])
        self.assertIn("extreme_value_candidate", rows[-1]["quality_flags"])
        analytical = build_analytical(rows)
        self.assertEqual(len(analytical), 5)
        self.assertTrue(analytical[-1]["valid_for_price_series"])

    def test_species_summary_separate_from_detail(self):
        rows = normalized([row(), row(Variedad="Prom.Esp.", Procedencia=None, Envase=None)])
        self.assertEqual(rows[1]["record_kind"], "species_summary")
        data = dashboard_rows(build_analytical(rows))
        self.assertEqual(len(data["MONTHLY"]), 2)
        self.assertTrue(all(r["coverage_status"] == "partial_unverified" for r in data["MONTHLY"]))

    def test_suspicious_character_preserved(self):
        r = normalized([row(Variedad="PI¥A")])[0]
        self.assertEqual(r["variety"], "PI¥A")
        self.assertIn("suspicious_source_character_preserved", r["parse_warnings"])

    def test_unexpected_html_schema_empty_outside_window(self):
        cases = [b"<html>error</html>", export(headers=["unknown"] + HEADERS[1:]), export([]),
                 export([row(Fecha=datetime(2026, 8, 25))])]
        for body in cases:
            with self.subTest(size=len(body)), self.assertRaises(PipelineError):
                parse_export(body, DAY)

    def test_revisions_select_whole_latest_publication(self):
        old = normalized([row(), row(Especie="PERA")])
        new = normalized([row(**{"Promedio x Kg.": 1800})])
        for r in new:
            r["capture_id"] = "new-capture"
            r["capture_timestamp"] = "2026-10-06T13:00:00Z"
        result = build_analytical(old + new)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["price"], 1800)

    def test_ids_stable_and_sensitive_to_economic_dimensions(self):
        a, b = normalized()[0], normalized()[0]
        self.assertEqual(a["observation_id"], b["observation_id"])
        c = normalized([row(Procedencia="SALTA")])[0]
        self.assertNotEqual(a["observation_id"], c["observation_id"])

    def test_network_disabled_and_dry_run_no_writes(self):
        script = Path("scripts/magyp/mcba/fetch_mcba.py").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "new"
            result = subprocess.run([sys.executable, str(script), "--dry-run", "--data-root", str(target)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertFalse(target.exists())
            result = subprocess.run([sys.executable, str(script), "--date", DAY, "--data-root", str(target)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(target.exists())

    def test_http_error_is_not_captured(self):
        with patch("scripts.magyp.mcba.fetch_mcba.build_opener") as mocked:
            response = mocked.return_value.open.return_value.__enter__.return_value
            response.status = 503
            with self.assertRaises(PipelineError):
                fetch_export("https://ssma.magyp.gob.ar/sample.xlsx")

    def test_wrong_content_type_valid_xlsx_accepted(self):
        with patch("scripts.magyp.mcba.fetch_mcba.build_opener") as mocked:
            response = mocked.return_value.open.return_value.__enter__.return_value
            response.status = 200
            response.read.return_value = export()
            response.headers.get.return_value = "text/html"
            body, status, content_type = fetch_export("https://ssma.magyp.gob.ar/sample.xlsx")
            self.assertEqual(status, 200)
            self.assertEqual(content_type, "text/html")
            self.assertEqual(len(parse_export(body, DAY)), 1)

    def test_end_to_end_traceability_idempotence_regenerability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = export([row(), row(Especie="PERA")])
            folder = capture(body, DAY, root, "browser_export_import")
            rows = normalize_run(root)
            self.assertEqual(rows[0]["raw_sha256"], sha256(load_raw(folder)[0]))
            analytical_run(root)
            dashboard_run(root)
            files = list((root / "dashboard/mcba").glob("*.csv"))
            original = {p.name: p.read_bytes() for p in files}
            normalized_bytes = (root / "normalized/mcba/market_price_observation.jsonl").read_bytes()
            normalize_run(root)
            self.assertEqual(normalized_bytes, (root / "normalized/mcba/market_price_observation.jsonl").read_bytes())
            for p in files:
                p.unlink()
            dashboard_run(root)
            self.assertEqual(original, {p.name: p.read_bytes() for p in files})

    def test_invalid_analytical_preserves_last_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capture(export(), DAY, root, "browser_export_import")
            normalize_run(root)
            analytical_run(root)
            dashboard_run(root)
            path = root / "dashboard/mcba/MCBA_MAGYP_DAILY.csv"
            before = path.read_bytes()
            (root / "analytical/mcba/market_price_observation.jsonl").write_text('{}\n')
            with self.assertRaises(PipelineError):
                dashboard_run(root)
            self.assertEqual(path.read_bytes(), before)

    def test_failed_download_and_normalization_preserve_valid_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = capture(export(), DAY, root, "browser_export_import")
            normalize_run(root)
            analytical_run(root)
            dashboard_run(root)
            path = root / "dashboard/mcba/MCBA_MAGYP_DAILY.csv"
            before = path.read_bytes()
            with self.assertRaises(PipelineError):
                capture(b"<html>503</html>", DAY, root, "http_export", 503)
            (folder / "response.xlsx").write_bytes(b"changed")
            with self.assertRaises(PipelineError):
                normalize_run(root)
            self.assertEqual(path.read_bytes(), before)

    def test_incomplete_capture_blocks_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capture(export(), DAY, root, "browser_export_import")
            normalize_run(root)
            before = (root / "normalized/mcba/market_price_observation.jsonl").read_bytes()
            (root / "raw/mcba/incomplete").mkdir()
            with self.assertRaises(PipelineError):
                normalize_run(root)
            self.assertEqual(before, (root / "normalized/mcba/market_price_observation.jsonl").read_bytes())

    def test_unknown_raw_contract_blocks_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = capture(export(), DAY, root, "browser_export_import")
            path = folder / "manifest.json"
            m = json.loads(path.read_text())
            m["schema_version"] = "unknown"
            path.write_text(json.dumps(m))
            with self.assertRaises(PipelineError):
                normalize_run(root)

    def test_comparison_does_not_treat_month_anchor_as_day(self):
        current = [{"fecha": "2026-08-01", "fecha_precision": "mensual", "rubro": "Frutas",
                    "especie": "Manzana", "variedad": "RED DELICI", "procedencia": "R. NEGRO",
                    "envase": "CAJA", "unidad": "$/kg", "precio": "1500"}]
        result, daily, monthly = compare(current, build_analytical(normalized()))
        self.assertEqual(len(daily), 0)
        self.assertEqual(len(monthly), 1)
        self.assertEqual({r["match_status"] for r in result}, {"monthly_not_comparable", "current_monthly_not_comparable"})


if __name__ == "__main__":
    unittest.main()
