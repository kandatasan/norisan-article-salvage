<?php
/**
 * SOFT LAYER: HTML only. Backend / database / REST route are independent.
 *
 * Render an inert <template> and mount it under Shadow DOM from the UI script.
 * SWELL .post_content h2, .post_content form and button rules cannot cross
 * the shadow boundary. No WordPress posts or tables are touched here.
 */
if (!defined('ABSPATH')) { exit; }
?>
<div class="tsr-mount" id="<?php echo esc_attr($id); ?>" data-tsr-app="1">
  <template data-tsr-layout>
    <section class="tsr-app" aria-label="つりくえ！全国河川図鑑">
      <header class="tsr-heading">
        <p class="tsr-kicker">つりくえ！全国河川図鑑 <span class="tsr-beta">β</span></p>
        <h2>全国の川を探す</h2>
        <p class="tsr-intro">川名・都道府県の公式資料・魚類調査を検索できます。</p>
      </header>
      <div class="tsr-tabs" role="tablist" aria-label="検索する資料の種類">
        <button type="button" role="tab" aria-selected="true" class="tsr-selected" data-mode="codes">川名・コード</button>
        <button type="button" role="tab" aria-selected="false" data-mode="local" tabindex="-1">県の資料</button>
        <button type="button" role="tab" aria-selected="false" data-mode="fish" tabindex="-1">魚の調査</button>
      </div>
      <form class="tsr-form" role="search">
        <div class="tsr-controls">
          <label class="tsr-pref-wrap" hidden>
            <span>都道府県</span>
            <select name="prefecture"><option value="">すべての都道府県</option></select>
          </label>
          <label class="tsr-kind-wrap" hidden>
            <span>資料の区分</span>
            <select name="kind">
              <option value="">すべての種類</option>
              <option value="river">川の名前</option>
              <option value="watershed">水系の名前</option>
              <option value="planning_region">整備計画圏域</option>
            </select>
          </label>
          <label class="tsr-region-wrap" hidden>
            <span>調査した地域</span>
            <select name="region">
              <option value="">全国9地域</option>
              <option value="hokkaido">北海道</option><option value="tohoku">東北</option>
              <option value="kanto">関東</option><option value="hokuriku">北陸</option>
              <option value="chubu">中部</option><option value="kinki">近畿</option>
              <option value="chugoku">中国</option><option value="shikoku">四国</option>
              <option value="kyushu">九州</option>
            </select>
          </label>
          <label class="tsr-watershed-wrap" hidden>
            <span>水系名</span>
            <input name="watershed" type="search" maxlength="70" placeholder="例：太田川">
          </label>
          <label class="tsr-query-wrap">
            <span data-query-label>川名・水系名・河川コード</span>
            <input name="q" type="search" maxlength="70" placeholder="例：諸木川" autocomplete="off">
          </label>
        </div>
        <button class="tsr-submit" type="submit">川を探す <span aria-hidden="true">→</span></button>
      </form>
      <p class="tsr-scope" data-scope>国のコード表だけでは川の所在地を確定できません。</p>
      <section class="tsr-search-output" aria-label="検索結果">
        <p data-status class="tsr-status" role="status" aria-live="polite"></p>
        <div data-results class="tsr-results"></div>
        <nav class="tsr-pager" data-pager hidden aria-label="検索結果ページ">
          <button type="button" data-prev>前へ</button>
          <span data-page-info></span>
          <button type="button" data-next>次へ</button>
        </nav>
      </section>
      <p class="tsr-footnote">※ 県別資料は全河川の一覧ではありません。魚類調査は水系単位であり、特定の支流で釣れる魚を示すものではありません。各結果の出典をご確認ください。</p>
    </section>
  </template>
  <noscript>河川検索を利用するにはJavaScriptを有効にしてください。</noscript>
</div>
