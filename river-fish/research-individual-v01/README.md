# 日本の河川大図鑑：個別河川の生物記録・研究試作 v0.1

## 結論

公式原本には個別の**河川名**が残っていた。既存の取込処理がC/F/G/J列のみを残していたため、現在の水系別検索用スナップショットからは落ちていた情報を、同一SHAの原本から復元する独立した試作を作成した。

- 既存WordPress・API・MySQLへの変更、デプロイは実施していない。
- 研究用ブランチ以外への成果物保存・マージは実施していない。
- 既存スナップショットは `mode=ro` で検査し、処理前後のSHA256が一致。
- 重要種を対象に詳細地点を補完せず、地区名・地点番号・距離・座標・詳細調査日・個体数を出力しない。
- 以下の件数の本体は**GitHub Actionsの既存SQLite成果物**。本番MySQL直接確認と公開API全件確認は未完了。

## 原本に残っていた列

| 情報 | 旧取込処理 | 今回 |
| --- | --- | --- |
| 生物項目 C、水系 F、調査年度 G、種名 J | 保存 | 原文表記を保持 |
| 地整 D | 省略 | 河川同一性の根拠として保持 |
| 河川名 | 省略 | 見出し名から抽出。魚・底生動物・鳥はM列、植物はL列を実測 |
| 地区名・調査地点・距離・詳細日付等 | 省略 | 今回も出力対象外 |

「底生」と「底生動物」、「魚介類」と「魚類」を勝手に同一区分にしない。既存408,036件と同じ受入条件で照合し、対象外の元カテゴリの行数は `audit_summary.json` の `original_categories` に別記する。

## 数え方

1. **旧キー**：分類 × 地方 × 水系名 × 調査年度 × 掲載名。既存408,036件の単位。
2. **復元キー**：旧キーに河川名・原資料の地整を追加。同じ旧キーから複数の河川が復元され得る。件数増は新しい観測の追加を意味しない。
3. **掲載名数**：原文の名前の異なり数。分類学的な種数ではない。「属」「類」「型不明」や旧分類を統合しない。
4. A/B/C/Dの旧キー別割合と、復元キー別件数を別集計する。旧キーをAとするのは復元した全候補がAの場合だけ。一部の川だけAの旧キーは `has_any_approved_river` で別に追える。

| 判定 | 条件 |
| --- | --- |
| A | 原本に河川名あり。原本の地方整備局・水系・河川名と、独立した公式地域別コード台帳・全国コードCSVが一致し、地域内で候補が一つ |
| B | 原本の河川名を復元したが、コードの独立照合が未承認。唯一の名称候補だけでAにしない |
| C | 検査した原本に河川名が空欄の記録を含み、個別河川として帰属を確定できない。水系の調査文脈は保持 |
| D | 原本照合未完了、または同一性要確認。未確認を「河川名なし」と決めつけない |

Aは現行生息や現在の河川形状を保証しない。コード台帳は2016年12月版と既存全国CSVを突合しており、公開前には更新履歴と公開粒度の最終確認が必要。

## 河川コードの照合根拠

- [国交省 全国河川コード](https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html)
- [国交省 水系域コード](https://nlftp.mlit.go.jp/ksj/gml/codelist/WaterSystemCodeCd.html)
- [中国地方整備局 河川コード台帳の案内](https://www.cgr.mlit.go.jp/kasen/code/code_index.html)
- [一級水系・河川コード表 2016-12](https://www.cgr.mlit.go.jp/kasen/code/pdf/000ikkatu201612.pdf)

`approved_river_crosswalk.csv` は同台帳のコードと名前の完全な同一行・水系のページ見出し・全国CSVとの一致を検査した結果。改行により判読できない行、名称不一致、同一水系内の同名複数コードは承認しない。独立確認済みの中国13水系の地域台帳内で候補が一つであることを使い、河川コードの先頭2桁から県を推定しない。台帳64ページの三篠川 `8707090029`、根谷川 `8707090047` の行は画像でも確認。

## 生物原本・利用条件

国土交通省「河川水辺の国勢調査」の全国9地方・河川版、魚類／底生動物／鳥類／植物の確認種一覧、計36資料を使用。具体的なZIP・メンバー名・SHA256・原分類・復元列・元行数・除外量は `outputs/audit_summary.json` に保持。

- [提供データ一覧](https://www.nilim.go.jp/lab/fbg/ksnkankyo/dl_00_index.html)
- [利用上の注意](https://www.nilim.go.jp/lab/fbg/ksnkankyo/Mokj_chui.htm)
- 中国地方：`RT87_B01.zip`（魚類）、`RT87_B02.zip`（底生動物）、`RT87_B03.zip`（植物）、`RT87_B04.zip`（鳥類）。同じ公式パスのRT81〜RT89が地方別の原本。

出典と加工した旨の表示が必要。重要種の調査地点を特定できる情報は提供元から除外されている。今回も詳細地点の復元や別資料との地点結合をしない。沖縄の河川版データは提供一覧になく、未収録。

## DBと検索の契約

SQLite本体はアップロード上限のため `outputs/river_individual_research.sqlite.gz.part000` ～ `part002` の3ファイルに分割した。`outputs/snapshot_parts.json` に各部品・圧縮ファイル・復元SQLiteのSHA256を収録。`snapshot_parts.py` で結合・展開・ハッシュとSQLite整合性を確認できる。

```bash
python river-fish/research-individual-v01/snapshot_parts.py assemble \
  --parts-dir river-fish/research-individual-v01/outputs \
  --output /tmp/river_individual_research.sqlite.gz
python river-fish/research-individual-v01/river_detail.py \
  --db /tmp/river_individual_research.sqlite --river-code 8707090029 --limit 20
```

展開したSQLiteは、正規化した出典・水系・掲載名・河川文脈のテーブルと、以下の読み取り用ビューを持つ。

- `evidence`：原本から復元したA/B/C/Dの河川文脈別記録。出典・SHA・年度・掲載名・照合理由・公開注意を含む。
- `approved_individual_river`：Aの個別河川記録のみ。河川詳細は10桁コードでここを検索。
- `original_key_audit`：旧408,036キーを保持し、復元結果の判定を重ねた表。
- `watershed_history`：所属水系の過去調査。個別河川の記録を埋めるために使わない。

`river_detail.py` は魚・底生動物・鳥・植物の個別記録を別々に返す。直接記録が0件なら「個別河川の記録は未確認」。水系記録は別の `watershed_context` に返す。例えば根谷川の鳥類は個別0件のまま、水系には鳥類記録があることを別枠表示する。

県の帰属は常に未推定。全国の「都道府県 → 水系 → 河川」を完成するには、所在地を明示した独立した県・河川の対応表が必要。水系所属を直接の合流関係にも変換しない。

## 実行・再現

Python 3.12標準ライブラリ。大容量XMLは既存環境の `lxml` がある場合に高速化する。コード台帳抽出にはPoppler `pdftotext` を使う。追加のネットワーク取得は `--download` を指定したときの公式原本のみ。

```bash
python river-fish/research-individual-v01/build_chugoku_crosswalk.py --pdf /tmp/000ikkatu201612.pdf --out /tmp/crosswalk.csv
python river-fish/research-individual-v01/audit_individual_rivers.py --raw-dir /tmp/river-originals --out /tmp/source-audit --regions all --download --approvals /tmp/crosswalk.csv --input-commit d179a00d4900dd40dd223ca6f61444b5ef81e79b
# 既存DBの独立した読み取り検査と照合結果の重ね合わせ
python river-fish/research-individual-v01/integrate_baseline.py --baseline /tmp/biota-snapshot-v27.sqlite --manifest /tmp/biota-snapshot-v27.json --research-db /tmp/source-audit/individual_river_research.sqlite --out /tmp/source-audit
python river-fish/research-individual-v01/compact_snapshot.py --source /tmp/source-audit/individual_river_research.sqlite --out /tmp/river_individual_research.sqlite
python river-fish/research-individual-v01/river_detail.py --db /tmp/river_individual_research.sqlite --river-code 8707090029 --limit 20
python -m unittest discover -s river-fish/research-individual-v01 -p 'test_*.py' -v
```

全国原本の並列検査は `parallel_audit.py`（3プロセス上限、出典SHA・処理コードSHA・照合表SHA付きの再利用キャッシュ）でも実行できる。各出力先は既存フォルダへの上書きを拒否する。

保存失敗後の再生成では公式原本36ZIPを再取得して各SHAを検査し、`parallel_audit.py` で全件を再監査した。前回の原本別件数と、`group_counts.csv`・`watershed_counts.csv`・`river_counts.csv` のハッシュは完全一致。前回の v27 ベースライン成果物はこの再生成時には再取得できなかったため、前回のキー全件双方向照合結果を保持した監査JSONと照合し、`restore_key_index.py` で旧キーを復元した。新しいDBについては `outputs/recovery_validation.json` の11項目と、分割→結合→展開のSHA・SQLite整合性で再検査した。前回のDB本体とはバイト単位の同一性を主張しない。

既存DBは [Actions run 39130312796](https://github.com/kandatasan/norisan-article-salvage/actions/runs/39130312796) の `research-only-biota-four-groups-v27`（artifact ID `12137787609`）を使用。既存manifestとDB本体SHAの一致を検証。生成時コミットは `af62f05cf1a86eec07a8e7a3b541fd010985b5ad`。

## 未完了

- 本番MySQLの直接確認と、既存公開APIの全件数の確認。公開APIは以前の読み取りで40行のサンプルのみ確認しており、本成果の実測件数と同一DBとは断定しない。
- 中国地方以外の独立した地域別コード台帳の照合。全国原本の河川名を復元しても、未承認のコード候補はBのまま。
- 全国の所在地県対応、現行生息判定、詳細地点、分類学的な厳密な種同定。
- UIの全面改修、WordPress反映、既存API改修、本番デプロイ。

集計結果・分野別評価・テスト結果は以下の実測結果と `outputs/` を参照。

## 検証記録

`outputs/qa_results.json` は初回生成時に既存 v27 スナップショットと直接照合した14項目の結果。`outputs/recovery_validation.json` は今回再生成したSQLiteの11項目の結果。新しいSQLiteのSHA256は `9143419acb23c9181eaea8112ca44d0b219a92a15723baa1ae43ef075b0b9f34`。
