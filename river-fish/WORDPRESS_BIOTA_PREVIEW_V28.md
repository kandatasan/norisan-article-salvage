# 全国生物×水系検索・WordPress導入候補 v0.1.0

2026-10-18。**GitHub Actionsの隔離環境でZIPを作成・検証。WordPress本番への自動インストールなし。**

## 構成

- プラグイン：tsurikue-biota-search。既存のtsurikue-river-searchと名前空間・DBテーブル・ショートコードを完全分離。
- 設置ショートコード：[tsurikue_biota_search]
- ハード：includes/class-tbs-rest.php。GET専用REST、1ページ最大20件。水系・年度重複を集約して表示。SQL文字列はプレースホルダー。
- ソフト：frontend/view.php、app.js、style.css。SWELL干渉防止のShadow DOM。分類チェックはデータセットのcatalogから自動生成。
- 取込：admin権限+nonce、500行ごとの再開可能な手動インポート、CSV元ハッシュとグループ別件数を検証後に世代切り替え、旧版への復元。
- 専用DBのみを編集し、WordPress記事・既存河川検索プラグインは変更しない。

## 取込データ

- 魚類18,814件、底生動物74,949件、鳥類44,093件、植物270,180件。合計**408,036掲載記録**。
- 国土交通省「河川水辺の国勢調査」（個別ZIP出典を加工して作成） https://www.nilim.go.jp/lab/fbg/ksnkankyo/dl_00_index.html
- 利用ルール https://www.nilim.go.jp/lab/fbg/ksnkankyo/Mokj_chui.htm
- 生物の実際の種数、現在の生息、個別河川・都道府県の生息記録ではない。調査地点・希少種所在地は保存しない。
- 水生昆虫の単独チェックは分類照合未審査につき保留。

## オフラインZIP生成

確認済みv2.7のSQLiteとchecksum付きmanifestを準備して以下を実行：

    python river-fish/build_wp_biota_plugin_v28.py --db /tmp/biota-snapshot-v27.sqlite --manifest /tmp/biota-snapshot-v27.json --out /tmp/biota-wp-build --zip /tmp/tsurikue-biota-search.zip

## 公開前の必須確認

1. GitHub ActionsでPHP・JS構文、ZIP中のSHA照合、実データ408,036行、隔離WordPress/MySQLでの取込・REST・ショートコードを検査。
2. WordPress本番の事前バックアップ、Webホストの容量/CPU/MySQL性能/CSVアクセス制限を確認する。Apacheのdata/.htaccessは付属するが、**Nginx等は別途CSVとmanifestへの外部アクセスを拒否する設定が必要**。
3. iPhoneの実機表示、SWELL干渉、アクセス集中時の性能、権利・出典の表示、公開ページのURL/SEOを最終確認する。
4. **本PRはWordPress本番にも旧プラグインにもデータを送信しない。** 人間が承認するまでZIPは研究用成果物。

## 2026-10-18 公開前QAの追加（研究用 v2.9）

- `biota/audit_aquatic_insect_names_v29.py` は、SHA確認済みの2025年公式分類表と底生動物74,949件の**掲載名の完全一致**だけを比較する。結果は区分別の集計レポートであり、特定個体の同定や水生昆虫の確定分類ではない。
- 「昆虫綱一致候補」「非昆虫」「昆虫と非昆虫の同名衝突」「分類欄不足・不整合」「底生動物以外の分類表にのみ一致」「一致なし」を相互排他的に数える。和名の正規化による類推や分類コードの自動付与をしない。
- 集計結果は `aquatic-insect-name-screening-v29` Actions artifact のJSONに保存。本番のWordPressプラグインZIPには含めない。判定できない名前・同名の衝突を処理するまで**水生昆虫専用チェックは無効**。
- 水系カードの詳細へ進む際、調査年度と生物名の絞り込み条件を保持する。静的回帰テストを追加。
- 公開前の実機作業として、iPhoneのSafariで三検索方向・検索結果なし・ページ送り・画面回転・SWELL干渉・リンク表示を確認する。GitHubのCLI/隔離WPテストは実機確認の代替ではない。
- **本番WordPressへの自動導入・データ送信なし。**
