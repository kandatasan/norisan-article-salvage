<?php
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Public, read-only REST search. The tables are explicitly scoped:
 * codes -> official code/name only, no prefecture;
 * local -> source document mention only, no national code or direct fish;
 * fish -> region / watershed / year only, no specific river or prefecture.
 */
final class TSR_Search {
    private const MODES = array('codes', 'local', 'fish');
    private const KINDS = array('river', 'watershed', 'planning_region');
    private const REGIONS = array(
        'hokkaido', 'tohoku', 'kanto', 'hokuriku', 'chubu',
        'kinki', 'chugoku', 'shikoku', 'kyushu'
    );

    public static function ready() {
        $gen = (int) get_option('tsr_active_gen', 0);
        return ($gen === 1 || $gen === 2)
            && get_option('tsr_active_version', '') === TSR_DATA_VERSION;
    }

    public static function register_routes() {
        register_rest_route('tsurikue-rivers/v1', '/search', array(
            'methods' => WP_REST_Server::READABLE,
            'callback' => array(__CLASS__, 'respond'),
            'permission_callback' => '__return_true',
            'args' => array(
                'mode' => array('type' => 'string', 'default' => 'codes', 'sanitize_callback' => 'sanitize_text_field'),
                'q' => array('type' => 'string', 'default' => '', 'sanitize_callback' => 'sanitize_text_field'),
                'prefecture' => array('type' => 'string', 'default' => '', 'sanitize_callback' => 'sanitize_text_field'),
                'kind' => array('type' => 'string', 'default' => '', 'sanitize_callback' => 'sanitize_text_field'),
                'watershed' => array('type' => 'string', 'default' => '', 'sanitize_callback' => 'sanitize_text_field'),
                'region' => array('type' => 'string', 'default' => '', 'sanitize_callback' => 'sanitize_text_field'),
                'page' => array('type' => 'integer', 'default' => 1, 'sanitize_callback' => 'absint'),
                'per_page' => array('type' => 'integer', 'default' => 20, 'sanitize_callback' => 'absint')
            )
        ));
    }

    private static function safe_text($value) {
        $text = trim(sanitize_text_field((string) $value));
        if (function_exists('mb_substr')) {
            return mb_substr($text, 0, 70, 'UTF-8');
        }
        return $text; // Query bytes are still protected by prepare().
    }

    public static function respond($request) {
        global $wpdb;
        if (!self::ready()) {
            return new WP_Error('tsr_not_ready',
                '全国河川データは準備中です。管理者がデータ取込を完了した後に検索できます。',
                array('status' => 503));
        }
        $mode = self::safe_text($request->get_param('mode'));
        if (!in_array($mode, self::MODES, true)) {
            return new WP_Error('tsr_bad_mode', '未対応の検索区分です。', array('status' => 400));
        }
        $q = self::safe_text($request->get_param('q'));
        $prefecture = self::safe_text($request->get_param('prefecture'));
        $kind = self::safe_text($request->get_param('kind'));
        $watershed = self::safe_text($request->get_param('watershed'));
        $region = self::safe_text($request->get_param('region'));
        if (($kind && !in_array($kind, self::KINDS, true))
            || ($region && !in_array($region, self::REGIONS, true))) {
            return new WP_Error('tsr_bad_filter', '検索条件が正しくありません。', array('status' => 400));
        }
        $page = max(1, min(2000, (int) $request->get_param('page')));
        $per_page = max(1, min(25, (int) $request->get_param('per_page')));
        $gen = (int) get_option('tsr_active_gen', 0);
        $tables = Tsurikue_River_Search::tables();
        $cols = '';
        $table = '';
        $where = array('generation = %d');
        $args = array($gen);
        $notice = '';

        if ($mode === 'codes') {
            $table = $tables['codes'];
            $cols = 'river_code,river_name,watershed_name,watershed_code,source_url';
            $notice = '全国10桁コードの資料掲載名です。所在県、直接合流先、個別の生息魚は未確認です。';
            if ($q !== '') {
                $like = '%' . $wpdb->esc_like($q) . '%';
                $where[] = '(river_name LIKE %s OR watershed_name LIKE %s OR river_code LIKE %s)';
                array_push($args, $like, $like, $like);
            }
            $has_filter = $q !== '';
            $order = 'river_code ASC';
        } elseif ($mode === 'local') {
            $table = $tables['local'];
            $cols = 'source_id,prefecture,label_name,label_kind,watershed_name,source_area,source_url,source_scope,source_date';
            $notice = '47都道府県の公式資料に登場した名称です。県内全河川の網羅や10桁コードとの一致を意味しません。';
            if ($q !== '') {
                $like = '%' . $wpdb->esc_like($q) . '%';
                $where[] = '(label_name LIKE %s OR watershed_name LIKE %s OR source_area LIKE %s)';
                array_push($args, $like, $like, $like);
            }
            if ($prefecture !== '') {
                $where[] = 'prefecture = %s';
                $args[] = $prefecture;
            }
            if ($kind !== '') {
                $where[] = 'label_kind = %s';
                $args[] = $kind;
            }
            $has_filter = $q !== '' || $prefecture !== '' || $kind !== '';
            $order = 'source_id ASC';
        } else {
            $table = $tables['fish'];
            $cols = 'region_code,watershed_name,survey_year,fish_name,source_url';
            $notice = '水系×調査年度×魚名の記録です。特定の支流での魚の生息・現在の釣果を示すものではありません。';
            if ($q !== '') {
                $where[] = 'fish_name LIKE %s';
                $args[] = '%' . $wpdb->esc_like($q) . '%';
            }
            if ($watershed !== '') {
                $where[] = 'watershed_name LIKE %s';
                $args[] = '%' . $wpdb->esc_like($watershed) . '%';
            }
            if ($region !== '') {
                $where[] = 'region_code = %s';
                $args[] = $region;
            }
            $has_filter = $q !== '' || $watershed !== '' || $region !== '';
            $order = 'region_code,watershed_name,survey_year,fish_name,row_id';
        }

        if (!$has_filter) {
            return rest_ensure_response(array(
                'mode' => $mode, 'rows' => array(), 'total' => 0,
                'page' => $page, 'per_page' => $per_page, 'notice' => $notice
            ));
        }
        $clause = implode(' AND ', $where);
        // Identifiers originate ONLY from the three trusted table name values.
        $count_sql = $wpdb->prepare("SELECT COUNT(*) FROM {$table} WHERE {$clause}", $args);
        $total = (int) $wpdb->get_var($count_sql);
        $offset = ($page - 1) * $per_page;
        $query_args = array_merge($args, array($per_page, $offset));
        $sql = $wpdb->prepare(
            "SELECT {$cols} FROM {$table} WHERE {$clause} ORDER BY {$order} LIMIT %d OFFSET %d",
            $query_args
        );
        $rows = $wpdb->get_results($sql, ARRAY_A);
        if ($rows === null || $wpdb->last_error) {
            return new WP_Error('tsr_search_error', '検索DBにアクセスできません。管理者へお知らせください。',
                array('status' => 503));
        }
        return rest_ensure_response(array(
            'mode' => $mode, 'rows' => $rows, 'total' => $total,
            'page' => $page, 'per_page' => $per_page, 'notice' => $notice
        ));
    }
}
