<?php
/**
 * One-time guarded edit of the new SWELL native Gutenberg draft 4507 only.
 * Reuses the complete affiliate anchor + 1px tracking image already stored in 4506.
 * Changes ONLY advertising text when needed; never alters A8 href/pixel/attributes.
 * Never edits 4505/4506 or published articles.
 */
if(!defined('ABSPATH'))exit(10);
$src=get_post(4506);
$tool=get_post(4505);
$draft=get_post(4507);
if(!$src||$src->post_type!=='blog_parts'||$src->post_name!=='lexus-ux-carsensor-gulliver'||
 $src->post_title!=='レクサスUX購入導線｜カーセンサーとガリバー'||
 !$tool||$tool->post_type!=='blog_parts'||$tool->post_status!=='publish'||
 !$draft||$draft->post_type!=='blog_parts'||$draft->post_name!=='lexus-ux-buying-native-copy-demo'||
 $draft->post_title!=='レクサスUX購入導線｜ブロック版・コピペ用（試作）'||
 $draft->post_status!=='draft')
 throw new RuntimeException('Expected original parts or private draft identity changed; no write');
$source=(string)$src->post_content;
$body=(string)$draft->post_content;
$affiliate='https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY';
$pixel='https://www13.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY';
if(substr_count($source,$affiliate)!==1||substr_count($source,$pixel)!==1)
 throw new RuntimeException('Original A8 code identity/quantity changed');
$pattern='~(<a\b[^>]*href="'.preg_quote($affiliate,'~').'"[^>]*>)([^<]*)(</a>)(\s*)(<img\b[^>]*src="'.preg_quote($pixel,'~').'"[^>]*>)~iu';
if(!preg_match($pattern,$source,$m))throw new RuntimeException('Cannot find unbroken A8 anchor and pixel in original 4506');
if(strpos($m[1],'rel="nofollow"')===false)throw new RuntimeException('Original A8 nofollow missing');
$advertisingLink=$m[1].'ガリバーで希望のUXを探す'.$m[3].$m[4].$m[5];
$old=<<<'OLD'
<!-- wp:buttons -->
<div class="wp-block-buttons">
<!-- wp:button {"width":100} -->
<div class="wp-block-button has-custom-width wp-block-button__width-100"><a class="wp-block-button__link wp-element-button">ガリバーで希望のUXを探す</a></div>
<!-- /wp:button -->
</div>
<!-- /wp:buttons -->
OLD;
$disclaimer=<<<'DISCLAIMER'
<!-- wp:paragraph {"fontSize":"small"} -->
<p class="has-small-font-size"><strong>【試作中】ガリバーの広告リンクは未設定です。公開記事に貼り付けないでください。</strong></p>
<!-- /wp:paragraph -->
DISCLAIMER;
$replacement='<!-- wp:paragraph {"align":"center"} -->'."\n".
 '<p class="has-text-align-center">'.$advertisingLink.'</p>'."\n".
 '<!-- /wp:paragraph -->';
$already=(substr_count($body,$affiliate)===1 && substr_count($body,$pixel)===1 &&
 strpos($body,$disclaimer)===false && strpos($body,'<!-- wp:html ')===false);
if($already){
  if(strpos($body,$advertisingLink)===false)throw new RuntimeException('Previously edited affiliate snippet differs; stop');
  echo 'UX_NATIVE_A8_ID=4507'.PHP_EOL.'UX_NATIVE_A8_STATUS=draft'.PHP_EOL.'UX_NATIVE_A8_RESULT=ALREADY_LINKED'.PHP_EOL;return;
}
if(substr_count($body,$old)!==1||substr_count($body,$disclaimer)!==1||
 strpos($body,$affiliate)!==false||strpos($body,$pixel)!==false||
 strpos($body,'<!-- wp:html ')!==false)
 throw new RuntimeException('Draft was modified since prototype; do not overwrite changes');
$new=str_replace($old,$replacement,$body);
$new=str_replace($disclaimer,'',$new);
if(substr_count($new,$affiliate)!==1||substr_count($new,$pixel)!==1||
 strpos($new,$old)!==false||strpos($new,$disclaimer)!==false)
 throw new RuntimeException('Unexpected new draft advertising source');
$tree=parse_blocks($new);
$types=['core/group','core/paragraph','core/separator'];
$validate=function($nodes)use(&$validate,$types){foreach($nodes as $n){
  if(!in_array($n['blockName']??null,$types,true))throw new RuntimeException('Non-native or invalid Gutenberg block found');
  $validate($n['innerBlocks']??[]);
}};$validate($tree);
$updated=wp_update_post(['ID'=>4507,'post_content'=>$new],true);
if(is_wp_error($updated))throw new RuntimeException('Draft update failed: '.$updated->get_error_code());
$p=get_post(4507);
if(!$p||$p->post_status!=='draft'||$p->post_content!==$new||
 substr_count($p->post_content,$affiliate)!==1||
 substr_count($p->post_content,$pixel)!==1){
 // Restore original draft only if the update is not as expected.
 wp_update_post(['ID'=>4507,'post_content'=>$body]);
 throw new RuntimeException('New draft verification failed; restored original draft');
}
echo 'UX_NATIVE_A8_ID=4507'.PHP_EOL.'UX_NATIVE_A8_STATUS=draft'.PHP_EOL.'UX_NATIVE_A8_RESULT=UPDATED'.PHP_EOL;
echo 'UX_NATIVE_A8_INTACT_ANCHOR_PIXEL=PASS'.PHP_EOL;
echo 'UX_NATIVE_A8_CORE_BLOCKS_ONLY=PASS'.PHP_EOL;
echo 'UX_NATIVE_A8_ORIGINAL_4505_4506=UNCHANGED'.PHP_EOL;
