# 全国河川コード・水系コード台帳 v0.7

更新：2026-10-18。**つりくえ！サイトへは未公開。GitHub上の研究・検証用データ**。

## 国土交通省の公式コード一覧から直接取得

- [河川コード一覧（10桁）](https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html)
- [水系域コード一覧（6桁）](https://nlftp.mlit.go.jp/ksj/gml/codelist/WaterSystemCodeCd.html)
- [国土数値情報ダウンロードサイトの利用規約（2026年3月23日施行）](https://nlftp.mlit.go.jp/ksj/other/agreement.html)

実測結果：

| 指標 | 件数 |
| --- | ---: |
| 河川コード（10桁） | **35,449** |
| 6桁の水系域コード | **5,475** |
| 異なる河川名の文字列 | **22,524** |
| 6桁水系域コードと照合できない河川コードの行 | **19** |

登録件数は「現時点の日本に存在する河川の総数」ではない。元コード一覧にない河川、普通河川、細流、更新されていないコードもあり得る。河川名の表記数は独立した河川数と同義ではない。特に同じ名前でも異なる10桁コードは絶対に統合しない。

### ユーザーが気にしていた諸木川も登録

- **諸木川：8707090023**
- 先頭6桁は **870709＝太田川水系**。
- 広島県の別資料から得た「諸木川／太田川／広島県」は、`potential_local_evidence_matches_unapproved` として候補照合できる。ただし、これだけで所在地の確認や同一河川としてのコード統合は承認しない。
- 太田川の魚類調査記録を諸木川固有の魚として流用しない。魚類の個別記録は未確認のまま。

### データの保存先

- `national-codes-staged/river_codes_national_v07.csv`：10桁河川コード、名称、6桁水系コード、対応水系名（不明時は空欄）、コード管轄プレフィックス、出典、非公開／未確認状態。
- `national-codes-staged/watershed_codes_national_v07.csv`：6桁の水系域コードと名称。
- `national-codes-staged/river_code_manifest_v07.json`：実件数、原本SHA-256、照合保留、コード頭2桁の分布など。加工前のHTML全文・測量地物・GIS形状データは保存しない。
- `import_national_river_codes_v07.py`：国交省の2ページのみを許可して、公式HTMLをダウンロード・解析する再実行可能スクリプト。元HTMLの突然の変化、河川名やコードの衝突に対して停止する。
- `national_river_catalog_v07.py`：上記から **SQLite検索DB**を生成。名前、水系、河川コード、コードの発行地域先頭2桁で検索。
- `test_national_river_codes_v07.py`、`test_national_river_catalog_v07.py`：データ形状と現行CSV・諸木川・同名別河川・魚類誤帰属防止をQA。

### 使用例

```bash
python river-fish/national_river_catalog_v07.py --build --db /tmp/river-codes.sqlite
python river-fish/national_river_catalog_v07.py --db /tmp/river-codes.sqlite --name 諸木川
python river-fish/national_river_catalog_v07.py --db /tmp/river-codes.sqlite --name 八幡川 --watershed 太田川
python river-fish/national_river_catalog_v07.py --db /tmp/river-codes.sqlite --river-code 8707090023
python river-fish/national_river_catalog_v07.py --db /tmp/river-codes.sqlite --code-prefix 47 --limit 30
```

**重要：コード先頭2桁は実際の河川が存在する県の判定キーではない。** 一級水系では地方整備局等の番号になることがあり、複数県にまたがる。コード番号から都道府県・市町村・合流先を推測しない。

## 権利と出典

- 元コード一覧は国土交通省サイトで公開された**コード・名称表**。出典として2つの公式リンク、取得・加工の事実を掲示。
- [国土数値情報ダウンロードサイト利用規約](https://nlftp.mlit.go.jp/ksj/other/agreement.html)では、2026年3月23日からPDL1.0準拠を基本とし、個別の利用条件があるデータに別ルールが適用される。
- 国土数値情報の**旧W05河川線データは非商用**。今回、W05の線分・座標・図版・属性のダウンロードや転載は一切しない。
- 同じサイトに掲載されていても、元コード表や他の掲載コンテンツに個別の権利・制限がある可能性を排除できない。実サイトへ大量公開する前に、必要な出典表示・加工表記・個別制約の最終確認を行う。
- 河川コードが古い情報を含む可能性、同名の異河川、名称変更を考慮し、今回の段階は **research_only** とする。

## まだ未完了の箇所

- 47都道府県別に全国の河川名を地理的に正確に分類すること。
- 19件の水系コード照合未解決。
- 既存広島66河川／河川名候補98行の公式10桁コードとの同一性承認。
- 親川への直接合流先、町村境界、源流位置等の検証。
- 全国の小河川（諸木川を含む）それぞれに生息魚を登録すること。
- WordPressでの検索フォームやページ公開。

次は、**旧66件＋98候補と全国コードの突合監査**、その後**所在県が確認できる県・市町村の河川台帳**を徐々に収録していく。国交省の魚類全国18,814レコードは既に水系・年度単位で利用できるが、小河川固有の魚類観測とは区別する。
