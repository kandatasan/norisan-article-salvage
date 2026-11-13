<?php
// Isolated plugin/shortcode rendering smoke tests.
define('ABSPATH', '/tests/');
$GLOBALS['hooks'] = array();
$GLOBALS['shortcodes'] = array();
function add_action($event, $callback, $priority=10) {$GLOBALS['hooks'][$event]=$callback;}
function add_filter($event, $callback, $priority=10) {$GLOBALS['hooks'][$event]=$callback;}
function add_shortcode($tag, $callback) {$GLOBALS['shortcodes'][$tag]=$callback;}
class WP_Post {public $post_content='';public $post_name='';}
require __DIR__ . '/../tsurikue-can-drive-japan.php';
function ensure($v, $message) {if (!$v) {throw new RuntimeException($message);}}
ensure(isset($GLOBALS['hooks']['wp_enqueue_scripts']), 'Assets hook missing');
ensure(isset($GLOBALS['shortcodes']['tsurikue_can_drive_japan']), 'Shortcode not registered');
$html=tsu_drive_checker_shortcode();
$css=tsu_drive_checker_css();
$js=tsu_drive_checker_js();
ensure(strpos($html,'Can I Drive in Japan?')!==false, 'Missing English UI title');
ensure(substr_count($html,'name="issuer"')===1, 'Country selector count');
ensure(substr_count($html,'name="documents"')===6, 'Permit options count');
ensure(strpos($html,'<option value="tw">Taiwan')!==false, 'Taiwan selection missing');
ensure(strpos($html,'value="fr"')!==false, 'French issuing region missing');
ensure(strpos($html,'source-url')===false, 'Unknown content');
ensure(strpos($js,'window.tsurikueDriveDecide = decide')!==false,'Pure decision function absent');
ensure(strpos($js,'1949 Geneva Convention')!==false, 'Permit rules missing');
ensure(strpos($js,'A 1968 Vienna Convention IDP is not accepted')!==false,'Vienna reject missing');
ensure(strpos($js,'eligibleTranslations = ["fr","de","be","ch","mc","tw"]')!==false,'6 translation regions');
ensure(strpos($html,'https://www.npa.go.jp/english/')!==false,'NPA official source missing');
ensure(strpos($html,'https://english.jaf.or.jp/')!==false,'JAF official source missing');
ensure(strpos($js,'rel=sponsored nofollow noopener')===false,'Unintended unquoted link');
ensure(strpos($js,'sponsored nofollow noopener')!==false,'Affiliate attribution missing');
ensure(strpos($css,'.tsu-drive')!==false,'Scoped CSS missing');
ensure(strpos($html,'data-answer')!==false,'Accessible result area missing');
ensure(strpos($html,'aria-live="polite"')!==false,'Result aria-live missing');
ensure(strpos($html,'name="reentry"')!==false,'Re-entry safety missing');
ensure(substr_count($html,'name="arrival"')===5, 'Landing date options missing');
ensure(strpos($html,'I have not arrived yet')!==false,'Pre-trip visitors cannot answer');
ensure(strpos($html,'One year ago or earlier')!==false,'One-year expiry option missing');
ensure(strpos($js,'s.arrival === "yearplus"')!==false,'Landing limit validation missing');
ensure(strpos($js,'s.arrival === "unsure"')!==false,'Unknown landing date validation missing');
ensure(isset($GLOBALS['hooks']['language_attributes']),'English document language hook missing');

ensure(strpos($html,'Check my documents')!==false,'Submission action missing');
echo "Japan licence checker PHP + markup smoke PASS\n";
