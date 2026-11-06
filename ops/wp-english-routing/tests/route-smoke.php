<?php
// Minimal pure-PHP pilot tests. No WordPress write APIs are loaded.
define('ABSPATH', '/test/');
$GLOBALS['actions'] = [];
$GLOBALS['filters'] = [];
function add_action($name, $call, $priority = 10) { $GLOBALS['actions'][$name][] = $call; }
function add_filter($name, $call, $priority = 10, $args = 1) { $GLOBALS['filters'][$name][] = $call; }
function home_url($path) { return 'http://tsurikue.com' . $path; }
function set_url_scheme($url,$scheme='https') { return preg_replace('~^https?://~', $scheme.'://', $url); }
class WP_Post { public $ID; public $post_status; public function __construct($id,$status='draft') {$this->ID=$id;$this->post_status=$status;} }
function wp_parse_url($url, $part) { return parse_url($url,$part); }
$GLOBALS['rewrites']=[];
function add_rewrite_rule($match, $target, $where) { $GLOBALS['rewrites'][$match]=$target; }
require __DIR__ . '/../tsurikue-en-routes.php';
function assert_same($expected,$actual,$label) { if ($actual !== $expected) { throw new Exception($label . ': '.var_export($actual,true)); } }
assert_same(5,count(tsurikue_en_pairs()),'expected five pairs');
assert_same('https://tsurikue.com/en/orizuru-tower/',tsurikue_en_post_link('old',new WP_Post(4375)),'English canonical Orizuru');
assert_same('https://tsurikue.com/en/yamaguchi-road-trip/',tsurikue_en_post_link('old',new WP_Post(4380)),'English canonical Yamaguchi');
assert_same('https://tsurikue.com/en/okunoshima-rabbit-island/',tsurikue_en_post_link('old',new WP_Post(4392)),'English canonical Okunoshima');
assert_same('https://tsurikue.com/en/matsue-vogel-park/',tsurikue_en_post_link('old',new WP_Post(4391)),'English canonical Matsue');
assert_same('https://tsurikue.com/en/tottori-road-trip/',tsurikue_en_post_link('old',new WP_Post(4393)),'English canonical Tottori');
assert_same('https://tsurikue.com/yamaguchi-drive/',tsurikue_en_post_link('https://tsurikue.com/yamaguchi-drive/',new WP_Post(2664)),'Japanese route unchanged');
assert_same('old',tsurikue_en_post_link('old',new WP_Post(99)),'unrelated content unchanged');
tsurikue_en_add_rewrites();
assert_same('index.php?post_type=post&name=orizuru-tower-english',$GLOBALS['rewrites']['^en/orizuru\\-tower/?$'],'Orizuru rewrite');
assert_same('index.php?post_type=post&name=yamaguchi-roadtrip-english',$GLOBALS['rewrites']['^en/yamaguchi\\-road\\-trip/?
assert_same(false,tsurikue_en_redirect_canonical('https://tsurikue.com/orizuru-tower-english/','https://tsurikue.com/en/orizuru-tower/'),'English redirect suppressed');
assert_same('https://tsurikue.com/random/',tsurikue_en_redirect_canonical('https://tsurikue.com/random/','https://tsurikue.com/random/'),'unknown route untouched');
echo "Pilot route tests OK\n";
],'Yamaguchi rewrite');
assert_same('index.php?post_type=post&name=okunoshima-rabbit-island-english',$GLOBALS['rewrites']['^en/okunoshima\\-rabbit\\-island/?
assert_same(false,tsurikue_en_redirect_canonical('https://tsurikue.com/orizuru-tower-english/','https://tsurikue.com/en/orizuru-tower/'),'English redirect suppressed');
assert_same('https://tsurikue.com/random/',tsurikue_en_redirect_canonical('https://tsurikue.com/random/','https://tsurikue.com/random/'),'unknown route untouched');
echo "Pilot route tests OK\n";
],'Okunoshima rewrite');
assert_same('index.php?post_type=post&name=matsue-vogel-park-english',$GLOBALS['rewrites']['^en/matsue\\-vogel\\-park/?
assert_same(false,tsurikue_en_redirect_canonical('https://tsurikue.com/orizuru-tower-english/','https://tsurikue.com/en/orizuru-tower/'),'English redirect suppressed');
assert_same('https://tsurikue.com/random/',tsurikue_en_redirect_canonical('https://tsurikue.com/random/','https://tsurikue.com/random/'),'unknown route untouched');
echo "Pilot route tests OK\n";
],'Matsue rewrite');
assert_same('index.php?post_type=post&name=tottori-drive-english',$GLOBALS['rewrites']['^en/tottori\\-road\\-trip/?
assert_same(false,tsurikue_en_redirect_canonical('https://tsurikue.com/orizuru-tower-english/','https://tsurikue.com/en/orizuru-tower/'),'English redirect suppressed');
assert_same('https://tsurikue.com/random/',tsurikue_en_redirect_canonical('https://tsurikue.com/random/','https://tsurikue.com/random/'),'unknown route untouched');
echo "Pilot route tests OK\n";
],'Tottori rewrite');
assert_same(false,tsurikue_en_redirect_canonical('https://tsurikue.com/orizuru-tower-english/','https://tsurikue.com/en/orizuru-tower/'),'English redirect suppressed');
assert_same('https://tsurikue.com/random/',tsurikue_en_redirect_canonical('https://tsurikue.com/random/','https://tsurikue.com/random/'),'unknown route untouched');
echo "Pilot route tests OK\n";
