import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from scripts.magyp.investigate_corrientes import (
    PublicLinks, classify, inspect_legacy, main, probe)


class CorrientesInvestigationTests(unittest.TestCase):
    def test_broken_provider_is_not_misclassified_as_historical(self):
        results = [{"url":"https://www.mptt.gov.ar/site13/index.php/preciosmercado", "result":"dns_error"}]
        self.assertEqual(classify(results), "D_NO_UTILIZABLE")
        results[0]["result"] = "html_received"
        self.assertEqual(classify(results), "PENDING_REVIEW")

    def test_rejects_unknown_urls_and_session_queries_without_requests(self):
        for url in ["https://other.example/precios", "https://www.mptt.gov.ar/precios?token=synthetic",
                    "https://name:synthetic@www.mptt.gov.ar/precios"]:
            with self.subTest(url=url), patch("scripts.magyp.investigate_corrientes.build_opener") as opener:
                with self.assertRaises(ValueError):
                    probe(url)
                opener.assert_not_called()

    def test_public_links_use_image_label_without_script_or_hidden_state(self):
        parser = PublicLinks()
        parser.feed('<script>synthetic-private-state</script><input type="hidden" value="synthetic-private-state">'
                    '<a href="http://www.mptt.gov.ar/site13/index.php/preciosmercado">'
                    '<img alt="Precios Diarios del Mercado de Corrientes"></a>')
        self.assertIn("Corrientes", parser.links[0][1])
        self.assertNotIn("synthetic-private-state", json.dumps(parser.text))

    def test_legacy_metrics_exclude_future_invalid_dates_and_invalid_prices_without_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy.csv"
            rows = [
                {"mercado":"Mercado de Corrientes","fecha":"2026-08-25","precio_observado":"1.250,50",
                 "precio_kg_estimado":"125.05","confianza_conversion_precio":"Alta","especie":"BANANA",
                 "envase":"Caja","unidad":"$/bulto"},
                {"mercado":"Mercado de Corrientes","fecha":"2026-10-07","precio_observado":"200"},
                {"mercado":"Mercado de Corrientes","fecha":"bad","precio_observado":"200"},
                {"mercado":"Mercado de Corrientes","fecha":"2026-08-24","precio_observado":"0"},
                {"mercado":"Mercado Central de Buenos Aires","fecha":"2026-08-25","precio_observado":"200"},
            ]
            fields = list(dict.fromkeys(k for r in rows for k in r))
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
                writer.writeheader(); writer.writerows(rows)
            before = path.read_bytes()
            metrics = inspect_legacy(path, date(2026,10,6))
            self.assertEqual(metrics["rows"], 4)
            self.assertEqual(metrics["valid_observed_rows"], 1)
            self.assertEqual(metrics["comparable_rows"], 1)
            self.assertEqual(metrics["date_max"], "2026-08-25")
            self.assertEqual(metrics["future_date_rows"], 1)
            self.assertEqual(metrics["invalid_date_rows"], 1)
            self.assertEqual(metrics["invalid_or_nonpositive_price_rows"], 1)
            self.assertEqual(metrics["dimension_counts"]["variedad"], 0)
            self.assertEqual(path.read_bytes(), before)

    def test_default_is_dry_run_without_writes_or_network(self):
        with patch("sys.argv", ["investigate_corrientes.py"]), patch(
                "scripts.magyp.investigate_corrientes.probe") as fetch, patch(
                "scripts.magyp.investigate_corrientes.inspect_legacy") as inspect:
            main()
            fetch.assert_not_called()
            inspect.assert_not_called()
