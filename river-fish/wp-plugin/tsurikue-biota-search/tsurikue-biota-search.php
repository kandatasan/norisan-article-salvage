<?php
/**
 * Plugin Name: つりくえ！全国生物×水系検索
 * Description: 公式の過去の河川調査（水系・年度・掲載名）を分類別に検索。独立した管理者承認型データ取込。
 * Version: 0.1.0
 * Requires at least: 6.2
 * Requires PHP: 7.4
 * Author: つりくえ！
 * License: GPL-2.0-or-later
 * Text Domain: tsurikue-biota-search
 */
if (!defined('ABSPATH')) { exit; }
define('TBS_VERSION', '0.1.0');
define('TBS_DATA_VERSION', 'biota-four-groups-v28');
define('TBS_MAIN', __FILE__);
define('TBS_DIR', plugin_dir_path(__FILE__));
require_once TBS_DIR . 'includes/class-tbs-data.php';
require_once TBS_DIR . 'includes/class-tbs-rest.php';

final class Tsurikue_Biota_Search {
    public static function table() {
        global $wpdb;
        return $wpdb->prefix . 'tsb_survey_evidence';
    }
    public static function activate() {
        require_once ABSPATH . 'wp-admin/includes/upgrade.php';
        global $wpdb;
        $table = self::table();
        $collate = $wpdb->get_charset_collate();
        dbDelta("CREATE TABLE {$table} (
generation tinyint unsigned NOT NULL,
row_id int unsigned NOT NULL,
group_id varchar(40) NOT NULL,
region_code varchar(20) NOT NULL,
watershed_name varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
survey_year char(4) NOT NULL,
recorded_name varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
source_url varchar(500) NOT NULL,
source_sha256 char(64) NOT NULL,
PRIMARY KEY  (generation,row_id),
KEY region_group (generation,region_code,group_id),
KEY watershed_group (generation,watershed_name(80),group_id),
KEY name_group (generation,recorded_name(80),group_id)
) $collate");
        // No data import, posts, WP pages or old river plugin mutations on activation.
    }
    public static function boot() {
        add_action('rest_api_init', array('TBS_REST','routes'));
        add_shortcode('tsurikue_biota_search', array(__CLASS__,'shortcode'));
        add_action('admin_menu', array(__CLASS__,'admin_menu'));
        add_action('admin_enqueue_scripts', array(__CLASS__,'admin_assets'));
        add_action('wp_ajax_tbs_import_start', array('TBS_Data','ajax_start'));
        add_action('wp_ajax_tbs_import_step', array('TBS_Data','ajax_step'));
        add_action('wp_ajax_tbs_import_status', array('TBS_Data','ajax_status'));
        add_action('wp_ajax_tbs_import_rollback', array('TBS_Data','ajax_rollback'));
    }
    public static function shortcode() {
        $id = function_exists('wp_unique_id') ? wp_unique_id('tsb-') : 'tsb-search';
        wp_enqueue_script('tsurikue-biota-front',
            plugins_url('frontend/app.js',TBS_MAIN),array(),TBS_VERSION,true);
        wp_localize_script('tsurikue-biota-front','TsurikueBiotaSettings',array(
            'search' => esc_url_raw(rest_url('tsurikue-biota/v1/search')),
            'catalog' => esc_url_raw(rest_url('tsurikue-biota/v1/catalog')),
            'css' => esc_url_raw(add_query_arg('ver',TBS_VERSION,plugins_url('frontend/style.css',TBS_MAIN)))
        ));
        ob_start();
        include TBS_DIR . 'frontend/view.php';
        return ob_get_clean();
    }
    public static function admin_menu() {
        add_management_page('全国生物DBの取込','全国生物DB',
            'manage_options','tsurikue-biota-import',array(__CLASS__,'admin_page'));
    }
    public static function admin_assets($hook) {
        if ($hook!=='tools_page_tsurikue-biota-import') { return; }
        wp_enqueue_script('tsurikue-biota-admin',
            plugins_url('assets/admin.js',TBS_MAIN),array(),TBS_VERSION,true);
        wp_localize_script('tsurikue-biota-admin','TsurikueBiotaAdmin',array(
            'ajax'=>admin_url('admin-ajax.php'),'nonce'=>wp_create_nonce('tbs_import_v1')
        ));
    }
    public static function admin_page() {
        if (!current_user_can('manage_options')) { wp_die('管理者権限が必要です。'); }
        $state=TBS_Data::status();
        ?>
        <div class="wrap" id="tbs-admin">
          <h1>つりくえ！全国生物×水系DB</h1>
          <p>国交省・河川水辺の国勢調査の過去記録。<strong>現在の生息・個々の支流での確認を示しません。</strong>
             出典：<a href="https://www.nilim.go.jp/lab/fbg/ksnkankyo/dl_00_index.html">国交省河川環境データベース</a>を加工して作成。</p>
          <p>このプラグインを入れただけでは取込・公開されません。WordPressのバックアップ、
             DB容量と空き領域を確認後、管理者が実行してください。既存の全国河川検索や投稿・記事には書き込みません。</p>
          <p>魚類18,814・底生動物74,949・鳥類44,093・植物270,180（計408,036掲載記録）。生物の種数ではありません。</p>
          <p><strong>状態：</strong><span id="tbs-status"><?php echo esc_html($state['message']); ?></span></p>
          <p id="tbs-progress" aria-live="polite"></p>
          <p><button type="button" class="button button-primary" id="tbs-start">取込を開始</button>
             <button type="button" class="button" id="tbs-resume">取込を再開</button>
             <button type="button" class="button" id="tbs-rollback">旧版へ戻す</button></p>
          <p id="tbs-error" role="alert" style="color:#a12d1d"></p>
          <h2>下書きページでの試用</h2>
          <p><code>[tsurikue_biota_search]</code></p>
          <p>公開前にスマホ/SWELL実機表示、APIの検索速度と出典表示を確認してください。</p>
        </div>
        <?php
    }
}
register_activation_hook(__FILE__,array('Tsurikue_Biota_Search','activate'));
Tsurikue_Biota_Search::boot();
