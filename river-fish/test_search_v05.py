"""Regression tests for searched official survey and report-only sources."""
import unittest
from search_v05 import search

class FishSearchV05(unittest.TestCase):
    def test_official_loaded(self):
        x=search(name='アユ',watershed='太田川')
        self.assertGreater(x['official_count'],0)
        self.assertTrue(all(r['prefecture'] is None for r in x['records'] if r['record_type'].startswith('official')))

    def test_year_omits_non_surveyed_curated(self):
        x=search(name='アユ',year='2020')
        self.assertEqual(x['curated_count'],0)
        self.assertTrue(all(r['survey_year']=='2020' for r in x['records']))

    def test_prefecture_never_infers_official_location(self):
        x=search(prefecture='広島県',name='アユ')
        self.assertEqual(x['official_count'],0)
        self.assertTrue(all(r['record_type'].startswith('curated') for r in x['records']))

    def test_local_alias_stays_searchable(self):
        x=search(name='てんきり',prefecture='広島県')
        self.assertEqual(x['curated_count'],3)

    def test_dont_conflate_census_with_report(self):
        x=search(name='アユ',watershed='太田川')
        self.assertTrue(any(r['record_type']=='official_census_watershed_year' for r in x['records']))
        self.assertTrue(any(r['record_type']=='curated_report_not_direct_census' for r in x['records']))

    def test_zero_does_not_mark_absent(self):
        x=search(name='架空の魚類名')
        self.assertEqual(x['total'],0)
        self.assertTrue(any('非生息を意味しません' in note for note in x['notes']))

    def test_pagination(self):
        x=search(name='アユ',limit=2,offset=1)
        self.assertLessEqual(len(x['records']),2)
        self.assertGreaterEqual(x['total'],len(x['records']))

    def test_invalid_year(self):
        with self.assertRaises(ValueError):
            search(year='令和4')

    def test_unknown_not_native(self):
        x=search(name='アユ',alien='native')
        self.assertEqual(x['official_count'],0)

    def test_regulated_origin_still_unknown(self):
        x=search(name='ブルーギル',alien='regulated')
        self.assertGreater(x['total'],0)
        self.assertTrue(all(r['origin']=='unknown' for r in x['records'] if r['record_type'].startswith('official')))

if __name__=='__main__':
    unittest.main()
