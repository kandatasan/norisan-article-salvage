<?php
/**
 * One-time site-specific assignment of three English drafts to English Travel.
 * Run only from a guarded WP CLI deploy after the five-route MU plugin is installed.
 * No post bodies, Japanese categories, titles or publish statuses are altered.
 */
if (!defined('ABSPATH')) { throw new RuntimeException('WordPress environment required'); }

function tsurikue_batch3_assert($ok, $message) {
    if (!$ok) { throw new RuntimeException('EN_BATCH3_BLOCKED: ' . $message); }
}

$expected = array(
    array('ja' => 3730, 'ja_slug' => 'okunoshima-rabbit-island', 'en' => 4392, 'en_slug' => 'okunoshima-rabbit-island-english', 'path' => 'okunoshima-rabbit-island'),
    array('ja' => 3438, 'ja_slug' => 'matsue-vogel-park', 'en' => 4391, 'en_slug' => 'matsue-vogel-park-english', 'path' => 'matsue-vogel-park'),
    array('ja' => 2658, 'ja_slug' => 'tottori-drive', 'en' => 4393, 'en_slug' => 'tottori-drive-english', 'path' => 'tottori-road-trip'),
);
$cat = get_category_by_slug('english-travel');
tsurikue_batch3_assert($cat instanceof WP_Term && (int)$cat->term_id === 49, 'English Travel category ID changed');
tsurikue_batch3_assert(function_exists('tsurikue_en_pairs') && count(tsurikue_en_pairs()) === 5, 'five-route plugin not active');
tsurikue_batch3_assert(get_post_status(4375) === 'publish' && get_post_status(4380) === 'publish', 'existing English posts changed status');
tsurikue_batch3_assert(wp_get_post_categories(4375) === array(49) && wp_get_post_categories(4380) === array(49), 'existing English categories changed');
$before_count=(int)wp_count_posts('post')->publish;
$before_pages=(int)wp_count_posts('page')->publish;
$oldCats=array();
foreach ($expected as $data) {
    $ja=get_post($data['ja']);
    $en=get_post($data['en']);
    tsurikue_batch3_assert($ja instanceof WP_Post && $ja->post_type === 'post' && $ja->post_name === $data['ja_slug'] && $ja->post_status === 'publish', 'Japanese source changed: ' . $data['ja']);
    tsurikue_batch3_assert($en instanceof WP_Post && $en->post_type === 'post' && $en->post_name === $data['en_slug'] && $en->post_status === 'draft', 'English draft changed: ' . $data['en']);
    $oldCats[$en->ID]=wp_get_post_categories($en->ID);
    tsurikue_batch3_assert($oldCats[$en->ID] === array(1), 'English draft category no longer default: ' . $data['en']);
    $url=tsurikue_en_post_link('invalid', $en);
    tsurikue_batch3_assert($url === 'https://tsurikue.com/en/' . $data['path'] . '/', 'English URL unexpected: ' . $data['en']);
}
$changes=array();
try {
    foreach($expected as $data) {
        $ok=wp_set_post_categories($data['en'], array(49), false);
        tsurikue_batch3_assert(!is_wp_error($ok), 'category set failed for ' . $data['en']);
        $changes[]=$data['en'];
        tsurikue_batch3_assert(wp_get_post_categories($data['en']) === array(49), 'category verification failed for ' . $data['en']);
    }
    $rules=get_option('rewrite_rules');
    foreach(tsurikue_en_pairs() as $pair) {
        $key='^en/' . preg_quote($pair['en_path'], '/') . '/?$';
        tsurikue_batch3_assert(isset($rules[$key]), 'missing rewrite rule for ' . $pair['en_path']);
    }
    foreach(array(2647 => '/orizuru-tower/', 2664 => '/yamaguchi-drive/', 3730 => '/okunoshima-rabbit-island/',3438 => '/matsue-vogel-park/',2658 => '/tottori-drive/') as $id => $path) {
        tsurikue_batch3_assert(wp_parse_url(get_permalink($id), PHP_URL_PATH)===$path, 'Japanese permalink changed: ' . $id);
    }
    tsurikue_batch3_assert((int)wp_count_posts('post')->publish === $before_count, 'published post count changed');
    tsurikue_batch3_assert((int)wp_count_posts('page')->publish === $before_pages, 'published page count changed');
    tsurikue_batch3_assert(get_post_status(4391) === 'draft' && get_post_status(4392) === 'draft' && get_post_status(4393) === 'draft', 'an English draft was published unexpectedly');
    $report=array();
    foreach($expected as $data) { $report[]=array('source'=>$data['ja'],'english'=>$data['en'],'status'=>'draft','categories'=>wp_get_post_categories($data['en']),'planned_url'=>'https://tsurikue.com/en/' . $data['path'] . '/'); }
    echo 'EN_BATCH3_SUCCESS ' . wp_json_encode(array('pairs'=>count(tsurikue_en_pairs()),'articles'=>$report,'published_posts_before_after'=>array($before_count,(int)wp_count_posts('post')->publish),'published_pages_before_after'=>array($before_pages,(int)wp_count_posts('page')->publish),'japanese_article_writes'=>0,'publish_count'=>0),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES) . PHP_EOL;
} catch (Throwable $e) {
    foreach($changes as $id) { wp_set_post_categories($id, $oldCats[$id], false); }
    echo 'EN_BATCH3_CATEGORY_ROLLBACK_ATTEMPTED=yes' . PHP_EOL;
    throw $e;
}
