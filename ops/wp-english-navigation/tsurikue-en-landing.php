<?php
/**
 * Plugin Name: Tsurikue English Travel landing
 * Description: Only the English landing and English Travel archive receive an English document language, plus a published-article listing shortcode.
 * Version: 0.1.0
 */
if (!defined('ABSPATH')) { exit; }

function tsurikue_en_travel_lang_attributes($attributes) {
    if (!is_page('en') && !is_category('english-travel')) { return $attributes; }
    if (preg_match('/\\blang=(["\\\']).*?\\1/', $attributes)) {
        return preg_replace('/\\blang=(["\\\']).*?\\1/', 'lang="en"', $attributes, 1);
    }
    return trim($attributes . ' lang="en"');
}
add_filter('language_attributes', 'tsurikue_en_travel_lang_attributes', 30);

function tsurikue_en_articles_shortcode() {
    $term = get_term_by('slug', 'english-travel', 'category');
    if (!$term || is_wp_error($term)) {
        return '<p>English travel stories are being prepared.</p>';
    }
    $posts = get_posts(array(
        'post_type' => 'post',
        'post_status' => 'publish',
        'category' => (int) $term->term_id,
        'posts_per_page' => 30,
        'orderby' => 'date',
        'order' => 'DESC',
        'suppress_filters' => false,
    ));
    if (!$posts) { return '<p>Our first English guide is coming soon.</p>'; }

    $out = '<div class="tsurikue-en-travel-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px;margin:24px 0">';
    foreach ($posts as $post) {
        $url = get_permalink($post->ID);
        $title = get_the_title($post->ID);
        $thumb = get_the_post_thumbnail_url($post->ID, 'medium_large');
        $excerpt = wp_trim_words(wp_strip_all_tags(get_the_excerpt($post)), 24, '…');
        $out .= '<article class="tsurikue-en-travel-card" style="border:1px solid #e6e6e6;border-radius:12px;overflow:hidden;background:#fff">';
        $out .= '<a href="' . esc_url($url) . '" style="display:block;color:inherit;text-decoration:none">';
        if ($thumb) {
            $out .= '<img src="' . esc_url($thumb) . '" alt="' . esc_attr($title) . '" loading="lazy" style="width:100%;height:180px;object-fit:cover;display:block">';
        }
        $out .= '<div style="padding:15px">';
        $out .= '<strong style="font-size:1.08em;line-height:1.45;display:block;margin-bottom:8px">' . esc_html($title) . '</strong>';
        $out .= '<p style="font-size:.94em;line-height:1.65;margin:0;color:#555">' . esc_html($excerpt) . '</p>';
        $out .= '</div></a></article>';
    }
    return $out . '</div>';
}
add_shortcode('tsurikue_en_articles', 'tsurikue_en_articles_shortcode');
