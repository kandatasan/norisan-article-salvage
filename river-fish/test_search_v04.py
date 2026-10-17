import unittest
from search_v04 import search


class SearchV04(unittest.TestCase):
    def test_total(self):
        self.assertEqual(search()['total_records'],48)

    def test_aliens(self):
        r=search(prefecture='岡山県',alien='alien')
        self.assertEqual({x['fish'] for x in r['records']},{'オオクチバス','ブルーギル'})

    def test_specific_law(self):
        r=search(alien='regulated')
        self.assertEqual({x['fish'] for x in r['records']},{'オオクチバス','ブルーギル'})

    def test_no_native_guess(self):
        self.assertEqual(search(alien='native')['total_records'],0)

    def test_no_domestic_guess(self):
        self.assertEqual(search(alien='domestic')['total_records'],0)

    def test_oyanirami_unreviewed(self):
        r=search(name='オヤニラミ',prefecture='岡山県')['records'][0]
        self.assertEqual(r['origin'],'unknown')
        self.assertEqual(r['legal_status'],'unreviewed')

    def test_alias(self):
        self.assertEqual(search('てんきり','広島県')['total_records'],3)

    def test_not_found_is_not_absent(self):
        self.assertEqual(search('ブルーギル','広島県')['total_records'],0)

    def test_regional_scope(self):
        self.assertEqual(search('オオクチバス','山口県',alien='alien')['total_records'],0)

    def test_sources(self):
        r=search('ブルーギル','岡山県')['records'][0]
        self.assertIn('env.go.jp',r['legal_source'])
        self.assertIn('mlit.go.jp',r['origin_source'])


if __name__ == '__main__':
    unittest.main()
