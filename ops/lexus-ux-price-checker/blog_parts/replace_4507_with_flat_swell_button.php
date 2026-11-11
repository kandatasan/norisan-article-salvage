<?php
/**
 * Replace ONLY the expressly authorized draft 4507 with flat Gutenberg blocks and
 * the site's actual native loos/button SWELL A8 tag shape. No group, no custom HTML,
 * no shortcodes. Protect 4505 / 4506 / published posts.
 */
if(!defined('ABSPATH'))exit(10);
$part=get_post(4507);$orig=get_post(4506);$tool=get_post(4505);
if(!$part||$part->post_type!=='blog_parts'||$part->post_name!=='lexus-ux-buying-native-copy-demo'||$part->post_status!=='draft'||
   !$orig||$orig->post_type!=='blog_parts'||$orig->post_name!=='lexus-ux-carsensor-gulliver'||
   $orig->post_title!=='レクサスUX購入導線｜カーセンサーとガリバー'||
   !$tool||$tool->post_type!=='blog_parts'||$tool->post_status!=='publish')
  throw new RuntimeException('Protected content identity or draft status drift; abort');
if(!WP_Block_Type_Registry::get_instance()->is_registered('loos/button'))
  throw new RuntimeException('Native SWELL button block is not registered');
$oldHash=hash('sha256',(string)$orig->post_content);
$toolHash=hash('sha256',(string)$tool->post_content);
$source=(string)$orig->post_content;
$href='https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY';
$pixel='https://www13.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY';
$carsensor='https://www.carsensor.net/usedcar/bLE/s021/index.html';
if(substr_count($source,$href)!==1||substr_count($source,$pixel)!==1||
   strpos($source,'本気で愛車を探すなら、まだネット上に出ていない非公開車両も確認しよう！')===false)
  throw new RuntimeException('Source 4506 is not the expected affiliate template');
// Only the publisher-added inline style is stripped; A8 href, rel and full 1px image remain.
$re='~(<a\b[^>]*href="'.preg_quote($href,'~').'"[^>]*>)([^<]*)(</a>)(\s*)(<img\b[^>]*src="'.preg_quote($pixel,'~').'"[^>]*>)~iu';
if(!preg_match($re,$source,$match))throw new RuntimeException('Exact A8 anchor/pixel pair is missing');
$open=preg_replace('~\s+style="[^"]*"~iu','',$match[1]);
if(strpos($open,'rel="nofollow"')===false||strpos($open,$href)===false)
  throw new RuntimeException('A8 anchor URL or nofollow missing');
$pair=$open.'ガリバーで希望のUXを探す'.$match[3].$match[4].$match[5];
$template=<<<'BLOCKS'
<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><a href="https://www.carsensor.net/usedcar/bLE/s021/index.html" target="_blank" rel="noopener noreferrer">カーセンサーでUXの中古相場を見る</a></p>
<!-- /wp:paragraph -->

<!-- wp:separator {"className":"is-style-wide"} -->
<hr class="wp-block-separator has-alpha-channel-opacity is-style-wide"/>
<!-- /wp:separator -->

<!-- wp:paragraph -->
<p><strong>本気で愛車を探すなら、まだネット上に出ていない非公開車両も確認しよう！</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ガリバーなら一般公開前の車両も探せる！</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"fontSize":"small"} -->
<p class="has-small-font-size">PR｜ガリバー</p>
<!-- /wp:paragraph -->

<!-- wp:loos/button {"color":"blue","className":"is-style-btn_solid"} -->
<div class="swell-block-button -html blue_ is-style-btn_solid">__EXACT_A8_PAIR__</div>
<!-- /wp:loos/button -->

<!-- wp:paragraph {"fontSize":"small"} -->
<p class="has-small-font-size">※希望条件・連絡先の入力が必要です。</p>
<!-- /wp:paragraph -->
BLOCKS;
$new=str_replace('__EXACT_A8_PAIR__',$pair,$template);
$want=['core/paragraph','core/separator','core/paragraph','core/paragraph','core/paragraph','loos/button','core/paragraph'];
$rawBlocks=parse_blocks($new);
$blocks=array_values(array_filter($rawBlocks,function($block){
  // WordPress parse_blocks returns harmless null blocks for separators/newlines
  // between top-level blocks; do not mistake whitespace for an actual block.
  return ($block['blockName']??null)!==null || trim((string)($block['innerHTML']??''))!=='';
}));
if(count($blocks)!==count($want))throw new RuntimeException('Incorrect number of nonempty direct Gutenberg blocks');
foreach($blocks as $i=>$b){
  if(($b['blockName']??null)!==$want[$i]||!empty($b['innerBlocks']))throw new RuntimeException('Unexpected nesting or block type');
}
$button=$blocks[5];
if(($button['attrs']['color']??'')!=='blue'||($button['attrs']['className']??'')!=='is-style-btn_solid'||
 strpos($button['innerHTML'],'swell-block-button -html blue_ is-style-btn_solid')===false)
  throw new RuntimeException('SWELL button saved markup mismatch');
if(substr_count($new,$href)!==1||substr_count($new,$pixel)!==1||
   substr_count($new,$carsensor)!==1||
   strpos($new,'wp:group')!==false||strpos($new,'wp:html')!==false||
   strpos($new,'wp:shortcode')!==false||
   strpos($new,'希望のUXが見つからなかったら？')!==false)
  throw new RuntimeException('Flat layout or affiliate integrity check failed');
$finalTitle='レクサスUX購入導線｜通常ブロック＋SWELLボタン（コピペ用）';
$current=(string)$part->post_content;
$previousTitle=(string)$part->post_title;
if($current===$new && $previousTitle===$finalTitle){
  echo 'UX_4507_FLAT_RESULT=ALREADY_COMPLETE'.PHP_EOL;
}else{
  // User explicitly approved overwriting their partially edited 4507 draft.
  // Keep a private one-time backup of their current content on the SAME draft.
  if(!metadata_exists('post',4507,'_ux_4507_backup_before_flat_swell_20261111'))
    add_post_meta(4507,'_ux_4507_backup_before_flat_swell_20261111',$current,true);
  $u=wp_update_post(['ID'=>4507,'post_title'=>$finalTitle,'post_content'=>$new,'post_status'=>'draft'],true);
  if(is_wp_error($u))throw new RuntimeException('4507 update failed: '.$u->get_error_code());
  echo 'UX_4507_FLAT_RESULT=UPDATED'.PHP_EOL;
}
$after=get_post(4507);
$render=do_blocks((string)($after->post_content??''));
$success=$after&&$after->post_status==='draft'&&$after->post_title===$finalTitle&&
 $after->post_name==='lexus-ux-buying-native-copy-demo'&&$after->post_content===$new&&
 substr_count($render,$href)===1&&substr_count($render,$pixel)===1&&
 substr_count($render,$carsensor)===1&&
 strpos($render,'swell-block-button -html blue_ is-style-btn_solid')!==false&&
 strpos($render,'本気で愛車を探すなら、まだネット上に出ていない非公開車両も確認しよう！')!==false&&
 strpos($render,'ガリバーなら一般公開前の車両も探せる！')!==false;
if(!$success){
  if($current!==$new||$previousTitle!==$finalTitle)
    wp_update_post(['ID'=>4507,'post_title'=>$previousTitle,'post_content'=>$current,'post_status'=>'draft']);
  throw new RuntimeException('SWELL button draft render failed: previous 4507 restored');
}
if(hash('sha256',(string)get_post(4506)->post_content)!==$oldHash||
   hash('sha256',(string)get_post(4505)->post_content)!==$toolHash)
  throw new RuntimeException('A protected source part changed unexpectedly');
echo 'UX_4507_FLAT_ID=4507'.PHP_EOL;
echo 'UX_4507_FLAT_STATUS=draft'.PHP_EOL;
echo 'UX_4507_FLAT_CORE_GROUP=NONE'.PHP_EOL;
echo 'UX_4507_FLAT_SWELL_BUTTON=PASS'.PHP_EOL;
echo 'UX_4507_FLAT_A8_FULL_PAIR=PASS'.PHP_EOL;
echo 'UX_4507_FLAT_RENDERED_LINKS=PASS'.PHP_EOL;
echo 'UX_4507_FLAT_SOURCE_PARTS_UNCHANGED=PASS'.PHP_EOL;
