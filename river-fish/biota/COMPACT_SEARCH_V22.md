# つりくえ！全国生物×水系図鑑 v2.2 — 集約表示・複数チェック・検索結果の暴発防止

## 状態・対象

2026-10-18、**研究用ローカル検索プレビュー**。正式公開サイト WordPress / tsurikue.com への書き込み・公開変更はしていない。

既存v1.9の出典付き調査記録を用いる。現在の実測基礎件数は魚類18,814（水系×年度×当時の掲載名）、底生動物74,949（水系×年度×当時の掲載名）、参考分類名簿37,648行。いずれも **確認された実生物種数ではない**。

## 実装した検索表示

- 「地方 → 水系一覧」：同じ水系に属する複数の過去の年度・名称を1件の**水系カード**にまとめる。魚類・底生動物の**掲載名の重複排除件数**を別々に表示。検索対象地方は国交省の9地方。県別実績や市町村には自動変換しない。
- 「水系 → 生物」：地方×水系×**調査資料上の名前**×魚類/底生動物の区分で集約。過去に掲載された調査年度を展開すると見られる。翌年度に同じ名が出ても表示を増やさない。
- 「生物 → 水系」：同じ魚/底生動物名を含む水系の掲載履歴を集約。ただし名前の一致は分類同定、希少種の現在分布の証明ではない。
- **チェックボックス**：魚類・底生動物をそれぞれON/OFF（片方だけも可能）。「水生昆虫だけ」は種分類を照合していないため無効化、鳥類は水系別調査記録を取り込む前なので無効化。底生動物には昆虫を含むことがあるため、未審査の独立分類として二重計上しない。
- **検索結果は集約後に20件/ページ**。水系サマリーカードをタップして当該地方のその水系だけを **完全一致条件** で再検索（例：「太田川」から「太田川支流」という別名称へ漏らさない）。
- ブラウザへ生物データ全件は送らず、必要なページの集約結果だけを返す。原資料へ出典リンク表示。スマホではフォームを縦積み。

## 実装／安全性

- ソフト: compact_frontend_v22.html（HTML/CSS/素のJS、外部ライブラリなし）
- ハード: compact_search_v22.py（v2.0の固定SQLソース定義を利用、v1.9研究SQLiteの**read-only**）
- テスト: test_compact_search_v22.py。GitHub Actions: river-biota-compact-v22.yml。
- 地方は9公式地域のenum。調査区分は魚類/底生動物のみ許可、チェックの未選択や重複はエラーにする。水系・名称はSQLプレースホルダー。部分検索の % _ \ はエスケープ。年度は西暦4桁。HTTPはGETのみ。APIは選択された調査区分の固定ソースを参照。
- 集約はSQLのGROUP BYで、**LIMIT前に全件のグループ化**を行う。年度配列はソートし、20件だけ返す。
- region×watershed一覧で数えるのは **異なる掲載名（literal label）** であり、現在の動物種・魚種や観測個体のカウントではない。
- 研究プレビューは127.0.0.1:8765のみ。noindex,nofollow。WordPressプラグインへの合流・本番ホスティングは別審査。
- 2025分類名簿との自動結合、支流・都道府県への生息誤帰属、位置/希少種の詳細地点保存、現在生息の判定なし。

## 利用

v1.9の検証済み研究SQLite生成後にローカルで起動する（公式源の9地方 staging が必要）：

    python river-fish/biota/compact_search_v22.py --db /tmp/national-biota-v19.sqlite --serve

画面 http://127.0.0.1:8765/

CLI例：

    python river-fish/biota/compact_search_v22.py --db /tmp/national-biota-v19.sqlite --direction region_explore --region chugoku
    python river-fish/biota/compact_search_v22.py --db /tmp/national-biota-v19.sqlite --direction watershed_to_organism --region chugoku --watershed 太田川 --watershed-match exact
    python river-fish/biota/compact_search_v22.py --db /tmp/national-biota-v19.sqlite --direction organism_to_watershed --organism アユ --group fish

QA：

    python -m unittest discover -s river-fish/biota -p 'test_compact_search_v22.py' -v

## 残りの主要工程

1. v2.1の63資料URL候補を原資料・カテゴリ・実行ファイルSHA・列スキーマで分類・検証し、鳥類等の水系×年度の根拠を取り込む（分割処理・出典保存）。
2. 水生昆虫だけの抽出は、承認された元資料の区分が直接取れる場合を除き、分類群の証拠・命名規則を別途作ってから有効化。
3. 生物名・水系名の別名、分類上の変更を審査し、単純なテキスト一致と承認済み同定を明確に分ける。
4. WordPress/MySQL/既存全国河川プラグイン統合。レコード数が膨らむのでDBインデックス、実機操作、SWELLテーマCSS干渉、リスト/詳細/SEO/著作・出典表示、権限/性能/テスト/ロールバックのQAを別PR。
5. 個別河川への生物情報を載せるのは、個別の水路・支流の一次資料で直接裏付け可能な場合に限る。
