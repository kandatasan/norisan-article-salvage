<?php
/** Attach three new English WordPress drafts to category English Travel; no publication. */
if(!defined('ABSPATH')){throw new RuntimeException('WordPress context required');}
function tsurikue_batch5_check($ok,$msg){if(!$ok){throw new RuntimeException('EN_BATCH5_BLOCKED: '.$msg);}}
$items=array(
 array('ja'=>2408,'ja_slug'=>'muvalley','en'=>4409,'en_slug'=>'mikawa-mu-valley-english','path'=>'mikawa-mu-valley'),
 array('ja'=>2125,'ja_slug'=>'human-beach-nagase','en'=>4410,'en_slug'=>'nagase-beach-etajima-english','path'=>'nagase-beach'),
 array('ja'=>1887,'ja_slug'=>'etajima-sightseeing','en'=>4408,'en_slug'=>'etajima-island-guide-english','path'=>'etajima-island')
);
$term=get_category_by_slug('english-travel');
tsurikue_batch5_check($term instanceof WP_Term && (int)$term->term_id===49,'English Travel category changed');
tsurikue_batch5_check(function_exists('tsurikue_en_pairs') && count(tsurikue_en_pairs())===10,'ten-route MU plugin not active');
foreach(array(4375,4380,4391,4392,4393,4402,4403) as $id) {
 tsurikue_batch5_check(get_post_status($id)==='publish','existing English post no longer published: '.$id);
 tsurikue_batch5_check(wp_get_post_categories($id)===array(49),'existing English category changed: '.$id);
}
$beforePosts=(int)wp_count_posts('post')->publish;
$beforePages=(int)wp_count_posts('page')->publish;
$oldCats=array();$applied=array();
foreach($items as $item){
 $ja=get_post($item['ja']);$en=get_post($item['en']);
 tsurikue_batch5_check($ja instanceof WP_Post&&$ja->post_type==='post'&&$ja->post_status==='publish'&&$ja->post_name===$item['ja_slug'],'Japanese original drift: '.$item['ja']);
 tsurikue_batch5_check($en instanceof WP_Post&&$en->post_type==='post'&&$en->post_status==='draft'&&$en->post_name===$item['en_slug'],'new English draft drift: '.$item['en']);
 $oldCats[$item['en']]=wp_get_post_categories($item['en']);
 tsurikue_batch5_check($oldCats[$item['en']]===array(1),'unexpected draft categories '.$item['en']);
 tsurikue_batch5_check(tsurikue_en_post_link('none',$en)==='https://tsurikue.com/en/'.$item['path'].'/','new canonical mismatch '.$item['en']);
}
try{
 foreach($items as $item){
   $result=wp_set_post_categories($item['en'],array(49),false);
   tsurikue_batch5_check(!is_wp_error($result),'category update failed: '.$item['en']);
   $applied[]=$item['en'];
   tsurikue_batch5_check(wp_get_post_categories($item['en'])===array(49),'category verify failed: '.$item['en']);
 }
 $rules=get_option('rewrite_rules');
 tsurikue_batch5_check(is_array($rules),'rewrite rules not an array');
 foreach(tsurikue_en_pairs() as $pair){
   $key='^en/'.preg_quote($pair['en_path'],'/').'/?$';
   tsurikue_batch5_check(isset($rules[$key]),'missing rewrite '.$pair['en_path']);
 }
 $sources=array(
 2647=>'/orizuru-tower/',2664=>'/yamaguchi-drive/',3730=>'/okunoshima-rabbit-island/',
 3438=>'/matsue-vogel-park/',2658=>'/tottori-drive/',3384=>'/kochi-1night-2days-drive/',
 3882=>'/kurahashijima-autumn-drive/',2408=>'/muvalley/',2125=>'/human-beach-nagase/',
 1887=>'/etajima-sightseeing/'
 );
 foreach($sources as $id=>$path){
   tsurikue_batch5_check(wp_parse_url(get_permalink($id),PHP_URL_PATH)===$path,'Japanese permalink changed '.$id);
 }
 tsurikue_batch5_check((int)wp_count_posts('post')->publish===$beforePosts,'published post count changed');
 tsurikue_batch5_check((int)wp_count_posts('page')->publish===$beforePages,'published page count changed');
 foreach($items as $item){tsurikue_batch5_check(get_post_status($item['en'])==='draft','draft became published '.$item['en']);}
 echo 'EN_BATCH5_SUCCESS '.wp_json_encode(array(
  'new_drafts'=>array(4408,4409,4410),
  'new_categories'=>array(wp_get_post_categories(4408),wp_get_post_categories(4409),wp_get_post_categories(4410)),
  'new_urls'=>array('https://tsurikue.com/en/etajima-island/','https://tsurikue.com/en/mikawa-mu-valley/','https://tsurikue.com/en/nagase-beach/'),
  'total_translation_pairs'=>count(tsurikue_en_pairs()),
  'published_posts_before_after'=>array($beforePosts,(int)wp_count_posts('post')->publish),
  'new_post_publications'=>0,'japanese_post_content_writes'=>0
 ),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES).PHP_EOL;
}catch(Throwable $e){
 foreach($applied as $id){wp_set_post_categories($id,$oldCats[$id],false);}
 echo 'EN_BATCH5_CATEGORY_ROLLBACK_ATTEMPTED=yes'.PHP_EOL;
 throw $e;
}
