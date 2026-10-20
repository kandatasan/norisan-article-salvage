# つりくえ！河川魚類図鑑 v0.23｜中国地方13水系の参考魚図鑑

2026-10-20。**研究ZIPにのみ実装、本番WordPress／API／DB／GitHub mainには反映しない。**

## やったこと

国土交通省『河川水辺の国勢調査』中国地方・河川版・魚類の既存検証済み集計（v0.5）を、**水系全体の参考魚記録としてだけ**閲覧できるようにした。

- **13水系**、**2,285件**の水系×調査年×原資料の魚類掲載名レコード（2006～2023年）、**216種類の資料上の魚名表記**。216は分類学的な魚種数ではない。
- 川単位の魚の記録・環境DNAの記録とは**別の折りたたみセクション**に表示。川で生息する魚と断定できないことを明記。
- 元の水系名が一致し、旧資料の地方区分が中国地方である河川名グループ、または中国5県の公式掲載名グループから参照可能。ただしこれも**地理的な同一水系の正式な同定ではない**。
- 魚名が編集マスター375草案の確定待ち名称と完全一致した場合だけ、既存の**一般★と一言メモ草案**を参考に添える。表記・分類が未照合なら星を作らない。
- JSONはページ読込時に全部埋め込まず、参考魚セクションを開いたときに**水系別に遅延読込**し、30件ずつ表示。
- 元の2,285行CSVはZIP内に一字も変更せず保存。重要種の詳細採集位置や生物採捕区間は持ち込まない。

## 調査原資料と利用条件

- [国交省・中国地方魚類元資料](https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B01.zip)
- [国交省・利用上のご注意点](https://www.nilim.go.jp/lab/fbg/ksnkankyo/Mokj_chui.htm)

公式の一般利用条件は商用利用を認める一方、出典表示・加工表示・第三者著作物の配慮を要求している。重要種の精密地点は公開対象から除外されている。**WordPressでの本番表示は依然未承認**。

## 検証

```bash
python river-fish/research-individual-v19/build_evidence_v19.py
python river-fish/research-individual-v20/build_general_stars_v20.py
python river-fish/research-individual-v21/build_47pref_directory_v21.py
python river-fish/research-individual-v22/build_same_name_navigation_v22.py
python river-fish/research-individual-v23/build_chugoku_watershed_reference_v23.py
```

Actionsで元ZIPのSHA、13水系の出典行、他の既存1,568掲載名の保持、明示的な支流魚データへの誤紐付けゼロ、JS構文、閲覧模擬操作、参考欄の遅延読込を検証する。DOM模擬はSafariなどの実機ブラウザ試験を代替しない。
