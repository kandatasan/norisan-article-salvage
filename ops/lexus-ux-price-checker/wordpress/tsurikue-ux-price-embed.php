<?php
/**
 * Plugin Name: Tsurikue UX Price Checker Embed
 * Description: Adds the shared UX price checker to two exact purchase-intent articles; no stored post edits.
 * Version: 0.1.0
 */
if (!defined('ABSPATH')) { exit; }

add_filter('the_content', static function ($html) {
    // Fail closed until the price data, A8 destination and production URL pass review.
    if (!defined('TSURIKUE_UX_PRICE_ENABLED') || TSURIKUE_UX_PRICE_ENABLED !== true) { return $html; }
    if (!is_singular('post') || !in_the_loop() || !is_main_query()) { return $html; }
    $post = get_post();
    if (!$post || $post->post_status !== 'publish' || !is_string($html)) { return $html; }
    $config = array(
        2948 => array('slug' => 'lexus-ux-used', 'heading' => 'レクサス認定中古車CPOという選択肢', 'query' => 'model=250h&grade=fs&year=2021'),
        3601 => array('slug' => 'lexus-ux250h-used-vs-ux300h', 'heading' => 'UX300hはちゃんと良くなっている｜試乗して感じた違い', 'query' => 'model=250h&grade=all&year=2021'),
    );
    $id = (int)$post->ID;
    if (!isset($config[$id]) || $post->post_name !== $config[$id]['slug']) { return $html; }
    if (strpos($html, 'data-tsurikue-ux-price-widget') !== false) { return $html; }
    $want = $config[$id]['heading'];
    if (!preg_match_all('~<h2\b[^>]*>.*?</h2>~is', $html, $hits, PREG_OFFSET_CAPTURE)) { return $html; }
    $position = null;
    foreach ($hits[0] as $hit) {
        $visible = trim(html_entity_decode(strip_tags($hit[0]), ENT_QUOTES | ENT_HTML5, 'UTF-8'));
        if ($visible === $want) { $position = $hit[1]; break; }
    }
    if ($position === null) { return $html; }
    $src = 'https://tsurikue.com/ux-price-checker/?' . $config[$id]['query'];
    $src = htmlspecialchars($src, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    $embed = '<div data-tsurikue-ux-price-widget="1" class="tsurikue-ux-price-embed" style="margin:28px 0 30px;clear:both">'
           . '<iframe title="レクサスUX中古車の参考価格・一般中古車とCPOを比較" src="' . $src . '" '
           . 'loading="lazy" referrerpolicy="strict-origin-when-cross-origin" '
           . 'style="display:block;width:100%;height:860px;border:0;border-radius:12px;" '
           . 'aria-label="レクサスUXの中古車参考価格"></iframe></div>';
    return substr($html, 0, $position) . $embed . substr($html, $position);
}, 20);