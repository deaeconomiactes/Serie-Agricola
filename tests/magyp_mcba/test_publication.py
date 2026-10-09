import csv
import io
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from scripts.magyp.common.platform import PipelineError, publish_bundle, sha256
from scripts.magyp.mcba.build_dashboard_mcba import run as build
from scripts.magyp.mcba.update_mcba_dashboard import (
    merge_daily, outputs_for, publish_incremental, read_bundle, update, validate_daily)
from test_mcba import normalized, row
from scripts.magyp.mcba.model import dashboard_rows, build_analytical


def daily():
    return dashboard_rows(build_analytical(normalized()))["DAILY"]


class PublicationTests(unittest.TestCase):
    def test_contract_preserves_raw_and_no_volume(self):
        r = daily()[0]
        self.assertEqual(r["currency"], "ARS")
        self.assertEqual(r["price_unit"], "kg")
        self.assertEqual(r["price_unit_raw"], "ARS/kg")
        self.assertEqual(r["kg_raw"], 0)
        self.assertIsNone(r["volume"])
        self.assertEqual(r["product_raw"], "MANZANA")
        self.assertEqual(r["data_source"], "MAGYP")
        validate_daily(daily())

    def test_merge_preserves_uncovered_dates(self):
        old = daily()
        fresh = deepcopy(old)
        fresh[0].update(date="2026-08-25", observation_id="new-id")
        merged = merge_daily(old, fresh)
        self.assertEqual(len(merged), 2)
        self.assertEqual({r["date"] for r in merged}, {"2026-08-24", "2026-08-25"})

    def test_whole_day_revision_does_not_fill_removed_product(self):
        old = daily()
        other = deepcopy(old[0])
        other.update(product_normalized="PERA", product_raw="PERA", observation_id="other-id")
        revised = deepcopy(old)
        revised[0].update(price=1700, capture_id="revision", capture_timestamp="2026-10-06T13:00:00Z")
        self.assertEqual(merge_daily(old + [other], revised), revised)

    def test_old_revision_rejected(self):
        old = daily()
        fresh = deepcopy(old)
        fresh[0]["capture_timestamp"] = "2026-10-06T11:00:00Z"
        with self.assertRaises(PipelineError):
            merge_daily(old, fresh)

    def test_empty_invalid_schema_currency_volume_and_duplicates_rejected(self):
        for field, value in [("price", "bad"), ("date", "2026-02-31"), ("currency", "USD"),
                             ("price_unit", "tn"), ("volume", 0), ("raw_sha256", "z" * 64),
                             ("product_normalized", "")]:
            with self.subTest(field=field):
                rows = daily()
                rows[0][field] = value
                with self.assertRaises(PipelineError):
                    validate_daily(rows)
        with self.assertRaises(PipelineError):
            validate_daily([])
        with self.assertRaises(PipelineError):
            validate_daily(daily() * 2)
        changed = daily()
        changed[0].pop("product_raw")
        with self.assertRaises(PipelineError):
            merge_daily(daily(), changed)

    def test_failed_merge_preserves_all_published_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "published"
            staging = Path(folder) / "staging"
            publish_bundle(target, outputs_for(daily()), 1)
            before = {p.name: sha256(p.read_bytes()) for p in target.iterdir()}
            # Valid CSV shape but invalid economic contract.
            bad = daily()
            bad[0]["price"] = "bad"
            payload = io.StringIO()
            writer = csv.DictWriter(payload, fieldnames=list(bad[0]))
            writer.writeheader(); writer.writerows(bad)
            publish_bundle(staging, {"MCBA_MAGYP_DAILY.csv": payload.getvalue().encode()}, 1)
            with self.assertRaises(PipelineError):
                publish_incremental(staging, target)
            self.assertEqual(before, {p.name: sha256(p.read_bytes()) for p in target.iterdir()})

    def test_successful_incremental_publish_and_idempotence(self):
        with tempfile.TemporaryDirectory() as folder:
            target, staging = Path(folder) / "published", Path(folder) / "staging"
            publish_bundle(target, outputs_for(daily()), 1)
            fresh = daily()
            fresh[0].update(date="2026-08-25", observation_id="next-date")
            publish_bundle(staging, outputs_for(fresh), 1)
            publish_incremental(staging, target)
            self.assertEqual(len(read_bundle(target)), 2)
            first = {p.name: sha256(p.read_bytes()) for p in target.iterdir()}
            publish_incremental(staging, target)
            self.assertEqual(first, {p.name: sha256(p.read_bytes()) for p in target.iterdir()})

    def test_fetch_error_leaves_bundle_and_marks_last_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            target, raw = Path(folder) / "published", Path(folder) / "raw"
            publish_bundle(target, outputs_for(daily()), 1)
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            with patch("scripts.magyp.mcba.update_mcba_dashboard.browser_fetch", side_effect=PipelineError("HTTP fallido")):
                with self.assertRaises(PipelineError):
                    update("2026-08-25", raw, target, True)
            self.assertTrue(all((target / name).read_bytes() == content for name, content in before.items()))
            self.assertEqual(json.loads((target / "MCBA_MAGYP_UPDATE_STATUS.json").read_text())["source_status"], "MAGYP_LAST_VALID")

    def test_partial_invalid_capture_is_not_published(self):
        rows = build_analytical(normalized([row(), row(**{"Promedio x Kg.": "inválido"})]))
        with patch("scripts.magyp.mcba.build_dashboard_mcba.read_jsonl", return_value=rows):
            with self.assertRaises(PipelineError):
                build(Path("unused"))
