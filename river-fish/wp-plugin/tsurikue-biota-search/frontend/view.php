<?php
if (!defined('ABSPATH')) {exit;}
?>
<div id="<?php echo esc_attr($id); ?>" data-tbs-mount="1" class="tbs-mount">
  <template data-tbs-view>
    <section class="tbs-app" aria-label="つりくえ！全国の生物と水系">
      <header class="tbs-hero">
        <div class="tbs-dots" aria-hidden="true"><span></span><span></span><span></span></div>
        <p class="tbs-kicker">つりくえ！ 全国生物×水系図鑑</p>
        <h2>川には、どんな生き物がいる？</h2>
        <p>魚や鳥、植物まで。全国の川の調査記録を、気になる場所や生き物の名前から探してみよう！</p>
      </header>
      <div class="tbs-tabs" role="group" aria-label="検索方法">
        <button type="button" data-direction="region_explore" aria-pressed="true">🗾 地域から探す</button>
        <button type="button" data-direction="watershed_to_organism" aria-pressed="false">🏞️ 川から探す</button>
        <button type="button" data-direction="organism_to_watershed" aria-pressed="false">🐟 生き物から探す</button>
      </div>
      <form data-tbs-form role="search">
        <div class="tbs-fields">
          <label>地方
            <select name="region">
              <option value="">地方を選択</option>
              <option value="hokkaido">北海道</option><option value="tohoku">東北</option>
              <option value="kanto">関東</option><option value="hokuriku">北陸</option>
              <option value="chubu">中部</option><option value="kinki">近畿</option>
              <option value="chugoku">中国</option><option value="shikoku">四国</option>
              <option value="kyushu">九州</option>
            </select>
          </label>
          <label>水系名（支流ではありません）
            <input name="watershed" maxlength="100" placeholder="例：太田川">
          </label>
          <label>生物名（当時の調査掲載名）
            <input name="organism" maxlength="100" placeholder="例：アユ・カワセミ">
          </label>
          <label>調査年度（任意）
            <input name="year" inputmode="numeric" maxlength="4" placeholder="例：2020">
          </label>
        </div>
        <fieldset>
          <legend>表示する生物を選ぶ</legend>
          <div data-tbs-groups class="tbs-checks"><span>検証済みデータを確認しています…</span></div>
          <div data-tbs-pending class="tbs-checks"></div>
        </fieldset>
        <button type="submit" class="tbs-submit">🔎 生き物を探してみる</button>
      </form>
      <section aria-live="polite" aria-label="検索結果">
        <h3>検索結果</h3>
        <p data-tbs-status role="status">データを確認しています…</p>
        <div data-tbs-results class="tbs-results"></div>
        <nav data-tbs-pager hidden class="tbs-pager" aria-label="ページ送り">
          <button type="button" data-tbs-prev>前へ</button><span data-tbs-page></span>
          <button type="button" data-tbs-next>次へ</button>
        </nav>
      </section>
      <p class="tbs-note">国土交通省「河川水辺の国勢調査」（原資料の各URL）を加工して作成。
      掲載名数は生物の種数ではありません。水系単位の過去の調査結果であり、
      特定の支流や都道府県での確認・現在の生息を示すものではありません。
      調査資料に載っていないことは、生息しない証明ではありません。</p>
    </section>
  </template>
  <noscript>生物×水系検索にはJavaScriptが必要です。</noscript>
</div>
