<?php
/**
 * Create/publish the shared CTN appraisal CTA blog part.
 * Guardrails:
 * - never rewrites articles
 * - never overwrites a human-edited existing blog part
 * - idempotent by slug/title/marker
 * - validates native SWELL button render and the exact A8 anchor/pixel pair
 */
if (!defined('ABSPATH')) { exit(10); }
if (!post_type_exists('blog_parts') || !shortcode_exists('blog_parts')) {
  throw new RuntimeException('SWELL blog_parts/shortcode unavailable');
}
if (!WP_Block_Type_Registry::get_instance()->is_registered('loos/button')) {
  throw new RuntimeException('Native SWELL button block is not registered');
}

$title='CTN一括車査定｜共通CTA（SWELLボタン）';
$slug='ctn-car-appraisal-common-cta';
$marker='data-tsurikue-ctn-common-cta="20261112"';
$href='https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEF1M+5I4S+5YRHE';
$pixel='https://www18.a8.net/0.gif?a8mat=3Z8YF4+7VEF1M+5I4S+5YRHE';

$content=<<<'BLOCKS'
<!-- wp:paragraph {"style":{"typography":{"textAlign":"center"}},"className":"u-mb-ctrl u-mb-5"} -->
<p class="has-text-align-center u-mb-ctrl u-mb-5" data-tsurikue-ctn-common-cta="20261112"><strong>お試しだけでもOK！</strong></p>
<!-- /wp:paragraph -->

<!-- wp:loos/button {"color":"green","className":"is-style-btn_solid u-mb-ctrl u-mb-5"} -->
<div class="swell-block-button -html green_ is-style-btn_solid u-mb-ctrl u-mb-5"><a href="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEF1M+5I4S+5YRHE" rel="nofollow">【CTN一括車査定】</a>
<img border="0" width="1" height="1" src="https://www18.a8.net/0.gif?a8mat=3Z8YF4+7VEF1M+5I4S+5YRHE" alt=""></div>
<!-- /wp:loos/button -->

<!-- wp:paragraph {"style":{"typography":{"textAlign":"center"}},"fontSize":"small"} -->
<p class="has-text-align-center has-small-font-size">電話がかかってくるのは、最大でも3社まで</p>
<!-- /wp:paragraph -->
BLOCKS;

$blocks=parse_blocks($content);
$want=array('core/paragraph','loos/button','core/paragraph');
if(count($blocks)!==count($want)) throw new RuntimeException('Unexpected direct block count');
foreach($blocks as $i=>$b){
  if(($b['blockName']??null)!==$want[$i] || !empty($b['innerBlocks'])) {
    throw new RuntimeException('Unexpected nesting or block type');
  }
}
if(substr_count($content,$href)!==1 || substr_count($content,$pixel)!==1) {
  throw new RuntimeException('Exact A8 anchor/pixel pair count mismatch');
}
if(strpos($content,'rel="nofollow"')===false ||
   strpos($content,'>【CTN一括車査定】</a>')===false ||
   strpos($content,'お試しだけでもOK！')===false ||
   strpos($content,'電話がかかってくるのは、最大でも3社まで')===false ||
   strpos($content,'swell-block-button -html green_ is-style-btn_solid')===false) {
  throw new RuntimeException('CTA source validation failed');
}

$ids=get_posts(array(
  'post_type'=>'blog_parts',
  'post_status'=>array('publish','draft','pending','private','future','trash'),
  'posts_per_page'=>-1,
  'fields'=>'ids',
));
$found=array();
foreach($ids as $id){
  $p=get_post((int)$id);
  if(!$p) continue;
  if($p->post_name===$slug || $p->post_title===$title ||
     strpos((string)$p->post_content,$marker)!==false){
    $found[]=$p;
  }
}
if(count($found)>1) throw new RuntimeException('Multiple matching CTN blog parts found');

$created=false;
if(count($found)===0){
  $admins=get_users(array('role'=>'administrator','fields'=>'ID','number'=>1,'orderby'=>'ID','order'=>'ASC'));
  if(!is_array($admins) || count($admins)!==1) throw new RuntimeException('Cannot resolve admin author');
  $id=wp_insert_post(array(
    'post_type'=>'blog_parts',
    'post_status'=>'draft',
    'post_title'=>$title,
    'post_name'=>$slug,
    'post_content'=>$content,
    'post_author'=>(int)$admins[0],
    'comment_status'=>'closed',
    'ping_status'=>'closed',
  ),true);
  if(is_wp_error($id)) throw new RuntimeException('CTN blog part insert failed: '.$id->get_error_code());
  $created=true;
  $p=get_post((int)$id);
}else{
  $p=$found[0];
  $id=(int)$p->ID;
  if($p->post_name!==$slug || $p->post_title!==$title || (string)$p->post_content!==$content){
    echo 'CTN_COMMON_BLOGPART_RESULT=SKIP_EXISTING_DRIFT'.PHP_EOL;
    echo 'CTN_COMMON_BLOGPART_ID='.$id.PHP_EOL;
    echo 'CTN_COMMON_BLOGPART_STATUS='.$p->post_status.PHP_EOL;
    return;
  }
  if(!in_array($p->post_status,array('draft','publish'),true)){
    throw new RuntimeException('Matching CTN blog part has unexpected status: '.$p->post_status);
  }
}

$render=do_blocks((string)$p->post_content);
$valid=$p &&
  $p->post_type==='blog_parts' &&
  $p->post_title===$title &&
  $p->post_name===$slug &&
  (string)$p->post_content===$content &&
  substr_count($render,$href)===1 &&
  substr_count($render,$pixel)===1 &&
  strpos($render,'swell-block-button -html green_ is-style-btn_solid')!==false &&
  strpos($render,'お試しだけでもOK！')!==false &&
  strpos($render,'電話がかかってくるのは、最大でも3社まで')!==false;

if(!$valid){
  if($created) wp_delete_post($id,true);
  throw new RuntimeException('CTN blog part render audit failed'.($created?'; rolled back':''));
}

if($p->post_status==='draft'){
  $u=wp_update_post(array('ID'=>$id,'post_status'=>'publish'),true);
  if(is_wp_error($u)){
    if($created) wp_delete_post($id,true);
    throw new RuntimeException('CTN blog part publish failed: '.$u->get_error_code());
  }
}

$after=get_post($id);
$render2=do_blocks((string)($after->post_content??''));
$success=$after &&
  $after->post_type==='blog_parts' &&
  $after->post_status==='publish' &&
  $after->post_title===$title &&
  $after->post_name===$slug &&
  (string)$after->post_content===$content &&
  substr_count($render2,$href)===1 &&
  substr_count($render2,$pixel)===1 &&
  strpos($render2,'swell-block-button -html green_ is-style-btn_solid')!==false;

if(!$success){
  if($created) wp_delete_post($id,true);
  throw new RuntimeException('Published CTN blog part verification failed'.($created?'; rolled back':''));
}

echo 'CTN_COMMON_BLOGPART_RESULT='.($created?'CREATED_AND_PUBLISHED':'ALREADY_COMPLETE').PHP_EOL;
echo 'CTN_COMMON_BLOGPART_ID='.$id.PHP_EOL;
echo 'CTN_COMMON_BLOGPART_STATUS=publish'.PHP_EOL;
echo 'CTN_COMMON_BLOGPART_SHORTCODE=[blog_parts id="'.$id.'"]'.PHP_EOL;
echo 'CTN_COMMON_BLOGPART_SWELL_BUTTON=PASS'.PHP_EOL;
echo 'CTN_COMMON_BLOGPART_A8_PAIR=PASS'.PHP_EOL;
echo 'CTN_COMMON_BLOGPART_RENDER=PASS'.PHP_EOL;
