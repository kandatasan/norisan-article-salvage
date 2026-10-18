# 全国河川検索 v0.2.0 — ハード／ソフト分離・スマホ表示修正

## なぜ修正したか

つりくえ！SWELLのスマホ画面で、既存ショートコードの**見出しの文字色や背景・フォーム列・検索ボタン**がSWELL側のグローバル装飾に干渉され、検索欄が縦長・文字が1文字ずつ改行され、入力しにくい状態になっていた。

## 変更の境界

| パーツ | 担当 | 今回の変更 |
| --- | --- | --- |
| ハード | `tsurikue-river-search.php`, `includes/class-tsr-search.php`, `includes/class-tsr-import.php`, `data/` | **検索DB・API・取込仕様は維持**。本体から画面HTMLだけを撤去。 |
| ソフト | `frontend/view.php`, `frontend/style.css`, `frontend/app.js` | 独立ファイル化。UIのデザイン変更はこの3ファイルだけで可能。 |

技術的には**1つのWordPressプラグイン内の2層構成**。プラグインを2本に分割して旧DBを移行する必要はない。

## SWELL対策

- PHPショートコードは、表示用の `<template>` を読み込むだけ。
- JavaScriptが**Shadow DOM**を作成し、HTMLと独立CSSを内部に配置する。
- SWELL等の親ページにある見出し・フォーム・ボタンの装飾は基本的にShadow DOMの内部へ浸透しない。
- スマホでは**全要素1列表示**が初期値。タブは短い文言、検索欄とボタンは全幅。十分に横幅があるコンテナのみ2列フォーム。
- CSSは `:host` とShadow DOM内部だけ。既存のSWELLページや他の記事には影響させない。
- バージョンを0.1.0→0.2.0に更新し、キャッシュされている古いJSの使い回しを回避する。

## 更新時の重要事項

- **DB形式は一切変更しない。** `TSR_DATA_VERSION` は引き続き `v1.5-20261018`。
- 既に取込完了なら**55,712行を再インポートする必要はない**。ショートコードも `[tsurikue_river_search]` のまま。
- WordPress管理画面からZIPをアップロードするとき、**同じプラグインを置換**すること。別のプラグインとして同時に有効化しない。
- WP記事、固定ページ、投稿内容、スラッグ、メディアには一切変更なし。テーマ、WordPressの管理DBにも自動修正なし。
- **サイトの実物を確認できたわけではなく**、スクリーンショットに対する防御的修正。iPhoneの実機表示はアップデート後に最終確認する。
- 一般公開の判断には、出典と商用再利用条件の別監査が必要。

## 検証手順

```bash
python -m unittest discover -s river-fish -p 'test_wp_plugin_v16.py' -v
python river-fish/build_wp_plugin_v16.py --out /tmp/wp-v02 --zip /tmp/tsurikue-river-search-v02.zip
```

GitHub Actions `.github/workflows/river-fish-wp-plugin-v16.yml` は、更新後も実際に隔離WordPress＋MySQLへ**全55,712件を取込**し、API検索と再取込の旧データ保持を検証する。

## 今後の開発

画面やデザインを変更したいときは、ソフト側の `frontend/view.php`（文章・部品）、`frontend/style.css`（デザイン）、`frontend/app.js`（タブ・フォームの挙動）だけ変更。バックエンドのCSV取込や3つの検索テーブルには触れない。独立機能の要望が増えるまでは、プラグイン自体を2本に分けず、この構成が更新しやすく安全。
