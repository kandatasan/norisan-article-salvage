# 中国地方5県｜魚名と河川の根拠収集 第1便（2026-10-21）

**調査専用ステージング。サイト、WordPress、Xserver、公開検索JSONには未反映。** 魚の名前と川を結ぶ「資料上の記載」を1行1組で整理したもの。**現在の生息・釣果・釣り場情報ではない。**

## 収集成果

- 候補 **124行**／出典 **7件**／中国地方 **5県**。
- うち**名前のある個別河川に関する記載115行・13河川**。ただしこのうち20行は流域説明からの河川文脈で、独立の採集地点が明示されない（`named_river_context`）。個別河川の名を出す公式表・説明がある95行は `named_river`。
- **水系単位のみ9行**（`watershed_only`）は本川や支流に接続してはならない。
- 114行は公式ページ・PDF本文のテキストを確認。山口県の研究報告に基づく10行はPDFが大きく**検索抜粋のみ**なので、`search_excerpt_only` のまま、正式な採用前に原本ページ・表を再検証する。
- 県別：島根77／広島7／岡山15／鳥取15／山口10。これは**新規登録可能数ではない**。既存atlasとの重複・同一河川IDの突合は未実施。

## データ構造と意味

- `recorded_name`: **資料に記載された文字表記**。フナ類・ヨシノボリ類は種名へ分割・正規化しない。
- `watershed`: 資料で明記された水系、または研究報告の水系。県名は資料出典の県。県を越える河川の全流域へ拡張しない。
- `river`: 資料に**個別河川名が示されている場合だけ**。空欄は `watershed_only`。
- `evidence_scope`: `named_river` / `named_river_context` / `watershed_only`。後二者は個別調査地点を保証しない。
- `evidence_kind`: `official_survey_summary`（県計画に転載された確認種表）、`official_environment_narrative`（県の河川環境説明）、`research_field_report`（研究報告の現地調査記述）、`historical_river_distribution`（旧資料の生息水系一覧）。**混同しない。**
- `survey_year`: 原資料に**その魚の調査年が明記**される場合だけ。島根県資料の「平成22年」「令和2年」は参考報告書の年であり、個々の魚の確認年とはみなさない。
- `source_locator`: ページ/表/節への手がかり。PDFの「資料p20」と「PDF p21」を区別。
- `verification_status`: `source_text_checked` または `search_excerpt_only`。
- `conservation_review=required`: アカザ・スイゲンゼニタナゴ・シロヒレタビラ・ミナミメダカ・ホンモロコ・カネヒラ等は公開粒度・保全上のリスクを追加審査。位置・座標・採集地点は保存しない。
- `integration_status=staged_only`: **公開DBには一切取り込まない**。

## 今回確認した公式資料

| ID | 発行主体・資料 | 掲載対象・制約 |
| --- | --- | --- |
| SH22 | [島根県・斐伊川水系中流支川域河川整備計画 付属資料（令和4年3月）](https://www1.pref.shimane.lg.jp/infra/river/kasen/hoshin/hiikawachuryusisen_kawadukuri/index.data/chuuryuuikifuzokusiryou.pdf) | 表2-4、資料p20（PDF p21）。斐伊川の指定区間・赤川・三刀屋川・久野川・深野川・阿井川の魚類確認種一覧。元報告書の実施年を各種の調査年へ流用しない |
| HIY | [広島県・八幡川水系流域の現状](https://www.pref.hiroshima.lg.jp/soshiki/99/1172477579468.html) | 上中流と河口部の魚類説明。**アユは稚魚放流の記載のみなので生息確認としては未採録**。木末川・石内川へ魚名を割り振らない |
| HIN | [広島県・江の川本川ブロック](https://www.pref.hiroshima.lg.jp/soshiki/99/1172196461943.html) | 支川の長瀬川にアカザ・カジカとの記述。保全配慮が必要 |
| OK19 | [岡山県・笹ヶ瀬川水系河川整備計画（平成31年2月）](https://www.pref.okayama.jp/uploaded/life/879682_8371002_misc.pdf) | 資料p5（PDF p7）。笹ヶ瀬川の上中下流と足守川を**区別**。足守川の希少種は公開前審査 |
| TO16 | [鳥取県・日野川水系指定区間河川整備計画（平成28年1月）](https://www.pref.tottori.lg.jp/secure/210292/hinogawasiteikukan_kasenseibikeikaku20160121.pdf) | 資料p19–20。日野川と**大川**を区別。アマゴの放流由来の可能性に留意し、今回の候補には含めない |
| YA07 | [山口県水産研究センター研究報告 第07号](https://www.pref.yamaguchi.lg.jp/uploaded/attachment/197780.pdf) | 佐波川水系**小島川**で2005年ヌマムツ確認、**長沢川水系**で2007年確認。後者は個別河川の確認に変換しない。PDF原本未通読 |
| YA04 | [山口県水産研究センター研究報告 第04号](https://www.pref.yamaguchi.lg.jp/uploaded/attachment/197775.pdf) | 表3オオクチバス生息河川/水系の旧資料。個別の本川確認に昇格させず**水系単位**で保留。PDF原本未通読 |

## 実際の追加候補と誤接続防止

1. **島根**：斐伊川水系の支川ごとに魚の資料掲載名を結び付けられる可能性がある。県・水系・川名の一致だけで全国10桁河川コードを確定しない。
2. **広島**：八幡川は湯来町に源を持つ。記事の幼少期の話と資料の川が**同じ川であるとは確認できない**。個人の記憶を出典の代わりに使わない。
3. **岡山**：笹ヶ瀬川と足守川は別河川。魚類リストの流用を禁止。
4. **鳥取**：日野川と大川は別河川。魚類の所属を水系全体へ広げない。
5. **山口**：水系レベルのオオクチバス分布資料を、個別河川の現在の確認種に変換しない。

## 次の監査（上位モデル・スクリプトで実施する対象）

1. 公式資料原本の魚名表・版・更新年月・転載条件を再点検。山口のPDF2件は特に全文確認。
2. 現行公開atlasの`atlas.json`・`fish_master.json`と**（県・水系・川・原文魚名・証拠種別）**単位で重複照合し、既存・新規・同名異川・曖昧を分類。
3. 河川コードは別の根拠で確定。**河川名が同じだけでは接続しない**。希少種の公開可否も別審査。
4. 承認済みだけを別の公開候補CSVに移し、検索UIへの追加前後で47県・既存結果・JS/HTMLの回帰テストを行う。

テスト：`python -m unittest discover -s river-fish/research-20261021 -p 'test_*.py' -v`

**出典・加工表記案**：各行の出典URLとともに「各県の河川整備計画・研究報告を基に、つりくえ！が魚名・河川名の掲載情報を整理（現在の生息や釣果を保証するものではありません）」。

## 第2便：本番の川名と魚の資料を照合する（読み取り専用）

- `audit_live_atlas_river_fish.py`：公開 `/river-fish-atlas/data/atlas.json` と `fish_master.json` を**GETのみ**で読み、124候補を「県＋水系＋川名」完全一致で比較。全国10桁河川コードを確定しない。候補IDが1件でも公開承認にはしない。
- `build_source_river_fish_layer.py`：個別河川名がある資料だけを使い、**川→魚**と**魚→川**の研究用双方向索引を生成。水系単位のみ・PDF未通読・保全要審査を自動除外。残った魚名も**資料掲載の事実**であり、現在の生息・釣果を保証しない。
- `.github/workflows/river-fish-live-atlas-audit-20261021.yml`：PR時に読み取り専用の実データ突合、ユニットテスト、研究用JSONと照合レポートをActions artifactに保存。**本番サイトへの書き込みなし**。

公開済み図鑑の初回照合（2026-10-21）では、124候補のうち15行が既存の名前に一意一致、92行は同一の県・水系・川名が見つからず、7行が保全要審査、残り10行が資料確認待ち・水系単位だった。一意一致15行は**2つの川名グループ**であり、15本の河川ではない。出典の川を図鑑側へ新規登録するための**資料由来の名称層**が必要。最新の集計はActionsの`summary.json`を優先する。

次は、未登録の資料由来河川名を、県・水系・出典・同名別河川の識別ができる独立索引に取り込む。公開atlasの511既存調査グループや1,057名称のみグループを**無断で書き換えない**。新規の川名は出典上の河川名であって全国河川コードが確定したものではない。

```bash
python -m unittest discover -s river-fish/research-20261021 -p 'test_*.py' -v
python river-fish/research-20261021/build_source_river_fish_layer.py --out /tmp/river_fish_source_layer_v01.json
python river-fish/research-20261021/audit_live_atlas_river_fish.py --out /tmp/river-fish-atlas-review
```

### オフライン操作プレビュー

Actionsの `river-fish-live-review` artifact に `river-fish-preview.html` を同梱。単体HTMLでネット接続なしでも、**県→川→資料掲載魚名**と、魚名ボタンを押して**魚→資料掲載河川**を逆引きできる。出典リンクを開くときだけネット接続が必要。

研究用の安全境界：資料未通読、保全要審査、水系だけの記録はデモに含めない。**公開サイトの図鑑に反映したものではない。** 元データに川名があっても、同名別河川・全国河川コード・調査地点の同一性を確定していない。

```bash
python river-fish/research-20261021/build_river_fish_preview.py --out /tmp/river-fish-preview.html
```

## 第3便：広島・黒瀬川を追加して川⇔魚を増やす（研究用v02）

既存の `river-fish/hiroshima_river_fish_narratives_v08.csv` にある、広島県公式「黒瀬川の河川環境概説」の**9魚名記録**を追加調査対象とする。このうち保全上の確認が必要な**2件は自動除外**し、7件だけを出典つきの研究用索引に接続。資料掲載日は観測年として扱わない。

- `build_river_fish_layer_v02.py`：前便の107件＋黒瀬川7件＝**114研究用魚名記録／12河川名グループ**の川→魚・魚→川索引を構築。全国河川コード・現在の生息・釣果は未確認。
- `build_river_fish_preview_v02.py`：スマホでも動く単体HTML。川の名前で探す・魚名ボタンから逆引き。保全要審査・未通読・水系だけの記録は含めない。
- `build_atlas_overlay_v02.py`：本番公開 `atlas.json` をGETで読み、**県＋水系＋川名**の完全一致で既存グループ候補を抽出。見つからない資料由来河川名も、追加候補として独立表示。完全一致でも**コード同一性・地点同一性・公開承認はしない**。
- Actions artifact `river-fish-live-review` にv02 JSON・オフラインプレビュー・公開図鑑との照合結果を保存。本番WordPress/Xserverへの書き込みは**ゼロ**。

重要：黒瀬川の資料は**特定採集地点や調査年を確定できない河川環境の説明**。実際にその川で現在釣れる魚の一覧として公開しない。元資料の魚名は分類学的な同定・生息確定と同義ではない。

```bash
python -m unittest discover -s river-fish/research-20261021 -p 'test_*.py' -v
python river-fish/research-20261021/build_river_fish_layer_v02.py --out /tmp/river-fish-layer-v02.json
python river-fish/research-20261021/build_river_fish_preview_v02.py --out /tmp/river-fish-preview-v02.html
python river-fish/research-20261021/build_atlas_overlay_v02.py --out /tmp/atlas-overlay-v02.json
```

## 第4便：国交省の調査原本から「水系＋個別河川名＋魚名」を直接取り出す（v03）

従来の全国 `watershed_year_fish.csv` は水系単位に集約されており、**支流の魚としては表示できない**。しかし、中国地方の国交省公開原本 `RT87_B01.zip` のワークブックには、別列 `M=河川名` が存在することが既存の収録確認ツールで判明している。今回、その原本を固定SHAで再取得し、次の**5列だけ**を読み取る。

- `C=生物項目`（`魚類` のみ採用、`魚介類` 混合区分は除外）
- `F=水系`
- `G=調査年度`
- `J=種名`（原文表記のまま）
- `M=河川名`（原本に明記された場合のみ）

抽出した5列から、`水系×河川名×年度×魚名` を重複除去してレビュー専用CSVへ保存。**地点名、調査地点コード、座標、区間、個体数、日時などは最初から読み込まない。** 都道府県・全国河川コードを推定しない。同名別河川の識別、保全対象の公開可否、資料の原記載の検証を経るまではサイトに出さない。

- コード：`extract_official_named_river_fish_v03.py`
- テスト：`test_official_named_river_fish_v03.py`
- CI：`.github/workflows/river-fish-official-named-river-v03.yml`
- 成果物：Actionsの`official-direct-named-river-fish-v03-review-only`。本番サイトへの書き込みはゼロ。
- 正式な「川→魚」接続に近づけるための、**水系一括付与ではない一次資料に基づく新しい候補層**。国交省の提供データに含まれない魚・河川は未確認であり、不在の証明ではない。

注意：原本の「河川名」は全国一意のIDではない。水系＋同名の河川が複数ある場合は個別の河川への割り当てを禁止する。魚の名前が書いてあっても、最新の生息や釣果を保証しない。

## 第5便：全国9地方の国交省調査原本から個別河川名×魚名を抽出（v04）

中国地方で確認した原本の5列（生物項目・水系・年度・魚名・**河川名**）を、国交省の**9地方**へ広げる。各地方の既存 `nationwide-staged/<region>/manifest.json` に保存済みの**配布ZIP URL・SHA256・原本行数・Excel名**を固定検証する。元の河川名列を直接読み、水系から個別河川への推定をしない。

- スクリプト：`extract_official_named_river_fish_nationwide_v04.py --region chugoku --out /tmp/review-chugoku`
- GitHub Actions：`river-fish-official-national-direct-v04.yml`（最大3地方ずつ、9地方独立の実原本検証）
- 成果物：地方別のレビュー専用CSVとmanifest（30日保存）。サイト・WordPress・Xserverには**未反映**。
- 「魚類」カテゴリのみ採用し、「魚介類」の混在区分は除外。地点・座標・細かな区間・個体数・日時は読み込まない。魚名の旧分類や保全上の公開可否、河川名の同一性は別途審査。
- **県名は原本から確定できないので推定しない。** 同じ河川名が別地域・水系にある場合も一括接続しない。

既存の全国 `watershed_year_fish.csv` は水系単位の調査結果であり、v04の個別河川候補とは根拠の粒度が違う。**数値を単純加算しない。** 新しい候補は実在の川名と魚名を結ぶ研究データであって、現在の生息・釣果を保証するものではない。
