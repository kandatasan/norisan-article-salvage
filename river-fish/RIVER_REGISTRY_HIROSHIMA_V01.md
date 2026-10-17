# 広島県・河川マスター v0.1（つりくえ！）

作成日: 2026-10-18。**サイト公開前の河川名調査・検索プログラム**。今後47都道府県へ拡大。

## 現時点のデータ

- `river_registry_hiroshima_v01.csv`：**66河川／15水系**、それぞれ名称・所在地の一例・出典を記録。
- 出典：広島県『河川内の堆積土等除去計画2021』p.14–16に掲載された実施対象河川から、流域や小河川の異なる例を抜粋して独自に整理した**初期台帳**。県内の全河川を網羅しない。
- `river_registry_v01.py`：上記台帳＋国交省の既存魚類集約データから**独立したSQLite**を生成して河川名を検索。
- `test_river_registry_v01.py`：諸木川の検索、同名河川の区別、魚類の誤帰属防止など自動検証。
- `.github/workflows/river-fish-river-registry-v01.yml`：魚類DB専用の読み取り／SQLite作成テスト。WordPress操作なし。

## 台帳カラムの意味

| 列 | 意味 |
| --- | --- |
| river_id | 地域内の独立した河川ID。名前の重複時に区別する |
| prefecture | 出典で所在地が確認された都道府県。流域全体を示さない |
| watershed | 出典に明記された**水系名**。直接の合流先ではない |
| river_name | 出典に書かれた河川名 |
| municipality_example | 資料に登場した**所在地の一例**で、通過する全市町村ではない |
| legal_class | 一級／二級／準用／普通河川。今回はすべて **unverified**（未照合） |
| direct_parent_river | 実際に合流する**直接の親河川**。出典不足で全件空欄 |
| record_status | 河川名の掲載は確認済み |
| source_url | 出典URL（資料の複製はしない） |
| source_document_year | 資料の発行年。現況確認年ではない |
| publication_status | 全件 `registry_staged`＝サイトで公開する前の候補 |

## 既存の魚類調査との接続

`official_chugoku_watershed_year_fish_v05.csv` は **水系×調査年度×魚名** の2,285行。直接の小河川への生息記録ではない。

SQLiteには **rivers / river_aliases / watershed_fish_context / direct_river_fish_evidence** を別テーブルで作る。特に `direct_river_fish_evidence` は、河川固有の生態出典が確認できるまでは**0件**。

例：
- 「諸木川」：広島県・太田川水系に河川名あり。ただし魚種の直接確認データは未登録。
- 「大谷川」：大谷川水系と沼田川水系の**別河川**がある。名前だけでまとめない。
- 「太田川」：太田川水系の公式魚類資料は参考件数としてのみ表示。子河川の魚種としては表示しない。

実行：

```bash
python river-fish/river_registry_v01.py --build
python river-fish/river_registry_v01.py --name 諸木川
python river-fish/river_registry_v01.py --name 大谷川
python river-fish/river_registry_v01.py --prefecture 広島県 --watershed 黒瀬川
```

## 権利とデータ利用の監査（公開前必須）

- **国土数値情報 W05（河川）には「非商用」の個別指定**。収益化ブログ向け河川データの複製元には使用しない。
- 広島県の一般公式ホームページは、無断転載・複製を制限。行政機関が公開した資料だから自由に丸ごと再配布できるとは限らない。
- 県オープンデータライブラリ／県オープンデータポータルには独自の利用規約がある。**今回の河川管理PDFが自動的にオープンデータライセンスになるわけではない**。
- 今回は資料を転載せず、個々の**河川名・水系・所在地という事実関係**を少数抽出して調査用台帳へ整理。**サイトへの一括掲載や検索ページ公開は未実施**。本番での商用利用に先立ち、資料の許諾と出典表示、必要なら河川課への照会を行う。
- 写真・地図画像・GIS線データの転載は一切していない。

参照元：
- 広島県『河川内の堆積土等除去計画2021』 https://www.pref.hiroshima.lg.jp/uploaded/attachment/429109.pdf
- 広島県 河川整備計画一覧 https://www.pref.hiroshima.lg.jp/soshiki/99/keikaku.html
- 広島市 河川の種別・管理区分 https://www.city.hiroshima.lg.jp/living/doro-kotsu-kasen/1026440/1026441/1003366.html
- 国土数値情報 W05 使用許諾（非商用） https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-W05.html
- 広島県公式サイト著作権 https://www.pref.hiroshima.lg.jp/soshiki/19/1173052529569.html
- 広島県オープンデータ利用規約 https://www.pref.hiroshima.lg.jp/soshiki/266/opendata.html

## 次の拡張

1. 広島県の「河川整備計画」「河川統計年鑑」、各市町村の普通河川・準用河川情報から追加候補を抽出し、権利確認と重複・水系判定を経て台帳へ追加する。
2. 行政上の河川区分、直接の合流先、複数市町村・県境をまたぐ範囲を資料照合で確定。
3. 河川固有の魚類資料を発見した川だけ `direct_river_fish_evidence` に追加し、調査年・出典・公開粒度を管理。
4. 許諾とQA済みの情報だけWordPress検索ツールに反映。網羅性・生息状況を誇張しない。
