import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import old_tsurikue_remake_publish_polish_dry_run as m

def p(t): return f'<!-- wp:paragraph -->\n<p>{t}</p>\n<!-- /wp:paragraph -->'
def h(t): return f'<!-- wp:heading {{"level":2}} -->\n<h2>{t}</h2>\n<!-- /wp:heading -->'
def img(mid=1): return f'<!-- wp:image {{"id":{mid}}} -->\n<figure><img src="x" class="wp-image-{mid}"/></figure>\n<!-- /wp:image -->'

def article(slug, content):
    return {'slug':slug,'title':slug,'content':content,'matched_media_ids':[],'matched_media_source_urls':[],'matched_media_omitted_redundant':[],'placeholders':[],'omitted_photo_positions':[]}

class ReaderPolishTests(unittest.TestCase):
    def test_yakitori_tail_removed_but_image_kept(self):
        c='\n\n'.join([p(m.YAKITORI_CONCLUSION_OLD),p('希釈タイプのチー坊売ってた！チー坊ウォーターはたまに見かけるけど、希釈タイプはあんまり見ないですよね'),h('お店の情報'),p('今回は、オススメの焼き鳥屋さん『炭火焼鳥 陸』さんを紹介します。'),img(155),p('チー坊についての記事はコチラ')])
        out,q=m.polish(article('yakitori-riku',c))
        self.assertNotIn('チー坊についての記事はコチラ',out['content'])
        self.assertNotIn('お店の情報',out['content'])
        self.assertIn('wp-image-155',out['content'])
        self.assertIn('笑顔のステキな店長さん',out['content'])
        self.assertGreaterEqual(q['blocks_removed'],3)

    def test_visit_time_and_project_meta_fixes(self):
        cases=[
            ('totoya-iiyo','ただ、終電が23時ごろなので就寝には静かになっていると思われます。','訪問当時は終電が23時ごろ'),
            ('fishing','旧つりくえ！では「さあ、釣りに行こう」を入口に、初心者向けの釣り方解説と実際の釣行記録をまとめていました。このページでは、復活させる各記事へつながる入口として内容を整理しています。','釣り記事の入口'),
            ('shiosoba-maeda-hiroshima','平日のランチタイムのみの営業に超人気店ということもあって、','訪問当時は平日のランチタイムのみの営業で'),
        ]
        for slug,old,want in cases:
            out,_=m.polish(article(slug,p(old)))
            self.assertNotIn(old,out['content'])
            self.assertIn(want,out['content'])

    def test_manual_toc_and_old_cta_paragraphs_removed(self):
        c='\n\n'.join([p('お店の情報'),p('オススメメニュー'),p('私の感想'),h('私の感想'),p('本文')])
        out,_=m.polish(article('hiroshima-station-ramen-michimaru',c))
        self.assertEqual(out['content'].count('私の感想'),1)
        self.assertNotIn('<p>お店の情報</p>',out['content'])
        self.assertNotIn('<p>オススメメニュー</p>',out['content'])
        out,_=m.polish(article('shiosoba-maeda-hiroshima',p('広島の美味しい！をもっと見る')))
        self.assertNotIn('もっと見る',out['content'])

    def test_known_typo_and_affiliate_fixes(self):
        out,_=m.polish(article('hiroshima-station-ramen-michimaru',p('端的に言います。みちまるラーメンと替玉以上！')+'\n\n'+p('麺の固さバリカタ、面が立っちゃう固さ。')))
        self.assertIn('みちまるラーメンと替玉。以上！',out['content'])
        self.assertIn('麺が立っちゃう固さ',out['content'])
        out,_=m.polish(article('roast-beef-yusen',p('コチラのお店で購入したので、驚き価格を見てみてくださいね。同じお店にある、送料無料の牛スジ肉とセットで注文をすると送料が無料になったのでお得でした。')))
        self.assertNotIn('驚き価格',out['content'])

    def test_polish_has_no_network_or_write_path(self):
        src=Path(m.__file__).read_text(encoding='utf-8')
        for token in ('requests','urllib','urlopen','wp-json','POST','PUT','PATCH','DELETE'):
            self.assertNotIn(token,src)

if __name__=='__main__': unittest.main()
