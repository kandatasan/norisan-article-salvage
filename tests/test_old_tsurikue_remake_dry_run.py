import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import old_tsurikue_remake_dry_run as m

class RemakeDryRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=m.load_sources(); cls.photos=m.load_photo_manifest()
    def test_scope_and_phase2_counts(self):
        m.validate_inputs(self.sources,self.photos)
        self.assertEqual(len(self.sources),46); self.assertEqual(self.photos['lexus_targets'],0)
        self.assertEqual(sum(r['result']=='MATCH_FILENAME' for r in self.photos['refs']),110)
        self.assertEqual(sum(r['result']=='PLACEHOLDER' for r in self.photos['refs']),253)
    def test_placeholder_selection_is_conservative(self):
        selected=m.select_placeholders(self.photos['refs'])
        self.assertEqual(len(selected),29)
        per={}
        for slug,order in selected: per[slug]=per.get(slug,0)+1
        self.assertLessEqual(max(per.values()),3)
    def test_builds_46_nonempty_articles_and_totals(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.build(Path(d))
            self.assertEqual(r['summary']['articles_generated'],46)
            self.assertEqual(r['summary']['matched_images_used'],110)
            self.assertEqual(r['summary']['placeholders_used'],29)
            self.assertEqual(r['summary']['unmatched_photos_omitted'],224)
            self.assertEqual(len(list((Path(d)/'articles').glob('*.html'))),46)
            self.assertTrue(all((Path(d)/'articles'/f"{x['slug']}.html").read_text(encoding='utf-8').strip() for x in r['articles']))
    def test_known_articles_use_confirmed_media_only(self):
        known={'orizuru-tower','yamaguchi-drive','agetate-tenpura-hongo'}
        refs={s:{int(r['matched_media_id']) for r in self.photos['refs'] if r['target_slug']==s and r['result']=='MATCH_FILENAME'} for s in known}
        with tempfile.TemporaryDirectory() as d:
            m.build(Path(d))
            for s in known:
                a=json.loads((Path(d)/'articles'/f'{s}.json').read_text(encoding='utf-8'))
                self.assertEqual(set(a['matched_media_ids']),refs[s])
    def test_unmatched_never_substituted(self):
        selected=m.select_placeholders(self.photos['refs'])
        src=next(x for x in self.sources if x['slug']=='totoya-iiyo')
        refs=[x for x in self.photos['refs'] if x['target_slug']=='totoya-iiyo']
        a=m.render_article(src,refs,selected)
        allowed={int(x['matched_media_id']) for x in refs if x['result']=='MATCH_FILENAME'}
        self.assertEqual(set(a['matched_media_ids']),allowed)
    def test_zero_photo_articles_still_generate(self):
        with tempfile.TemporaryDirectory() as d:
            m.build(Path(d))
            for s in ('fishing','komugikodesakanatsureruyo'):
                a=json.loads((Path(d)/'articles'/f'{s}.json').read_text(encoding='utf-8'))
                self.assertTrue(a['content'].strip())
    def test_banned_elements_and_writes_zero(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.build(Path(d)); blob='\n'.join(p.read_text(encoding='utf-8') for p in (Path(d)/'articles').glob('*.html')).lower()
            for bad in ('web.archive.org','lexus-diary.com','<script','<style'): self.assertNotIn(bad,blob)
            self.assertEqual(r['summary']['wordpress_write_count'],0); self.assertEqual(r['summary']['draft_creation_count'],0); self.assertEqual(r['summary']['media_upload_count'],0)
if __name__=='__main__': unittest.main()
