# 河川同一性照合・河川別魚類資料 v0.8（広島県で検証）

作成日：2026-10-18。GitHubでの調査用データ／**つりくえ！本番未公開**。

## 背景：全国の河川コードはその川の所在県を保証しない

全国版v0.7は**35,449河川コード／5,475水系コード**を収録した。しかし、名前が同じ・水系が同じ・10桁コードが異なるケースがある。また、コードの先頭2桁を都道府県番号に読み替えることもできない。

**県資料と全国コードの突合は「同一性候補」を見つけるだけ**。単一候補になっても、自動的に「広島県にあるこの川のコード」とは確定しない。

## v0.8の追加

- `review_hiroshima_code_links_v08.py`：広島県v0.1で確認した**66河川**と、三原・尾道・世羅・広島市資料の**河川名掲載98行**を、全国河川コードと自動照合。
  - v0.1は「川の名称×出典にある水系」を厳密一致。
  - v0.2の掲載資料には水系情報がないため、「川の名称」だけで候補を提示。
  - **0件・1件・複数件**のいずれの場合も、手動の同一河川確認が必要。
  - 出力：`review-staged/hiroshima_river_code_candidates_v08.csv` と集計manifest。各レコードの所在地県と魚類の帰属は常に未承認。
- `hiroshima_river_fish_narratives_v08.csv`：**黒瀬川について9種類の魚類名**を、県公式「黒瀬川水系流域の現状」に基づき記録。
  - オイカワ／カワムツ／ヨシノボリ類／オオクチバス／ブルーギル／スナヤツメ／メダカ／アユ／ゴクラクハゼ。
  - 県の古い河川環境に関する**解説文の記載**をそのまま分類した。現地調査の個別記録ではない。
  - ページ掲載日**2024-07-29は現地調査の実施年ではない**。調査年不明、種名は出典表記のまま（現行分類名に勝手に修正しない）。
  - 重要種の詳細生息位置を公開しない。上流・中流の具体的地点名、座標等もレコードには含めない。
  - 全国の10桁コードとは未照合。川の名前が一致しても魚の記録をコードに自動付与しない。
- `river_review_catalog_v08.py`：照合候補と魚類の説明文を**別テーブルのSQLite**に取り込み、「川の名前」「出典にある県」「資料掲載の市町村」で検索。
- `test_river_identity_ecology_v08.py`：重複、同名異河川、未確定の位置／年／コード、希少種の情報粒度、SQLite整合性など13件のテスト。

## 出典

1. [国土交通省 河川コード一覧](https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html)、[水系域コード一覧](https://nlftp.mlit.go.jp/ksj/gml/codelist/WaterSystemCodeCd.html)：公式10桁・6桁コード。
2. [広島県「河川内の堆積土等除去計画2021」](https://www.pref.hiroshima.lg.jp/uploaded/attachment/429109.pdf)：旧66河川の出典。
3. [広島県三原支所「維持課」](https://www.pref.hiroshima.lg.jp/soshiki/218/mihara-iji.html)、[広島市「河川の種別と管理区分」](https://www.city.hiroshima.lg.jp/living/doro-kotsu-kasen/1026440/1026441/1003366.html)：旧98掲載行の出典。
4. [広島県「1-1.黒瀬川水系流域の現状」](https://www.pref.hiroshima.lg.jp/soshiki/99/1172470253504.html)：9種の魚類名の**河川環境説明**の記載元（2024-07-29掲載）。

## ローカル実行

```bash
python river-fish/review_hiroshima_code_links_v08.py --out river-fish/review-staged
python river-fish/river_review_catalog_v08.py --build --db /tmp/river-review-v08.sqlite
python river-fish/river_review_catalog_v08.py --db /tmp/river-review-v08.sqlite --river 諸木川
python river-fish/river_review_catalog_v08.py --db /tmp/river-review-v08.sqlite --river 黒瀬川
python -m unittest discover -s river-fish -p 'test_river_identity_ecology_v08.py' -v
```

## 未完了・次の工程

- 県の特定河川と10桁コードの一致を、**コードも河川名も確認できる別の正式資料**や、利用条件を確認した地理情報で人手検証して承認する。今回は0件承認。
- 出典にない市町村・親河川・県境を推測しない。
- 魚類生態資料の分類・基準年・県名との紐付けを再確認したものから公開候補に昇格。希少種は公開粒度を別途判定。
- 全国の県・市町村資料を使って確認済み河川と魚の情報を増やす。大量取得・再利用条件と出典表示を毎回確認。
- **今回もWordPress記事・検索UI・画像・サーバーDBへの変更なし。**


## 実データ突合の検証結果（2026-10-18）

| 県資料 | 唯一の一致候補 | 複数一致 | 候補なし |
| --- | ---: | ---: | ---: |
| 既存66河川（水系名まで資料で確認） | 55 | 10 | 1 |
| 市町等の98掲載行（名称のみ） | 44 | 50 | 4 |
| **合計164資料行** | **99** | **60** | **5** |

国交省の全国35,449コードとの候補レコードは **1,222行**。複数候補に対する1行ずつのコード候補と、候補ゼロを示す行を含む。**164の資料行が1,222の異なる川へ増えたわけではない**。一致1件は確定ではない。承認済みの河川コード／県の対応や生息魚の帰属は**0件**のまま。

データは `review-staged/hiroshima_river_code_candidates_v08.csv` と `review-staged/river_code_candidates_manifest_v08.json` に保管。自動調査の個別コード照合候補を記録したもので、釣り場や個体群が存在することの証明ではない。
