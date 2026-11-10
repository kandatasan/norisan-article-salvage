<?php
/** Read-only audit of the SWELL UX purchase-CTA draft. */
if (!defined('ABSPATH')) exit(10);
if (!post_type_exists('blog_parts') || !shortcode_exists('blog_parts')) throw new RuntimeException('SWELL unavailable');
$part=get_post(4506);
if (!$part || $part->post_type!=='blog_parts' || $part->post_name!=='lexus-ux-carsensor-gulliver'
 || $part->post_title!=='レクサスUX購入導線｜カーセンサーとガリバー') throw new RuntimeException('UX buying blog part identity mismatch');
$text=(string)$part->post_content;
$need=array(
 'data-tsurikue-ux-buying-links',
 'カーセンサーでUXの中古相場を見る',
 'https://www.carsensor.net/usedcar/bLE/s021/index.html',
 '本気で愛車を探すなら、まだネット上に出ていない非公開車両も確認しよう！',
 'ガリバーなら一般公開前の車両も探せる！',
 'PR｜ガリバー',
 'ガリバーで希望のUXを探す',
 'https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY',
 'https://www13.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY',
 '※希望条件・連絡先の入力が必要です。',
);
foreach($need as $word)if(strpos($text,$word)===false)throw new RuntimeException('Required UX buying link content missing: '.substr(hash('sha256',$word),0,12));
if(strpos($text,'www15.a8.net')!==false)throw new RuntimeException('Old A8 tracking image host detected');
if(substr_count($text,'https://px.a8.net/svt/ejp?a8mat=')!==1)throw new RuntimeException('Incorrect A8 link count');
if(substr_count($text,'www13.a8.net/0.gif?a8mat=')!==1)throw new RuntimeException('Incorrect A8 pixel count');
if(substr_count($text,'https://www.carsensor.net/usedcar/bLE/s021/index.html')!==1)throw new RuntimeException('Incorrect non-affiliate Carsensor link count');
if($part->post_status!=='draft')throw new RuntimeException('New part status drift; expected draft');
$tool=get_post(4505);
if(!$tool || $tool->post_type!=='blog_parts' || $tool->post_status!=='publish' ||
   strpos((string)$tool->post_content,'ux-price-checker/')===false ||
   strpos((string)$tool->post_content,'px.a8.net')!==false)
  throw new RuntimeException('Existing checker 4505 was altered unexpectedly');
echo 'UX_BUYING_PART_ID=4506'.PHP_EOL;
echo 'UX_BUYING_PART_SLUG='.$part->post_name.PHP_EOL;
echo 'UX_BUYING_PART_STATUS='.$part->post_status.PHP_EOL;
echo 'UX_BUYING_A8_LINK_COUNT=1'.PHP_EOL;
echo 'UX_BUYING_A8_IMAGE_HOST=www13.a8.net'.PHP_EOL;
echo 'UX_BUYING_CARSENSOR_DIRECT_LINK=PASS'.PHP_EOL;
echo 'UX_CHECKER_PART_4505_UNCHANGED=PASS'.PHP_EOL;
echo 'UX_BUYING_READONLY_AUDIT=PASS'.PHP_EOL;
