<?php
/**
 * Finalize UX buying CTA Gutenberg draft #4507 using the strong copy already approved
 * in #4506. Keep every A8 hyperlink/attribute/1x1 tracking image unchanged.
 * Only draft #4507 may be edited. The production checker (#4505), the old CTA
 * (#4506), and published posts stay untouched.
 */
if (!defined('ABSPATH')) exit(10);
$part=get_post(4507);
$old=get_post(4506);
$tool=get_post(4505);
$slug='lexus-ux-buying-native-copy-demo';
$oldTitle='レクサスUX購入導線｜ブロック版・コピペ用（試作）';
$finalTitle='レクサスUX購入導線｜ブロック版・コピペ用（完成）';
if (!$part || $part->post_type!=='blog_parts' || $part->post_name!==$slug ||
    $part->post_status!=='draft' ||
    !in_array($part->post_title,[$oldTitle,$finalTitle],true) ||
    !$old || $old->post_type!=='blog_parts' ||
    $old->post_name!=='lexus-ux-carsensor-gulliver' ||
    $old->post_title!=='レクサスUX購入導線｜カーセンサーとガリバー' ||
    !$tool || $tool->post_type!=='blog_parts' || $tool->post_status!=='publish') {
    throw new RuntimeException('CTA draft or protected source identity drift: no write');
}
$oldSource=(string)$old->post_content;
$oldSourceHash=hash('sha256',$oldSource);
$toolHash=hash('sha256',(string)$tool->post_content);
$href='https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY';
$pixel='https://www13.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY';
$carsensor='https://www.carsensor.net/usedcar/bLE/s021/index.html';
if (substr_count($oldSource,$href)!==1 ||
    substr_count($oldSource,$pixel)!==1 ||
    substr_count($oldSource,$carsensor)!==1 ||
    strpos($oldSource,'本気で愛車を探すなら、まだネット上に出ていない非公開車両も確認しよう！')===false ||
    strpos($oldSource,'ガリバーなら一般公開前の車両も探せる！')===false) {
    throw new RuntimeException('Original #4506 copy or full A8 code differs');
}
// Copy the exact A8 link and image from the original rather than reconstructing them.
$rx='~(<a\b[^>]*href="'.preg_quote($href,'~').'"[^>]*>ガリバーで希望のUXを探す</a>\s*<img\b[^>]*src="'.preg_quote($pixel,'~').'"[^>]*>)~u';
if(!preg_match($rx,$oldSource,$matches) ||
   strpos($matches[1],'rel="nofollow"')===false) {
    throw new RuntimeException('Full original A8 hyperlink and companion pixel missing');
}
$adPair=$matches[1];
$block=<<<'BLOCKS'
<!-- wp:group {"className":"tsurikue-ux-buying-native-demo","layout":{"type":"constrained"}} -->
<div class="wp-block-group tsurikue-ux-buying-native-demo">
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
<!-- wp:paragraph -->
<p>__ORIGINAL_A8_AD_PAIR__</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {"fontSize":"small"} -->
<p class="has-small-font-size">※希望条件・連絡先の入力が必要です。</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
BLOCKS;
$new=str_replace('__ORIGINAL_A8_AD_PAIR__',$adPair,$block);
if (substr_count($new,$href)!==1 || substr_count($new,$pixel)!==1 ||
    substr_count($new,$carsensor)!==1 ||
    strpos($new,'wp:html')!==false ||
    strpos($new,'試作中')!==false ||
    strpos($new,'希望のUXが見つからなかったら？')!==false) {
    throw new RuntimeException('Final Gutenberg blocks failed source audit');
}
$blocks=parse_blocks($new);
if (!is_array($blocks) || count($blocks)!==1 || $blocks[0]['blockName']!=='core/group')
    throw new RuntimeException('Expected exactly one native Gutenberg group');
$allowed=['core/group','core/paragraph','core/separator'];
$check=function($nodes)use(&$check,$allowed) {
    foreach($nodes as $node){
        if(!in_array($node['blockName']??null,$allowed,true))throw new RuntimeException('Unexpected block type');
        $check($node['innerBlocks']??[]);
    }
};
$check($blocks);
if (count($blocks[0]['innerBlocks'])!==7)throw new RuntimeException('Final group child count differs');
$current=(string)$part->post_content;
if ($current===$new && $part->post_title===$finalTitle) {
    echo 'UX_4507_FINAL_RESULT=ALREADY_COMPLETE'.PHP_EOL;
} else {
    $expected=['中古UX、気になる一台を探してみよう。',
        '希望のUXが見つからなかったら？',
        'ガリバーでも、年式やグレードなどの希望条件を伝えて探してみよう。',
        'PR｜ガリバー','※希望条件・連絡先の入力が必要です。'];
    if ($part->post_title!==$oldTitle ||
        strpos($current,'wp:html')!==false ||
        substr_count($current,$href)!==1 ||
        substr_count($current,$pixel)!==1 ||
        strpos($current,$adPair)===false ||
        strpos($current,'ガリバーで希望のUXを探す')===false) {
        throw new RuntimeException('Existing #4507 has manual changes; not overwritten');
    }
    foreach($expected as $needle)if(strpos($current,$needle)===false)
        throw new RuntimeException('Expected previous prototype copy missing; not overwritten');
    $result=wp_update_post(['ID'=>4507,'post_title'=>$finalTitle,'post_name'=>$slug,
        'post_status'=>'draft','post_content'=>$new],true);
    if(is_wp_error($result))throw new RuntimeException('4507 draft update failed: '.$result->get_error_code());
    echo 'UX_4507_FINAL_RESULT=UPDATED'.PHP_EOL;
}
$after=get_post(4507);
if (!$after || $after->post_type!=='blog_parts' || $after->post_name!==$slug ||
    $after->post_status!=='draft' || $after->post_title!==$finalTitle ||
    (string)$after->post_content!==$new) {
    throw new RuntimeException('Updated draft identity or bytes mismatched');
}
$render=do_blocks((string)$after->post_content);
if(substr_count($render,$href)!==1 ||
   substr_count($render,$pixel)!==1 ||
   substr_count($render,$carsensor)!==1 ||
   strpos($render,'本気で愛車を探すなら、まだネット上に出ていない非公開車両も確認しよう！')===false ||
   strpos($render,'ガリバーなら一般公開前の車両も探せる！')===false) {
    throw new RuntimeException('WordPress block rendering removed a link, pixel or strong copy');
}
$oldAfter=get_post(4506);$toolAfter=get_post(4505);
if(!$oldAfter || !$toolAfter ||
   hash('sha256',(string)$oldAfter->post_content)!==$oldSourceHash ||
   hash('sha256',(string)$toolAfter->post_content)!==$toolHash)
    throw new RuntimeException('Protected existing parts were changed unexpectedly');
echo 'UX_4507_FINAL_ID=4507'.PHP_EOL;
echo 'UX_4507_FINAL_STATUS=draft'.PHP_EOL;
echo 'UX_4507_FINAL_COPY=STRONG_4506_COPY'.PHP_EOL;
echo 'UX_4507_FINAL_CARSENSOR_LINK=PASS'.PHP_EOL;
echo 'UX_4507_FINAL_A8_ANCHOR_PIXEL=PASS'.PHP_EOL;
echo 'UX_4507_FINAL_NATIVE_BLOCKS=PASS'.PHP_EOL;
echo 'UX_4507_FINAL_RENDERED_LINKS=PASS'.PHP_EOL;
echo 'UX_4507_FINAL_4505_4506_UNCHANGED=PASS'.PHP_EOL;
