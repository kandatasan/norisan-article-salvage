# UX中古車相場ツール：共通埋め込みと公開判定

## システム構成
- Xserverに共通の静的HTML `index.html` と価格JSON `data/reference_price_bands.json` を置く。MySQL・PHP・WordPress DBは不要。
- WordPressの記事は同じURLを iframe で表示する。記事ごとの初期選択はクエリパラメータ `model` / `grade` / `year` / `mileage` / `color` で変更。
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
- 現在グレード×年式別5コホートしかなく、ほとんどの検索条件は集計中。
- 過去13件と追加27件の重複再確認、CPOの複数条件の網羅率改善。
- 実スマホで埋め込みの高さを確認。別設置アフィリエイトは記事側で独立監査。
- 本番公開前にWordPress対象記事のpost ID／slug／statusと既存本文の位置を一意に特定する。

## スマホ表示の監査（2026-11-09）
- 広告付き版では860px必要だったが、広告を除去した新しいツールは320〜600px幅で約544〜582px。
- WordPress埋め込みの推奨高さを**620px**へ変更。実端末Safariによる最終検証は別途必要。
- ツール内部にアフィリエイトコードを置かず、記事のPRブロックとは独立した更新・確認を行う。
- **価格データの本番公開ゲートは未許可のまま**。Xserver隔離プレビューと記事公開を混同しない。
