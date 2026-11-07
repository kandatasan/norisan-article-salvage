<?php
// Pure-PHP English route tests. No WordPress write APIs are loaded.
define('ABSPATH', '/test/');
$GLOBALS['actions'] = array();
$GLOBALS['filters'] = array();
function add_action($name, $call, $priority = 10) { $GLOBALS['actions'][$name][] = $call; }
function add_filter($name, $call, $priority = 10, $args = 1) { $GLOBALS['filters'][$name][] = $call; }
function home_url($path) { return 'http://tsurikue.com' . $path; }
function set_url_scheme($url, $scheme = 'https') { return preg_replace('~^https?://~', $scheme . '://', $url); }
class WP_Post {
    public $ID;
    public $post_status;
    public function __construct($id, $status = 'draft') {
        $this->ID = $id;
        $this->post_status = $status;
    }
}
function wp_parse_url($url, $part) { return parse_url($url, $part); }
$GLOBALS['rewrites'] = array();
function add_rewrite_rule($match, $target, $where) { $GLOBALS['rewrites'][$match] = $target; }
require __DIR__ . '/../tsurikue-en-routes.php';
function assert_same($expected, $actual, $label) {
    if ($actual !== $expected) { throw new Exception($label . ': ' . var_export($actual, true)); }
}
$expected = array(
    4375 => array('ja' => 2647, 'path' => 'orizuru-tower', 'slug' => 'orizuru-tower-english'),
    4380 => array('ja' => 2664, 'path' => 'yamaguchi-road-trip', 'slug' => 'yamaguchi-roadtrip-english'),
    4392 => array('ja' => 3730, 'path' => 'okunoshima-rabbit-island', 'slug' => 'okunoshima-rabbit-island-english'),
    4391 => array('ja' => 3438, 'path' => 'matsue-vogel-park', 'slug' => 'matsue-vogel-park-english'),
    4393 => array('ja' => 2658, 'path' => 'tottori-road-trip', 'slug' => 'tottori-drive-english'),
    4402 => array('ja' => 3384, 'path' => 'kochi-road-trip', 'slug' => 'kochi-roadtrip-english'),
    4403 => array('ja' => 3882, 'path' => 'kurahashi-island', 'slug' => 'kurahashi-island-english'),
    4409 => array('ja' => 2408, 'path' => 'mikawa-mu-valley', 'slug' => 'mikawa-mu-valley-english'),
    4410 => array('ja' => 2125, 'path' => 'nagase-beach', 'slug' => 'nagase-beach-etajima-english'),
    4408 => array('ja' => 1887, 'path' => 'etajima-island', 'slug' => 'etajima-island-guide-english'),
    4417 => array('ja' => 1955, 'path' => 'sera-day-trip', 'slug' => 'sera-day-trip-english'),
    4418 => array('ja' => 1996, 'path' => 'sera-kogen-farm', 'slug' => 'sera-kogen-farm-english'),
    4427 => array('ja' => 2479, 'path' => 'tsunoshima-bridge', 'slug' => 'tsunoshima-bridge-english'),
    4425 => array('ja' => 2437, 'path' => 'motonosumi-shrine', 'slug' => 'motonosumi-shrine-english'),
    4426 => array('ja' => 2941, 'path' => 'saijo-sake-street', 'slug' => 'saijo-sake-street-english'),
    4424 => array('ja' => 3507, 'path' => 'kurashiki-bikan-quarter', 'slug' => 'kurashiki-bikan-quarter-english'),
);
assert_same(16, count(tsurikue_en_pairs()), 'number of English pairs');
tsurikue_en_add_rewrites();
foreach (tsurikue_en_pairs() as $pair) {
    $entry = $expected[$pair['en_id']] ?? null;
    if (!$entry) { throw new Exception('unexpected English post: ' . $pair['en_id']); }
    assert_same($entry['ja'], $pair['ja_id'], 'original post ID');
    assert_same($entry['path'], $pair['en_path'], 'English path');
    assert_same($entry['slug'], $pair['en_slug'], 'English slug');
    assert_same(
        'https://tsurikue.com/en/' . $entry['path'] . '/',
        tsurikue_en_post_link('old', new WP_Post($pair['en_id'])),
        'English permalink'
    );
    $route = '^en/' . preg_quote($entry['path'], '/') . '/?$';
    assert_same(
        'index.php?post_type=post&name=' . $entry['slug'],
        $GLOBALS['rewrites'][$route] ?? null,
        'English rewrite route'
    );
    assert_same(
        false,
        tsurikue_en_redirect_canonical('https://tsurikue.com/wrong/', 'https://tsurikue.com/en/' . $entry['path'] . '/'),
        'custom permalink must not redirect elsewhere'
    );
}
assert_same('old', tsurikue_en_post_link('old', new WP_Post(999)), 'unrelated post untouched');
assert_same('https://tsurikue.com/tottori-drive/', tsurikue_en_post_link('https://tsurikue.com/tottori-drive/', new WP_Post(2658)), 'Japanese path untouched');
assert_same('https://tsurikue.com/unrelated/', tsurikue_en_redirect_canonical('https://tsurikue.com/unrelated/', 'https://tsurikue.com/unrelated/'), 'unrelated canonical untouched');
echo "English sixteen-route tests OK\n";
