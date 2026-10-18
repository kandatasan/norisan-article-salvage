<?php
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Administrator-controlled, resumable, atomic-generation importer.
 *
 * Each dataset has generations 1 and 2. Rebuilds delete ONLY the inactive
 * generation. Public queries continue using the last fully verified generation
 * until counts for the new generation are validated and option flips.
 *
 * This class never writes posts, terms, WP options unrelated to TSR, or
 * passwords. Import starts only from an authorized manual admin action.
 */
final class TSR_Import {
    private const BATCH = 300;
    private const ORDER = array('codes', 'local', 'fish');
    private const EXPECTED = array('codes' => 35449, 'local' => 1449, 'fish' => 18814);
    private const REGION_CODES = array(
        'hokkaido', 'tohoku', 'kanto', 'hokuriku', 'chubu',
        'kinki', 'chugoku', 'shikoku', 'kyushu'
    );

    private static function data_file($type) {
        $paths = array(
            'codes' => 'data/river_codes.csv',
            'local' => 'data/source_mentions.csv',
            'fish' => 'data/watershed_fish.csv'
        );
        if (!isset($paths[$type])) {
            throw new RuntimeException('Invalid dataset type');
        }
        return TSR_PLUGIN_DIR . $paths[$type];
    }

    private static function manifest($verify_hashes) {
        $path = TSR_PLUGIN_DIR . 'data/manifest.json';
        if (!is_readable($path)) {
            throw new RuntimeException('データマニフェストが見つかりません。プラグインを再インストールしてください。');
        }
        $m = json_decode((string) file_get_contents($path), true);
        if (!is_array($m)
            || !isset($m['version'], $m['counts'], $m['sha256'])
            || $m['version'] !== TSR_DATA_VERSION
            || $m['counts'] !== self::EXPECTED) {
            throw new RuntimeException('データのバージョンや件数が一致しません。');
        }
        foreach (self::ORDER as $type) {
            $file = self::data_file($type);
            if (!is_readable($file) || !isset($m['sha256'][$type])) {
                throw new RuntimeException('取込用のCSVが不足しています。');
            }
            if ($verify_hashes && !hash_equals((string) $m['sha256'][$type], hash_file('sha256', $file))) {
                throw new RuntimeException('CSVのチェックサムが一致しません。取込を中止しました。');
            }
        }
        return $m;
    }

    private static function authorize() {
        if (!current_user_can('manage_options')) {
            wp_send_json_error(array('message' => '管理者権限が必要です。'), 403);
        }
        check_ajax_referer('tsr_river_import', 'nonce');
    }

    private static function lock() {
        $key = 'tsr_import_mutex';
        $taken = add_option($key, time(), '', false);
        if (!$taken) {
            $old = (int) get_option($key, 0);
            if ($old > 0 && $old < time() - 90) {
                delete_option($key);
                $taken = add_option($key, time(), '', false);
            }
        }
        if (!$taken) {
            throw new RuntimeException('別の取込処理が進行中です。');
        }
    }

    private static function unlock() {
        delete_option('tsr_import_mutex');
    }

    public static function status() {
        $active = (int) get_option('tsr_active_gen', 0);
        $version = (string) get_option('tsr_active_version', '');
        $state = get_option('tsr_import_state', null);
        $ready = TSR_Search::ready();
        if (is_array($state)) {
            $message = '取込中：' . $state['phase'] . ' ／ '
                . array_sum($state['imported']) . ' / ' . array_sum(self::EXPECTED) . '行';
        } elseif ($ready) {
            $message = '取込完了・検索可能（' . esc_html($version) . '）';
        } else {
            $message = '未取込。専用テーブルは検索に使用されていません。';
        }
        return array(
            'ready' => $ready,
            'active_generation' => $ready ? $active : null,
            'active_version' => $ready ? $version : null,
            'importing' => is_array($state),
            'phase' => is_array($state) ? $state['phase'] : null,
            'imported' => is_array($state) ? $state['imported'] : array('codes' => 0, 'local' => 0, 'fish' => 0),
            'expected' => self::EXPECTED,
            'message' => $message
        );
    }

    public static function ajax_status() {
        self::authorize();
        wp_send_json_success(self::status());
    }

    private static function begin() {
        global $wpdb;
        self::manifest(true);
        $active = (int) get_option('tsr_active_gen', 0);
        $target = $active === 1 ? 2 : 1;
        $tables = Tsurikue_River_Search::tables();
        // Remove ONLY the inactive generation; preserve public data if available.
        foreach (self::ORDER as $type) {
            $result = $wpdb->query($wpdb->prepare(
                "DELETE FROM {$tables[$type]} WHERE generation = %d", $target
            ));
            if ($result === false) {
                throw new RuntimeException('DBに書き込めません。専用テーブルの作成状態を確認してください。');
            }
        }
        $state = array(
            'version' => TSR_DATA_VERSION,
            'target' => $target,
            'phase' => 'codes',
            'byte_offset' => 0,
            'imported' => array('codes' => 0, 'local' => 0, 'fish' => 0)
        );
        update_option('tsr_import_state', $state, false);
        return self::status();
    }

    public static function ajax_start() {
        self::authorize();
        $error = null;
        try {
            self::lock();
            try { $result = self::begin(); }
            finally { self::unlock(); }
        } catch (Throwable $e) {
            $error = $e->getMessage();
        }
        if ($error !== null) {
            wp_send_json_error(array('message' => $error), 500);
        }
        wp_send_json_success($result);
    }

    private static function insert_row($type, $gen, $row, $row_id) {
        global $wpdb;
        $tables = Tsurikue_River_Search::tables();
        $expected_columns = array('codes' => 5, 'local' => 9, 'fish' => 5);
        if (count($row) !== $expected_columns[$type]) {
            throw new RuntimeException('CSVの列数が正しくありません（' . $type . '）。');
        }
        if ($type === 'codes') {
            list($code, $name, $basin, $watershed_code, $source) = $row;
            if (!preg_match('/^[0-9]{10}$/D', $code)
                || !preg_match('/^[0-9]{6}$/D', $watershed_code)
                || substr($code, 0, 6) !== $watershed_code || $name === '') {
                throw new RuntimeException('国の河川コードデータが不正です。');
            }
            $entry = array(
                'generation' => $gen, 'river_code' => $code, 'river_name' => $name,
                'watershed_name' => $basin, 'watershed_code' => $watershed_code,
                'source_url' => $source
            );
        } elseif ($type === 'local') {
            list($pref, $name, $kind, $basin, $area, $url, $source_id, $scope, $date) = $row;
            if ($name === '' || $source_id === '' || $pref === ''
                || !in_array($kind, array('river','watershed','planning_region'), true)) {
                throw new RuntimeException('県別資料の分類または識別子が不正です。');
            }
            $entry = array(
                'generation' => $gen, 'source_id' => $source_id,
                'prefecture' => $pref, 'label_name' => $name, 'label_kind' => $kind,
                'watershed_name' => $basin, 'source_area' => $area,
                'source_url' => $url, 'source_scope' => $scope, 'source_date' => $date
            );
        } else {
            list($region, $basin, $year, $fish, $url) = $row;
            if (!in_array($region, self::REGION_CODES, true) || !$basin || !$fish) {
                throw new RuntimeException('水系別魚類資料の分類が不正です。');
            }
            $entry = array(
                'generation' => $gen, 'row_id' => $row_id, 'region_code' => $region,
                'watershed_name' => $basin, 'survey_year' => $year,
                'fish_name' => $fish, 'source_url' => $url
            );
        }
        if (!preg_match('~^https://[a-z0-9.-]+\.jp(?:/|$)~i', $type === 'codes' ? $row[4] : ($type === 'local' ? $row[5] : $row[4]))) {
            throw new RuntimeException('出典URLが公的なHTTPSドメインではありません。');
        }
        // replace() makes retry of an interrupted batch idempotent by source ID.
        if ($wpdb->replace($tables[$type], $entry) === false) {
            throw new RuntimeException('データの書込に失敗しました。DB容量や権限をご確認ください。');
        }
    }

    private static function next_phase($phase) {
        if ($phase === 'codes') return 'local';
        if ($phase === 'local') return 'fish';
        if ($phase === 'fish') return 'finished';
        throw new RuntimeException('不明な取込段階です。');
    }

    private static function finish($state) {
        global $wpdb;
        $tables = Tsurikue_River_Search::tables();
        $gen = (int) $state['target'];
        foreach (self::ORDER as $type) {
            $actual = (int) $wpdb->get_var($wpdb->prepare(
                "SELECT COUNT(*) FROM {$tables[$type]} WHERE generation = %d", $gen
            ));
            if ($actual !== self::EXPECTED[$type] || $state['imported'][$type] !== self::EXPECTED[$type]) {
                throw new RuntimeException('取込行数とDB登録数が一致しません（' . $type . '）。旧データは保持しています。');
            }
        }
        // Manifest hashes checked again before final activation.
        self::manifest(true);
        update_option('tsr_active_version', TSR_DATA_VERSION, false);
        update_option('tsr_active_gen', $gen, false); // single logical switch
        delete_option('tsr_import_state');
        return self::status();
    }

    private static function advance() {
        $state = get_option('tsr_import_state', null);
        if (!is_array($state) || $state['version'] !== TSR_DATA_VERSION
            || !in_array($state['target'], array(1,2), true)
            || !in_array($state['phase'], self::ORDER, true)) {
            throw new RuntimeException('再開できる取込がありません。開始ボタンから実行してください。');
        }
        $type = $state['phase'];
        $file = self::data_file($type);
        $fh = fopen($file, 'rb');
        if ($fh === false) {
            throw new RuntimeException('取込CSVを開けません。');
        }
        try {
            if ($state['byte_offset'] > 0) {
                if (fseek($fh, (int) $state['byte_offset'], SEEK_SET) !== 0) {
                    throw new RuntimeException('CSV再開位置が不正です。');
                }
            } else {
                $header = fgetcsv($fh, 0, ',', '"', '');
                if ($header === false) {
                    throw new RuntimeException('CSVにヘッダーがありません。');
                }
            }
            $finished = false;
            for ($i=0; $i < self::BATCH; $i++) {
                $row = fgetcsv($fh, 0, ',', '"', '');
                if ($row === false) {
                    $finished = true;
                    break;
                }
                $id = (int) $state['imported'][$type] + 1;
                if ($id > self::EXPECTED[$type]) {
                    throw new RuntimeException('原本の行数が定義を超えています。');
                }
                self::insert_row($type, (int) $state['target'], $row, $id);
                $state['imported'][$type] = $id;
                $state['byte_offset'] = ftell($fh);
            }
        } finally {
            fclose($fh);
        }
        if ($finished) {
            if ((int) $state['imported'][$type] !== self::EXPECTED[$type]) {
                throw new RuntimeException('CSVの行数が不足しています（' . $type . '）。');
            }
            $state['phase'] = self::next_phase($type);
            $state['byte_offset'] = 0;
            if ($state['phase'] === 'finished') {
                return self::finish($state);
            }
        }
        update_option('tsr_import_state', $state, false);
        return self::status();
    }

    public static function ajax_step() {
        self::authorize();
        $error = null;
        try {
            self::lock();
            try { $result = self::advance(); }
            finally { self::unlock(); }
        } catch (Throwable $e) {
            $error = $e->getMessage();
        }
        if ($error !== null) {
            wp_send_json_error(array('message' => $error), 500);
        }
        wp_send_json_success($result);
    }
}
