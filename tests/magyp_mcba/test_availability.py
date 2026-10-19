import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.magyp.common.platform import PipelineError, publish_bundle
from scripts.magyp.mcba.update_mcba_dashboard import run_productive, outputs_for
from test_publication import daily
import test_initial_get as fixtures

MODULE = "scripts.magyp.mcba.update_mcba_dashboard."

class AvailabilityTests(unittest.TestCase):
    def test_current_skips_network(self):
        with tempfile.TemporaryDirectory() as tmp, patch(MODULE + "browser_fetch") as fetch:
            root = Path(tmp); target = root / "published"
            publish_bundle(target, outputs_for(daily()), len(daily()))
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            state = run_productive("2026-08-24", root / "raw", target, True)
            self.assertEqual(state["result"], "NO_OP_ALREADY_CURRENT")
            self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})
            fetch.assert_not_called()

    def test_absence_and_errors_preserve_csv(self):
        for kind, stage, expected in [
            ("NO_PUBLICATION", "validate_xlsx", "NO_PUBLICATION"),
            ("TIMEOUT", "initial_get", "SOURCE_UNAVAILABLE"),
            ("HTTP_5XX", "initial_get", "SOURCE_UNAVAILABLE"),
            ("VALIDATION_ERROR", "validate_xlsx", "PIPELINE_ERROR")]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); target = root / "published"
                publish_bundle(target, outputs_for(daily()), len(daily()))
                before = {p.name: p.read_bytes() for p in target.iterdir()}
                error = PipelineError("synthetic")
                error.diagnostics = {"error_type": kind, "acquisition_stage": stage}
                with patch(MODULE + "browser_fetch", side_effect=error):
                    if expected == "PIPELINE_ERROR":
                        with self.assertRaises(PipelineError):
                            run_productive("2026-08-25", root / "raw", target, True)
                    else:
                        self.assertEqual(run_productive("2026-08-25", root / "raw", target, True)["result"], expected)
                state = json.loads((root / "raw/reports/MCBA_RUN_STATUS.json").read_bytes())
                self.assertEqual(state["result"], expected)
                self.assertEqual(state["last_observation_date"], "2026-08-24")
                self.assertTrue(all((target / n).read_bytes() == v for n,v in before.items()))

    def test_valid_browser_export_runs_full_pipeline(self):
        fixture = fixtures.InitialGetTests(methodName="runTest")
        with tempfile.TemporaryDirectory() as tmp, fixture.scenario([200]):
            root = Path(tmp)
            state = run_productive("2026-08-24", root / "raw", root / "published", True)
            self.assertEqual(state["result"], "UPDATED")
            self.assertEqual(state["last_observation_date"], "2026-08-24")
            self.assertTrue((root / "published/MCBA_MAGYP_DAILY.csv").is_file())

    def test_empty_known_export_is_no_publication(self):
        fixture = fixtures.InitialGetTests(methodName="runTest")
        with tempfile.TemporaryDirectory() as tmp, fixture.scenario([200]) as (sessions, _, sleep, _):
            Path(sessions[0][2].fixture_download.path.return_value).write_bytes(fixtures.export([]))
            root = Path(tmp)
            state = run_productive("2026-08-24", root / "raw", root / "published", True)
            self.assertEqual(state["result"], "NO_PUBLICATION")
            self.assertFalse((root / "published/MCBA_MAGYP_DAILY.csv").exists())
            sleep.assert_not_called()
