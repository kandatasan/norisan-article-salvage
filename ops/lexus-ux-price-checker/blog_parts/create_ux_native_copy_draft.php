<?php
/** Create one new copyable Gutenberg block CTA draft; never modify 4505, 4506 or articles. */
if(!defined('ABSPATH'))exit(10);
if(!post_type_exists('blog_parts'))throw new RuntimeException('SWELL blog_parts unavailable');
$old=get_post(4506);$tool=get_post(4505);
if(!$old||$old->post_type!=='blog_parts'||$old->post_name!=='lexus-ux-carsensor-gulliver'||
$old->post_title!=='レクサスUX購入導線｜カーセンサーとガリバー'||!$tool||
$tool->post_type!=='blog_parts'||$tool->post_status!=='publish')
 throw new RuntimeException('Existing WordPress records changed; no write');
$title='レクサスUX購入導線｜ブロック版・コピペ用（試作）';
$slug='lexus-ux-buying-native-copy-demo';
$body=<<<'BLOCKS'
<!-- wp:group {"className":"tsurikue-ux-buying-native-demo","layout":{"type":"constrained"}} -->
<div class="wp-block-group tsurikue-ux-buying-native-demo">
<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>中古UX、気になる一台を探してみよう。</strong></p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><a href="https://www.carsensor.net/usedcar/bLE/s021/index.html" target="_blank" rel="noopener noreferrer">カーセンサーでUXの中古車を見る</a></p>
<!-- /wp:paragraph -->
<!-- wp:separator {"className":"is-style-wide"} -->
<hr class="wp-block-separator has-alpha-channel-opacity is-style-wide"/>
<!-- /wp:separator -->
<!-- wp:paragraph -->
<p><strong>希望のUXが見つからなかったら？</strong></p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>ガリバーでも、年式やグレードなどの希望条件を伝えて探してみよう。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {"fontSize":"small"} -->
<p class="has-small-font-size">PR｜ガリバー</p>
<!-- /wp:paragraph -->
<!-- wp:buttons -->
<div class="wp-block-buttons">
<!-- wp:button {"width":100} -->
<div class="wp-block-button has-custom-width wp-block-button__width-100"><a class="wp-block-button__link wp-element-button">ガリバーで希望のUXを探す</a></div>
<!-- /wp:button -->
</div>
<!-- /wp:buttons -->
<!-- wp:paragraph {"fontSize":"small"} -->
<p class="has-small-font-size">※希望条件・連絡先の入力が必要です。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {"fontSize":"small"} -->
<p class="has-small-font-size"><strong>【試作中】ガリバーの広告リンクは未設定です。公開記事に貼り付けないでください。</strong></p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
BLOCKS;
if(strpos($body,'wp:html')!==false||strpos($body,'px.a8.net')!==false||
strpos($body,'a8.net/0.gif')!==false||strpos($body,'https://www.carsensor.net/usedcar/bLE/s021/index.html')===false)
 throw new RuntimeException('Unsafe/missing ad or Carsensor URL in template');
$parsed=parse_blocks($body);
if(count($parsed)!==1||($parsed[0]['blockName']??'')!=='core/group')throw new RuntimeException('Invalid Gutenberg root');
$allowed=['core/group','core/paragraph','core/separator','core/buttons','core/button'];
$check=function($nodes)use(&$check,$allowed){foreach($nodes as $n){
 if(!in_array($n['blockName']??null,$allowed,true))throw new RuntimeException('Unexpected block');
 $check($n['innerBlocks']??[]);
}};$check($parsed);
$found=[];
foreach(get_posts(['post_type'=>'blog_parts','post_status'=>['publish','draft','pending','private','future','trash'],
 'posts_per_page'=>-1,'fields'=>'ids']) as $id){
 $p=get_post((int)$id);if($p&&($p->post_name===$slug||$p->post_title===$title))$found[]=$p;
}
if(count($found)>1)throw new RuntimeException('Duplicate draft names');
if(count($found)===1){
 $p=$found[0];
 if($p->post_name!==$slug||$p->post_title!==$title||$p->post_status!=='draft'||$p->post_content!==$body)
  throw new RuntimeException('Previously edited prototype; no overwrite');
 echo 'UX_NATIVE_ID='.$p->ID.PHP_EOL.'UX_NATIVE_STATUS=draft'.PHP_EOL.'UX_NATIVE_RESULT=EXISTS'.PHP_EOL;return;
}
$a=get_users(['role'=>'administrator','fields'=>'ID','number'=>1,'orderby'=>'ID','order'=>'ASC']);
if(!is_array($a)||count($a)!==1)throw new RuntimeException('Admin author missing');
$id=wp_insert_post(['post_type'=>'blog_parts','post_status'=>'draft','post_title'=>$title,'post_name'=>$slug,
 'post_content'=>$body,'post_author'=>(int)$a[0],'comment_status'=>'closed','ping_status'=>'closed'],true);
if(is_wp_error($id))throw new RuntimeException('Draft creation failed');
$p=get_post($id);
if(!$p||$p->post_status!=='draft'||$p->post_name!==$slug||$p->post_title!==$title||
 $p->post_type!=='blog_parts'||$p->post_content!==$body){
 wp_delete_post($id,true);throw new RuntimeException('New draft integrity failure; own draft rolled back');
}
echo 'UX_NATIVE_ID='.$id.PHP_EOL.'UX_NATIVE_STATUS=draft'.PHP_EOL.'UX_NATIVE_RESULT=CREATED'.PHP_EOL;
echo 'UX_NATIVE_CORE_BLOCKS=PASS'.PHP_EOL.'UX_NATIVE_GULLIVER_LINK=UNSET'.PHP_EOL;
echo 'UX_EXISTING_4505_4506=UNCHANGED'.PHP_EOL;
