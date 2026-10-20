# 日本の河川大図鑑 v0.8：個別河川の生物名・全文検索索引

作成：2026-10-20 JST。研究ブランチ：`research/river-biota-full-name-index-20261020`。

**本番WordPress・API・Xserver/MySQLの変更はゼロ。** v0.5の公開前研究SQLiteをSHA256検証して「読み取り専用」で参照し、別ファイルへ軽量化した生物掲載名索引を新規生成。

## いちばん大きな改善

v0.7の画面は都道府県→水系→河川→4分類へ進めたが、各分類には実データの「例」しか表示していなかった。v0.8では、**魚類・底生動物・鳥類・植物の元調査にある掲載名を全部保持**。どの川で、何年の資料に、どの表記が登場したかまで読める。

| 指標 | 実測 |
|---|---:|
| データを検索できる個別河川名ID | **428**（変化なし） |
| 生物記録の4分類窓 | **1,712**（428×4） |
| 過去調査の河川別文脈記録 | **553,351**（変化なし） |
| **河川×分類×資料掲載名の組合せ** | **254,574行** |
| 掲載名×原典資料の対応 | **254,574行** |
| 元データの参照資料ファイル | 45 |
| 4分類のうち記録未確認の窓 | 456 |
| 新しい検索用SQLite | 74.7MB、gzip圧縮後 **14.5MB**（2分割） |

注意：**254,574は種数ではない**。同じアユの名前が複数の河川にあれば別の組合せとして数え、属・科・同定未確定名・表記揺れもそのまま保存。「記録件数」は年度などの調査文脈であり、個体数・現在の生息数でもない。

### 分類別に索引化できた件数

| 分類 | 過去調査文脈 | 河川×分類×生物掲載名 |
|---|---:|---:|
| 魚類 | 25,843 | 11,772 |
| 底生動物 | 92,576 | 58,351 |
| 鳥類 | 64,691 | 25,233 |
| 植物 | 370,241 | 159,218 |
| **合計** | **553,351** | **254,574** |

### 実際に取得できた例

**広島県関連の太田川水系・三篠川**

- 魚類の過去調査文脈67件、調査資料の掲載名25表記、年度2009～2023。
- 上位に、**アユ、イトモロコ、オイカワ、カワムツ、カワヨシノボリ、ギギ**などの掲載名。
- 同じ三篠川の底生動物464文脈／244掲載名、鳥類214文脈／68掲載名、植物1,347文脈／589掲載名を保持。
- 魚類のデータベースで生物名ごとに参照した年度範囲、調査元URL・元データハッシュの一覧を取得可能。

**九州地方の筑後川水系・宝満川（10桁コード未確認のまま検索可能）**

- 底生動物124文脈／94資料掲載名／1993～2003年。
- **Polypedilum属、Stictochironomus属、イシビル科、イトミミズ科、ミズムシ**などの原本表記を保存。
- 魚類は個別河川記録0であり、生息しないという断定ではない。
- 植物492文脈／262掲載名、鳥類6文脈／5掲載名も保存。

ここでの「掲載名」は科・属等の同定階級を含むため、「25魚種」「94種」とは言わない。

## 作成物と使い方

- `build_full_literal_name_index_v08.py`：元研究DBを読み取り専用で参照して、すべての河川×4分類×原文名称の索引・調査年・元資料URL/ハッシュを作成。元の553,351行が減っていないか独立検算。
- `read_full_literal_name_index_v08.py`：任意の水系・川名・分類で検索。名前の一覧を20件ずつ取得し、さらにページを進められる。河川コードは不要。
- `snapshot_parts_v08.py`：SQLiteをSHA256付き分割gzipでGitHubに保管し、別のSQLiteへ復元、整合性を確認。
- `outputs/river_biota_category_counts_v08.csv`：428河川×4分類の記録数・掲載名数・最古／最新調査年度。
- `outputs/all_taxa_label_audit_v08.json`：照合結果、ゼロ件の分類窓、分類別件数、元データ不変の検証結果。
- `outputs/hiroshima_misasagawa_fish_v08.json`：三篠川の魚類を実際に検索した例。
- `outputs/kyushu_homangawa_benthic_v08.json`：宝満川の底生動物を検索した例。
- `outputs/chubu_mibugawa_birds_v08.json`：三峰川の鳥類を検索した例。
- `outputs/river_biota_literal_names_v08.sqlite.gz.part000`～`part001`、`outputs/snapshot_parts_v08.json`：実際に再構成できるSQLite本体。

使い方（このリポジトリをcheckoutし、v08分割DBを復元した後）：

```bash
python river-fish/research-individual-v08/snapshot_parts_v08.py verify \
  --parts-dir river-fish/research-individual-v08/outputs \
  --db /tmp/river_biota_literal_names_v08.sqlite

python river-fish/research-individual-v08/read_full_literal_name_index_v08.py \
  --db /tmp/river_biota_literal_names_v08.sqlite \
  --region chugoku --watershed 太田川 --river 三篠川 --category fish --limit 25

python river-fish/research-individual-v08/read_full_literal_name_index_v08.py \
  --db /tmp/river_biota_literal_names_v08.sqlite \
  --region kyushu --watershed 筑後川 --river 宝満川 --category benthic_animals \
  --limit 25 --offset 25
```

GitHub Actions の成功ログ：
https://github.com/kandatasan/norisan-article-salvage/actions/runs/39347271213

## UIへつなぐときの方針

利用者の理想は **都道府県→水系（生物なし）→河川→魚類・底生動物・鳥類・植物の4窓**。

大きなSQLiteをブラウザへ丸ごと配るのではなく、画面は軽い428河川索引だけロードし、**河川を押して分類を開いた時だけ**新v0.8索引へ問い合わせるAPIを追加するのが適切。

- カテゴリ一覧は各河川の掲載名数・歴史的記録件数・年代を先に返す。
- タップ後は1ページ20～50件ずつ、資料原文の生物名と出典、調査年度を返す。
- 同一水系の別の川に、生物名を横流ししない。
- 未確認は「個別河川の調査記録は未確認」。水系の記録や別県の同名河川と混ぜない。
- プライバシー・希少種の詳細位置・第三者の権利と引用・データ再配布の利用条件を、本番公開前に別途監査。
- 都道府県別の実際の河川所在地は、v0.7で「県の公式資料による水系ナビゲーション」と別に保持。**その県内の川だと確証がないものは所在地として表示しない**。

**現時点ではAPIもWordPressも更新していない。** GitHubの研究ブランチに索引・検索プログラム・復元可能なDBがある。
