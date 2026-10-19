# 日本の河川大図鑑 v0.2｜本番DBを守るAPI接続契約

## 基本方針
既存の `/biota/api/search.php` は読み取り専用の既存公開APIとして扱い、破壊・置換・初期化しない。全国河川コードの参照系は新規の名前空間 `/river-atlas/api/v1/` を想定する。**この文書は実装契約の設計案であり、現時点でサーバーに新APIは存在しない。**

## エンドポイント案
- `GET /prefectures`：47都道府県の選択肢。各県に `coverageStatus` を返す。公式根拠のない水系を県に紐づけない。
- `GET /watersheds?pref=34&cursor=...`：当該県との関係を出典付きで確認できた水系のみ。越県水系は複数県の結果に含む。
- `GET /watersheds/{sixDigitCode}/rivers?limit=36&cursor=...`：10桁河川コード先頭6桁が一致するレコードを安定順で返す。県内河川という主張はしない。
- `GET /rivers/{tenDigitCode}`：コード、名称、水系、出典。所在地・合流先・個別生物は `null` と `verificationStatus` を返し、未確認を推定で補わない。
- `GET /watersheds/{sixDigitCode}/biota?category=fish&cursor=...`：**照合表で水系同一性が承認された場合だけ**既存生物DBから参照。未承認時は `linkStatus: unverified` と空の結果を返し、別枠で「水系名による参考検索」を選択可能にする。
- `GET /biota/names/{name}/watersheds?cursor=...`：水系名義の調査記録から逆引き。生物名の同名異種・表記ゆれを区別する。

## レスポンスの最低限の契約
```json
{
  "schemaVersion": "1",
  "status": "ok",
  "sourceEdition": "research-2026-10-18",
  "items": [
    {"riverCode":"8707090023","riverName":"諸木川","watershedCode":"870709",
     "prefecture":null,"prefectureVerification":"unverified",
     "parentRiverCode":null,"parentVerification":"unverified",
     "directBiotaRecords":null,"directBiotaStatus":"not_collected"}
  ],
  "nextCursor":null,
  "hasMore":false
}
```

`null` はゼロ件や不存在ではない。未調査・未確認・掲載なしを区別する。水系名義の生物調査は `surveyScope: watershed`、河川そのものの調査は `surveyScope: individual_river` とし、必ず `surveyYear` と `sourceUrl` を持たせる。

## データベース構造案（新規テーブル、既存biotaテーブルは無変更）
- `atlas_watersheds`：`watershed_code CHAR(6) PRIMARY KEY`、名称、原典版
- `atlas_rivers`：`river_code CHAR(10) PRIMARY KEY`、`watershed_code CHAR(6)`、名称、原典版、INDEX(`watershed_code`,`river_code`)
- `atlas_watershed_pref_evidence`：水系コード、県コード、出典URL、掲載日、照合ステータス。UNIQUE(水系コード,県コード,出典URL)
- `atlas_river_pref_evidence`：河川コード、県コード、出典URL、確認ステータス。名前だけの一致では挿入しない。
- `atlas_biota_watershed_crosswalk`：水系コード、既存生物DBの地域名・水系名・対象年度・出典、照合ステータス。**承認済みのみ結合**。
- `atlas_river_parent_evidence`：子河川コード、合流先コード、出典、確認ステータス。根拠なしなら行を作らない。

## 安全性・性能の必須条件
- 既存DBの表は `DROP`/`TRUNCATE`/`UPDATE` しない。新規投入も本番バックアップ・承認後。
- APIはprepared statement、許容値ホワイトリスト、入力長制限、`limit <= 100`、安定カーソル方式、レート制限を採用。
- 文字列はHTMLに直結せず `textContent` 相当で出力。レスポンスはJSON、詳細地点・希少種位置は非公開。
- 同名の水系・河川はコードと出典で分離。19件の未解決照合行は隔離して再審査。
- 最初の画面は47県の選択肢を軽量に返し、必要な川名だけ36件ずつ取得。408,036件をクライアントに送らない。
- サーバー接続前に `search.php` の実際の応答形式、CORS、ページング、公開情報の範囲、MySQL索引、利用規約を読み取り監査。
- WPカスタムHTMLに入れるのは描画層だけ。API障害時には明確な再試行案内を表示し、既存検索へのリンクを保持。

## リリース判定
1. 太田川試作のiPhone Safari実機・VoiceOver・回転・長い川名を確認。
2. 県水系照合の出典・版管理、コードID一意性、19件の隔離をテスト。
3. Xserverは別テーブル・別URLのステージングで試す。本番DBバックアップ確認、読み取り権限最小化。
4. WordPressの下書きに載せ、承認を得てから公開。
