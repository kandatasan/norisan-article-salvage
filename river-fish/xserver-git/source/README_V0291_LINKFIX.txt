つりくえ！河川図鑑 v0.29.1 — リンク修正版

2026-10-26

修正内容
- 河川一覧の「河川検索ツールで探す」が旧URLに飛ぶ問題を修正
- 河川一覧・273河川資料詳細の内部リンクを相対URL化
- 検索ツールのJSON取得先を相対パス化（テスト公開と正式公開に共通対応）
- タイトル、掲載魚名、出典URL、元のデータファイル、sitemap.xml、canonicalは維持

【テスト公開】
サーバーの tsurikue.com/public_html/ に「river-fish-atlas-v0291」という名前で
本ZIP内の river-fish-atlas フォルダを配置します。
https://tsurikue.com/river-fish-atlas-v0291/river/
から「河川検索ツールで探す」を押すと、
https://tsurikue.com/river-fish-atlas-v0291/index.html
へ移動します。内部河川ページへのリンクも同じ v0291 内で動きます。

【正式公開】
表示と検索動作を確認してから、既存の公開フォルダ river-fish-atlas の名前を
バックアップ用に変更し、この v0291 フォルダを river-fish-atlas に変更します。
旧公開フォルダやWordPressの public_html 全体を削除・上書きしないでください。
Search Consoleに送るサイトマップは正式公開後の /river-fish-atlas/sitemap.xml です。

ご注意：テスト用URLはGoogle登録のためではなく動作確認用です。
旧WordPress本文や公開中の検索ツールを直接更新したものではありません。
