<?php
/** One-time English-only category attachment for two newly created draft posts. */
if (!defined('ABSPATH')) { throw new RuntimeException('WordPress environment required'); }
function tsurikue_batch4_assert($cond,$message) {
    if (!$cond) { throw new RuntimeException('EN_BATCH4_BLOCKED: '.$message); }
}
$expected=array(
    array('ja'=>3384,'ja_slug'=>'kochi-1night-2days-drive','en'=>4402,'en_slug'=>'kochi-roadtrip-english','path'=>'kochi-road-trip'),
    array('ja'=>3882,'ja_slug'=>'kurahashijima-autumn-drive','en'=>4403,'en_slug'=>'kurahashi-island-english','path'=>'kurahashi-island')
);
$cat=get_category_by_slug('english-travel');
tsurikue_batch4_assert($cat instanceof WP_Term && (int)$cat->term_id===49,'English Travel category changed');
tsurikue_batch4_assert(function_exists('tsurikue_en_pairs') && count(tsurikue_en_pairs())===7,'seven route plugin not loaded');
$existingEnglish=array(4375,4380,4391,4392,4393);
foreach($existingEnglish as $id) {
    tsurikue_batch4_assert(get_post_status($id)==='publish','existing English post no longer published: '.$id);
    tsurikue_batch4_assert(wp_get_post_categories($id)===array(49),'existing English category changed: '.$id);
}
$oldCategories=array();
foreach($expected as $item) {
    $ja=get_post($item['ja']);$en=get_post($item['en']);
    tsurikue_batch4_assert($ja instanceof WP_Post && $ja->post_type==='post' && $ja->post_status==='publish' && $ja->post_name===$item['ja_slug'],'source changed: '.$item['ja']);
    tsurikue_batch4_assert($en instanceof WP_Post && $en->post_type==='post' && $en->post_status==='draft' && $en->post_name===$item['en_slug'],'English draft changed: '.$item['en']);
    $oldCategories[$en->ID]=wp_get_post_categories($en->ID);
    tsurikue_batch4_assert($oldCategories[$en->ID]===array(1),'new draft categories not default: '.$en->ID);
    tsurikue_batch4_assert(tsurikue_en_post_link('unused',$en)==='https://tsurikue.com/en/'.$item['path'].'/','unexpected new canonical');
}
$beforePosts=(int)wp_count_posts('post')->publish;
$beforePages=(int)wp_count_posts('page')->publish;
$changed=array();
try {
    foreach($expected as $item) {
        $result=wp_set_post_categories($item['en'],array(49),false);
        tsurikue_batch4_assert(!is_wp_error($result),'category attachment failed');
        $changed[]=$item['en'];
        tsurikue_batch4_assert(wp_get_post_categories($item['en'])===array(49),'category verification failed');
    }
    $rules=get_option('rewrite_rules');
    tsurikue_batch4_assert(is_array($rules),'rewrite rules option invalid');
    foreach(tsurikue_en_pairs() as $pair) {
        $key='^en/'.preg_quote($pair['en_path'],'/').'/?$';
        tsurikue_batch4_assert(isset($rules[$key]),'rewrite missing for '.$pair['en_path']);
    }
    foreach(array(
        2647=>'/orizuru-tower/',2664=>'/yamaguchi-drive/',
        3730=>'/okunoshima-rabbit-island/',3438=>'/matsue-vogel-park/',2658=>'/tottori-drive/',
        3384=>'/kochi-1night-2days-drive/',3882=>'/kurahashijima-autumn-drive/'
    ) as $id=>$path) {
        tsurikue_batch4_assert(wp_parse_url(get_permalink($id),PHP_URL_PATH)===$path,'Japanese permalink changed '.$id);
    }
    tsurikue_batch4_assert((int)wp_count_posts('post')->publish===$beforePosts,'published post count changed');
    tsurikue_batch4_assert((int)wp_count_posts('page')->publish===$beforePages,'published page count changed');
    tsurikue_batch4_assert(get_post_status(4402)==='draft' && get_post_status(4403)==='draft','new drafts unexpectedly published');
    echo 'EN_BATCH4_SUCCESS '.wp_json_encode(array(
        'new_posts'=>array(4402,4403),
        'new_categories'=>array(wp_get_post_categories(4402),wp_get_post_categories(4403)),
        'routes'=>array('https://tsurikue.com/en/kochi-road-trip/','https://tsurikue.com/en/kurahashi-island/'),
        'pair_count'=>count(tsurikue_en_pairs()),
        'published_before_after'=>array($beforePosts,(int)wp_count_posts('post')->publish),
        'new_post_publications'=>0,'japanese_content_writes'=>0
    ),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES).PHP_EOL;
} catch(Throwable $error) {
    foreach($changed as $id) { wp_set_post_categories($id,$oldCategories[$id],false); }
    echo 'EN_BATCH4_CATEGORY_ROLLBACK_ATTEMPTED=yes'.PHP_EOL;
    throw $error;
}
