"""Packaging and non-public installation safety checks for river WP plugin v1.6."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from build_wp_plugin_v16 import build,prepare_rows,COUNTS,VERSION,SAFE_SOURCE_FILES

ROOT=Path(__file__).resolve().parent

class WordpressRiverPluginPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.folder=Path(cls.temp.name)/"prepared"
        cls.zip=Path(cls.temp.name)/"tsurikue-river-search.zip"
        cls.status=build(cls.folder,cls.zip)
        cls.plugin=cls.folder/"tsurikue-river-search"
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_actual_rows_and_zip(self):
        self.assertEqual(self.status["counts"],{"codes":35449,"local":1449,"fish":18814})
        self.assertGreater(self.zip.stat().st_size,100_000)
        with zipfile.ZipFile(self.zip) as z:
            self.assertIsNone(z.testzip())
            self.assertIn("tsurikue-river-search/tsurikue-river-search.php",z.namelist())
            self.assertNotIn("wp-config.php",str(z.namelist()))

    def test_data_manifest_hashes_valid(self):
        m=json.loads((self.plugin/"data/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(m["version"],VERSION)
        self.assertEqual(m["counts"],COUNTS)
        self.assertFalse(m["published_to_wordpress"])
        for k,file in (("codes","river_codes.csv"),("local","source_mentions.csv"),("fish","watershed_fish.csv")):
            data=(self.plugin/"data"/file).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),m["sha256"][k])

    def test_real_installed_csv_columns(self):
        sample={}
        for kind,file,columns in (
            ("codes","river_codes.csv",5),
            ("local","source_mentions.csv",9),
            ("fish","watershed_fish.csv",5)):
            with (self.plugin/"data"/file).open(encoding="utf-8",newline="") as f:
                values=list(csv.reader(f))
            self.assertEqual(len(values)-1,COUNTS[kind])
            self.assertTrue(all(len(r)==columns for r in values))
            sample[kind]=values
        self.assertIn("8707090023",[x[0] for x in sample["codes"]])
        self.assertTrue(any(x[0]=="沖縄県" and "国場川" in x[1] for x in sample["local"]))
        self.assertTrue(any(x[0]=="kyushu" and x[3]=="アユ" for x in sample["fish"]))

    def test_prefecture_not_added_to_national_code_rows(self):
        rows=prepare_rows()
        self.assertTrue(all(len(row)==5 and row[0].isdigit() for row in rows["codes"]))
        self.assertTrue(all(len(row)==9 and row[6].startswith(("HR-","HM-","CW-","YR-","TP-","NP-","AP-")) for row in rows["local"]))
        self.assertTrue(all(len(row)==5 for row in rows["fish"]))

    def test_installable_plugin_has_readme_and_frontend(self):
        for path in SAFE_SOURCE_FILES:
            self.assertTrue((self.plugin/path).is_file())

    def test_readonly_rest_parameterization_security(self):
        content=(self.plugin/"includes/class-tsr-search.php").read_text(encoding="utf-8")
        self.assertIn("$wpdb->prepare",content)
        self.assertIn("$wpdb->esc_like",content)
        self.assertIn("'permission_callback' => '__return_true'",content)
        self.assertIn("TSR_DATA_VERSION",content)
        self.assertNotIn("INSERT INTO",content)
        self.assertNotIn("CREATE TABLE",content)

    def test_managed_manual_import_nonce_and_generation_switch(self):
        content=(self.plugin/"includes/class-tsr-import.php").read_text(encoding="utf-8")
        self.assertIn("check_ajax_referer('tsr_river_import', 'nonce')",content)
        self.assertIn("current_user_can('manage_options')",content)
        self.assertIn("hash_file('sha256'",content)
        self.assertIn("tsr_active_gen",content)
        self.assertIn("generation = %d",content)
        self.assertIn("self::EXPECTED",content)

    def test_no_wordpress_deployment_actions(self):
        main=(self.plugin/"tsurikue-river-search.php").read_text(encoding="utf-8")
        self.assertIn("register_activation_hook",main)
        self.assertIn("add_shortcode('tsurikue_river_search'",main)
        self.assertNotIn("wp_insert_post(",main)
        self.assertNotIn("wp_update_post(",main)
        self.assertFalse((self.plugin/"uninstall.php").exists())

    def test_frontend_is_xss_safe_and_paginated(self):
        js=(self.plugin/"assets/river-search.js").read_text(encoding="utf-8")
        self.assertIn("textContent",js)
        self.assertNotIn("innerHTML",js)
        self.assertIn('url.searchParams.set("per_page","20")',js)
        self.assertIn('credentials:"same-origin"',js)

    def test_refuse_overwriting_installed_build(self):
        with self.assertRaises(FileExistsError):
            build(self.folder,Path(self.temp.name)/"a-second-zip.zip")

if __name__=="__main__":unittest.main()
