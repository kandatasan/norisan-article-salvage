# UX中古車相場ツール：共通埋め込みと公開判定

## システム構成
- Xserverに共通の静的HTML `index.html` と価格JSON `data/reference_price_bands.json` を置く。MySQL・PHP・WordPress DBは不要。
- WordPressの記事は同じURLを iframe で表示する。記事ごとの初期選択はクエリパラメータ `model` / `grade` / `year` / `mileage` で変更。
- JSはユーザー入力から計算可能な価格を検索し、一般中古車とCPOを2段で表示。生データは公開せず、掲載価格の小規模な集計結果のみJSONで保持。
- **相場ツールは広告非搭載。** ガリバー等のアフィリエイトボタンはWordPress記事本文に個別配置し、ツールのHTML・JSONへは含めない。

## WordPressのカスタムHTMLブロック例（本番公開後のみ）
```html
<iframe
  title="レクサスUXの中古車相場（一般中古車とCPO）"
  src="https://tsurikue.com/ux-price-checker/?model=250h&amp;grade=c&amp;year=2021"
  width="100%" height="620" loading="lazy"
  referrerpolicy="strict-origin-when-cross-origin"
  style="display:block;width:100%;max-width:100%;height:620px;border:0;border-radius:12px;"
></iframe>
```

## 配置を優先する既存記事候補（本文は未変更）
1. [UX中古車の選び方](https://tsurikue.com/lexus-ux-used/)：購入比較記事なので最優先。
2. [UX250h中古 vs UX300h新車](https://tsurikue.com/lexus-ux250h-used-vs-ux300h/)：価格を比較する箇所に配置。
3. [UXはひどい？](https://tsurikue.com/ux-koukai/)：主役は所有レビューなので、設置はスクロール・CTAの重複を監査してから判断。

## Xserver デプロイ
- `.github/workflows/ux-price-xserver-ci-preview.yml` はPRで検証のみ、mainで専用ディレクトリ `$HOME/tsurikue.com/public_html/ux-price-checker-ci-preview/` だけへ送る。
- プレビューURL：https://tsurikue.com/ux-price-checker-ci-preview/index.html
- WordPress・河川図鑑・テーマには一切触れず、`--delete`を使わない。
- `publication_reviewed=false`のためXserverで見ても価格は非表示。ローカルの`localhost/?preview=1`だけ価格確認可能。
- **本番用`/ux-price-checker/`への自動公開は未実装**。品質監査後に別PRで安全な公開・バックアップ・復旧手順を追加する。
- 公開するときは、価格データの市場偏り・網羅性・集計日・出典を必ず監査する。記事側の別設置広告の転送先・成果条件はその記事の公開時に確認する。

## 未完了の品質要件
- 22種類の集計候補があるが年式・グレード別では同じ個票の重複集計もあり、4項目の多くの組み合わせは集計中。
- 過去13件と追加27件の重複再確認、CPOの複数条件の網羅率改善。
- 実スマホで埋め込みの高さを確認。別設置アフィリエイトは記事側で独立監査。
- 本番公開前にWordPress対象記事のpost ID／slug／statusと既存本文の位置を一意に特定する。

## スマホ表示の監査（2026-11-09）
- 広告付き版では860px必要だったが、広告を除去した新しいツールは320〜600px幅で約544〜582px。
- WordPress埋め込みの推奨高さを**620px**へ変更。実端末Safariによる最終検証は別途必要。
- ツール内部にアフィリエイトコードを置かず、記事のPRブロックとは独立した更新・確認を行う。
- **価格データの本番公開ゲートは未許可のまま**。Xserver隔離プレビューと記事公開を混同しない。

## v0.15 — 記事への共通設置（2026-11-10）
- カラーなし。入力はグレード・年式・走行距離の3項目。
- 一般中古車・CPOを常時2行比較。両者を混ぜず、少数の掲載例に基づく参考帯。
- 正確な条件の集計がない場合、同車種の選択年を含む最大5年間の混合集計を**注意書き付き**で表示することがある。それ以外は「集計中」。
- SWELLブログパーツID4505を再作成・上書きしない。記事へのショートコードの個別追加もこの更新では行わない。

## v0.18（2026-11-11）全グレードの選択肢と混在価格を撤去
- UX200 / UX250h / UX300h / UX300e の**全グレード**を選択候補から撤去。選択できるのは個別グレードだけ。URLに旧 `grade=all` が付いていても既定の UX250h version C に戻す。
- 旧い全グレード混在コホート17件を公開データから撤去し、`research/ux_grade_sampling_20261111.json` で研究用に保管。個別グレードの推定に流用しない。
- 実車掲載情報で 2020年UX250h version C を追加：一般中古車7件（支払総額280〜340万円／中央値約316万円）・LEXUS CPO6件（310〜350万円／中央値約342万円）。2026-11-11調査の少数例で全国相場の代表値ではない。
- 公開するグレード別の集計は合計9条件（一般6／CPO3）。幅広い年式・各グレード・走行距離帯の標本が足りない条件は「集計中」。標準仕様の実データはさらに調査が必要。
- `tests/test_search.js` に「全グレード表示なし」「混在価格の流用なし」「version C・一般/CPOの条件別中央値」の回帰テストを追加。
- SWELLブログパーツID 4505および購入導線4506のWordPress本文には触れない。Xserverの共通ツールのHTMLとJSONのみを更新する。
