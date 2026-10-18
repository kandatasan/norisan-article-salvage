# つりくえ！全国生物図鑑 v1.8 — 公式「全生物種」名簿と過去の水系調査を分離

構築日：2026-10-18。**GitHub研究用データ。WordPress本番には未導入・未公開。**

## 今回完成したのは「生物名の基準台帳」

出典：[国土交通省 河川水辺の国勢調査・令和7年度全生物種リスト](https://www.nilim.go.jp/lab/fbg/ksnkankyo/mizukokuweb/system/seibutsuListfile.htm)
（[使用した直接ファイル](https://www.nilim.go.jp/lab/fbg/ksnkankyo/mizukokuweb/system/DownLoad/List/R07List/R07zenseibutsu.xlsx)）。
公式の変更情報は「令和7年度：2025-10-10更新、魚類は2025-11-27修正」。2026年度の動植物プランクトンのリスト変更は別物。今回の2025年度名簿に勝手に混ぜない。

公式Excel本体は **37,812データ行**。そのうち **164行は分類の区切りで個別の種・タクサコードがない行**なので、原本どおりに除外し、**37,648タクサ名掲載行**を保存（**37,648種ではない**）。表記上の異なる和名は37,632件で、同一名の複数コード・分類を自動的に統合しない。

分類区分は単一選択ではなく公式表の**複数所属フラグ**を忠実に記録した。以下は種数ではなく分類掲載行の所属件数。

| 生物グループ | 名前リストの掲載行 |
| --- | ---: |
| 魚類 | 1,063 |
| 底生動物 | 5,642 |
| 植物 | 5,842 |
| 鳥類 | 699 |
| 両爬哺（両生類・爬虫類・哺乳類） | 372 |
| 陸上昆虫類等 | 27,213 |
| 動植物プランクトン | 365 |

**水辺に暮らしているか、特定の県や川で確認されたか、現在釣れるかを示す台帳ではない**。調査で使用する和名・学名・分類体系の一覧であり、属レベルや分類未確定の表記も含む。

## 既存18,814件の魚類記録とどうつながる？

既存の国交省「河川版 魚類調査・確認種一覧」は、9地域・水系・調査年度・当時の表記を基準にした **18,814の魚類記録の組み合わせ**。このデータは研究用SQLiteの別テーブルに保持した。名前が一致していても**同じ分類コード・同じ現行名・河川固有の生息・特定県での確認を意味しない**。

クエリ時に「公式2025分類名」「過去の水系別魚類調査」を別結果欄に表示する。「アユ」の名称が双方に見つかった場合も、分類同一性は未審査。魚類以外の分類名に魚類調査の分布情報を自動付与しない。

## ファイル

- `biota/official_biota_reference_2025_v18.csv`：37,648原文タクサ掲載行、和名、学名、分類コード、門・綱・目・科・属、7つの調査フラグ。元Excelの行番号を保持。
- `biota/official_biota_manifest_2025_v18.json`：原本・生成CSVのSHA256、資料年月、7分類の実件数、除外した区切り行数、未公開／出典ステータス。
- `biota/import_official_biota_v18.py`：公式Excelから読み込み再現する検証用スクリプト。場所・調査地点・希少種座標を取得しない。
- `biota/build_biota_catalog_v18.py`：独立したSQLiteを生成し、和名・学名・7区分・過去の水系魚類調査（9地域）を検索。
- `biota/test_biota_catalog_v18.py`：実データの件数、分類、複数コード、アユ検索、調査地域の誤推論、SQL安全性などの自動テスト。

## 実行

```bash
python river-fish/biota/build_biota_catalog_v18.py --build --db /tmp/tsurikue-biota.sqlite
python river-fish/biota/build_biota_catalog_v18.py --db /tmp/tsurikue-biota.sqlite --name アユ --group fish
python river-fish/biota/build_biota_catalog_v18.py --db /tmp/tsurikue-biota.sqlite --group benthic_animals --limit 20
python river-fish/biota/build_biota_catalog_v18.py --db /tmp/tsurikue-biota.sqlite --scientific Plecoglossus
python river-fish/biota/build_biota_catalog_v18.py --db /tmp/tsurikue-biota.sqlite --survey-name アユ --region chugoku
python -m unittest discover -s river-fish/biota -p 'test_biota_catalog_v18.py' -v
```

## 出典の使用条件

[国交省・河川環境データベース利用上の注意](https://www.nilim.go.jp/lab/fbg/ksnkankyo/Mokj_chui.htm)は、出典明記と加工の記載などを条件に商用利用も認めている。第三者の権利、特別規約、ロゴ・写真は別途確認する。重要種の位置情報は人為的な採集や攪乱を防ぐためダウンロードから外されている。本DBにも座標や詳細調査地点を収録しない。

出典表示例：**「国土交通省 河川水辺の国勢調査・令和7年度 全生物種リストを加工して作成」**。

## 生物図鑑の完成までの残作業

1. **生物の名前・学名・分類：今回、2025基準で基盤完成。** 2026年度プランクトン更新の差分検証は未実装。
2. **過去の地域・水系別調査記録：魚類18,814行のみ取り込み済み。** 底生動物／両爬哺／昆虫／植物／鳥類の地域別確認種一覧はこれから独立取込。未調査地域は未収録と表記。
3. **地域×生物→河川／地域×河川→生物：** 水系別の文脈だけで該当する支流や都道府県へ帰属させない。公式の地点／河川／自治体を特定できる一次資料から、保護種に配慮した公開可能な地点情報だけ承認する。
4. **生物の説明・同定・画像・釣り方・外来種・保全：** 各項目は別資料で出典付き執筆・権利確認が必要。表の空欄から内容を創作しない。
5. **WordPress本番：** 既存の河川検索v0.2.0のDB形式や画面は今回変更していない。統合プラグイン更新は別の成果物とテストで実施する。公開権限の明示を待つ。

**生物名簿の大きさと生物図鑑の完成を混同しない**ことを、アプリケーションと出典で統一する。
