<?php
/**
 * Plugin Name: つりくえ！全国河川検索
 * Description: 全国河川コード、都道府県公式資料の掲載名、水系単位の魚類記録を出典別に検索する。手動インポート式のβ版。
 * Version: 0.2.0
 * Requires at least: 6.2
 * Requires PHP: 7.4
 * Author: つりくえ！
 * License: GPL-2.0-or-later
 * Text Domain: tsurikue-river-search
 */
if (!defined('ABSPATH')) {
    exit;
}
define('TSR_PLUGIN_VERSION', '0.2.0');
define('TSR_DATA_VERSION', 'v1.5-20261018');
define('TSR_PLUGIN_FILE', __FILE__);
define('TSR_PLUGIN_DIR', plugin_dir_path(__FILE__));

require_once TSR_PLUGIN_DIR . 'includes/class-tsr-import.php';
require_once TSR_PLUGIN_DIR . 'includes/class-tsr-search.php';

final class Tsurikue_River_Search {
    public static function boot() {
        add_action('rest_api_init', array('TSR_Search', 'register_routes'));
        add_shortcode('tsurikue_river_search', array(__CLASS__, 'shortcode'));
        add_action('admin_menu', array(__CLASS__, 'admin_menu'));
        add_action('admin_enqueue_scripts', array(__CLASS__, 'admin_assets'));
        add_action('wp_ajax_tsr_import_start', array('TSR_Import', 'ajax_start'));
        add_action('wp_ajax_tsr_import_step', array('TSR_Import', 'ajax_step'));
        add_action('wp_ajax_tsr_import_status', array('TSR_Import', 'ajax_status'));
    }

    public static function tables() {
        global $wpdb;
        return array(
            'codes' => $wpdb->prefix . 'tsr_river_codes',
            'local' => $wpdb->prefix . 'tsr_river_sources',
            'fish'  => $wpdb->prefix . 'tsr_watershed_fish'
        );
    }

    public static function activate() {
        global $wpdb;
        require_once ABSPATH . 'wp-admin/includes/upgrade.php';
        $tables = self::tables();
        $collate = $wpdb->get_charset_collate();

        $sql1 = "CREATE TABLE {$tables['codes']} (
generation tinyint unsigned NOT NULL,
river_code char(10) NOT NULL,
river_name varchar(200) NOT NULL,
watershed_name varchar(200) NOT NULL,
watershed_code char(6) NOT NULL,
source_url varchar(500) NOT NULL,
PRIMARY KEY  (generation,river_code),
KEY name_lookup (generation,river_name(80)),
KEY basin_lookup (generation,watershed_name(80))
) $collate";

        $sql2 = "CREATE TABLE {$tables['local']} (
generation tinyint unsigned NOT NULL,
source_id varchar(40) NOT NULL,
prefecture varchar(30) NOT NULL,
label_name varchar(200) NOT NULL,
label_kind varchar(30) NOT NULL,
watershed_name varchar(200) NOT NULL,
source_area varchar(160) NOT NULL,
source_url varchar(500) NOT NULL,
source_scope varchar(255) NOT NULL,
source_date varchar(30) NOT NULL,
PRIMARY KEY  (generation,source_id),
KEY pref_lookup (generation,prefecture),
KEY name_lookup (generation,label_name(80))
) $collate";

        $sql3 = "CREATE TABLE {$tables['fish']} (
generation tinyint unsigned NOT NULL,
row_id int unsigned NOT NULL,
region_code varchar(25) NOT NULL,
watershed_name varchar(200) NOT NULL,
survey_year varchar(15) NOT NULL,
fish_name varchar(200) NOT NULL,
source_url varchar(500) NOT NULL,
PRIMARY KEY  (generation,row_id),
KEY region_lookup (generation,region_code),
KEY basin_lookup (generation,watershed_name(80)),
KEY fish_lookup (generation,fish_name(80))
) $collate";

        dbDelta(array($sql1, $sql2, $sql3));
        // Activation only creates tables. Never loads rows, writes WP posts or
        // activates the dataset automatically.
    }

    /**
     * HARD LAYER owns the read-only API and data only.
     * SOFT LAYER owns the PHP view template, Shadow DOM CSS and JS.
     * The shortcode contract remains unchanged after upgrading v0.1 => v0.2.
     */
    public static function shortcode($attributes = array()) {
        $id = function_exists('wp_unique_id') ? wp_unique_id('tsr-') : 'tsr-river-search';

        // No global UI stylesheet: SWELL cannot bleed into the shadow root.
        // The Soft app injects its own scoped <link> into each widget.
        wp_enqueue_script(
            'tsurikue-river-front',
            plugins_url('frontend/app.js', TSR_PLUGIN_FILE),
            array(), TSR_PLUGIN_VERSION, true
        );
        wp_localize_script('tsurikue-river-front', 'TsurikueRiverSearchSettings', array(
            'endpoint' => esc_url_raw(rest_url('tsurikue-rivers/v1/search')),
            'styleUrl' => esc_url_raw(add_query_arg('ver', TSR_PLUGIN_VERSION, plugins_url('frontend/style.css', TSR_PLUGIN_FILE))),
            'prefectures' => array(
                '北海道','青森県','岩手県','宮城県','秋田県','山形県','福島県',
                '茨城県','栃木県','群馬県','埼玉県','千葉県','東京都','神奈川県',
                '新潟県','富山県','石川県','福井県','山梨県','長野県','岐阜県',
                '静岡県','愛知県','三重県','滋賀県','京都府','大阪府','兵庫県',
                '奈良県','和歌山県','鳥取県','島根県','岡山県','広島県','山口県',
                '徳島県','香川県','愛媛県','高知県','福岡県','佐賀県','長崎県',
                '熊本県','大分県','宮崎県','鹿児島県','沖縄県'
            )
        ));

        ob_start();
        include TSR_PLUGIN_DIR . 'frontend/view.php';
        return ob_get_clean();
    }

    public static function admin_menu() {
        add_management_page(
            '全国河川DBの取込',
            '全国河川DB',
            'manage_options',
            'tsurikue-river-import',
            array(__CLASS__, 'admin_page')
        );
    }

    public static function admin_assets($hook) {
        if ($hook !== 'tools_page_tsurikue-river-import') {
            return;
        }
        wp_enqueue_script(
            'tsurikue-river-admin',
            plugins_url('assets/river-admin.js', TSR_PLUGIN_FILE),
            array(), TSR_PLUGIN_VERSION, true
        );
        wp_localize_script('tsurikue-river-admin', 'TsurikueRiverImport', array(
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('tsr_river_import')
        ));
    }

    public static function admin_page() {
        if (!current_user_can('manage_options')) {
            wp_die(esc_html__('操作する権限がありません。'));
        }
        $status = TSR_Import::status();
        ?>
        <div class="wrap" id="tsr-admin-import">
          <h1>つりくえ！全国河川データ取込</h1>
          <p><strong>バックアップ確認後に利用してください。</strong>専用テーブルだけを更新します。記事、投稿、既存WordPressテーブルは編集しません。</p>
          <p>初期の収録量：全国河川コード35,449件、県別資料1,449行、水系・年度別の魚類記録18,814件。</p>
          <p>導入しただけでは取込を開始しません。取り込み中も旧データを保持し、件数検証に成功したときだけ新しい版に切り替えます。</p>
          <p><strong>現在の状態：</strong><span id="tsr-import-status"><?php echo esc_html($status['message']); ?></span></p>
          <p id="tsr-import-count" aria-live="polite"></p>
          <p><button class="button button-primary" id="tsr-import-start">取込を開始／最初から再開</button>
          <button class="button" id="tsr-import-resume">中断した取込を再開</button></p>
          <p id="tsr-import-error" style="color:#aa2e1c" role="alert"></p>
          <hr>
          <h2>ページへの設置</h2>
          <p>取込完了後、非公開または下書きページで次のショートコードを使用できます。</p>
          <p><code>[tsurikue_river_search]</code></p>
          <p>公開前に出典・権利・検索結果の表記を確認してください。専用データベースはデータ取込完了まで検索を返しません。</p>
        </div>
        <?php
    }
}
register_activation_hook(__FILE__, array('Tsurikue_River_Search', 'activate'));
Tsurikue_River_Search::boot();
