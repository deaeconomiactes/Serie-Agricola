import tempfile
import unittest
from pathlib import Path

from scripts.ci.prepare_pages import prepare


class PreparePagesCarnesTests(unittest.TestCase):
    def test_only_light_carnes_dashboard_is_copied_to_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / 'source'; destination = root / 'pages'
            carnes = source / 'data/carnes'
            for layer in ('raw', 'normalized', 'analytical', 'dashboard'):
                (carnes / layer).mkdir(parents=True)
                (carnes / layer / 'example.json').write_text('{}', encoding='utf-8')
            prepare(source, destination)
            published = destination / 'data/carnes'
            self.assertTrue((published / 'dashboard/example.json').exists())
            for layer in ('raw', 'normalized', 'analytical'):
                self.assertFalse((published / layer).exists())


if __name__ == '__main__':
    unittest.main()
