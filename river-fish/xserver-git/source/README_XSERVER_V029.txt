つりくえ！日本の河川図鑑 Xserver v0.29（SEO試験公開）

【内容】
v0.28検索ツールとJSONデータを保持したまま、魚名記録が一定量ある273の「資料上の河川名グループ」について、静的HTMLページを追加しました。
これは273の物理的な河川が同定済みという意味ではありません。

【設置手順】
1. 既存の public_html/river-fish-atlas/ を念のためバックアップ。
2. 本ZIPを解凍し、river-fish-atlas フォルダを public_html/ に上書き・統合アップロード。
   ※WordPressの public_html 全体を削除・置換しないこと。
3. https://tsurikue.com/river-fish-atlas/index.html で既存検索を確認。
4. https://tsurikue.com/river-fish-atlas/river/ で静的HTMLの一覧を確認。
5. https://tsurikue.com/river-fish-atlas/river/rn_09ffa2b6b65b7ddd81cbb6ed/ で太田川の表示を確認。
6. https://tsurikue.com/river-fish-atlas/sitemap.xml でXML表示を確認。
7. Search Consoleで /river-fish-atlas/sitemap.xml を追加送信する（送信は自動では行われません）。

【今回いじっていないもの】
- data/ 以下のJSON・CSV等すべて。元の情報源と魚名は変更していません。
- 現在のWordPress本文／記事URL／WordPressのSEOプラグイン設定。
- v0.28の検索プログラム本体。末尾に資料一覧リンクを1つ追加しただけ。
- 元index.htmlのnoindex。WordPress記事との重複を避けるため現状維持。

【公開の範囲】
- 出典URL付きの過去の魚名ラベルが10以上ある historical_national_river_survey のみ対象。
- 公式資料の「川名だけ」・「水系名だけ」・暫定同名候補・eDNA専用グループは今回の索引公開から除外。
- いずれも固有の物理河川であると確定した記録ではなく、資料名・水系名で区分した研究用グループ。
- 都道府県と河川本体が確定していない資料があるため、詳細ページでは所在地を断言しません。
- 公開資料中の魚名は現在の生息や釣れることを保証しません。

【Googleへの注意】
サイトマップ送信や静的HTML化はクロール・順位を保証しません。
Googleのインデックス登録後、Search Consoleのページ別登録・表示回数・検索流入で検証してください。
ルート（https://tsurikue.com/robots.txt）に /river-fish-atlas/ のクロール禁止がないか確認してください。

【URLと拡張】
・一覧： /river-fish-atlas/river/
・個別： /river-fish-atlas/river/<資料グループID>/
・検索ツール： /river-fish-atlas/index.html
・サイトマップ： /river-fish-atlas/sitemap.xml
URLは同名河川を誤統合しないため stable ID です。漢字の川名はタイトル・見出し・本文に表示。
新しい調査資料を取り込んだあとはページとサイトマップも同時に再生成する必要があります。

【重要】
本ZIPをサーバーへアップロードした事実はありません。設置・Search Consoleへの送信は未実施。
