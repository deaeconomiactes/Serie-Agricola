"""Fixtures sintéticos, sin internet ni escrituras en datos del repositorio."""
import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.magyp.fob import (DASHBOARD_FIELDS, FobPipeline, PipelineError, digest, load_calendar,
                              validate_response)

FIXTURES = Path(__file__).parent / "fixtures"
VALID = (FIXTURES / "valid_fob.json").read_bytes()
DAY = "2026-10-02"


def changed(**values):
    obj = json.loads(VALID)
    obj["posts"][0].update(values)
    return json.dumps(obj).encode("utf-8")


class ResponseValidationTests(unittest.TestCase):
    def test_valid_json(self):
        result, rows = validate_response(VALID, 200, DAY)
        self.assertTrue(result.valid)
        self.assertEqual(result.record_count, 1)
        self.assertEqual(rows[0]["posicion"], "00100-SYNTHETIC")

    def test_posts_absent(self):
        result, _ = validate_response(b'{"results": []}', 200, DAY)
        self.assertFalse(result.valid)
        self.assertIn("posts_missing", result.errors)

    def test_empty_weekday_is_anomaly(self):
        result, _ = validate_response(b'{"posts": []}', 200, DAY)
        self.assertFalse(result.valid)
        self.assertEqual(result.classification, "unexpected_empty")

    def test_empty_weekend_is_no_publication(self):
        result, _ = validate_response(b'{"posts": []}', 200, "2026-10-03")
        self.assertTrue(result.valid)
        self.assertEqual(result.classification, "no_publication")

    def test_explicit_calendar_explains_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calendar.json"
            path.write_text(json.dumps({"source_url": "https://www.magyp.gob.ar/example-fixture",
                                        "non_publication_dates": {DAY: "Synthetic fixture only"}}))
            calendar = load_calendar(path)
            self.assertEqual(calendar["sha256"], digest(path.read_bytes()))
            result, _ = validate_response(b'{"posts": []}', 200, DAY, calendar)
            self.assertTrue(result.valid)
            self.assertEqual(result.classification, "no_publication")

    def test_price_invalid(self):
        for value in ["abc", True, "NaN", "Infinity", -1, "1,23", "1e900000"]:
            with self.subTest(value=value):
                result, _ = validate_response(changed(precio=value), 200, DAY)
                self.assertFalse(result.valid)

    def test_date_invalid_or_mismatched(self):
        for value in ["2026-02-30", "not-a-date", "2026-10-01 00:00:00"]:
            with self.subTest(value=value):
                self.assertFalse(validate_response(changed(fecha=value), 200, DAY)[0].valid)

    def test_exact_duplicate_rejected(self):
        obj = json.loads(VALID)
        obj["posts"].append(copy.deepcopy(obj["posts"][0]))
        result, _ = validate_response(json.dumps(obj).encode(), 200, DAY)
        self.assertEqual(result.errors, ("exact_duplicate",))

    def test_conflicting_identity_rejected(self):
        obj = json.loads(VALID)
        second = copy.deepcopy(obj["posts"][0])
        second["precio"] = 200
        obj["posts"].append(second)
        result, _ = validate_response(json.dumps(obj).encode(), 200, DAY)
        self.assertEqual(result.errors, ("conflicting_identity",))

    def test_schema_changed_extra_or_missing(self):
        for key in ("currency", "añoHasta"):
            obj = json.loads(VALID)
            if key == "currency":
                obj["posts"][0][key] = "unknown"
            else:
                del obj["posts"][0][key]
            result, _ = validate_response(json.dumps(obj).encode(), 200, DAY)
            self.assertEqual(result.classification, "schema_error")

    def test_http_error(self):
        for status in [None, 302, 404, 500]:
            self.assertEqual(validate_response(VALID, status, DAY)[0].classification, "service_error")

    def test_unexpected_html_and_bad_json(self):
        result, _ = validate_response((FIXTURES / "unexpected.html").read_bytes(), 200, DAY)
        self.assertEqual(result.classification, "unexpected_html")
        self.assertEqual(validate_response(b'{broken', 200, DAY)[0].classification, "invalid_json")

    def test_repeated_json_key_rejected(self):
        self.assertFalse(validate_response(b'{"posts":[], "posts":[]}', 200, DAY)[0].valid)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        quiet_logs = patch("sys.stdout", new=io.StringIO())
        quiet_logs.start()
        self.addCleanup(quiet_logs.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pipeline = FobPipeline(Path(self.tmp.name) / "data", Path(self.tmp.name) / "external-raw")

    def fetch(self, body=VALID, status=200, content_type="application/json", day=DAY):
        return self.pipeline.fetch(day, transport=lambda _: (status, content_type, body))

    def baseline(self):
        self.fetch()
        self.pipeline.normalize()
        result = self.pipeline.build()
        self.assertTrue(result.published)
        return self.pipeline.dashboard.read_bytes()

    def test_wrong_content_type_with_json_publishes(self):
        manifest = self.fetch(content_type="text/html; charset=utf-8")
        self.assertEqual(manifest.content_type, "text/html; charset=utf-8")
        self.assertTrue(manifest.validation.valid)
        self.pipeline.normalize()
        result = self.pipeline.build()
        self.assertEqual(result.record_count, 1)
        rows = list(csv.DictReader(io.StringIO(self.pipeline.dashboard.read_text())))
        self.assertEqual(list(rows[0]), DASHBOARD_FIELDS)
        self.assertEqual(rows[0]["position"], "00100-SYNTHETIC")
        self.assertNotIn("currency", rows[0])
        self.assertNotIn("product", rows[0])

    def test_normalize_build_are_idempotent(self):
        original = self.baseline()
        pointer = self.pipeline.pointer.read_bytes()
        self.pipeline.normalize()
        result = self.pipeline.build()
        self.assertFalse(result.changed)
        self.assertEqual(original, self.pipeline.dashboard.read_bytes())
        self.assertEqual(pointer, self.pipeline.pointer.read_bytes())

    def test_immutable_captures_and_revisions(self):
        first = self.fetch()
        raw = self.pipeline.raw / first.capture_id / "response.json"
        old_bytes = raw.read_bytes()
        second = self.fetch(changed(precio="300.125"))
        self.assertNotEqual(first.capture_id, second.capture_id)
        self.assertEqual(old_bytes, raw.read_bytes())
        result = self.pipeline.normalize()
        self.assertEqual(result.record_count, 2)
        self.assertEqual(self.pipeline.build().record_count, 1)
        row = list(csv.DictReader(io.StringIO(self.pipeline.dashboard.read_text())))[0]
        self.assertEqual(row["price"], "300.125")
        pointer = json.loads(self.pipeline.pointer.read_text())
        norm = list(csv.DictReader(io.StringIO((self.pipeline.normalized / pointer["file"]).read_text())))
        self.assertEqual(norm[0]["observation_id"], norm[1]["observation_id"])
        self.assertNotEqual(norm[0]["record_id"], norm[1]["record_id"])

    def test_revision_removes_position_from_current_view(self):
        obj = json.loads(VALID)
        extra = copy.deepcopy(obj["posts"][0])
        extra["posicion"] = "SECOND-SYNTHETIC"
        obj["posts"].append(extra)
        self.fetch(json.dumps(obj).encode())
        self.pipeline.normalize()
        self.assertEqual(self.pipeline.build().record_count, 2)
        self.fetch()
        self.assertEqual(self.pipeline.normalize().record_count, 3)
        self.assertEqual(self.pipeline.build().record_count, 1)

    def test_failed_fetch_preserves_last_dashboard_and_blocks_stale_build(self):
        original = self.baseline()
        cases = [(b'{"posts":[]}', 200), (b'{"missing":[]}', 200),
                 (changed(precio="bad"), 200), (changed(fecha="bad"), 200),
                 ((FIXTURES / "unexpected.html").read_bytes(), 200), (VALID, 500)]
        for body, status in cases:
            with self.subTest(status=status, body_length=len(body)):
                with self.assertRaises(PipelineError):
                    self.fetch(body, status)
                with self.assertRaises(PipelineError):
                    self.pipeline.normalize()
                with self.assertRaises(PipelineError):
                    self.pipeline.build()
                self.assertEqual(original, self.pipeline.dashboard.read_bytes())

    def test_failed_normalization_preserves_dashboard(self):
        original = self.baseline()
        manifest = self.fetch()
        raw = self.pipeline.raw / manifest.capture_id / "response.json"
        raw.write_bytes(b'{"posts":[]}')  # Simular corrupción externa; el pipeline nunca hace esto.
        with self.assertRaises(PipelineError):
            self.pipeline.normalize()
        with self.assertRaises(PipelineError):
            self.pipeline.build()
        self.assertEqual(original, self.pipeline.dashboard.read_bytes())

    def test_failed_output_validation_preserves_dashboard(self):
        original = self.baseline()
        self.fetch(changed(precio=400))
        self.pipeline.normalize()
        def reject(_):
            raise PipelineError("synthetic validation failure")
        with self.assertRaises(PipelineError):
            self.pipeline.build(output_validator=reject)
        self.assertEqual(original, self.pipeline.dashboard.read_bytes())
        with self.assertRaises(PipelineError):
            self.pipeline.build()

    def test_replace_failure_preserves_dashboard(self):
        original = self.baseline()
        self.fetch(changed(precio=400))
        self.pipeline.normalize()
        import os
        real_replace = os.replace
        def refuse_dashboard(src, target):
            if Path(target) == self.pipeline.dashboard:
                raise OSError("synthetic disk failure")
            return real_replace(src, target)
        with patch("scripts.magyp.fob.os.replace", side_effect=refuse_dashboard):
            with self.assertRaises(OSError):
                self.pipeline.build()
        self.assertEqual(original, self.pipeline.dashboard.read_bytes())
        self.assertFalse(list(self.pipeline.dashboard.parent.glob(".fob-*.tmp")))

    def test_explained_empty_is_noop_not_delete(self):
        original = self.baseline()
        manifest = self.fetch(b'{"posts":[]}', day="2026-10-03")
        self.assertTrue(manifest.validation.valid)
        self.assertEqual(self.pipeline.normalize().classification, "no_publication")
        self.assertFalse(self.pipeline.build().published)
        self.assertEqual(original, self.pipeline.dashboard.read_bytes())

    def test_invalid_payload_is_not_retained(self):
        body = b'<html><input name="token" value="fixture-secret"></html>'
        with self.assertRaises(PipelineError):
            self.fetch(body)
        manifests = list(self.pipeline.raw.glob("*/manifest.json"))
        self.assertEqual(len(manifests), 1)
        obj = json.loads(manifests[0].read_text())
        self.assertIsNone(obj["response_file"])
        self.assertEqual(obj["sha256"], digest(body))
        self.assertNotIn("fixture-secret", manifests[0].read_text())
        self.assertFalse(list(self.pipeline.raw.glob("*/response.json")))

    def test_lock_prevents_concurrent_mutation(self):
        with self.pipeline.locked():
            with self.assertRaises(PipelineError):
                self.fetch()

    def test_missing_raw_history_blocks_loss_of_dashboard_dates(self):
        original = self.baseline()
        # Simular un runner nuevo con sólo el dashboard anterior, sin su RAW durable.
        other = FobPipeline(self.pipeline.data, Path(self.tmp.name) / "empty-raw")
        body = changed(fecha="2026-10-05 00:00:00.000")
        other.fetch("2026-10-05", transport=lambda _: (200, "application/json", body))
        other.normalize()
        with self.assertRaises(PipelineError):
            other.build()
        self.assertEqual(original, self.pipeline.dashboard.read_bytes())

    def test_build_without_capture_is_blocked(self):
        with self.assertRaises(PipelineError):
            self.pipeline.build()


if __name__ == "__main__":
    unittest.main()
