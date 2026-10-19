import unittest
from build_kyushu_evidence_queue import parse_pairs
from probe_kyushu_official_page import BASINS

class OfficialSourceParserTests(unittest.TestCase):
    @staticmethod
    def sample():
        return "<table>"+ "".join(
            '<tr><td>'+w+'</td><td>'+w+'<br>支流例</td><td>提供窓口</td></tr>'
            for w in sorted(BASINS)
        )+"</table>"

    def test_all_20_official_water_names_are_required(self):
        got=parse_pairs(self.sample())
        self.assertEqual(set(got),BASINS)
        self.assertIn("支流例",got["筑後川"])

    def test_missing_official_basins_must_fail(self):
        with self.assertRaises(ValueError):
            parse_pairs("<table><tr><td>筑後川</td><td>筑後川</td></tr></table>")

    def test_duplicate_official_basin_row_must_fail(self):
        html=self.sample().replace("</table>","<tr><td>筑後川</td><td>筑後川</td></tr></table>")
        with self.assertRaises(ValueError):
            parse_pairs(html)

if __name__=="__main__":
    unittest.main()
