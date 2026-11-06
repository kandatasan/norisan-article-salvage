<?php
/**
 * One-time guarded setup for Tsurikue English Travel.
 * Called only from an approved GitHub Actions job on Xserver via wp eval-file.
 * Preconditions, generated IDs and changes are explicitly verified.
 */
if (!defined('ABSPATH')) { throw new RuntimeException('WordPress must be loaded'); }

function tsurikue_en_nav_assert($condition, $message) {
    if (!$condition) { throw new RuntimeException('EN_NAV_BLOCKED: ' . $message); }
}
function tsurikue_en_nav_menu_items($menu_id) {
    $rows = wp_get_nav_menu_items($menu_id, array('post_status' => 'publish'));
    return is_array($rows) ? $rows : array();
}
function tsurikue_en_nav_labels($rows) {
    return array_values(array_map(function ($i) { return $i->title; }, $rows));
}
function tsurikue_en_nav_ids($rows) {
    return array_values(array_map(function ($i) { return (int) $i->ID; }, $rows));
}

$slug = 'english-travel';
$page_slug = 'en';
$locations = get_nav_menu_locations();
tsurikue_en_nav_assert((int)($locations['sp_head_menu'] ?? 0) === 21, 'mobile header menu assignment has changed');
tsurikue_en_nav_assert((int)($locations['nav_sp_menu'] ?? 0) === 20, 'drawer menu assignment has changed');
tsurikue_en_nav_assert(get_page_by_path($page_slug) === null, 'the /en/ page already exists');
tsurikue_en_nav_assert(!term_exists($slug, 'category'), 'English Travel category already exists');
tsurikue_en_nav_assert(function_exists('tsurikue_en_articles_shortcode'), 'English listing MU plugin not installed');
$header_before = tsurikue_en_nav_menu_items(21);
$drawer_before = tsurikue_en_nav_menu_items(20);
tsurikue_en_nav_assert(tsurikue_en_nav_labels($header_before) === array('おでかけ', '釣り', 'グルメ', 'クルマ'), 'mobile header labels differ from audited layout');
tsurikue_en_nav_assert(array_slice(tsurikue_en_nav_labels($drawer_before), 0, 4) === array('おでかけ', '魚釣り', 'グルメ', 'クルマ'), 'drawer first four entries changed');
foreach (array_merge($header_before, $drawer_before) as $item) {
    tsurikue_en_nav_assert(!in_array($item->title, array('EN','English Travel'), true), 'English nav already present');
}
$p1 = get_post(4375);
$p2 = get_post(4380);
tsurikue_en_nav_assert($p1 instanceof WP_Post && $p1->post_type === 'post' && $p1->post_name === 'orizuru-tower-english' && $p1->post_status === 'publish', 'Orizuru English post changed');
tsurikue_en_nav_assert($p2 instanceof WP_Post && $p2->post_type === 'post' && $p2->post_name === 'yamaguchi-roadtrip-english' && $p2->post_status === 'draft', 'Yamaguchi English post changed');
$before_cat_4375 = wp_get_post_categories(4375);
$before_cat_4380 = wp_get_post_categories(4380);
$before_posts = (int) wp_count_posts('post')->publish;
$before_pages = (int) wp_count_posts('page')->publish;
$landing = file_get_contents(__DIR__ . '/landing.html');
tsurikue_en_nav_assert(is_string($landing) && strlen($landing) > 600 && strpos($landing, '[tsurikue_en_articles]') !== false, 'landing page source file invalid');

echo 'EN_NAV_BEFORE ' . wp_json_encode(array(
    'header_menu_id' => 21,
    'header_labels' => tsurikue_en_nav_labels($header_before),
    'drawer_menu_id' => 20,
    'drawer_labels' => tsurikue_en_nav_labels($drawer_before),
    'post_categories' => array('4375' => $before_cat_4375, '4380' => $before_cat_4380),
    'published_posts' => $before_posts,
    'published_pages' => $before_pages,
), JSON_UNESCAPED_UNICODE) . PHP_EOL;

$snapshot = array(
    'date' => gmdate('c'),
    'original_header_item_ids' => tsurikue_en_nav_ids($header_before),
    'original_drawer_item_ids' => tsurikue_en_nav_ids($drawer_before),
    'original_categories' => array('4375' => $before_cat_4375, '4380' => $before_cat_4380),
    'original_post_statuses' => array('4375' => 'publish', '4380' => 'draft'),
    'original_published_counts' => array('posts' => $before_posts, 'pages' => $before_pages),
);
$backup_path = getenv('TSURIKUE_EN_NAV_SNAPSHOT');
tsurikue_en_nav_assert(is_string($backup_path) && $backup_path !== '' && file_put_contents($backup_path, wp_json_encode($snapshot, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT)) !== false, 'could not save navigation snapshot');

$new_category = 0;
$new_page = 0;
$new_menu_items = array();
try {
    $term = wp_insert_term('English Travel', 'category', array(
        'slug' => $slug,
        'description' => 'Firsthand English-language travel guides to Hiroshima, Yamaguchi and western Japan.',
    ));
    if (is_wp_error($term)) { throw new RuntimeException('category creation failed: ' . $term->get_error_message()); }
    $new_category = (int) $term['term_id'];
    tsurikue_en_nav_assert($new_category > 0, 'new category missing ID');
    wp_set_post_categories(4375, array($new_category), false);
    wp_set_post_categories(4380, array($new_category), false);
    tsurikue_en_nav_assert(wp_get_post_categories(4375) === array($new_category), 'English Orizuru category did not update');
    tsurikue_en_nav_assert(wp_get_post_categories(4380) === array($new_category), 'English Yamaguchi category did not update');

    $new_page = wp_insert_post(array(
        'post_type' => 'page',
        'post_name' => 'en',
        'post_title' => 'English Travel | Explore Hiroshima & Western Japan',
        'post_content' => $landing,
        'post_status' => 'draft',
        'post_author' => (int) $p1->post_author,
        'comment_status' => 'closed',
    ), true);
    if (is_wp_error($new_page)) { throw new RuntimeException('landing page creation failed: ' . $new_page->get_error_message()); }
    $new_page = (int) $new_page;
    tsurikue_en_nav_assert($new_page > 0, 'landing page has no ID');
    $new_page_post = get_post($new_page);
    tsurikue_en_nav_assert($new_page_post && $new_page_post->post_name === 'en' && $new_page_post->post_status === 'draft', 'new landing slug/status mismatch');

    $published = wp_update_post(array('ID' => $new_page, 'post_status' => 'publish'), true);
    if (is_wp_error($published)) { throw new RuntimeException('landing page publication failed: ' . $published->get_error_message()); }
    tsurikue_en_nav_assert(get_post_status($new_page) === 'publish', 'landing page did not publish');

    $url = 'https://tsurikue.com/en/';
    $head_item = wp_update_nav_menu_item(21, 0, array(
        'menu-item-title' => 'EN',
        'menu-item-type' => 'custom',
        'menu-item-url' => $url,
        'menu-item-description' => 'English travel guides',
        'menu-item-status' => 'publish',
        'menu-item-position' => 5,
    ));
    if (is_wp_error($head_item)) { throw new RuntimeException('mobile header item failed: ' . $head_item->get_error_message()); }
    $new_menu_items[] = (int) $head_item;
    $drawer_item = wp_update_nav_menu_item(20, 0, array(
        'menu-item-title' => 'English Travel',
        'menu-item-type' => 'custom',
        'menu-item-url' => $url,
        'menu-item-status' => 'publish',
        'menu-item-position' => 5,
    ));
    if (is_wp_error($drawer_item)) { throw new RuntimeException('drawer item failed: ' . $drawer_item->get_error_message()); }
    $new_menu_items[] = (int) $drawer_item;

    // Core menu insertion does not guarantee the requested position.
    // Assign all positions explicitly, preserving the four original category links.
    $desired_header_ids = array_merge(tsurikue_en_nav_ids($header_before), array((int) $head_item));
    $old_drawer_ids = tsurikue_en_nav_ids($drawer_before);
    $desired_drawer_ids = array_merge(
        array_slice($old_drawer_ids, 0, 4),
        array((int) $drawer_item),
        array_slice($old_drawer_ids, 4)
    );
    foreach (array(21 => $desired_header_ids, 20 => $desired_drawer_ids) as $menu_id => $ordered_ids) {
        foreach ($ordered_ids as $index => $id) {
            $result = wp_update_post(array('ID' => (int) $id, 'menu_order' => $index + 1), true);
            if (is_wp_error($result)) {
                throw new RuntimeException('unable to set navigation order for item ' . $id . ': ' . $result->get_error_message());
            }
        }
    }

    $now_header = tsurikue_en_nav_menu_items(21);
    $now_drawer = tsurikue_en_nav_menu_items(20);
    tsurikue_en_nav_assert(array_slice(tsurikue_en_nav_labels($now_header), 0, 5) === array('おでかけ','釣り','グルメ','クルマ','EN'), 'mobile header order invalid');
    tsurikue_en_nav_assert(array_slice(tsurikue_en_nav_labels($now_drawer), 0, 5) === array('おでかけ','魚釣り','グルメ','クルマ','English Travel'), 'drawer navigation order invalid');
    tsurikue_en_nav_assert((int)wp_count_posts('post')->publish === $before_posts, 'published post count changed');
    tsurikue_en_nav_assert((int)wp_count_posts('page')->publish === $before_pages + 1, 'published page count changed unexpectedly');
    tsurikue_en_nav_assert(get_post_status(4375) === 'publish' && get_post_status(4380) === 'draft', 'English article statuses changed');
    tsurikue_en_nav_assert(get_post(2647)->post_name === 'orizuru-tower' && get_post(2664)->post_name === 'yamaguchi-drive', 'Japanese article slugs changed');
    echo 'EN_NAV_SUCCESS ' . wp_json_encode(array(
        'category_id' => $new_category, 'category_slug' => $slug,
        'landing_page_id' => $new_page, 'landing_slug' => 'en', 'landing_status' => 'publish',
        'header_nav_item_id' => $head_item, 'drawer_nav_item_id' => $drawer_item,
        'header_labels' => tsurikue_en_nav_labels($now_header),
        'drawer_labels' => tsurikue_en_nav_labels($now_drawer),
        'english_post_categories' => array('4375' => wp_get_post_categories(4375), '4380' => wp_get_post_categories(4380)),
        'publish_posts_before_after' => array($before_posts, (int)wp_count_posts('post')->publish),
        'publish_pages_before_after' => array($before_pages, (int)wp_count_posts('page')->publish),
        'unrelated_post_content_writes' => 0,
    ), JSON_UNESCAPED_UNICODE) . PHP_EOL;
} catch (Throwable $e) {
    // Rollback only the entities created above; preserve all previously existing menus and articles.
    foreach (array_reverse($new_menu_items) as $id) { wp_delete_post($id, true); }
    // Revert the original navigation positions, including any shifting WordPress did.
    foreach (array_merge($header_before, $drawer_before) as $old) {
        wp_update_post(array('ID' => (int) $old->ID, 'menu_order' => (int) $old->menu_order), true);
    }
    if ($new_page) { wp_delete_post($new_page, true); }
    wp_set_post_categories(4375, $before_cat_4375, false);
    wp_set_post_categories(4380, $before_cat_4380, false);
    if ($new_category) { wp_delete_term($new_category, 'category'); }
    echo 'EN_NAV_ROLLBACK_ATTEMPTED=1' . PHP_EOL;
    throw $e;
}
