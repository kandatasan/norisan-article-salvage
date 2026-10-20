# 日本の河川大図鑑｜神奈川県環境DNA 2023–2024年度 v0.11

2026-10-20 / 研究用。**本番WordPress、公開API、MySQL、v0.10集計への書き込みなし。**

## 検証結果

神奈川県環境科学センター [環境DNAのページ](https://www.pref.kanagawa.jp/docs/b4f/suigen/edna.html) で公開される2023・2024年度の**5つの原本XLSX**をGitHub Actionsから取得し、SHA256、シート名、採取河川の水系・支川列、DNA配列陽性と生物名欄を検証。

- eDNA陽性の水系×河川名：**31グループ**
- v0.10の492表示名グループにない追加候補：**19グループ**
- 「鶴見川・早淵川」は別表記「早渕川」との同一性を**保留**（新しい1本と断定しない）
- 2023・2024年度の出典別DNA陽性・河川名×生物記載名：**3,675行**
- 年度・水系・河川・分類・記載名で重複整理したグループ：**3,570組**。105行相当の出典間重複は元の出典を保持
- 492＋19＝**511の研究用表示名候補**（現実の河川の本数でも、公開サイトへの反映済み数でもない）
- v0.10の2025年度eDNA 265組と従来調査651,435文脈は別レイヤーのまま維持。**新規の生体捕獲・目視は0件**

### 公式原本と固定SHA256

| 年度 | 区分 | Excel | SHA256 |
|---|---|---|---|
| 2023 | 水源河川 魚類 | [r5_kenmin_gyorui.xlsx](https://www.pref.kanagawa.jp/documents/97797/r5_kenmin_gyorui.xlsx) | 60c18a87a9522c5f8bd0ba90021d58a663a5b3696f5592a033ff85f8ed78d62a |
| 2023 | 水源河川 昆虫類等 | [r5_kenmin_mtinsects-16s.xlsx](https://www.pref.kanagawa.jp/documents/97797/r5_kenmin_mtinsects-16s.xlsx) | 50865de054e4ac12c097ca4ee8e880713f45b3947cd30364684854079e3957fc |
| 2023 | 全県河川 魚類 | [r5_project_gyorui.xlsx](https://www.pref.kanagawa.jp/documents/97797/r5_project_gyorui.xlsx) | 6292c5829709c7677abf83c6e18437205ea3b3d3964c9bf67a4f2086bce7d48c |
| 2024 | 水源河川 脊椎／無脊椎動物 | [r6_kenmin_mtinsects_amphi.xlsx](https://www.pref.kanagawa.jp/documents/97797/r6_kenmin_mtinsects_amphi.xlsx) | fdfc28f2c470625429334e603d62d212b4f7bb5c4bb3bd521c91c500397ab11a |
| 2024 | 全県河川 脊椎／無脊椎動物 | [r6_project_mtinsects-amphi.xlsx](https://www.pref.kanagawa.jp/documents/97797/r6_project_mtinsects-amphi.xlsx) | 0655f626405ae5a883ae2dba1589277f381fee170a2a2bf6735a304ca58b1258 |

### 重要な調査方法・信頼度の違い

- **2023魚類Excelには同定信頼度の高・中・低列がない**ため not_reported として保存。2023の魚類はExcel日付の暦年を確認し、年度だけで古い採取日を2023に変換しない
- 2023昆虫類・2024動物の信頼度があるExcelは **高・中のみ**採用。低・不明は追加しない
- 2023昆虫用マーカーで得た**魚類の対象外ヒットは魚類eDNAの確証として採用しない**
- 魚類DNA陽性 ≠ 生体を捕獲した事実。鳥類DNA陽性 ≠ 観察した鳥。昆虫・その他無脊椎動物のDNA陽性 ≠ 河床で採集した底生動物。**植物の新規確定記録なし**
- DNA陽性の読取値は個体数ではない。原資料の「アブラハヤ/タカハヤ」「cf.」等は一つの不確かな分析記載名として保管し、複数種に分割しない
- 本研究では**河川コード任意**。緯度・経度、採取点ID、調査者、位置情報は保存しない
- 「鶴見川・早淵川」の同一性保留：[横浜市公式河川一覧](https://www.city.yokohama.lg.jp/kurashi/machizukuri-kankyo/kasen-gesuido/kasen/shoukai/gaiyou.html)

### 研究用のコード・出力

- scan_kanagawa_edna_2023_2024_v11.py : 公的原本を再取得し、匿名化した表構造とSHAを監査
- extract_kanagawa_edna_2023_2024_v11.py : 原本SHA固定、年度、河川名、方法、陽性、生物原文、重複、留保の抽出
- outputs/kanagawa_2023_2024_source_schema_scout_v11.json : 原本検証5件
- outputs/kanagawa_2023_2024_edna_evidence_v11.csv : eDNA陽性の出典別3,675行
- outputs/kanagawa_2023_2024_edna_river_groups_v11.json : 年度・出典・生物分類ごとの31組
- outputs/kanagawa_2023_2024_new_river_edna_examples_v11.json : 19候補の原掲載名の少数例
- outputs/kanagawa_2023_2024_edna_provenance_qa_v11.json : 手法、信頼度、重複、保留、原資料監査
- .github/workflows/river-kanagawa-edna-2023-2024-v11.yml : 研究ブランチ限定の原本取得・検証・保存CI

### 次の段階

v0.9クリック試作は**428河川名**のまま。v0.10の40旧保留名＋24県eDNA名、および本v0.11の19候補を「都道府県→水系→河川・支流→魚類／底生動物／鳥類／植物」の研究用UIへ取り込む際は、**従来採集・目視 と eDNA を別表示**にする。

[県公式利用条件](https://www.pref.kanagawa.jp/documents/97797/riyo-kiyaku.pdf) に基づき、公開時には出典表示、加工の告知、第三者権利、希少種の細かな生息地点開示を再監査する。

**注意：v0.11専用CIと、既知の別ワークフロー river-atlas-ota-poc-v01.yml の失敗は区別して報告する。全CI成功とは言わない。**
