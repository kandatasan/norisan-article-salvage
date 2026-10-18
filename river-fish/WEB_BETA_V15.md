# 全国河川図鑑・検索β版 v1.5（オフラインで開ける試作品）

**GitHubで検証するβ版。WordPress投稿・固定ページ・公開URLにはまだ反映していません。**

## 何ができる？

1. **全国河川コード**：国交省の10桁河川コード一覧35,449件から、河川名・水系名・コード番号で検索。**所在県はこの一覧だけでは確認できない**ので未掲載。複数の同名河川は別コードのまま保持。
2. **都道府県別の資料**：47都道府県の県・市町村の資料掲載行をまとめ、県名・川名・水系名・計画圏域名で検索。**1,449掲載行**。これは全県の全河川数ではない。同名行、PDF機械抽出未審査行も残す。
3. **水系別の魚類調査**：国交省・河川水辺の国勢調査から18,814件の地域×水系×調査年度×魚名の記録を検索。支流の魚・現在釣れる魚という表示は**絶対にしない**。

データは **ブラウザ内で検索し、ネット接続なしで動作**。HTML/CSS/JSだけ、WPの認証情報や外部API・広告タグなし。結果の公式出典はネット接続があれば開けます。

## 使い方（初回）

1. GitHub Actions の [Build offline nationwide river search beta v1.5](../../actions/workflows/river-fish-web-beta-v15.yml) を開く。
2. 成功した実行の **Artifacts / tsurikue-national-river-search-beta-v15** をダウンロード。
3. 取り出した `tsurikue-river-search-beta.zip` を展開。
4. 中の `tsurikue-river-beta/index.html` をブラウザで開く。別ファイルのJSデータを参照するので、フォルダを分割しない。

スマートフォンでも操作可能ですが、iOSでは「ファイル」アプリからHTMLを直接開いた場合のローカルJS制限がブラウザによって異なる可能性があります。PCブラウザでのオフライン確認を優先し、スマホ本番の表示はWordPressへの適切な設置前に実機で検証します。

## ビルド方法

Python 3.12+ だけでデータバンドル生成が可能。アプリ自体はサーバ不要。

```bash
python river-fish/build_river_beta_v15.py --out /tmp/tsurikue-river-beta --zip /tmp/tsurikue-river-search-beta.zip
python -m unittest discover -s river-fish -p 'test_river_beta_v15.py' -v
node --check river-fish/web-beta/app.js
node --check river-fish/web-beta/search-core.js
node river-fish/test_river_beta_search_v15.cjs /tmp/tsurikue-river-beta
```

`.github/workflows/river-fish-web-beta-v15.yml` で毎回同じ検証を行い、**オフライン配布用ZIPをGitHub Actions Artifactに添付**します（保持30日）。このworkflowは本番サイトを変更しません。

## 表示・権利・誤解防止

- 川ごとの生息魚を国交省の水系別データから付けない。混合カテゴリの過去の候補11,868件もUIに混ぜない。
- 県別掲載行は**資料の掲載事実**であり、全国河川コードとの同一性や川の全流路を証明しない。
- 全国河川コードの先頭2桁を実際の所在地都道府県と扱わない。
- 地方自治体の水系資料の掲載名は独立した河川の本数にカウントしない。
- 資料のPDF原本・地図・画像・GIS座標などは配布しない。旧W05地物の非商用データは使用しない。
- 国交省・県・自治体の出典URL、参考時点、処理済みデータであることを記載。商用サイトで公開する前に、各資料の再利用条件と元表との照合を別途監査。
- 管理者画面やWordPressのREST APIを使う処理は含まれない。

## 現状の限界と次工程

1. β版の**実機操作・スマホ表示・結果の読みやすさ**を確認し、表示の改善を行う。
2. 47都道府県の資料収録は広さだけの達成で、県内すべての小河川を網羅していない。データを継続して増やす。
3. 河川コードの同一性、所在県、支流の直接魚類記録は**正式な一次資料による追加照合後**に承認。
4. 検索画面の本番設置は別PR・別QAとし、WPの対象下書き・status・slug・post IDを確認してから。**公開はユーザーの明示的な許可があるまでしない**。

技術的な確認対象：`index.html`、`style.css`、`app.js`、`search-core.js`、`data.js`（生成ファイル）。ユーザー入力やデータ文字列は `textContent` で表示し、HTMLとして埋め込まない。公式HTTPS出典リンク以外を生成しない。
