<?php
// Offline WordPress shortcode insertion regression test. No network or WP database.
define('ABSPATH', '/test/');
$filter = null;
function add_filter($name, $callback, $priority=10) { $GLOBALS['filter'] = $callback; }
function is_singular($type) { return true; }
function in_the_loop() { return true; }
function is_main_query() { return true; }
function get_post() { return $GLOBALS['post']; }
require dirname(__DIR__) . '/tsurikue-ux-price-embed.php';
$GLOBALS['post']=(object)array('ID'=>2948,'post_name'=>'lexus-ux-used','post_status'=>'publish');
$before_enabled='<h2>レクサス認定中古車CPOという選択肢</h2>';
if ($GLOBALS['filter']($before_enabled)!==$before_enabled) { throw new RuntimeException('Plugin must be inert unless explicitly enabled'); }
define('TSURIKUE_UX_PRICE_ENABLED', true);
$cases = array(
    array('id'=>2948,'slug'=>'lexus-ux-used','h'=>'レクサス認定中古車CPOという選択肢'),
    array('id'=>3601,'slug'=>'lexus-ux250h-used-vs-ux300h','h'=>'UX300hはちゃんと良くなっている｜試乗して感じた違い'),
);
foreach ($cases as $c) {
    $GLOBALS['post']=(object)array('ID'=>$c['id'],'post_name'=>$c['slug'],'post_status'=>'publish');
    $html='<p>最初の文章</p><h2>'.$c['h'].'</h2><p>次の文章</p>';
    $out=$GLOBALS['filter']($html);
    if (substr_count($out,'data-tsurikue-ux-price-widget')!==1) { throw new RuntimeException('Missing widget: '.$c['slug']); }
    if (strpos($out,'height:620px')===false) { throw new RuntimeException('Tool-only iframe height mismatch'); }
    if (strpos($out,'data-tsurikue-ux-price-widget')>strpos($out,'<h2>')) { throw new RuntimeException('Wrong insertion point'); }
    if ($out!==$GLOBALS['filter']($out)) { throw new RuntimeException('Duplicate on repeat'); }
    if (substr_count($out, '<p>次の文章</p>')!==1) { throw new RuntimeException('Post damaged'); }
}
$GLOBALS['post']=(object)array('ID'=>2517,'post_name'=>'ux-koukai','post_status'=>'publish');
$unchanged='<h2>レクサス認定中古車CPOという選択肢</h2>';
if ($GLOBALS['filter']($unchanged)!==$unchanged) { throw new RuntimeException('Non-target changed'); }
$GLOBALS['post']=(object)array('ID'=>2948,'post_name'=>'lexus-ux-used','post_status'=>'publish');
if ($GLOBALS['filter']('<h2>記事が更新されました</h2>')!== '<h2>記事が更新されました</h2>') { throw new RuntimeException('Missing heading should skip'); }
echo "UX_WP_EMBED_TEST=PASS\n";