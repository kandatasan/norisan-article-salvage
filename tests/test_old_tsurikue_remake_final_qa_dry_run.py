import json,re,sys,tempfile,unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import old_tsurikue_remake_final_qa_dry_run as m

class FinalQADryRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.out=Path(cls.tmp.name)/'out'
        cls.report=m.build(cls.out)
        cls.article_dir=cls.out/'articles'
        cls.contents={p.stem:p.read_text(encoding='utf-8') for p in cls.article_dir.glob('*.html')}
        cls.articles={p.stem:json.loads(p.read_text(encoding='utf-8')) for p in cls.article_dir.glob('*.json')}
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def test_scope_image_disposition_and_no_writes(self):
        s=self.report['summary']
        self.assertEqual(s['targets'],46); self.assertEqual(s['lexus_targets'],0)
        self.assertEqual(s['matched_images_available'],110)
        self.assertEqual(s['matched_images_used'],105)
        self.assertEqual(s['matched_images_omitted_redundant'],5)
        self.assertEqual(s['placeholders_retained'],28)
        self.assertEqual(s['unresolved_positions_omitted'],225)
        self.assertEqual(s['unresolved_positions_total'],253)
        self.assertEqual(s['wordpress_write_count'],0); self.assertEqual(s['draft_creation_count'],0); self.assertEqual(s['media_upload_count'],0)
        self.assertEqual(len(self.contents),46)

    def test_no_false_stale_prefix_or_builder_heading(self):
        blob='\n'.join(self.contents.values())
        for bad in (
            '訪問当時の所在地：山口県は','訪問当時の所在地：鳥取県は','訪問当時の所在地：島根県',
            '訪問当時の所在地：広島県民','訪問当時の所在地：大分県日田市は',
            '訪問当時の料金に関する記録：','記事内で使う写真・確認用'
        ): self.assertNotIn(bad,blob)

    def test_inbloom_truncation_and_old_referral_removed(self):
        c=self.contents['inbloombeppu']
        for bad in ('1棟貸しプランを</p>','0977222449','お得に泊まれるかも？オススメの宿泊予約サービス','招待コード','PGFTCS'):
            self.assertNotIn(bad,c)
        self.assertIn('訪問当時の1棟貸し宿泊料金は40,000円',c)

    def test_yakitori_and_gulp_affiliate_remnants_removed(self):
        y=self.contents['yakitori-riku']
        for bad in ('チチヤス チー坊 乳酸菌飲料 340ml','通販でチー坊売ってた','管理釣り場の魚は美味しい？これがオススメ！'):
            self.assertNotIn(bad,y)
        self.assertNotIn('管理釣り場の魚は美味しい', '\n'.join(self.articles['yakitori-riku'].get('placeholders') or []))
        self.assertTrue(any('管理釣り場の魚は美味しい' in x.get('nearest_heading','') for x in self.articles['yakitori-riku'].get('omitted_photo_positions') or []))
        g=self.contents['gulpalivepowder']
        for bad in ('魚のヤル気スイッヅを押す！(楽天)','バークレイ Berkley Gulp ガルプ アライブ パウダー','ポイント10倍'):
            self.assertNotIn(bad,g)

    def test_known_orphan_and_truncation_fixes(self):
        michi=self.contents['hiroshima-station-ramen-michimaru']
        self.assertNotRegex(michi,r'<h[23][^>]*>メニュー</h[23]>')
        self.assertIn('オススメメニュー',michi)
        iroha=self.contents['iroha-sushi-akitsu-menu']
        self.assertNotIn('お寿司もね、お手頃価格で美味しく食べられるの',iroha)
        self.assertIn('お寿司も、お手頃価格で美味しく食べられました。',iroha)
        sayori=self.contents['sayori-tsurikata']
        self.assertNotIn('サヨリ釣行編へ',sayori); self.assertNotIn('詳しい作り方はこちら',sayori)

    def test_ginnjoura_hours_are_not_conflicting(self):
        c=self.contents['ginnjoura-men']
        self.assertIn('回収できた旧記録には営業時間の表記違いがあるため',c)
        for old in ('11：00～14：00','17：30～22：00','11：00～14：30','17：00～22：00'):
            self.assertNotIn(old,c)

    def test_kotamagai_is_compact_but_keeps_both_species(self):
        c=self.contents['kotamagairyouri']
        self.assertIn('コタマガイ',c); self.assertIn('オキアサリ',c)
        self.assertEqual(c.count('ヤドカリ'),1)
        self.assertIn('オキアサリも同じ方法で食べてみた',c)

    def test_confirmed_images_are_deduped_only_with_reconciliation(self):
        total_blocks=0
        for slug,c in self.contents.items():
            ids=[int(x) for x in re.findall(r'wp-image-(\d+)',c)]
            self.assertEqual(len(ids),len(set(ids)),slug)
            a=self.articles[slug]
            self.assertEqual(set(ids),{int(x) for x in a.get('matched_media_ids') or []},slug)
            self.assertEqual(len(ids),len(a.get('matched_media_ids') or []),slug)
            total_blocks += len(ids)
        self.assertEqual(total_blocks,105)
        self.assertEqual(sum(len(a.get('matched_media_omitted_redundant') or []) for a in self.articles.values()),5)

    def test_no_terminal_headings_or_excessive_reduction(self):
        for slug,c in self.contents.items():
            self.assertFalse(m.content_has_terminal_orphan_heading(c),slug)
        self.assertEqual(self.report['summary']['articles_reduced_50pct_or_more'],0)
        self.assertEqual(self.report['summary']['newly_under_800'],0)

if __name__=='__main__': unittest.main()
