<?php
/** Inspect this site's existing SWELL button block shapes; zero WordPress writes. */
if(!defined('ABSPATH'))exit(10);
$parts=[4505,4506,4507];
foreach($parts as $id){
  $p=get_post($id);
  echo 'UX_PROBE_PART_'.$id.'='.($p?$p->post_type.':'.$p->post_status:'MISSING').PHP_EOL;
}
$reg=WP_Block_Type_Registry::get_instance()->get_registered('loos/button');
echo 'UX_PROBE_PHP_BLOCK_REGISTERED='.($reg?'YES':'NO').PHP_EOL;
if($reg){echo 'UX_PROBE_REG_ATTR_KEYS='.implode(',',array_keys($reg->get_attributes())).PHP_EOL;}
$root=get_template_directory();
$scanned=0;$matches=0;
$iter=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS));
foreach($iter as $file){
 if(++$scanned>6000)break;
 if(!$file->isFile()||$file->getFilename()!=='block.json'||stripos($file->getPath(),'button')===false)continue;
 if($file->getSize()>50000)continue;
 $d=json_decode(file_get_contents($file->getPathname()),true);
 if(!is_array($d)||($d['name']??'')!=='loos/button')continue;
 echo 'UX_PROBE_THEME_BLOCK_FILE='.$file->getPathname().PHP_EOL;
 echo 'UX_PROBE_THEME_ATTR_KEYS='.implode(',',array_keys($d['attributes']??[])).PHP_EOL;
 foreach($d['attributes']??[] as $key=>$attr){
   echo 'UX_PROBE_ATTR '.$key.' type='.($attr['type']??'unknown').' default_type='.gettype($attr['default']??null).PHP_EOL;
 }
 $matches++;break;
}
echo 'UX_PROBE_THEME_BLOCK_MATCHES='.$matches.PHP_EOL;
global $wpdb;
$like='%<!-- wp:loos/button%';
$rows=$wpdb->get_results($wpdb->prepare(
 "SELECT ID, post_content FROM {$wpdb->posts} WHERE post_type IN ('post','page','blog_parts') AND post_status IN ('publish','draft') AND post_content LIKE %s ORDER BY ID DESC LIMIT 40",
 $like
));
echo 'UX_PROBE_CANDIDATES='.count($rows).PHP_EOL;
$sample=0;
$walk=function($nodes,$postId)use(&$walk,&$sample){
 foreach($nodes as $n){
   if(($n['blockName']??'')==='loos/button' && $sample<5){
     $sample++;
     echo 'UX_PROBE_BUTTON_SAMPLE='.$sample.' POST_ID='.$postId.PHP_EOL;
     $attrs=$n['attrs']??[];
     echo 'UX_PROBE_SAMPLE_ATTR_KEYS='.implode(',',array_keys($attrs)).PHP_EOL;
     foreach($attrs as $k=>$v){
       echo 'UX_PROBE_SAMPLE_ATTR '.$k.' type='.gettype($v).' length='.(is_string($v)?strlen($v):0).PHP_EOL;
     }
     $inner=$n['innerHTML']??'';
     preg_match_all('/<([a-z][a-z0-9-]*)\b/iu',$inner,$tagMatches);
     echo 'UX_PROBE_SAMPLE_TAGS='.implode(',',array_slice($tagMatches[1],0,18)).PHP_EOL;
     if(preg_match('/\bclass="([^"]+)"/u',$inner,$cm))
       echo 'UX_PROBE_SAMPLE_OUTER_CLASS='.$cm[1].PHP_EOL;
     echo 'UX_PROBE_SAMPLE_AD_URL_IN_ATTR='.((strpos(json_encode($attrs),'px.a8.net')!==false)?'YES':'NO').PHP_EOL;
   }
   $walk($n['innerBlocks']??[],$postId);
 }
};
foreach($rows as $row)$walk(parse_blocks($row->post_content),(int)$row->ID);
echo 'UX_PROBE_TOTAL_BUTTON_SAMPLES='.$sample.PHP_EOL;
