# つりくえ！全国生物×水系DB v2.3 — データと検索ツールの契約分離

**実装日:** 2026-10-18。**WordPress本番未反映、研究用データ専用。**

## 目的

既存v2.2は魚類/底生動物をPythonプログラムとHTMLで固定していた。新しい鳥類・植物などの水系年度調査が**別途正式に確認**された際、検索エンジンと表示画面を改修せずに、新しいデータセットだけ更新して切り替えられるようにした。

呼び方は「データ側」と「検索ツール側」で整理する。画面（HTML/JS）と検索APIは表示・検索担当であり、国交省原資料ZIPやデータインポーターとは独立。

## v2.3の役割

| 役割 | ソース |
|---|---|
| データの正式な収録設定 | dataset_sources_v23.json |
| データ生成・検査 | build_dataset_v23.py |
| 独立配布するデータ本体 | biota-snapshot-v23.sqlite （Actionsの成果物、非公開研究用）|
| データの整合性と生物分類カタログ | biota-snapshot-v23.json（SHA-256とスキーマ版） |
| 検索エンジン | engine_v23.py |
| 検索画面 | engine_frontend_v23.html |
| 自動テスト | test_dataset_engine_v23.py |

### データの共通契約

- SQLite: dataset_contract（固定版と位置情報の安全境界）、available_groups（現在検索可能な分類名・説明）、survey_evidence（group_id・地方・水系・調査年度・元の生物掲載名・公式出典・任意の出典ハッシュ）。
- 個別支流・県の生息確認、2025分類コードとの未審査同定はすべて禁止（NULLチェック）。公開版への書き込みゼロ。
- 現在の検証済み入力は魚類18,814行と底生動物74,949行。2025年生物分類リスト37,648行は**参考リストのまま別データ**であり、水系観測データへ統合しない。
- SQLite本体と同時にmanifest JSONを生成し、DB SHA-256/グループ別件数/生物区分/データ契約版を固定する。
- ツール側は起動時にDBのSHA-256、整合性、全件数、安全条件を確認する。形式の合わないデータは受け付けない。
- 旧データを更新せず新しいスナップショットファイルを生成する。出力先に同名ファイルがあれば停止。**上書きや本番サイトへの自動差し替えはまだしない。**

### 新しいグループをデータだけで追加する条件

- 研究資料の監査済み確認種データを、定義済みのCSV列（region, watershed, survey_year, recorded_name, source_url, source_sha256）へ加工する。
- dataset_sources_v23.jsonのsource_groupsに**厳格に照合した原カテゴリ・ファイル名・SHA-256・予想行数**を記載、kindは verified_csv とする。
- 起動時/ビルド時に公式の9地方、年度、生物名、MLIT URL、ファイルchecksum、列を検査。
- 新しいSQLiteスナップショット＋manifestを生成すれば、検索エンジン/API/HTMLのコードを変えずに分類チェックと結果一覧が増える。
- 未審査の「水生昆虫だけ」「鳥類」は引き続き利用不可。**テストで追加する鳥類は架空の監査済みCSVを使った模擬試験であり、全国鳥類の取り込みを意味しない。**
- 「底生動物→水生昆虫」に細分化するには正式に区分同定を承認する必要があり、現時点で自動分割しない。
- 新データを登録するときは保留区分(unavailable_separate_groups)から重複したidを取り除く。画面の選択項目は新manifestのカタログから自動で生成。

### 操作例

前提：v1.9の9地方底生動物を検証して結合済みの全国研究SQLiteがあること。

    python river-fish/biota/build_dataset_v23.py \
      --legacy-db /tmp/national-biota-v19.sqlite \
      --db /tmp/biota-snapshot-v23.sqlite \
      --manifest /tmp/biota-snapshot-v23.json

ローカル専用の検索エンジン（WordPress非連携）：

    python river-fish/biota/engine_v23.py \
      --db /tmp/biota-snapshot-v23.sqlite \
      --manifest /tmp/biota-snapshot-v23.json --serve

localhost 127.0.0.1:8765 の試作画面に /api/catalog と /api/compact を提供する。検索は両方とも読み取りのみ。

自動QA:

    python -m unittest discover -s river-fish/biota -p 'test_dataset_engine_v23.py' -v

## 検証

- v1.9からの移行時、原資料に基づく区分と調査文脈・URLを維持。
- 同一生物の年度重複を集約。地方と水系を保持し、個別支流には絶対結合しない。
- 安全性テスト：原データ/スナップショットの不変性、SHA改ざん、データ不足、未審査の生物区分、URLすり替え、SQL特殊文字、ページング、API入力制限。
- **肝心の回帰試験：** fixtureの「鳥類」（テストだけの仮データ）をCSVとデータ設定に追加するだけで、エンジン改修ゼロでチェック項目と検索結果を返せること。

## 本番導入前の残工程

- 実資料監査：鳥類/植物/その他の区分をZIPの正式リンク・SHA・Excel列・原カテゴリで審査してから新しいCSVに移す。
- データ配布と更新切り替え：現行スナップショット、前版バックアップ、整合性確認、ロールバック、同時アクセス、容量・性能の運用設計。
- WordPress環境でPHP/MySQL移行する場合、研究用PythonをそのままWPへ埋め込まず、同じデータ契約を維持して専用のサーバー側読み取りAPIに移植する。
- SWELLテーマへの干渉確認、セキュリティQA、画面実機確認、公開承認。**現在のWordPressプラグインにv2.3が導入済みという意味ではない。**
