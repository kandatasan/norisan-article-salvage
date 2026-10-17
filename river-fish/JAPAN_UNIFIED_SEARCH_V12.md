# 全国の川・魚類図鑑DB v1.2：47都道府県対応の統合検索基盤

更新：2026-10-18。**つりくえ！サーバー・WordPressには未反映**。GitHubの研究用データ・CLI検索の段階。

## 結論と対象範囲

既存の公式出典に基づく **35,449件の10桁河川コード＋9地域18,814件の地域／水系／調査年度／魚名記録＋47都道府県の索引**を、1つのSQLiteファイルから安全に検索できるようにする。

**ここでいう「全国対応」は全国コード名検索と47都道府県の枠を意味する。47県すべての個別河川位置・小河川・生息魚を網羅した、という意味ではない。**

## 確認済みのデータ構造

| テーブル | スコープ | 行数 |
| --- | --- | ---: |
| prefectures | 全国都道府県の名称キー | 47 |
| national_named_river_codes | 全国の公式10桁河川コードと河川名・水系名（所在県未確認） | 35,449 |
| national_census_watershed_fish | 国交省の地域×水系×年度×魚名表記（県・支流へ自動配賦不可） | 18,814 |
| rivers | 広島県で確認済みの資料掲載河川 | 66 |
| river_name_mentions | 広島県市町の未照合河川名掲載行 | 98 |
| prefecture_watershed_source_mentions | 中国5県の水系掲載情報 | 87 |
| municipality_river_source_mentions | 山口県の河川名・関係市町の資料掲載行 | 81 |
| tottori_pdf_river_mentions | 鳥取県の2023年3圏域河川一覧の機械抽出掲載行（目視監査待ち） | 377 |
| official_station_localization_evidence | 今後公式資料から確認した観測所所在地と河川の組合せを収録する準備テーブル | **0** |

**18,814件は18,814種類の魚ではない。** 調査記録の名称組合せ数。35,449件も日本の河川すべてではなく、利用した公式コード一覧の収録件数。

## 検索上の重要な制限

1. 全国の河川名検索は可能。ただし、10桁コードの先頭2桁から都道府県を推定しない。
2. `--prefecture` で選ぶ県に一次資料がある場合は、その**資料に載った川**だけを地理情報の候補として示す。資料がない県は `no_local_river_source_loaded` と表示。川の不在を意味しない。
3. 県を指定し、全国コードに川名が一致しても、候補結果の `prefecture=null` を維持する。名称一致だけで県・コードの結合を許可しない。
4. 個別の魚類資料は、正式な河川固有の出典が見つかったものだけ今後追加。全国18,814件の水系別魚名を支流や県に流用しない。
5. 一般検索と魚類の水系コンテキスト検索（`--fish-context`）を完全に分けた。**`--prefecture` と `--fish-context` の同時使用は禁止**。
6. 鳥取県377行はPDFテキストから機械抽出した研究候補。全件の現況・漢字表記はまだ目視確定していない。

## 実行

```bash
# 47都道府県・全国35,449河川名・18,814水系魚類名を含むSQLiteを生成
python river-fish/japan_unified_registry_v12.py --build --db /tmp/japan-river-fish-v12.sqlite

# 全国の10桁河川コードで諸木川を探し、出典つき広島県の資料掲載行と別々に表示
python river-fish/japan_unified_registry_v12.py --db /tmp/japan-river-fish-v12.sqlite --name 諸木川

# 県を指定（候補不足なら未収録と表示、偽の「河川0件」を出さない）
python river-fish/japan_unified_registry_v12.py --db /tmp/japan-river-fish-v12.sqlite --prefecture 東京都 --name 荒川
python river-fish/japan_unified_registry_v12.py --db /tmp/japan-river-fish-v12.sqlite --prefecture 山口県 --name 三谷川
python river-fish/japan_unified_registry_v12.py --db /tmp/japan-river-fish-v12.sqlite --prefecture 鳥取県 --name 千代川

# 魚名は地域・水系だけで検索。県へのひも付けはしていない
python river-fish/japan_unified_registry_v12.py --db /tmp/japan-river-fish-v12.sqlite --fish-context --name アユ --limit 20
python river-fish/japan_unified_registry_v12.py --db /tmp/japan-river-fish-v12.sqlite --fish-context --region kyushu --watershed 筑後川
```

## 「一気に全国」の次工程

- **共通入口**はv1.2で整備。47県のそれぞれについて、一次資料の形式、商用利用条件、掲載年月日、河川区分、都道府県と水系の範囲を調査する。PDF・HTML・CSVで取り込み方を分岐。
- 国交省「水文水質データベース」は、全国の**水系・河川名・観測所・所在地**を検索でき、2025-12公表の利用規約で商用利用が可能。今後、観測所所在地という限定した県・河川対応の根拠として追加できる。ただし観測所のある場所は**河川全体の県別範囲ではない**。
  - https://www1.river.go.jp/contents.html
  - https://www1.river.go.jp/WDBrules_20251210.pdf
- 旧国土数値情報W05（河川線・非商用）は、つりくえ！収益化サイトの全国地理台帳の取得元に使わない。国土地理院の地理院地図Vectorは商用・大量取得・再配布の条件と測量法の適用について別途確認する。
- **47県一括で自動公開はしない**。先に全国から候補収集→件数・種別・重複・地理関係・ライセンスのQA→確認済みの川だけ検索サイトへ反映。希少種の確認地点は表示しない。
- 目的は「全国の川の名前を探す入口」を先に完成し、細かな魚類観測を徐々に育てること。

元データの出典・SHAは各既存v0.6～v1.1のmanifestとドキュメントを参照。独立した全国公式コード表と、県の地域資料を混ぜて元出典を書き換えていない。

**今回のコードとドキュメントはGitHubのみ。WordPress記事・下書き・固定ページ・サーバーDBを一切変更しない。**
