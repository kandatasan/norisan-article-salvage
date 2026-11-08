<?php
// Run with: php ops/wp-english-driving-cta/tests/notice-smoke.php
define('ABSPATH', '/tests/');
$GLOBALS['en_cta_hooks'] = array();
$GLOBALS['en_cta_queried_id'] = 4375;
$GLOBALS['en_cta_is_post'] = true;
$GLOBALS['en_cta_admin'] = false;
$GLOBALS['en_cta_category'] = true;

function add_filter($hook, $callback, $priority) { $GLOBALS['en_cta_hooks'][$hook] = $callback; }
function is_singular($post_type) { return $post_type === 'post' && $GLOBALS['en_cta_is_post']; }
function is_admin() { return $GLOBALS['en_cta_admin']; }
function get_queried_object_id() { return $GLOBALS['en_cta_queried_id']; }
function get_post($id) { return (object) array('ID' => $id, 'post_type' => 'post', 'post_name' => $id === 123 ? 'japanese-post' : 'english-post-english'); }
function has_category($slug, $id) { return $slug === 'english-travel' && $GLOBALS['en_cta_category']; }
require __DIR__ . '/../tsurikue-en-driving-cta.php';

function ensure($condition, $message) { if (!$condition) { throw new RuntimeException($message); } }
function count_occurs($s, $needle) { return substr_count($s, $needle); }

$examples = array(
    'in_paragraph' => '<p>For the trip, you can <a href="https://www.discovercars.com/?a_aid=tsurikue" rel="sponsored nofollow noopener" target="_blank"><strong>compare rental cars</strong></a>.</p>',
    'standalone' => "<h2>Driving</h2>\n<p><a href=\"https://www.discovercars.com/?a_aid=tsurikue\" target=\"_blank\" rel=\"sponsored nofollow noopener\"><strong>Compare rental car options</strong></a></p>",
    'more_text_after' => "<p>A car can help. You can <a href=\"https://www.discovercars.com/?a_aid=tsurikue\" rel=\"sponsored nofollow noopener\">compare cars</a>. Check the full cost.</p>\n<p><small>Affiliate disclosure: commission possible.</small></p>",
);
ensure(isset($GLOBALS['en_cta_hooks']['the_content']), 'WordPress filter not registered');

foreach ($examples as $label => $html) {
    $result = tsurikue_en_driving_decorate($html);
    ensure($result !== $html, $label . ': no transformation');
    ensure(count_occurs($result, 'data-tsurikue-en-driving="v1"') === 1, $label . ': notice count');
    ensure(count_occurs($result, 'class="tsurikue-en-rental-button"') === 1, $label . ': button count');
    ensure(count_occurs($result, 'https://www.discovercars.com/?a_aid=tsurikue') === 1, $label . ': duplicate affiliate URL');
    ensure(count_occurs($result, 'rel="sponsored nofollow noopener"') === 1, $label . ': changed sponsored rel');
    ensure(strpos($result, 'data-tsurikue-en-driving="v1"') < strpos($result, 'https://www.discovercars.com/?a_aid=tsurikue'), $label . ': wrong notice position');
    ensure(strpos($result, '1949 Geneva Convention') !== false, $label . ': missing required permit detail');
    ensure(strpos($result, 'Switzerland, Germany, France, Belgium, Monaco or Taiwan') !== false, $label . ': missing alternate licence rule');
    ensure(strpos($result, 'www.npa.go.jp/english/') !== false, $label . ': missing official guidance link');
    ensure(tsurikue_en_driving_decorate($result) === $result, $label . ': not idempotent');
    ensure(tsurikue_en_driving_filter($html) === $result, $label . ': filter output differs from pure renderer');
}
$no_affiliate = "<p>Enjoy the local trains and beaches!</p>";
ensure(tsurikue_en_driving_filter($no_affiliate) === $no_affiliate, 'Non-rental English story changed');

$GLOBALS['en_cta_queried_id'] = 123;
ensure(tsurikue_en_driving_filter($examples['standalone']) === $examples['standalone'], 'Japanese post changed');
$GLOBALS['en_cta_queried_id'] = 4375;
$GLOBALS['en_cta_category'] = false;
ensure(tsurikue_en_driving_filter($examples['standalone']) === $examples['standalone'], 'Non-English category changed');
$GLOBALS['en_cta_category'] = true;
$GLOBALS['en_cta_is_post'] = false;
ensure(tsurikue_en_driving_filter($examples['standalone']) === $examples['standalone'], 'Archive or homepage changed');
$GLOBALS['en_cta_is_post'] = true;
$GLOBALS['en_cta_admin'] = true;
ensure(tsurikue_en_driving_filter($examples['standalone']) === $examples['standalone'], 'Admin editor changed');
$GLOBALS['en_cta_admin'] = false;

$without_p = '<div><a href="https://www.discovercars.com/?a_aid=tsurikue">Cars</a></div>';
ensure(tsurikue_en_driving_decorate($without_p) === $without_p, 'Unsafe unknown HTML rewritten');
echo "English licence notice + CTA regression tests PASS\n";
