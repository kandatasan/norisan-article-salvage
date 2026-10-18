# つりくえ！全国生物×水系検索 v2.0 — 3方向の研究用ブラウザ

実装日：2026-10-18。**GitHub上の研究用プレビュー。WordPress本番には未反映・未公開。**

## v2.0でできること

- **生物名 → 記録が載った水系**：アユ／カワゲラなどの当時の記録表記から、地域×水系×調査年度の組み合わせを一覧。
- **水系 → 記録された生物名**：太田川などの水系名から過去の調査掲載名を一覧。
- **地方から探す**：全国9地方のうち、公式河川版で取込済みの地方を選択。魚類・底生動物別、年度別にも絞れる。
- 25件ページ送り、地域フィルター、部分一致検索、国交省原資料URL。スマホは1列フォーム。
- 全国の全件データはブラウザに渡さず、ローカルAPIでSQLiteを直接検索。外部JSライブラリ不要。
- UIは three_axis_frontend_v20.html、検索ハードは three_axis_search_v20.py。WordPress既存プラグインや本文は改修しない。

**重要：個体数・採取地点・釣りができる場所ではなく、国交省の過去の地方×水系×年度×名称の掲載記録を探すもの。** 未掲載は「不在」ではなく「未収録または未確認」。

## 研究SQLiteの準備

本ツールは別途 v1.9の公式9地方データを検証して生成した研究用DB（両テーブル付き）を読む。直接ダウンロードや再集計を行わず、データ取得は .github/workflows/river-benthic-v19.yml に分離。

- watershed_year_fish_evidence: 全国9地方、過去の水系年度別魚類名（18,814組み合わせ）。
- watershed_year_benthic_evidence: 全国9地方、過去の水系年度別底生動物名。集計件数はActions実測値に従う。
- 2025年分類名簿37,648行は**独立**。v2.0の調査記録検索では名称だけから分類コードに結び付けない。

研究用DBの生成例（9地方の底生動物stageと既存魚類ソースが用意されていること）：

    python river-fish/biota/build_biota_with_benthic_v19.py --build --db /tmp/biota-v19.sqlite

検索CLI：

    python river-fish/biota/three_axis_search_v20.py --db /tmp/biota-v19.sqlite --direction organism_to_watershed --organism アユ --region chugoku
    python river-fish/biota/three_axis_search_v20.py --db /tmp/biota-v19.sqlite --direction watershed_to_organism --watershed 太田川

ローカルUI：

    python river-fish/biota/three_axis_search_v20.py --db /tmp/biota-v19.sqlite --serve

ブラウザ http://127.0.0.1:8765/ で確認（**localhost限定**）。インターネット公開サーバーとして使わない。

## 出典・誤帰属防止

- 出典：国土交通省 河川水辺の国勢調査 河川版・魚類／底生動物「確認種一覧」。https://www.nilim.go.jp/lab/fbg/ksnkankyo/dl_00_index.html
- 検索の地方・水系・年度・生物名・原本リンクは公式調査の文脈に限定。
- verified_individual_river / verified_prefecture / approved_2025_taxon_code はすべて null。
- 同名水系でも別地方の記録を混同しない。県・市町村・支流の生息への推定なし。
- 魚類と底生動物の分類を混ぜず、旧「魚介類」混合区分は追加収録しない。
- 詳細位置・希少種の確認地点・緯度経度は表示しない。
- SQLiteは mode=ro + PRAGMA query_only=ON。MySQL・WP REST・公開サイト書込みなし。
- APIの調査名はSQLプレースホルダー。フロントエンドは textContent による安全なDOM出力、原本リンクは国交省のHTTPSに限定。

## テスト・完了判定

    python -m unittest discover -s river-fish/biota -p 'test_three_axis_v20.py' -v

fixture tests: 3方向、魚類と底生動物の分離、出典、調査年度、ページ送り、SQL wildcard/注入、異常値、API、未作成DBの保護、read-only byte比較。GitHub Actionsで検査。

さらに .github/workflows/river-benthic-v19.yml の実データビルド成功時に、v2.0の3方向検索スモークを行う。**Actions成功・実データ検証までは一般公開やWordPress導入済みとは報告しない。**

## 次工程

1. 公式確認種一覧の植物・鳥類・両爬哺・陸上昆虫について、地方×資料区分ごとにURL・ZIP原本ハッシュ・Excel列を監査してから独立取り込み。
2. 調査種名と2025公式分類名の厳密な照合は、同定と変更履歴を別審査にする。名前一致だけでは確定しない。
3. WordPress本番導入は既存河川プラグインを基準に、出典・権利・DB容量・API・スマホQA・バックアップ確認後に別PRで実施。
4. 個別の川の魚・生物は該当河川の一次資料で直接確認されたものだけ承認。「未検証」を「不在」としない。
