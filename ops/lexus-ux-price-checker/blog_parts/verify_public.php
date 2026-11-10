<?php
/** Read-only final UX price blog part verification. */
if (!defined('ABSPATH')) exit(10);
if (!post_type_exists('blog_parts') || !shortcode_exists('blog_parts')) throw new RuntimeException('SWELL part type missing');
$p=get_post(4505);
if(!$p || $p->post_type!=='blog_parts' || $p->post_name!=='lexus-ux-price-checker-tool' ||
 $p->post_title!=='レクサスUX中古車相場チェック（一般中古車・CPO）')
 throw new RuntimeException('Part identity mismatch');
echo 'UX_LIVE_PART_ID='.(int)$p->ID.PHP_EOL;
echo 'UX_LIVE_PART_STATUS='.$p->post_status.PHP_EOL;
echo 'UX_LIVE_PART_SLUG='.$p->post_name.PHP_EOL;
if($p->post_status!=='publish') throw new RuntimeException('Part not published');
if(strpos((string)$p->post_content,'px.a8.net')!==false) throw new RuntimeException('Unexpected affiliate');
$html=do_shortcode('[blog_parts id="4505"]');
if(strpos((string)$html,'<iframe')===false || strpos((string)$html,'https://tsurikue.com/ux-price-checker/')===false)
 throw new RuntimeException('Shortcode does not render UX iframe');
$json=ABSPATH.'ux-price-checker/data/reference_price_bands.json';
if(!is_file($json))throw new RuntimeException('Production JSON missing');
$j=json_decode(file_get_contents($json),true);
if(!$j || ($j['publication_reviewed']??false)!==true || ($j['limited_sample_release']??false)!==true
  || count($j['cohorts']??[])<20) throw new RuntimeException('Production JSON invalid');
echo 'UX_LIVE_RENDERED_IFRAME=PASS'.PHP_EOL;
echo 'UX_LIVE_DATA_COHORTS='.count($j['cohorts']).PHP_EOL;
echo 'UX_LIVE_AFFILIATE_IN_TOOL=NO'.PHP_EOL;
echo 'UX_LIVE_PART_SHORTCODE=[blog_parts id="4505"]'.PHP_EOL;
foreach(array(2948=>'lexus-ux-used',3601=>'lexus-ux250h-used-vs-ux300h') as $id=>$slug) {
  $post=get_post($id);
  if(!$post || $post->post_type!=='post' || $post->post_name!==$slug)throw new RuntimeException('Article identity mismatch');
  echo 'UX_UNCHANGED_ARTICLE '.(int)$id.' status='.$post->post_status.' iframe_count='.substr_count((string)$post->post_content,'ux-price-checker/').PHP_EOL;
}
echo 'UX_LIVE_READ_ONLY_VERIFICATION=PASS'.PHP_EOL;
