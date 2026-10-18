<?php
/** Only on disposable WP+MySQL GitHub runner via WP-CLI eval-file. */
if (!defined('ABSPATH') || !defined('WP_CLI') || !WP_CLI) {
    throw new RuntimeException('This test may run only in ephemeral WP CLI.');
}
function tsb_assert($condition,$message) {
    if (!$condition) { throw new RuntimeException('TBS WP integration failure: '.$message); }
}
function tsb_request($route,$options=array()) {
    $request=new WP_REST_Request('GET','/tsurikue-biota/v1/'.$route);
    foreach ($options as $key=>$value) {$request->set_param($key,$value);}
    return rest_do_request($request);
}
tsb_assert(class_exists('Tsurikue_Biota_Search'),'Biota plugin missing');
tsb_assert(class_exists('TBS_Data'),'Data class missing');
tsb_assert(class_exists('TBS_REST'),'Search class missing');
tsb_assert(!TBS_REST::ready(),'Activation cannot automatically expose data');

$not_ready=tsb_request('catalog');
tsb_assert($not_ready->get_status()===503,'Unimported catalog must reject');
$pre_posts=(int)wp_count_posts('post')->publish;
$begin=new ReflectionMethod('TBS_Data','begin');
$step=new ReflectionMethod('TBS_Data','step');
$rollback=new ReflectionMethod('TBS_Data','rollback');
$state=$begin->invoke(null);
tsb_assert($state['importing']===true&&!$state['ready'],'Manual staging not started correctly');
$steps=0;
while ($state['importing']) {
    $state=$step->invoke(null);$steps++;
    if ($steps>850) {throw new RuntimeException('Biota staged import batch loop exceeded 850');}
}
tsb_assert($state['ready']===true,'Final counts did not activate');
tsb_assert($state['generation']===1,'First verified generation must be one');
global $wpdb;
$table=Tsurikue_Biota_Search::table();
$actual=$wpdb->get_results($wpdb->prepare(
    "SELECT group_id, COUNT(*) AS record_count FROM {$table} WHERE generation=%d GROUP BY group_id",1),ARRAY_A);
$counts=array();
foreach($actual as $row){$counts[$row['group_id']]=(int)$row['record_count'];}
tsb_assert($counts['fish']===18814,'Fish historical record count changed');
tsb_assert($counts['benthic_animals']===74949,'Benthic historical record count changed');
tsb_assert($counts['birds']===44093,'Bird historical record count changed');
tsb_assert($counts['plants']===270180,'Plant historical record count changed');
tsb_assert((int)wp_count_posts('post')->publish===$pre_posts,'Posts were altered');

$cat=tsb_request('catalog');
tsb_assert($cat->get_status()===200,'Catalog REST failed');
$catalog=$cat->get_data();
tsb_assert(count($catalog['groups'])===4,'Unexpected biological classifications');
tsb_assert($catalog['data_rows']===408036,'Catalog total did not match manifest');
tsb_assert(isset($catalog['unavailable_groups']['aquatic_insects']),
    'Aquatic insects must remain separate and unavailable without taxonomy audit');

$waters=tsb_request('search',array(
    'direction'=>'region_explore','group'=>array('fish','benthic_animals','birds','plants'),
    'region'=>'chugoku','page'=>1,'per_page'=>20
));
tsb_assert($waters->get_status()===200,'Regional watershed summaries API failed');
$watersData=$waters->get_data();
tsb_assert($watersData['total']===13,'Chinese regional watershed count changed');
$ota=null;
foreach ($watersData['results'] as $row) {
    if ($row['watershed_name']==='太田川') {$ota=$row;break;}
}
tsb_assert(is_array($ota),'Ota watershed summary absent');
tsb_assert(isset($ota['group_label_counts']['plants']),
    'Plant source group did not appear in dynamic category count');

$plants=tsb_request('search',array(
    'direction'=>'watershed_to_organism','group'=>array('plants'),
    'region'=>'chugoku','watershed'=>'太田川','watershed_match'=>'exact'
));
tsb_assert($plants->get_status()===200,'Plant search API failed');
$plantData=$plants->get_data();
tsb_assert($plantData['total']===1212,'Ota watershed real plant literal labels count changed');
tsb_assert(!isset($plantData['results'][0]['prefecture']),
    'A survey observation must not be attributed to a prefecture');
tsb_assert($plantData['results'][0]['verified_individual_river']===null,
    'No individual river attribution permitted');
tsb_assert($plantData['results'][0]['approved_taxon_code']===null,
    'Literal source names cannot auto-assign taxon codes');
tsb_assert(isset($plantData['results'][0]['survey_years']),
    'Historical survey years not aggregated');

// Watershed summary classification chips must honor the selected survey year,
// rather than silently counting labels from every year.
$selected_year=$plantData['results'][0]['survey_years'][0];
$year_filters=array('direction'=>'region_explore','group'=>array('plants'),
    'region'=>'chugoku','watershed'=>'太田川','watershed_match'=>'exact',
    'year'=>$selected_year);
$year_waters=tsb_request('search',$year_filters);
$year_names=tsb_request('search',array_merge($year_filters,
    array('direction'=>'watershed_to_organism')));
tsb_assert($year_waters->get_status()===200&&$year_names->get_status()===200,
    'Year-filtered searches must succeed');
tsb_assert($year_waters->get_data()['total']===1,'Filtered Ota watershed absent');
tsb_assert($year_waters->get_data()['results'][0]['group_label_counts']['plants']
    ===$year_names->get_data()['total'],
    'Watershed category chip must use selected year filter');

$birds=tsb_request('search',array(
    'direction'=>'watershed_to_organism','group'=>array('birds'),
    'region'=>'chugoku','watershed'=>'太田川','watershed_match'=>'exact'
));
tsb_assert($birds->get_status()===200&&$birds->get_data()['total']===120,
    'Ota bird group count unexpectedly changed');

$invalid=tsb_request('search',array(
    'direction'=>'region_explore','group'=>array('aquatic_insects'),'region'=>'chugoku'
));
tsb_assert($invalid->get_status()===400,'Unverified insect subgroup must reject');
$injection=tsb_request('search',array(
    'direction'=>'organism_to_watershed','group'=>array('fish'),'organism'=>"' OR 1=1 --"
));
tsb_assert($injection->get_status()===200&&$injection->get_data()['total']===0,
    'User-supplied SQL text must remain literal');

$shortcode=do_shortcode('[tsurikue_biota_search]');
tsb_assert(strpos($shortcode,'data-tbs-mount="1"')!==false,'Independent shortcode missing');
tsb_assert(strpos($shortcode,'<template data-tbs-view>')!==false,'Shadow DOM layout missing');

$again=$begin->invoke(null);
tsb_assert($again['importing']===true&&$again['ready']===true,'Second import should keep old data visible');
tsb_assert($again['generation']===1,'Active generation switched during incomplete import');
$partial=$step->invoke(null);
tsb_assert($partial['ready']===true,'Old generation became unavailable mid-reimport');
$still=tsb_request('search',array(
    'direction'=>'region_explore','region'=>'chugoku','group'=>array('plants')));
tsb_assert($still->get_status()===200 && $still->get_data()['total']===13,
    'Old data must stay available while writing inactive generation');

// Finish re-import into the alternate generation, then actually restore
// the original generation and verify that it is still queryable.
$reimport_steps=1;
while ($partial['importing']) {
    $partial=$step->invoke(null);$reimport_steps++;
    if ($reimport_steps>850) {
        throw new RuntimeException('Second-generation batch loop exceeded 850');
    }
}
tsb_assert($partial['ready']===true && $partial['generation']===2,
    'Verified second generation did not become active');
tsb_assert($partial['rollback_available']===true,
    'Original generation is not marked as restorable');
$restored=$rollback->invoke(null);
tsb_assert($restored['ready']===true && $restored['generation']===1
    && $restored['rollback_available']===true,
    'Rollback failed to restore original generation');
$after=tsb_request('search',array(
    'direction'=>'watershed_to_organism','group'=>array('plants'),
    'region'=>'chugoku','watershed'=>'太田川','watershed_match'=>'exact'
));
tsb_assert($after->get_status()===200 && $after->get_data()['total']===1212,
    'Restored generation has changed Ota plant results');
tsb_assert((int)wp_count_posts('post')->publish===$pre_posts,
    'A re-import or rollback unexpectedly changed WordPress posts');
echo "BIOTA_WORDPRESS_REAL_DATA_PASS 408036 records; 4 groups, REST, shortcode, 2 full imports and successful rollback; batches=".$steps."+".$reimport_steps."\n";
