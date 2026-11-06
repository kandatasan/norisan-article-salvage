<?php
/**
 * One-time guarded menu label change: EN -> English.
 *
 * Scope: existing SWELL smartphone header item ID 4387 in menu 21 ONLY.
 * The original four links, drawer menu, page, and articles remain unchanged.
 */
if (!defined('ABSPATH')) {
    throw new RuntimeException('This script requires WordPress');
}
function tsurikue_english_menu_assert($condition, $message) {
    if (!$condition) {
        throw new RuntimeException('ENGLISH_MENU_BLOCKED: ' . $message);
    }
}
function tsurikue_english_menu_items($id) {
    $items = wp_get_nav_menu_items($id, array('post_status' => 'publish'));
    return is_array($items) ? array_values($items) : array();
}
function tsurikue_english_menu_labels($items) {
    return array_values(array_map(function ($item) { return $item->title; }, $items));
}
$locations = get_nav_menu_locations();
tsurikue_english_menu_assert((int) ($locations['sp_head_menu'] ?? 0) === 21, 'mobile header location changed');
tsurikue_english_menu_assert((int) ($locations['nav_sp_menu'] ?? 0) === 20, 'drawer location changed');
tsurikue_english_menu_assert(get_post_status(4385) === 'publish', 'English landing page is not published');
$en_page = get_page_by_path('en');
tsurikue_english_menu_assert($en_page instanceof WP_Post && (int) $en_page->ID === 4385, '/en/ page mismatch');

$old_labels = array('おでかけ', '釣り', 'グルメ', 'クルマ', 'EN');
$new_labels = array('おでかけ', '釣り', 'グルメ', 'クルマ', 'English');
$header_before = tsurikue_english_menu_items(21);
$before_labels = tsurikue_english_menu_labels($header_before);
$drawer_before = tsurikue_english_menu_items(20);
$drawer_before_ids = array_map(function ($item) { return (int) $item->ID; }, $drawer_before);
$drawer_before_labels = tsurikue_english_menu_labels($drawer_before);
tsurikue_english_menu_assert(
    $drawer_before_labels === array('おでかけ','魚釣り','グルメ','クルマ','English Travel','運営者情報','お問い合わせ','プライバシーポリシー'),
    'drawer menu changed'
);
tsurikue_english_menu_assert($before_labels === $old_labels || $before_labels === $new_labels, 'unexpected header menu items');

$item = get_post(4387);
tsurikue_english_menu_assert($item instanceof WP_Post && $item->post_type === 'nav_menu_item' && $item->post_status === 'publish', 'target post invalid');
$menu_item = $header_before[4];
tsurikue_english_menu_assert((int) $menu_item->ID === 4387, 'target is not the fifth header entry');
tsurikue_english_menu_assert($menu_item->type === 'custom', 'target entry is not a custom link');
tsurikue_english_menu_assert((int) $menu_item->menu_order === 5, 'target menu position changed');
tsurikue_english_menu_assert((int) $menu_item->menu_item_parent === 0, 'target became a submenu');
tsurikue_english_menu_assert($menu_item->url === 'https://tsurikue.com/en/', 'target destination changed');
tsurikue_english_menu_assert($item->post_title === $before_labels[4], 'stored title differs from current menu title');
if ($before_labels === $new_labels) {
    echo "ENGLISH_HEADER_ALREADY_UP_TO_DATE=yes\n";
    exit(0);
}

$before_counts = array(
    'posts' => (int) wp_count_posts('post')->publish,
    'pages' => (int) wp_count_posts('page')->publish,
);
$modified = false;
try {
    $result = wp_update_post(array('ID' => 4387, 'post_title' => 'English'), true);
    if (is_wp_error($result)) {
        throw new RuntimeException('could not rename header item: ' . $result->get_error_message());
    }
    $modified = true;
    clean_post_cache(4387);
    $header_after = tsurikue_english_menu_items(21);
    tsurikue_english_menu_assert(tsurikue_english_menu_labels($header_after) === $new_labels, 'final header labels mismatch');
    tsurikue_english_menu_assert(
        array_map(function ($item) { return (int) $item->ID; }, $header_after)
        === array_map(function ($item) { return (int) $item->ID; }, $header_before),
        'header item IDs/order changed'
    );
    tsurikue_english_menu_assert(
        $header_after[4]->url === 'https://tsurikue.com/en/'
        && (int) $header_after[4]->menu_order === 5,
        'target URL or menu order was modified'
    );
    $drawer_after = tsurikue_english_menu_items(20);
    tsurikue_english_menu_assert(
        tsurikue_english_menu_labels($drawer_after) === $drawer_before_labels
        && array_map(function ($item) { return (int) $item->ID; }, $drawer_after) === $drawer_before_ids,
        'drawer content changed'
    );
    tsurikue_english_menu_assert(
        (int) wp_count_posts('post')->publish === $before_counts['posts']
        && (int) wp_count_posts('page')->publish === $before_counts['pages'],
        'published post or page counts changed'
    );
    echo 'ENGLISH_HEADER_SUCCESS ' . wp_json_encode(array(
        'menu_id' => 21,
        'item_id' => 4387,
        'labels_before' => $before_labels,
        'labels_after' => tsurikue_english_menu_labels($header_after),
        'url' => $header_after[4]->url,
        'drawer_unchanged' => true,
        'published_posts_unchanged' => true,
        'published_pages_unchanged' => true,
        'post_article_writes' => 0,
    ), JSON_UNESCAPED_UNICODE) . PHP_EOL;
} catch (Throwable $e) {
    if ($modified) {
        wp_update_post(array('ID' => 4387, 'post_title' => 'EN'), true);
        clean_post_cache(4387);
        echo "ENGLISH_HEADER_ROLLBACK_ATTEMPTED=yes\n";
    }
    throw $e;
}
