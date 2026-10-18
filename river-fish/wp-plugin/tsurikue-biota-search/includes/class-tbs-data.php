<?php
if (!defined('ABSPATH')) { exit; }
/** Admin-only staged import of verified historical survey names. */
final class TBS_Data {
    private const BATCH = 500;
    private const GROUP_COUNTS = array(
        'fish'=>18814,'benthic_animals'=>74949,'birds'=>44093,'plants'=>270180
    );
    private const REGIONS = array(
        'hokkaido','tohoku','kanto','hokuriku','chubu',
        'kinki','chugoku','shikoku','kyushu'
    );
    private const HEAD = array(
        'group_id','region_code','watershed_name','survey_year',
        'recorded_name','source_url','source_sha256'
    );
    public static function csv_path() { return TBS_DIR.'data/survey_evidence.csv'; }
    public static function manifest_path() { return TBS_DIR.'data/manifest.json'; }

    public static function manifest($check_hash = false) {
        $mfile = self::manifest_path();
        $csv = self::csv_path();
        if (!is_readable($mfile) || !is_readable($csv)) {
            throw new RuntimeException('データ同梱ZIPのCSVまたはmanifestが見つかりません。');
        }
        $m = json_decode((string) file_get_contents($mfile),true);
        if (!is_array($m)
            || !isset($m['version'],$m['counts'],$m['total'],$m['sha256_csv'],$m['groups'],
                      $m['source_dataset_sha256'],$m['publication_status'])
            || $m['version'] !== TBS_DATA_VERSION
            || $m['counts'] !== self::GROUP_COUNTS
            || (int) $m['total'] !== array_sum(self::GROUP_COUNTS)
            || $m['publication_status'] !== 'not_imported_until_manual_admin_action'
            || !preg_match('/^[0-9a-f]{64}$/D', $m['sha256_csv'])
            || !preg_match('/^[0-9a-f]{64}$/D', $m['source_dataset_sha256'])
            || !is_array($m['groups'])
            || count($m['groups']) !== 4) {
            throw new RuntimeException('manifestの版・件数または公開境界が不正です。');
        }
        $ids=array();
        foreach ($m['groups'] as $g) {
            if (!isset($g['id'],$g['label'],$g['note'],$g['source_rows'])
                || !isset(self::GROUP_COUNTS[$g['id']])
                || (int) $g['source_rows'] !== self::GROUP_COUNTS[$g['id']]) {
                throw new RuntimeException('生物区分のmanifestが一致しません。');
            }
            $ids[]=$g['id'];
        }
        if (count(array_unique($ids))!==4) {
            throw new RuntimeException('生物区分が重複しています。');
        }
        if ($check_hash && !hash_equals($m['sha256_csv'],hash_file('sha256',$csv))) {
            throw new RuntimeException('CSVのSHA-256検査に失敗しました。古いデータは保持しています。');
        }
        return $m;
    }

    public static function active() {
        $x=get_option('tsb_active_pointer',null);
        if (!is_array($x) || !isset($x['generation'],$x['version'],$x['groups'],$x['counts'])
            || !in_array((int)$x['generation'],array(1,2),true)
            || !is_string($x['version']) || $x['version']===''
            || !is_array($x['groups']) || count($x['groups'])<1
            || !is_array($x['counts'])) {
            return null;
        }
        return $x;
    }
    public static function status() {
        $active=self::active();
        $state=get_option('tsb_import_state',null);
        $importing=is_array($state);
        $done=$importing?(int)$state['imported']:0;
        $total=array_sum(self::GROUP_COUNTS);
        return array(
            'ready'=>$active!==null,
            'importing'=>$importing,
            'imported'=>$done,
            'expected'=>$total,
            'version'=>$active?$active['version']:null,
            'generation'=>$active?$active['generation']:null,
            'rollback_available'=>is_array(get_option('tsb_previous_pointer',null)),
            'message'=>$importing?'取込中 '.$done.' / '.$total.'件'
                :($active?'利用可能：'.$active['version']:'未取込です。')
        );
    }
    private static function authorize() {
        if (!current_user_can('manage_options')) {
            wp_send_json_error(array('message'=>'管理者権限が必要です。'),403);
        }
        check_ajax_referer('tbs_import_v1','nonce');
    }
    private static function lock() {
        $key='tsb_import_mutex';
        if (add_option($key,time(),'',false)) { return; }
        $old=(int)get_option($key,0);
        if ($old>0 && $old<time()-120) {
            delete_option($key);
            if (add_option($key,time(),'',false)) {return;}
        }
        throw new RuntimeException('別の取込操作が進行中です。');
    }
    private static function unlock() { delete_option('tsb_import_mutex'); }
    private static function run_ajax($method) {
        self::authorize();
        try {
            self::lock();
            try { $result=call_user_func(array(__CLASS__,$method)); }
            finally { self::unlock(); }
            wp_send_json_success($result);
        } catch (Throwable $e) {
            wp_send_json_error(array('message'=>$e->getMessage()),500);
        }
    }
    public static function ajax_status() {
        self::authorize();
        wp_send_json_success(self::status());
    }
    public static function ajax_start() { self::run_ajax('begin'); }
    public static function ajax_step() { self::run_ajax('step'); }
    public static function ajax_rollback() { self::run_ajax('rollback'); }

    private static function begin() {
        global $wpdb;
        self::manifest(true);
        $active=self::active();
        $gen=$active && (int)$active['generation']===1?2:1;
        $table=Tsurikue_Biota_Search::table();
        $removed=$wpdb->query($wpdb->prepare("DELETE FROM {$table} WHERE generation = %d",$gen));
        if ($removed===false) {
            throw new RuntimeException('専用生物テーブルへアクセスできません。');
        }
        update_option('tsb_import_state',array(
            'version'=>TBS_DATA_VERSION,'generation'=>$gen,
            'offset'=>0,'imported'=>0
        ),false);
        return self::status();
    }

    private static function row_ok($line,$target,$id) {
        if (!is_array($line) || count($line)!==7) {
            throw new RuntimeException('CSVの列数が正しくありません。');
        }
        list($group,$region,$watershed,$year,$name,$url,$sha)=$line;
        if (!isset(self::GROUP_COUNTS[$group])
            || !in_array($region,self::REGIONS,true)
            || $watershed==='' || $name===''
            || (function_exists('mb_strlen') ? mb_strlen($watershed,'UTF-8') : strlen($watershed))>80
            || (function_exists('mb_strlen') ? mb_strlen($name,'UTF-8') : strlen($name))>150
            || preg_match('/^[=+@-]/u',$watershed) || preg_match('/^[=+@-]/u',$name)
            || !preg_match('/^(19|20)[0-9]{2}$/D',$year) || $year>'2026'
            || !preg_match('~^https://www\.nilim\.go\.jp/lab/fbg/ksnkankyo/[^\s]*$~D',$url)
            || ($sha!=='' && !preg_match('/^[0-9a-f]{64}$/D',$sha))) {
            throw new RuntimeException('公式調査の地方・区分・年度・出典が不正です。');
        }
        if ($group!=='fish' && $sha==='') {
            throw new RuntimeException('原本ハッシュが不足しています。');
        }
        return array(
            'generation'=>$target,'row_id'=>$id,
            'group_id'=>$group,'region_code'=>$region,
            'watershed_name'=>$watershed,'survey_year'=>$year,
            'recorded_name'=>$name,'source_url'=>$url,'source_sha256'=>$sha
        );
    }

    private static function finish($state) {
        global $wpdb;
        $m=self::manifest(true);
        if ((int)$state['imported']!==$m['total']) {
            throw new RuntimeException('行数が不足しています。旧版を維持します。');
        }
        $table=Tsurikue_Biota_Search::table();
        $target=(int)$state['generation'];
        $counts=$wpdb->get_results($wpdb->prepare(
            "SELECT group_id,COUNT(*) AS n FROM {$table} WHERE generation=%d GROUP BY group_id",
            $target),ARRAY_A);
        if ($counts===null || $wpdb->last_error) {
            throw new RuntimeException('取込済み分類を確認できません。');
        }
        $actual=array();
        foreach ($counts as $row) { $actual[$row['group_id']]=(int)$row['n']; }
        ksort($actual);
        $expected=self::GROUP_COUNTS;
        ksort($expected);
        if ($actual !== $expected) {
            throw new RuntimeException('取込分類件数が原本と一致しません。旧版を保持します。');
        }
        $old=self::active();
        if ($old) {
            update_option('tsb_previous_pointer',$old,false);
        } else {
            delete_option('tsb_previous_pointer');
        }
        // One option stores complete active generation, groups, version and counts.
        $pointer=array(
            'generation'=>$target,'version'=>TBS_DATA_VERSION,
            'groups'=>$m['groups'],'counts'=>$m['counts'],
            'source_dataset_sha256'=>$m['source_dataset_sha256']
        );
        update_option('tsb_active_pointer',$pointer,false);
        delete_option('tsb_import_state');
        return self::status();
    }

    private static function step() {
        global $wpdb;
        $s=get_option('tsb_import_state',null);
        if (!is_array($s) || !isset($s['version'],$s['generation'],$s['offset'],$s['imported'])
            || $s['version']!==TBS_DATA_VERSION
            || !in_array((int)$s['generation'],array(1,2),true)
            || (int)$s['imported']<0 || (int)$s['imported']>array_sum(self::GROUP_COUNTS)) {
            throw new RuntimeException('再開できるデータ取込がありません。');
        }
        $fh=fopen(self::csv_path(),'rb');
        if (!$fh) {throw new RuntimeException('取込CSVを開けません。');}
        $eof=false;
        try {
            if ((int)$s['offset']>0) {
                if (fseek($fh,(int)$s['offset'],SEEK_SET)!==0) {
                    throw new RuntimeException('再開位置が不正です。');
                }
            } else {
                $header=fgetcsv($fh,0,',','"','');
                if ($header!==self::HEAD) {
                    throw new RuntimeException('CSV見出しが公式データ契約と異なります。');
                }
            }
            $table=Tsurikue_Biota_Search::table();
            for ($i=0;$i<self::BATCH;$i++) {
                $line=fgetcsv($fh,0,',','"','');
                if ($line===false) { $eof=true;break; }
                $id=(int)$s['imported']+1;
                if ($id>array_sum(self::GROUP_COUNTS)) {
                    throw new RuntimeException('CSVに余計な行があります。');
                }
                $record=self::row_ok($line,(int)$s['generation'],$id);
                if ($wpdb->replace($table,$record)===false) {
                    throw new RuntimeException('専用DBへの書き込みに失敗しました。');
                }
                $s['imported']=$id;
                $s['offset']=ftell($fh);
            }
        } finally { fclose($fh); }
        if ($eof) { return self::finish($s); }
        update_option('tsb_import_state',$s,false);
        return self::status();
    }

    private static function rollback() {
        global $wpdb;
        if (is_array(get_option('tsb_import_state',null))) {
            throw new RuntimeException('取込中は旧版へ戻せません。');
        }
        $current=self::active();
        $previous=get_option('tsb_previous_pointer',null);
        if (!$current || !is_array($previous)
            || !isset($previous['generation'],$previous['counts'],$previous['groups'],$previous['version'])
            || !in_array((int)$previous['generation'],array(1,2),true)
            || (int)$previous['generation']===(int)$current['generation']) {
            throw new RuntimeException('復元可能な旧版はありません。');
        }
        $table=Tsurikue_Biota_Search::table();
        $n=(int)$wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$table} WHERE generation=%d",(int)$previous['generation']));
        if ($n!==array_sum($previous['counts'])) {
            throw new RuntimeException('旧版のデータが欠けています。切替を中止しました。');
        }
        update_option('tsb_previous_pointer',$current,false);
        update_option('tsb_active_pointer',$previous,false);
        return self::status();
    }
}
