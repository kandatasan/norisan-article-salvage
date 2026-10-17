# 河川同一性・公式台帳クロスチェック v0.9

更新：2026-10-18。**GitHub調査用・WordPress未公開**。

## 2016年の国土交通省台帳で10河川のコード記載を追加検証

中国地方整備局が公表する[太田川水系の河川コード台帳（2016年12月）](https://www.cgr.mlit.go.jp/kasen/code/pdf/009oota201612.pdf)の河川コード表と、広島県の[河川内の堆積土等除去計画2021](https://www.pref.hiroshima.lg.jp/uploaded/attachment/429109.pdf)に記載された**河川名・水系**を突き合わせた。

| 河川 | 10桁コード | 2016年の台帳ページ（PDF通し番号） |
| --- | --- | --- |
| 山本川 | 8707090006 | 3 |
| 京橋川 | 8707090010 | 3 |
| 府中大川 | 8707090013 | 3 |
| 矢口川 | 8707090021 | 3 |
| 落合川 | 8707090022 | 3 |
| **諸木川** | **8707090023** | **3** |
| 大塚川 | 8707090028 | 4 |
| 湯坂川 | 8707090034 | 4 |
| 関川 | 8707090036 | 4 |
| 栄堂川 | 8707090041 | 4 |

**確認できたこと**：2016年12月版の太田川水系コード台帳に、各名称・コード・河川管理者「広島県」が掲載。既存の2021年広島県河川名資料にも対応する名称・水系が掲載。既存v0.8コード候補との照合は、上の各10件すべて1候補に一致した。

**確認できていないこと**：2026年現在のコードや管理者に変更がないこと、河川が通る全市町村、細かな河川区間、直接の親川・合流先、当該川に生息する魚の種類。**管理者「広島県」は所在市区町村を示す地理データではない。**

従来のv0.8候補の `identity_approved` / `prefecture_approved` / `fish_approved` は全件 `false` のまま。新しく `historical_code_and_watershed_crosschecked` の証拠テーブルを作るが、**現在の地理同定を最終承認するテーブルではない**。

## 実装ファイル

- `ota_historical_code_crosschecks_v09.csv`：10河川の名称、10桁コード、2016年管理者と日付、公式PDFの掲載ページ、広島県の照合元URL。
- `historical_ledger_crosscheck_v09.py`：v0.8の河川名候補DBを作ったうえで、10件を**外部キー付きの独立証拠テーブル**に格納。名称、水系、候補数、出典URLが一致しない場合は処理を中断。
- `test_historical_ledger_v09.py`：実際の候補データを使って誤帰属・現在地理の推定・魚類の勝手な割当てを防止する回帰テスト。

ローカル実行例：

```bash
python river-fish/historical_ledger_crosscheck_v09.py --db /tmp/moroki-evidence.sqlite --build
python river-fish/historical_ledger_crosscheck_v09.py --db /tmp/moroki-evidence.sqlite --river 諸木川
python river-fish/historical_ledger_crosscheck_v09.py --db /tmp/moroki-evidence.sqlite --river-code 8707090036
python -m unittest discover -s river-fish -p 'test_historical_ledger_v09.py' -v
```

## 今後の全国展開

この仕組みを別の整備局・県の河川コード台帳（**更新年月日付き**）に拡張する。まず、単一候補から確定できるものは「当時の公式台帳にコードと管理者がある」という記録として昇格させ、所在地県の現況確認を別々に行う。全国調査の**水系別魚類18,814件を各支流に無条件割当てしない**。

商用サイトの掲載には原本の出典・加工表示・利用条件・データの現況を確認し、希少種の詳細位置を公開しない。今回もWordPressは未変更。


## v0.9追加：広島県の比較的新しい水防資料から「関係市町」を照合

[広島県の水防資料（PDF）](https://www.pref.hiroshima.lg.jp/uploaded/attachment/634919.pdf)の別表にある**10河川・12掲載行**を、2016年の10桁コード証拠と別テーブルで結合した。2026-10-18に公式公開資料を照合。

- **諸木川／8707090023**：太田川水系、関係市町「広島市」（PDF通し145ページ）。
- 京橋川：広島市・府中町の**2市町**。
- 関川：広島市・東広島市の**2市**。
- 山本川・矢口川・落合川・大塚川・湯坂川・栄堂川：広島市。
- 府中大川：県の河川監視カメラ一覧から「広島市に設置された監視箇所の所在市」を確認（PDF通し33ページ）。これは水防法上の指定関係市町とは異なる情報であり、同列に扱わない。
- 水防法の表にある2022年や2024年の日付は**その制度上の指定公表日**。魚類調査日でも、河川名・河川コード自体の更新日でもない。

**資料にその市町が登場したこと**と、川の全流路がその市町に収まることは別。複数市町を重複として消さない。全国コードから魚種を支流に付けることもしない。河川現況の最終認定は保留のまま。

### 追加ファイル

- `ota_municipality_evidence_v09.csv`：市町12行、出典PDFページ、出典における情報の種別、指定日（ある場合）。
- `municipality_sources_v09.py`：v0.9の10コードを検証後、外部キー付き `municipal_document_evidence` へ12行を保存。コードの現在性・魚の生息を勝手に承認しない。
- `test_municipality_sources_v09.py`：諸木川、2市町が載る川、カメラと指定の区別、魚の誤帰属防止をチェック。

```bash
python river-fish/municipality_sources_v09.py --db /tmp/ota-evidence.sqlite --build
python river-fish/municipality_sources_v09.py --db /tmp/ota-evidence.sqlite --river 諸木川
```

この追加も **GitHubの研究用データ**であり、WordPressには反映していない。
