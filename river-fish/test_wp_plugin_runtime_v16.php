<?php
/**
 * Real WordPress / MySQL smoke test, run ONLY on an ephemeral GitHub Actions WP.
 * Usage: php wp-cli.phar eval-file river-fish/test_wp_plugin_runtime_v16.php
 *
 * Reflection calls the exact importer core without exposing additional public
 * unauthenticated routes. Live AJAX entry points remain nonce/admin-guarded.
 */
if (!defined('ABSPATH')) {
    throw new RuntimeException('Run under wp-cli eval-file only.');
}
if (!defined('WP_CLI') || !WP_CLI) {
    throw new RuntimeException('This fixture must not run through public WordPress HTTP.');
}
function tsr_assert($ok, $message) {
    if (!$ok) {
        throw new RuntimeException('TSR WP INTEGRATION FAILURE: ' . $message);
    }
}
function tsr_request($options) {
    $req = new WP_REST_Request('GET', '/tsurikue-rivers/v1/search');
    foreach ($options as $k => $v) {
        $req->set_param($k, $v);
    }
    return rest_do_request($req);
}

tsr_assert(class_exists('Tsurikue_River_Search'), 'Plugin is not active');
tsr_assert(class_exists('TSR_Import'), 'Importer missing');
tsr_assert(class_exists('TSR_Search'), 'Search missing');
tsr_assert(!TSR_Search::ready(), 'Fresh plugin must not activate data itself');

$not_ready = tsr_request(array('mode'=>'codes','q'=>'諸木川'));
tsr_assert($not_ready->get_status() === 503, 'REST API must reject unimported data');

$init = new ReflectionMethod('TSR_Import', 'begin');
$step = new ReflectionMethod('TSR_Import', 'advance');
$pre_posts = (int) wp_count_posts('post')->publish;
$progress = $init->invoke(null);
tsr_assert($progress['importing'] === true, 'Import must be explicitly started');
tsr_assert($progress['ready'] === false, 'Import must not make incomplete data public');
$iterations = 0;
do {
    $progress = $step->invoke(null);
    $iterations++;
    if ($iterations > 300) {
        throw new RuntimeException('Import did not finish within 300 batches');
    }
} while ($progress['importing']);

tsr_assert($progress['ready'] === true, 'Complete import must become ready');
tsr_assert($progress['active_generation'] === 1, 'Expected first generation');
tsr_assert(array_sum($progress['imported']) === 0, 'Completed importer should have no pending state');
global $wpdb;
$tables = Tsurikue_River_Search::tables();
$expected = array('codes'=>35449,'local'=>1449,'fish'=>18814);
foreach ($expected as $key=>$count) {
    $actual = (int) $wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM {$tables[$key]} WHERE generation = %d", 1
    ));
    tsr_assert($actual === $count, 'Incorrect imported '.$key.' count: '.$actual);
}
tsr_assert((int) wp_count_posts('post')->publish === $pre_posts, 'WP posts unexpectedly modified');

$codes = tsr_request(array('mode'=>'codes','q'=>'諸木川'));
tsr_assert($codes->get_status() === 200, 'Official code API error');
$codedata = $codes->get_data();
tsr_assert($codedata['total'] > 0, 'Missing 諸木川 official name');
tsr_assert(in_array('8707090023',array_column($codedata['rows'],'river_code'),true),
    'Missing literal Moroki river code');
tsr_assert(!isset($codedata['rows'][0]['prefecture']), 'Illegal guessed prefecture in code result');
tsr_assert(!isset($codedata['rows'][0]['fish_name']), 'Illegal guessed fish in code result');

$local = tsr_request(array('mode'=>'local','q'=>'国場川','prefecture'=>'沖縄県'));
tsr_assert($local->get_status() === 200, 'Local source API error');
$localdata=$local->get_data();
tsr_assert($localdata['total']>0, 'Missing Okinawa official source');
tsr_assert(!isset($localdata['rows'][0]['river_code']), 'Unverified official code wrongly assigned to source');
tsr_assert(!isset($localdata['rows'][0]['fish_name']), 'Unverified fish wrongly assigned to local river');

$tokyo = tsr_request(array('mode'=>'local','q'=>'神田川','prefecture'=>'東京都'));
tsr_assert($tokyo->get_data()['total']>0, 'Tokyo local source unavailable');

$fish = tsr_request(array('mode'=>'fish','q'=>'アユ','region'=>'kyushu'));
tsr_assert($fish->get_status() === 200, 'Fish context API error');
$fishdata=$fish->get_data();
tsr_assert($fishdata['total']>0, 'Missing watershed-year アユ');
tsr_assert($fishdata['rows'][0]['region_code']==='kyushu','Fish region filter broken');
tsr_assert(!isset($fishdata['rows'][0]['river_code']), 'Fish census wrongly assigned to particular river');
tsr_assert(!isset($fishdata['rows'][0]['prefecture']), 'Fish census wrongly assigned to prefecture');

$bad = tsr_request(array('mode'=>'codes','q'=>"' OR 1=1 --"));
tsr_assert($bad->get_status()===200 && $bad->get_data()['total']===0,
    'SQL injection-like input should be treated as a literal');

$bounds = tsr_request(array('mode'=>'codes','q'=>'川','per_page'=>999,'page'=>1));
tsr_assert(count($bounds->get_data()['rows'])<=25, 'Public API exceeded 25-row limit');

$shortcode = do_shortcode('[tsurikue_river_search]');
tsr_assert(strpos($shortcode,'data-tsr-app="1"')!==false, 'Shortcode did not output an accessible search widget');
tsr_assert(strpos($shortcode,'[tsurikue_river_search]')===false, 'Shortcode was not evaluated');

// Re-import starts writing the INACTIVE generation. Old generation remains
// queryable until ALL three sets pass final checks.
$progress = $init->invoke(null);
tsr_assert($progress['ready']===true && $progress['importing']===true,
    'A second import should preserve the previous active generation');
tsr_assert($progress['active_generation']===1, 'Active generation switched too early');
$progress = $step->invoke(null);
tsr_assert($progress['ready']===true, 'Partial second import must not hide old data');
tsr_assert(tsr_request(array('mode'=>'codes','q'=>'諸木川'))->get_status()===200,
    'Old data disappeared during staged reimport');

echo "PASS WordPress integration: 55,712 actual rows imported, REST scope constraints, real shortcode, safe inactive-generation updates; steps=".$iterations."\n";
