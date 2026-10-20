"""El reporte publicado no debe cargar los parsers ni la adquisición diaria."""
import subprocess
import sys
import unittest
from pathlib import Path


class DependencyTests(unittest.TestCase):
    def test_freshness_build_without_site_packages_or_acquisition_imports(self):
        # -S excluye site-packages, incluso si el entorno de tests tiene openpyxl.
        code = """
import sys
from scripts.magyp import build_price_freshness as freshness
freshness.atomic_write = lambda *args: None
report = freshness.build()
assert len(report['sources']) == 10
for name in ('openpyxl', 'xlrd', 'playwright',
             'scripts.magyp.mcba.update_mcba_dashboard',
             'scripts.magyp.mcba.acquisition', 'scripts.magyp.mcba.model'):
    assert name not in sys.modules, name
print('freshness: stdlib only; published bundle validation retained')
"""
        result = subprocess.run(
            [sys.executable, '-S', '-c', code],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('published bundle validation retained', result.stdout)
