import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from scripts.magyp.common.platform import (PipelineError, RawManifest, atomic_write, csv_bytes,
    load_raw, official_url, publish_bundle, sha256, store_raw, validate_manifest)


def manifest(payload=b"public", **overrides):
    m = RawManifest("mcba", "market_price_observation", "https://ssma.magyp.gob.ar/frutas.precios.aspx",
                    None, {"date_from": "2026-08-24", "date_to": "2026-08-24"},
                    "2026-10-06T12:00:00Z", None, None, None, len(payload), sha256(payload),
                    "market_price_observation-v1", "mcba-xlsx-1.0.0", 1, "validated", "capture-1",
                    "browser_export_import")
    return replace(m, **overrides)


class PlatformTests(unittest.TestCase):
    def test_known_sha256(self):
        self.assertEqual(sha256(b"abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_manifest_roundtrip_and_exact_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = store_raw(Path(tmp), b"public", manifest())
            body, m = load_raw(folder)
            self.assertEqual(body, b"public")
            self.assertEqual(m, manifest())
            saved = json.loads((folder / "manifest.json").read_text())
            self.assertIsNone(saved["http_status"])
            self.assertNotIn("cookies", saved)

    def test_immutable_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_raw(Path(tmp), b"public", manifest())
            with self.assertRaises(FileExistsError):
                store_raw(Path(tmp), b"revision", manifest(b"revision"))
            self.assertEqual(load_raw(Path(tmp) / "raw/mcba/capture-1")[0], b"public")

    def test_revision_new_capture_preserves_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            one = store_raw(Path(tmp), b"public", manifest())
            two = store_raw(Path(tmp), b"revision", manifest(b"revision", capture_id="capture-2"))
            self.assertEqual(one.read_bytes() if one.is_file() else load_raw(one)[0], b"public")
            self.assertEqual(load_raw(two)[0], b"revision")

    def test_tampered_raw_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = store_raw(Path(tmp), b"public", manifest())
            (folder / "response.xlsx").write_bytes(b"tampered")
            with self.assertRaises(PipelineError):
                load_raw(folder)

    def test_no_secrets_public_parameters(self):
        with self.assertRaises(PipelineError):
            validate_manifest(manifest(public_parameters={"token": "redacted"}), b"public")

    def test_bad_manifest_conditions(self):
        cases = [dict(sha256="0" * 64), dict(byte_size=7), dict(validation_status="error"),
                 dict(record_count=0), dict(http_status=403), dict(capture_id="../escape"),
                 dict(captured_at_utc="2026-10-06T12:00:00-03:00"), dict(source="../../escape"),
                 dict(public_parameters={"date_from": "2026-08-24", "date_to": "2026-08-25"}),
                 dict(response_url="https://ssma.magyp.gob.ar/export.xlsx?token=redacted")]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(PipelineError):
                validate_manifest(manifest(**case), b"public")

    def test_allowlist(self):
        for url in ("http://ssma.magyp.gob.ar/x", "https://ssma.magyp.gob.ar.evil/x",
                    "https://user:secret@ssma.magyp.gob.ar/x", "https://ssma.magyp.gob.ar:444/x"):
            with self.subTest(url=url), self.assertRaises(PipelineError):
                official_url(url)

    def test_publish_valid_and_hash_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = csv_bytes([{"price": 5, "flags": ["context"]}], ["price", "flags"])
            publish_bundle(root, {"valid.csv": body}, 1)
            marker = json.loads((root / "_SUCCESS.json").read_text())
            self.assertEqual(marker["files"]["valid.csv"], sha256(body))

    def test_invalid_output_preserves_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = b"price\n5\n"
            publish_bundle(root, {"valid.csv": good}, 1)
            with self.assertRaises(PipelineError):
                publish_bundle(root, {"valid.csv": b"a,b\n1\n"}, 1)
            self.assertEqual((root / "valid.csv").read_bytes(), good)

    def test_empty_output_preserves_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            publish_bundle(root, {"valid.csv": b"price\n5\n"}, 1)
            with self.assertRaises(PipelineError):
                publish_bundle(root, {"valid.csv": b"price\n"}, 0)
            self.assertEqual((root / "valid.csv").read_bytes(), b"price\n5\n")

    def test_bundle_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            publish_bundle(root, {"one.csv": b"p\n1\n", "two.csv": b"p\n2\n"}, 2)
            calls = 0
            def fail_once(path, body):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected failure")
                atomic_write(path, body)
            with patch("scripts.magyp.common.platform.atomic_write", side_effect=fail_once):
                with self.assertRaises(OSError):
                    publish_bundle(root, {"one.csv": b"p\n3\n", "two.csv": b"p\n4\n"}, 2)
            self.assertEqual((root / "one.csv").read_bytes(), b"p\n1\n")
            self.assertEqual((root / "two.csv").read_bytes(), b"p\n2\n")

    def test_repeated_write_preserves_bytes_and_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "valid.csv"
            atomic_write(path, b"same")
            before = path.stat().st_mtime_ns
            atomic_write(path, b"same")
            self.assertEqual(path.stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()
