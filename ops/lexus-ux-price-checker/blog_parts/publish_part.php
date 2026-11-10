<?php
/** Publish only the pre-verified UX blog part after static production passed HTTPS checks. */
if (!defined('ABSPATH')) exit(10);
if (!post_type_exists('blog_parts') || !shortcode_exists('blog_parts')) throw new RuntimeException('SWELL missing');
$id=4505;
$p=get_post($id);
$title='レクサスUX中古車相場チェック（一般中古車・CPO）';
$slug='lexus-ux-price-checker-tool';
if (!$p || $p->post_type!=='blog_parts' || $p->post_title!==$title || $p->post_name!==$slug)
  throw new RuntimeException('UX blog part mismatch; refuse write');
if (!in_array($p->post_status,array('draft','publish'),true)) throw new RuntimeException('Unexpected blog part status');
$body=(string)$p->post_content;
if (substr_count($body,'<iframe')!==1 ||
 strpos($body,'src="https://tsurikue.com/ux-price-checker/?model=250h&amp;grade=all&amp;year=2021"')===false ||
 strpos($body,'height:620px')===false ||
 strpos($body,'px.a8.net')!==false || strpos($body,'www15.a8.net')!==false)
  throw new RuntimeException('UX blog part content changed; refuse publish');
$root=ABSPATH;
$json=$root.'ux-price-checker/data/reference_price_bands.json';
if (!is_file($json)) throw new RuntimeException('No production price JSON file');
$d=json_decode(file_get_contents($json),true);
if (!$d || ($d['publication_reviewed']??false)!==true ||
 ($d['research_preview_only']??true)!==false || ($d['limited_sample_release']??false)!==true)
  throw new RuntimeException('Production data not approved for limited sample display');
$before=array();
foreach(array(2948,3601) as $post_id){
  $article=get_post($post_id);
  if(!$article || $article->post_type!=='post') throw new RuntimeException('Unrecognized article');
  $before[$post_id]=hash('sha256',(string)$article->post_content);
}
$original_status=$p->post_status;
if ($original_status==='draft') {
  $updated=wp_update_post(array('ID'=>$id,'post_status'=>'publish'),true);
  if (is_wp_error($updated)) throw new RuntimeException('Blog part publishing error: '.$updated->get_error_code());
}
$after=get_post($id);
$rendered=do_shortcode('[blog_parts id="4505"]');
$valid=$after && $after->post_status==='publish' && $after->post_content===$body &&
 strpos((string)$rendered,'ux-price-checker/')!==false && strpos((string)$rendered,'<iframe')!==false;
foreach($before as $post_id=>$hash){
  $article=get_post($post_id);
  if (!$article || hash('sha256',(string)$article->post_content)!==$hash) $valid=false;
}
if (!$valid) {
  if ($original_status==='draft') wp_update_post(array('ID'=>$id,'post_status'=>'draft'));
  throw new RuntimeException('Blog part rendering or article integrity failed; draft rollback attempted');
}
echo 'UX_SWELL_PART_ID=4505'.PHP_EOL;
echo 'UX_SWELL_PART_STATUS=publish'.PHP_EOL;
echo 'UX_SWELL_PART_SHORTCODE=[blog_parts id="4505"]'.PHP_EOL;
echo 'UX_SWELL_SHORTCODE_RENDER=PASS'.PHP_EOL;
echo 'UX_WORDPRESS_ARTICLES_UNCHANGED=PASS'.PHP_EOL;
