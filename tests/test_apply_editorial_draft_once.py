import importlib.util, json, pathlib, tempfile, unittest
P=pathlib.Path(__file__).parents[1]/'scripts'/'apply_editorial_draft_once.py'
spec=importlib.util.spec_from_file_location('m',P); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class T(unittest.TestCase):
  def package(self):
    td=tempfile.TemporaryDirectory(); d=pathlib.Path(td.name); (d/'content.html').write_text('<p>Hello</p>',encoding='utf-8')
    cfg={"post_id":1,"slug":"x","title":"X","salvage_marker":"<!-- s -->","editorial_marker":"<!-- e -->","content_file":"content.html","featured_media":7,"expected_media":{"7":"/x.jpg"}}
    p=d/'config.json'; p.write_text(json.dumps(cfg),encoding='utf-8'); return td,p,cfg
  def test_payload_full_content(self):
    td,p,cfg=self.package(); c,full=m.load_package(p); self.assertIn('<!-- s -->\n<!-- e -->\n<p>Hello</p>',full); td.cleanup()
  def test_reject_non_draft(self):
    td,p,cfg=self.package(); c,full=m.load_package(p)
    with self.assertRaises(RuntimeError): m.validate_target({"id":1,"slug":"x","status":"publish","content":{"raw":"<!-- s -->"}},cfg,full)
    td.cleanup()
  def test_reject_missing_salvage(self):
    td,p,cfg=self.package(); c,full=m.load_package(p)
    with self.assertRaises(RuntimeError): m.validate_target({"id":1,"slug":"x","status":"draft","content":{"raw":"nope"}},cfg,full)
    td.cleanup()
  def test_update_initial_salvage(self):
    td,p,cfg=self.package(); c,full=m.load_package(p); self.assertEqual(m.validate_target({"id":1,"slug":"x","status":"draft","content":{"raw":"<!-- s -->\nold"}},cfg,full),'UPDATE'); td.cleanup()
  def test_idempotent_exact_editorial(self):
    td,p,cfg=self.package(); c,full=m.load_package(p); row={"id":1,"slug":"x","status":"draft","title":{"raw":"X"},"content":{"raw":full},"featured_media":7}; self.assertEqual(m.validate_target(row,cfg,full),'ALREADY_UP_TO_DATE'); td.cleanup()
  def test_reject_later_edit(self):
    td,p,cfg=self.package(); c,full=m.load_package(p); row={"id":1,"slug":"x","status":"draft","title":{"raw":"X"},"content":{"raw":full+'changed'},"featured_media":7}
    with self.assertRaises(RuntimeError): m.validate_target(row,cfg,full)
    td.cleanup()
  def test_featured_must_be_expected(self):
    cfg={"featured_media":8,"expected_media":{"7":"/x.jpg"}}
    with self.assertRaises(RuntimeError): m.validate_media(cfg,'auth')
if __name__=='__main__': unittest.main()
