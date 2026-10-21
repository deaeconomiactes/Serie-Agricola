import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.ci.prepare_pages import prepare
from scripts.magyp import build_price_freshness as freshness


class CommoditiesCutoverTests(unittest.TestCase):
    def test_pages_excludes_retired_archive_and_preserves_other_outputs_and_originals(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'repo';destination=root/'pages'
            archive=source/'data/commodities_local_mensual/dashboard/manual.csv'
            official=source/'data/magyp/dashboard/commodities/internal.csv'
            for path in [archive,official,source/'data/other.csv',source/'index.html']:
                path.parent.mkdir(parents=True,exist_ok=True);path.write_text('unchanged')
            prepare(source,destination)
            self.assertFalse((destination/'data/commodities_local_mensual').exists())
            self.assertEqual(archive.read_text(),'unchanged')
            for path in [official,source/'data/other.csv',source/'index.html']:
                self.assertEqual((destination/path.relative_to(source)).read_bytes(),path.read_bytes())

    def test_pages_rejects_recursive_or_existing_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'repo';source.mkdir()
            for destination in [source,source/'nested']:
                with self.assertRaises(ValueError):prepare(source,destination)
            destination=Path(temp)/'existing';destination.mkdir()
            with self.assertRaises(FileExistsError):prepare(source,destination)

    def test_production_freshness_no_longer_reads_manual_price_files(self):
        real_read=freshness.read_csv
        def read(path,*args,**kwargs):
            self.assertNotIn('commodities_local_mensual',str(path))
            return real_read(path,*args,**kwargs)
        with patch.object(freshness,'read_csv',side_effect=read),patch.object(freshness,'atomic_write'):
            report=freshness.build()
        archive=next(row for row in report['sources'] if row['source_family']=='local_mensual')
        self.assertFalse(archive['runtime_active'])
        self.assertEqual(archive['status'],'STATIC')
