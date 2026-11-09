<?php
/**
 * Read-only WordPress target inventory for Lexus UX iframe placement.
 * Never creates, deletes, updates or exposes full post content.
 */
if (!defined('ABSPATH')) { exit(1); }
$slugs = array('lexus-ux-used', 'lexus-ux250h-used-vs-ux300h', 'ux-koukai');
foreach ($slugs as $slug) {
  $p = get_page_by_path($slug, OBJECT, 'post');
  if (!$p || $p->post_name !== $slug) {
    echo 'UX_TARGET_AUDIT '.wp_json_encode(array('slug'=>$slug,'error'=>'NOT_FOUND'),JSON_UNESCAPED_UNICODE).PHP_EOL;
    continue;
  }
  $body = (string)$p->post_content;
  preg_match_all('/<h2[^>]*>(.*?)<\/h2>/is', $body, $matches);
  $headings = array();
  foreach ($matches[1] as $raw) {
    $heading=trim(wp_strip_all_tags($raw));
    if ($heading!=='') $headings[]=mb_substr($heading,0,90);
  }
  $counts=array(
     'existing_ux_iframe'=>substr_count($body,'ux-price-checker/'),
     'gulliver_a8'=>substr_count($body,'4B65SD+8DUSHE+9QU+NVHCY'),
     'ctn'=>substr_count($body,'CTN'),
     'custom_html_blocks'=>substr_count($body,'<!-- wp:html'),
  );
  echo 'UX_TARGET_AUDIT '.wp_json_encode(array(
     'id'=>(int)$p->ID, 'slug'=>$p->post_name,
     'status'=>$p->post_status, 'type'=>$p->post_type, 'title'=>get_the_title($p),
     'sha256'=>hash('sha256',$body),
     'counts'=>$counts, 'headings'=>$headings
  ),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES).PHP_EOL;
}
