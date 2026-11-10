<?php
// Read-only verification of Lexus UX SWELL blog part.
if (!defined('ABSPATH')) exit(2);
echo "UX_PARTS_REGISTERED=".(post_type_exists('blog_parts') ? 'YES' : 'NO').PHP_EOL;
echo "UX_SHORTCODE_REGISTERED=".(shortcode_exists('blog_parts') ? 'YES' : 'NO').PHP_EOL;
$title='レクサスUX中古車相場チェック（一般中古車・CPO）';
$slug='lexus-ux-price-checker-tool';
$parts=get_posts(array('post_type'=>'blog_parts','post_status'=>array('publish','draft','pending','private','future','trash'),'posts_per_page'=>-1,'fields'=>'ids'));
$matches=array();
foreach($parts as $id) {
    $p=get_post((int)$id);
    if($p && ($p->post_name===$slug || $p->post_title===$title || strpos((string)$p->post_content,'ux-price-checker/?')!==false)) $matches[]=$p;
}
echo 'UX_PARTS_MATCH_COUNT='.count($matches).PHP_EOL;
foreach($matches as $p){
  echo 'UX_PART_ID='.(int)$p->ID.PHP_EOL;
  echo 'UX_PART_STATUS='.$p->post_status.PHP_EOL;
  echo 'UX_PART_SLUG='.$p->post_name.PHP_EOL;
  echo 'UX_PART_TITLE='.$p->post_title.PHP_EOL;
  echo 'UX_PART_HAS_AFFILIATE='.(strpos((string)$p->post_content,'px.a8.net')!==false?'YES':'NO').PHP_EOL;
  echo 'UX_PART_IFRAME_HEIGHT_620='.(strpos((string)$p->post_content,'height:620px')!==false?'YES':'NO').PHP_EOL;
}
if (!post_type_exists('blog_parts') || !shortcode_exists('blog_parts') || count($matches)!==1 ||
$matches[0]->post_name!==$slug || $matches[0]->post_status!=='draft' ||
strpos((string)$matches[0]->post_content,'px.a8.net')!==false ||
strpos((string)$matches[0]->post_content,'height:620px')===false) {
  throw new RuntimeException('UX_SWELL_DRAFT_READ_ONLY_VERIFICATION_FAILED');
}
echo 'UX_SWELL_DRAFT_READ_ONLY_VERIFICATION=PASS'.PHP_EOL;
