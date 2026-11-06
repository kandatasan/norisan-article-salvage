<?php
/**
 * Plugin Name: Tsurikue English pilot routes
 * Description: Narrow bilingual routing for two approved travel article pairs.
 * Version: 0.1.0
 *
 * MU plugin: do not translate, edit or republish Japanese content.
 * The routes only become public when the corresponding English posts are published.
 */
if (!defined('ABSPATH')) { exit; }

/**
 * Explicit, auditable translations. Keep Japanese slug and content unchanged.
 * All post IDs and source slugs are verified by project audits.
 */
function tsurikue_en_pairs() {
    return array(
        array('ja_id' => 2647, 'en_id' => 4375, 'en_path' => 'orizuru-tower', 'en_slug' => 'orizuru-tower-english'),
        array('ja_id' => 2664, 'en_id' => 4380, 'en_path' => 'yamaguchi-road-trip', 'en_slug' => 'yamaguchi-roadtrip-english'),
    );
}

function tsurikue_en_pair_for_post($post_id) {
    foreach (tsurikue_en_pairs() as $pair) {
        if ((int) $post_id === $pair['ja_id'] || (int) $post_id === $pair['en_id']) {
            return $pair;
        }
    }
    return null;
}

function tsurikue_en_url_for_pair($pair) {
    return home_url('/en/' . $pair['en_path'] . '/');
}

function tsurikue_en_add_rewrites() {
    foreach (tsurikue_en_pairs() as $pair) {
        add_rewrite_rule(
            '^en/' . preg_quote($pair['en_path'], '/') . '/?$',
            'index.php?post_type=post&name=' . $pair['en_slug'],
            'top'
        );
    }
}
add_action('init', 'tsurikue_en_add_rewrites', 20);

/** Let core canonical tags and the WordPress sitemap use the English URL. */
function tsurikue_en_post_link($permalink, $post, $leavename = false) {
    if (!($post instanceof WP_Post)) { return $permalink; }
    $pair = tsurikue_en_pair_for_post($post->ID);
    if (!$pair || (int) $post->ID !== $pair['en_id']) { return $permalink; }
    return tsurikue_en_url_for_pair($pair);
}
add_filter('post_link', 'tsurikue_en_post_link', 20, 3);

/** Keep legitimate /en/ requests from being canonical-redirected to native slugs. */
function tsurikue_en_redirect_canonical($redirect, $requested) {
    $path = wp_parse_url($requested, PHP_URL_PATH);
    if (!is_string($path)) { return $redirect; }
    foreach (tsurikue_en_pairs() as $pair) {
        if (rtrim($path, '/') === '/en/' . $pair['en_path']) {
            return false;
        }
    }
    return $redirect;
}
add_filter('redirect_canonical', 'tsurikue_en_redirect_canonical', 20, 2);

function tsurikue_en_pair_is_live($pair) {
    $ja = get_post($pair['ja_id']);
    $en = get_post($pair['en_id']);
    return $ja instanceof WP_Post && $en instanceof WP_Post
        && $ja->post_status === 'publish' && $en->post_status === 'publish';
}

function tsurikue_en_current_live_pair() {
    if (!is_singular('post')) { return null; }
    $pair = tsurikue_en_pair_for_post(get_queried_object_id());
    return $pair && tsurikue_en_pair_is_live($pair) ? $pair : null;
}

/** Google reciprocal language alternatives: only once both pages are public. */
function tsurikue_en_hreflang_head() {
    $pair = tsurikue_en_current_live_pair();
    if (!$pair) { return; }
    $ja_url = get_permalink($pair['ja_id']);
    $en_url = tsurikue_en_url_for_pair($pair);
    if (!$ja_url) { return; }
    echo "\n" . '<link rel="alternate" hreflang="ja" href="' . esc_url($ja_url) . '" />' . "\n";
    echo '<link rel="alternate" hreflang="en" href="' . esc_url($en_url) . '" />' . "\n";
}
add_action('wp_head', 'tsurikue_en_hreflang_head', 3);

/** Site language remains Japanese; the matched English article uses English lang. */
function tsurikue_en_language_attributes($attributes) {
    if (!is_singular('post')) { return $attributes; }
    $id = (int) get_queried_object_id();
    $pair = tsurikue_en_pair_for_post($id);
    if (!$pair || $id !== $pair['en_id']) { return $attributes; }
    if (preg_match('/\\blang=(["\\\']).*?\\1/', $attributes)) {
        return preg_replace('/\\blang=(["\\\']).*?\\1/', 'lang="en"', $attributes, 1);
    }
    return trim($attributes . ' lang="en"');
}
add_filter('language_attributes', 'tsurikue_en_language_attributes', 20);

/** Contextual language switch; does not change any stored Japanese post body. */
function tsurikue_en_content_language_switch($content) {
    if (!is_singular('post') || !in_the_loop() || !is_main_query()) { return $content; }
    $pair = tsurikue_en_current_live_pair();
    if (!$pair) { return $content; }
    $id = (int) get_queried_object_id();
    if ($id === $pair['ja_id']) {
        $label = 'Read this article in English';
        $target = tsurikue_en_url_for_pair($pair);
    } else {
        $label = '日本語で読む (Japanese version)';
        $target = get_permalink($pair['ja_id']);
    }
    $html = '<nav class="tsurikue-en-language-switch" aria-label="Article language">'
        . '<p><a href="' . esc_url($target) . '" hreflang="' . ($id === $pair['ja_id'] ? 'en' : 'ja') . '">'
        . esc_html($label) . '</a></p></nav>';
    return $html . $content;
}
add_filter('the_content', 'tsurikue_en_content_language_switch', 8);
