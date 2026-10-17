# 鳥取県：東部・中部・西部 詳細河川一覧 v1.1

2026-10-18実装。**研究／目視監査待ちデータ。つりくえ！のWordPressには未公開。**

## 今回の資料

鳥取県の公式ページ [河川の管理](https://www.pref.tottori.lg.jp/307111.htm) に掲載されている、**令和5年4月1日（2023年4月1日）時点**の河川一覧PDF（東部・中部・西部）の３点を原資料とした。

| 圏域 | 一級河川の掲載行 | 二級河川の掲載行 | 準用河川の掲載行 | 計 |
| --- | ---: | ---: | ---: | ---: |
| 東部 | 87 | 38 | 16 | **141** |
| 中部 | 32 | 49 | 33 | **114** |
| 西部 | 64 | 27 | 31 | **122** |
| **合計** | **183** | **114** | **80** | **377** |

- **掲載行377件／名称335種類**はPDFからテキスト抽出した値。現在の県内河川総数や独立した河川数ではない。
- 元表は自治体内の河川整理番号を持つが、**それを国交省の10桁河川コードと混同しない**。
- 同名の「清水川」なども、異なる圏域・種別・元表の整理番号を保った独立した掲載行として残す。
- PDFの「水系名」セルが明示される行に限って取り込む。表のセルが縦に結合され、明示文字がない場合は空欄とし、前の行から機械的に引き継がない。
- PDFにある延長や橋・ダムの詳細位置、特定の調査地点などは記録していない。今回の資料自体は**魚の観測情報を載せたものではない**。
- 一級・二級・準用の区分は**2023年版PDFのページ見出し**。2026年の現行指定区分と断定しない。名称変更の可能性も別途監査。
- PDFのテキストをOCRで推測せず、機械抽出したもの。レイアウトや外字による文字化けの可能性があるため**全件の目視確定は未実施**。

## ファイル

- `import_tottori_river_pdfs_v11.py`：公式3 PDF URL以外へのアクセス禁止、PDF形式・サイズ制限、poppler `pdftotext -raw` による一覧の抽出と河川種別・掲載ページ・SHAの記録。
- `tottori-pdf-staged/tottori_river_pdf_mentions_v11.csv`：377掲載行。状態はすべて `pdf_text_machine_extracted_requires_visual_review` で、魚類生息や10桁コードとの結合は未承認。
- `tottori-pdf-staged/tottori_river_pdf_manifest_v11.json`：3原本のSHA-256、種別別集計、圏域別集計、抽出時の拒否数。
- `tottori_detailed_registry_v11.py`：既存の中国地方5県v1.0検索SQLiteに鳥取県の河川名掲載テーブルを追加。河川名・河川種別・圏域で検索。
- `test_tottori_river_pdfs_v11.py`、`test_tottori_detailed_registry_v11.py`：入力の安全性、分類、原本識別子、同名、出典日付、既存の5県・47都道府県データ維持のテスト。

### 検索例

```bash
python river-fish/tottori_detailed_registry_v11.py --build --db /tmp/tottori-review.sqlite
python river-fish/tottori_detailed_registry_v11.py --db /tmp/tottori-review.sqlite --name 皆込谷川
python river-fish/tottori_detailed_registry_v11.py --db /tmp/tottori-review.sqlite --river-class 準用河川 --district 西部
python river-fish/tottori_detailed_registry_v11.py --db /tmp/tottori-review.sqlite --name 清水川
```

## 公式原資料

- 一覧ページ：https://www.pref.tottori.lg.jp/307111.htm
- 東部PDF：https://www.pref.tottori.lg.jp/secure/1313532/toubu.pdf
- 中部PDF：https://www.pref.tottori.lg.jp/secure/1313532/230401chubu.pdf
- 西部PDF：https://www.pref.tottori.lg.jp/secure/1313532/230401seibu.pdf

河川名・分類・元資料URL等の事実を研究用データとして整理し、元PDF画像・表レイアウトやGIS形状は複製していない。商用サイトでの公開前に著作権・利用条件の確認、出典・加工表示、全件の表記監査が必要。

## 次工程

1. PDFの抽出結果と原表を照合して、外字・漢字の揺れ、番号・種別・欠落行を監査。
2. 島根県の一級・二級・準用河川の河川指定一覧も同様に取得し、地名・水系名・管理年月を区別して台帳へ登録。
3. 岡山県の浸水区域対象河川一覧等からさらに河川を追加。正式10桁コードは独立した出典による照合後のみ紐づける。
4. 生息魚は実際の河川ごとの生物調査資料が見つかったものから追加。**地域・水系単位の魚類情報をそのまま支流に流用しない**。

**公開WordPress記事・検索ページには変更なし。**
