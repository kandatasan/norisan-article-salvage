<?php
// Small read-only smoke test for the English landing language filter.
define('ABSPATH', '/test/');
$GLOBALS['hooks'] = array();
function add_filter($name,$fn,$priority=10) { $GLOBALS['hooks'][$name][] = $fn; }
function add_shortcode($name,$fn) { $GLOBALS['hooks']['shortcodes'][$name]=$fn; }
$GLOBALS['page_en']=false;
$GLOBALS['category_en']=false;
function is_page($slug) { return $slug==='en' && $GLOBALS['page_en']; }
function is_category($slug) { return $slug==='english-travel' && $GLOBALS['category_en']; }
require __DIR__ . '/../tsurikue-en-landing.php';
function assert_eq($expect,$got) { if ($expect!==$got) { throw new RuntimeException('got '.var_export($got,true)); } }
assert_eq('lang="ja" class="wp"', tsurikue_en_travel_lang_attributes('lang="ja" class="wp"'));
$GLOBALS['page_en']=true;
assert_eq('lang="en" class="wp"', tsurikue_en_travel_lang_attributes('lang="ja" class="wp"'));
$GLOBALS['page_en']=false;
$GLOBALS['category_en']=true;
assert_eq('lang="en" class="wp"', tsurikue_en_travel_lang_attributes('lang="ja" class="wp"'));
echo "English landing language smoke test: OK\n";
