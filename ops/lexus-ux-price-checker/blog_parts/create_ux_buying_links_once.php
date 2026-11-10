<?php
/**
 * One-time guarded creation of the SWELL UX purchase links blog part.
 * New parts are drafts; existing parts and all articles are NEVER rewritten.
 * Designed to be idempotent, and to NOT throw on a human-edited existing part.
 */
if (!defined('ABSPATH')) { exit(10); }
if (!post_type_exists('blog_parts') || !shortcode_exists('blog_parts')) {
  throw new RuntimeException('SWELL blog_parts/shortcode unavailable');
}
$title='レクサスUX購入導線｜カーセンサーとガリバー';
$slug='lexus-ux-carsensor-gulliver';
$content=<<<'HTML'
<!-- wp:html -->
<div data-tsurikue-ux-buying-links="1" style="margin:14px 0 24px;max-width:560px;">
  <p style="font-size:14px;margin:0 0 24px;text-align:center;"><a href="https://www.carsensor.net/usedcar/bLE/s021/index.html" target="_blank" rel="noopener noreferrer" style="text-decoration:underline;text-underline-offset:3px;">カーセンサーでUXの中古相場を見る</a></p>
  <div style="border-top:1px solid #dbe3e8;padding-top:18px;">
    <p style="font-size:16px;line-height:1.6;font-weight:700;margin:0 0 9px;">本気で愛車を探すなら、まだネット上に出ていない非公開車両も確認しよう！</p>
    <p style="font-size:14px;line-height:1.6;margin:0 0 11px;">ガリバーなら一般公開前の車両も探せる！</p>
    <p style="font-size:11px;color:#687782;margin:0 0 5px;">PR｜ガリバー</p>
    <a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" rel="nofollow" style="display:block;padding:14px 12px;border-radius:9px;background:#28536a;color:#fff;text-decoration:none;text-align:center;font-size:15px;line-height:1.4;font-weight:700;">ガリバーで希望のUXを探す</a>
    <img border="0" width="1" height="1" src="https://www13.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY" alt="">
    <p style="font-size:11px;line-height:1.6;color:#687782;margin:7px 0 0;">※希望条件・連絡先の入力が必要です。</p>
  </div>
</div>
<!-- /wp:html -->
HTML;
$ids=get_posts(array(
  'post_type'=>'blog_parts',
  'post_status'=>array('publish','draft','pending','private','future','trash'),
  'posts_per_page'=>-1, 'fields'=>'ids',
));
$found=array();
foreach($ids as $id){
  $p=get_post((int)$id);
  if(!$p)continue;
  if($p->post_name===$slug || $p->post_title===$title ||
     strpos((string)$p->post_content, 'data-tsurikue-ux-buying-links')!==false){
    $found[]=$p;
  }
}
if(count($found)>1){
  echo 'UX_BUYING_BLOGPART_STATUS=SKIP_MULTIPLE_MATCHES'.PHP_EOL;
  return;
}
if(count($found)===1){
  $p=$found[0];
  echo 'UX_BUYING_BLOGPART_ID='.(int)$p->ID.PHP_EOL;
  echo 'UX_BUYING_BLOGPART_STATUS='.$p->post_status.PHP_EOL;
  if($p->post_name!==$slug || $p->post_title!==$title ||
     strpos((string)$p->post_content,'data-tsurikue-ux-buying-links')===false){
    echo 'UX_BUYING_BLOGPART_RESULT=SKIP_EXISTING_DRIFT'.PHP_EOL;
    return;
  }
  echo 'UX_BUYING_BLOGPART_RESULT=ALREADY_EXISTS'.PHP_EOL;
  echo 'UX_BUYING_BLOGPART_SHORTCODE=[blog_parts id="'.(int)$p->ID.'"]'.PHP_EOL;
  return;
}
$admins=get_users(array('role'=>'administrator','fields'=>'ID','number'=>1,'orderby'=>'ID','order'=>'ASC'));
if(!is_array($admins) || count($admins)!==1)throw new RuntimeException('Cannot resolve admin author');
$id=wp_insert_post(array('post_type'=>'blog_parts','post_status'=>'draft',
  'post_title'=>$title,'post_name'=>$slug,'post_content'=>$content,
  'post_author'=>(int)$admins[0],'comment_status'=>'closed','ping_status'=>'closed'),true);
if(is_wp_error($id))throw new RuntimeException('UX blog part draft insert failed: '.$id->get_error_code());
$p=get_post((int)$id);
$actual=(string)($p->post_content??'');
$required=array(
  'data-tsurikue-ux-buying-links',
  'https://www.carsensor.net/usedcar/bLE/s021/index.html',
  'https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY',
  'https://www13.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY',
  'PR｜ガリバー',
  '※希望条件・連絡先の入力が必要です。',
);
$valid=($p && $p->post_type==='blog_parts' && $p->post_status==='draft' &&
  $p->post_title===$title && $p->post_name===$slug);
foreach($required as $needle){if(strpos($actual,$needle)===false)$valid=false;}
if(substr_count($actual, 'https://px.a8.net/svt/ejp?a8mat=')!==1 ||
   substr_count($actual, 'www13.a8.net/0.gif?a8mat=')!==1)$valid=false;
if(!$valid){
  wp_delete_post((int)$id,true);
  throw new RuntimeException('Newly created UX blog part failed audit; rolled back');
}
echo 'UX_BUYING_BLOGPART_ID='.(int)$id.PHP_EOL;
echo 'UX_BUYING_BLOGPART_STATUS=draft'.PHP_EOL;
echo 'UX_BUYING_BLOGPART_RESULT=CREATED_DRAFT'.PHP_EOL;
echo 'UX_BUYING_BLOGPART_SHORTCODE=[blog_parts id="'.(int)$id.'"]'.PHP_EOL;
