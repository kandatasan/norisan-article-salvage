# つりくえ！河川魚類図鑑 v0.25｜川の名前から全国の資料を直接検索

2026-10-20。研究版のみ。**GitHub main／本番 WordPress／公開API／MySQL は変更しない**。

## 読者向け改善

v0.24の「魚名から川を逆引き」と、従来の「都道府県→水系→川名」の間に、**川の名前を直接入力できる検索窓**を追加した。

- 全国47都道府県からの入口を維持しつつ、**元の調査資料511河川名グループ＋県などの公式掲載名1,057グループ**を川名・水系名の表記のまま横断検索する。
- 同じ名前の異なる可能性のある川を自動統合しない。メニューは県の元資料名・水系名・川名を表示し、元の出典詳細画面へ案内する。
- **「魚名が載った調査資料がある項目だけ」**の絞り込み。元の511グループの魚類原資料JSONを毎回検査し、実際に掲載魚名が存在するグループだけを表示する。
- 魚名の過去調査記録と**環境DNAの陽性記録**は区別。どちらも元の「資料記載名」であって、魚種数・現在の生息証明・採捕成功の保証ではない。
- 新たに魚が記録されていない公式掲載名には「川名資料・魚未接続」「水系名資料・魚未接続」と明示。「未接続＝いない」ではない。
- 25件ずつ読み進められ、読み込みは入力時だけ。個別調査JSONをブラウザへ一括展開しない。元の魚星349件／味160件／一言メモ375件は一切変更しない。

## 成果物

- `outputs/river_fish_direct_search_v25.zip`：検索窓と研究用のデータ一式
- ZIP内 `river_fish_label_counts_v25.json`：元の511グループごとに、過去調査の魚名掲載数と魚eDNA記載数を**別々に**計数。魚名の種の同定ではない
- `outputs/river_name_search_status_v25.csv`：元資料グループごとの掲載数・県の選択入口・未確定の地理的同一性
- `outputs/river_fish_direct_search_qa_v25.json`：SHA保全／ZIP検証／テストの集計

魚の記録が「0」の資料であってもその川に魚がいないという意味ではない。魚が載るのは過去の調査資料かDNA陽性の場合のみ。元の魚データ・河川名データ・v24逆引きのJSONはZIP内で**バイト単位で不変**。

## 研究版の再生成

```bash
python river-fish/research-individual-v19/build_evidence_v19.py
python river-fish/research-individual-v20/build_general_stars_v20.py
python river-fish/research-individual-v21/build_47pref_directory_v21.py
python river-fish/research-individual-v22/build_same_name_navigation_v22.py
python river-fish/research-individual-v23/build_chugoku_watershed_reference_v23.py
python river-fish/research-individual-v24/build_reverse_fish_index_v24.py
python river-fish/research-individual-v25/build_river_name_search_v25.py
```

GitHub Actionsでデータ数・魚の個別資料名の再集計・既存データバイト整合・JS構文・DOMモックでの検索→川選択→既存画面復帰・フィルター・逆引きと13水系参考パネルの回帰を確認。**実際のiPhone Safari／PC実機／アクセシビリティ・権利監査は完了していない**。
