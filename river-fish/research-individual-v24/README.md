# つりくえ！全国河川魚類図鑑 v0.24｜魚の名前から記録された川を逆引き

2026-10-20。研究用ZIP／研究ブランチのみ。本番WordPress、API、DB、mainへの反映は行わない。

## 読者ができること

従来の **都道府県 → 水系 → 河川 → 魚** に加えて、**魚の名前 → 過去の調査や環境DNAの元資料に登場する河川名グループ**を調べられるようにする。

- 原資料にある**魚の記載名**を部分一致検索。
- 川があるとされる県、元の水系・川名、証拠の調査方法（過去の魚類調査／DNA検出）を区別して表示。
- 見つかった元の調査グループをクリックすれば、元の魚カード、記録年・出典へ移動できる。
- **魚の生息を保証しない。** 環境DNAは捕獲・現地目視記録ではない。過去の調査記載名は現在の生息や地理同定の保証ではない。
- **所在地未確定195グループは「所在県未確定」入口のまま**閲覧できる。独断で県・河川コードを決めない。
- 逆引き対象の魚名は**分類状態が named_fish かつ記事草案あり**の記載名候補だけ。名前が未確定、別名・品種等の要審査26件、魚以外50件や属科レベル214件は「確定した独立魚種」として逆引き表示しない。
- 過去の調査記録と環境DNAは、同じ魚名・同じ元の川でも区別して持ち、「年範囲」は最初と最後の記録年であり途中の全年度に生息を確認した意味ではない。
- 中国地方の13水系参考魚データは個別河川に転用せず、これまでどおり独立の参考タブ。

## 成果物

- `outputs/river_fish_reverse_lookup_v24.zip`：魚名逆引き操作つきの研究用静的図鑑
- ZIP内部 `fish_to_river_reverse_v24.json`：正規化しない原資料記載名ごとの**元河川調査グループ参照**。出典別の手法・最早最遅年・元の都道府県選択肢を保持。
- `outputs/fish_to_river_reverse_evidence_v24.csv`：魚名×元河川調査グループの監査表
- `outputs/fish_to_river_reverse_qa_v24.json`：上流ZIPのSHA確認、連結数、保全範囲の監査記録

全て元の511河川名調査グループに属する実データJSONから生成。**1,057件の公式資料だけの掲載名に魚を新たに割り当てない。** ブラウザ用の新しいJSONは検索開始時にだけ遅延ロードする。

## 手元の再生成

```bash
python river-fish/research-individual-v19/build_evidence_v19.py
python river-fish/research-individual-v20/build_general_stars_v20.py
python river-fish/research-individual-v21/build_47pref_directory_v21.py
python river-fish/research-individual-v22/build_same_name_navigation_v22.py
python river-fish/research-individual-v23/build_chugoku_watershed_reference_v23.py
python river-fish/research-individual-v24/build_reverse_fish_index_v24.py
```

GitHub Actionsで元の魚データを再読して逆引きの妥当性、ZIP・JavaScript、疑似クリック試験、実データ「アユ」「eDNA記録」の画面表示と元の河川検索画面への遷移をチェック。実際のiPhone Safari・アクセシビリティ実機QAとデータライセンス最終審査は未完了。
