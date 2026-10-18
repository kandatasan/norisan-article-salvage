<?php
if (!defined('ABSPATH')) { exit; }
/** Public read-only MySQL-backed search over active fully verified generation. */
final class TBS_REST {
    private const REGIONS = array(
        'hokkaido','tohoku','kanto','hokuriku','chubu','kinki',
        'chugoku','shikoku','kyushu'
    );
    private const DIRECTIONS = array(
        'region_explore','watershed_to_organism','organism_to_watershed'
    );
    public static function ready() {return TBS_Data::active()!==null;}
    public static function routes() {
        register_rest_route('tsurikue-biota/v1','/catalog',array(
            'methods'=>WP_REST_Server::READABLE,
            'callback'=>array(__CLASS__,'catalog'),
            'permission_callback'=>'__return_true'
        ));
        register_rest_route('tsurikue-biota/v1','/search',array(
            'methods'=>WP_REST_Server::READABLE,
            'callback'=>array(__CLASS__,'search'),
            'permission_callback'=>'__return_true'
        ));
    }
    private static function not_ready() {
        return new WP_Error('tsb_not_ready',
            '全国生物の調査記録は取込準備中です。',
            array('status'=>503));
    }
    public static function catalog() {
        $active=TBS_Data::active();
        if (!$active) {return self::not_ready();}
        return rest_ensure_response(array(
            'contract_version'=>1,
            'groups'=>$active['groups'],
            'unavailable_groups'=>array(
                'aquatic_insects'=>'底生動物からの独立した厳密な分類照合が未完了'
            ),
            'data_rows'=>array_sum($active['counts']),
            'version'=>$active['version'],
            'geographic_scope'=>'regional_watershed_year_only',
            'wordpress_posts_modified'=>false,
            'notice'=>'国土交通省河川水辺の国勢調査を加工して作成。過去の水系×調査年度×掲載名であり、現在の生息・個別の支流や県での確認ではありません。'
        ));
    }
    private static function value($req,$key) {
        $value=$req->get_param($key);
        if ($value===null || $value==='') {return '';}
        if (!is_string($value) || strlen($value)>350) {
            throw new InvalidArgumentException('検索文字列が長すぎるか不正です。');
        }
        $clean=trim(sanitize_text_field($value));
        $len=function_exists('mb_strlen')?mb_strlen($clean,'UTF-8'):strlen($clean);
        if ($len>100 || preg_match('/[\x00-\x1f\x7f]/u',$clean)) {
            throw new InvalidArgumentException('検索に使用できない文字です。');
        }
        return $clean;
    }
    private static function parse($request,$active) {
        $direction=self::value($request,'direction');
        if (!in_array($direction,self::DIRECTIONS,true)) {
            throw new InvalidArgumentException('検索方向が不正です。');
        }
        $groups=$request->get_param('group');
        if (is_string($groups)) {$groups=array($groups);}
        if (!is_array($groups) || !$groups || count($groups)>count($active['groups'])) {
            throw new InvalidArgumentException('生物分類を1つ以上選択してください。');
        }
        $valid=array_column($active['groups'],'id');
        foreach ($groups as $g) {
            if (!is_string($g) || !in_array($g,$valid,true)) {
                throw new InvalidArgumentException('未検証の生物分類が指定されています。');
            }
        }
        if (count(array_unique($groups))!==count($groups)) {
            throw new InvalidArgumentException('生物分類が重複しています。');
        }
        $region=self::value($request,'region');
        $watershed=self::value($request,'watershed');
        $organism=self::value($request,'organism');
        $year=self::value($request,'year');
        $match=self::value($request,'watershed_match');
        if ($match==='') {$match='contains';}
        if (($region!=='' && !in_array($region,self::REGIONS,true))
            || !in_array($match,array('contains','exact'),true)
            || ($year!=='' && !preg_match('/^(19|20)[0-9]{2}$/D',$year))) {
            throw new InvalidArgumentException('地方・調査年度・水系検索条件が不正です。');
        }
        if (($direction==='region_explore' && $region==='')
            || ($direction==='watershed_to_organism' && $watershed==='')
            || ($direction==='organism_to_watershed' && $organism==='')) {
            throw new InvalidArgumentException('検索方向に必要な項目を入力してください。');
        }
        $page=$request->get_param('page');
        $per=$request->get_param('per_page');
        $page=($page===null)?1:filter_var($page,FILTER_VALIDATE_INT);
        $per=($per===null)?20:filter_var($per,FILTER_VALIDATE_INT);
        if ($page===false || $per===false || $page<1 || $page>2000 || $per<1 || $per>20) {
            throw new InvalidArgumentException('ページ指定が不正です。');
        }
        return compact('direction','groups','region','watershed','organism','year','match','page','per');
    }
    public static function search($request) {
        global $wpdb;
        $active=TBS_Data::active();
        if (!$active) {return self::not_ready();}
        try {
            $p=self::parse($request,$active);
        } catch (InvalidArgumentException $e) {
            return new WP_Error('tsb_bad_input',$e->getMessage(),array('status'=>400));
        }
        $table=Tsurikue_Biota_Search::table();
        $placeholders=implode(',',array_fill(0,count($p['groups']),'%s'));
        $where=array('generation=%d',"group_id IN ({$placeholders})");
        $args=array_merge(array((int)$active['generation']),$p['groups']);
        if ($p['region']!=='') {$where[]='region_code=%s';$args[]=$p['region'];}
        if ($p['watershed']!=='') {
            $where[]=($p['match']==='exact'?'watershed_name=%s':'watershed_name LIKE %s');
            $args[]=($p['match']==='exact'?$p['watershed']:'%'.$wpdb->esc_like($p['watershed']).'%');
        }
        if ($p['organism']!=='') {
            $where[]='recorded_name LIKE %s';
            $args[]='%'.$wpdb->esc_like($p['organism']).'%';
        }
        if ($p['year']!=='') {$where[]='survey_year=%s';$args[]=$p['year'];}
        $predicate=implode(' AND ',$where);
        $src="{$table} WHERE {$predicate}";
        if ($p['direction']==='region_explore') {
            $sub="SELECT region_code,watershed_name FROM {$src} GROUP BY region_code,watershed_name";
            $sql="SELECT region_code,watershed_name,COUNT(*) AS historical_records, MIN(survey_year) AS first_year,MAX(survey_year) AS last_year FROM {$src} GROUP BY region_code,watershed_name ORDER BY region_code,watershed_name LIMIT %d OFFSET %d";
        } else {
            $sub="SELECT group_id,region_code,watershed_name,recorded_name FROM {$src} GROUP BY group_id,region_code,watershed_name,recorded_name";
            $sql="SELECT group_id AS survey_group,region_code,watershed_name,recorded_name, COUNT(*) AS historical_records, GROUP_CONCAT(DISTINCT survey_year ORDER BY survey_year SEPARATOR ',') AS survey_years, MIN(source_url) AS source_url,COUNT(DISTINCT source_url) AS source_count FROM {$src} GROUP BY group_id,region_code,watershed_name,recorded_name ORDER BY region_code,watershed_name,group_id,recorded_name LIMIT %d OFFSET %d";
        }
        $total=(int)$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM ({$sub}) AS grouped_names",$args));
        if ($wpdb->last_error) {
            return new WP_Error('tsb_database_error','検索DBにアクセスできません。',array('status'=>503));
        }
        $offset=($p['page']-1)*$p['per'];
        $rows=$wpdb->get_results($wpdb->prepare($sql,array_merge($args,array($p['per'],$offset))),ARRAY_A);
        if ($rows===null || $wpdb->last_error) {
            return new WP_Error('tsb_database_error','検索結果を取得できません。',array('status'=>503));
        }
        foreach ($rows as &$r) {
            if ($p['direction']==='region_explore') {
                $group_sql="SELECT group_id,COUNT(DISTINCT recorded_name) AS count_labels FROM {$table} WHERE generation=%d AND region_code=%s AND watershed_name=%s AND group_id IN ({$placeholders})";
                $params=array_merge(array((int)$active['generation'],$r['region_code'],$r['watershed_name']),$p['groups']);
                $group_sql.=' GROUP BY group_id';
                $counts=$wpdb->get_results($wpdb->prepare($group_sql,$params),ARRAY_A);
                if ($counts===null || $wpdb->last_error) {
                    return new WP_Error('tsb_database_error','生物分類の件数を取得できません。',array('status'=>503));
                }
                $r['group_label_counts']=array();
                foreach ($counts as $c) {$r['group_label_counts'][$c['group_id']]=(int)$c['count_labels'];}
            } else {
                $r['survey_years']=$r['survey_years']?explode(',',$r['survey_years']):array();
                $r['survey_year_count']=count($r['survey_years']);
                $r['source_count']=(int)$r['source_count'];
            }
            $r['historical_records']=(int)$r['historical_records'];
            $r['geographic_scope']='regional_watershed_year_only';
            $r['verified_prefecture']=null;
            $r['verified_individual_river']=null;
            $r['approved_taxon_code']=null;
        }
        unset($r);
        return rest_ensure_response(array(
            'direction'=>$p['direction'],
            'result_type'=>$p['direction']==='region_explore'?'watershed_summary':'distinct_source_labels_by_watershed',
            'selected_groups'=>$p['groups'],'total'=>$total,'page'=>$p['page'],'per_page'=>$p['per'],
            'results'=>$rows,
            'historical_observations_are_not_distinct_species'=>true,
            'individual_river_verified'=>false,'current_distribution_verified'=>false,
            'taxonomy_identity_verified'=>false,
            'notice'=>'出典：国土交通省河川水辺の国勢調査（元URL）を加工。水系×年度の過去の掲載名であり、現在の生息・個別支流の確認ではありません。'
        ));
    }
}
