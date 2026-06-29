# つりくえ！不通内部リンク整理計画

2026年6月27日のWordPressエクスポートXMLを、追加したdry-runスクリプトで検証した結果です。

- 対象URL種類数: **13**
- 対象リンク出現数: **23**
- 対象記事数: **10**
- 段落・リスト項目ごと削除: **22**
- aタグだけ解除して本文を残す: **1**
- 要確認: **0**

## 対象記事

| ID | 記事 | URL | 件数 | 処理 |
|---:|---|---|---:|---|
| 1883 | 島根半島の地磯で秋アオリイカ釣り | `/aoriika-nikki/` | 2 | 2件削除 |
| 1892 | 東広島ラーメン食べ歩き | `/higashihiroshima-ramen/` | 4 | 3件削除、1件aタグ解除 |
| 1939 | 広島から山陰へ1泊2日ドライブ旅 | `/hiroshima-sanin-1night-2days/` | 2 | 2件削除 |
| 2096 | 江田島オリーブファクトリー | `/oliveoil/` | 1 | 1件削除 |
| 2135 | 初めてでも簡単！秋アオリイカの釣り方 | `/kantan-aoriika/` | 2 | 2件削除 |
| 2152 | アオリイカとコタマガイのイカ墨パスタ | `/aoriika-oisiiyo/` | 2 | 2件削除 |
| 2157 | インコの羽で作った毛バリ | `/inkonohane-tsuretayo/` | 2 | 2件削除 |
| 2180 | 安芸津いろは寿司の海鮮丼 | `/irohasushi/` | 4 | 4件削除 |
| 2350 | フィッシングレイクたかみやで初フライ | `/kanritsuriba/` | 2 | 2件削除 |
| 2358 | シェアーズ エブリマン3実釣レビュー | `/everyman-iiyo/` | 2 | 2件削除 |

## 本文を残す1件

`/higashihiroshima-ramen/` 内の次の文章は、リンクだけ解除します。

```html
<p><a href="/hanabiramenn/">華火のラーメン</a>は、魚介系ダシで濃厚かつスッキリとした味わいが特徴。</p>
```

変更後:

```html
<p>華火のラーメンは、魚介系ダシで濃厚かつスッキリとした味わいが特徴。</p>
```

それ以外の22件は、未公開記事へ案内するためだけの段落またはリスト項目なので、Gutenbergの開始・終了コメントを含めてブロック単位で削除します。

## 対象URL

- `/fishingpage/`
- `/managed-fishing-area/`
- `/aoriika-fishing/`
- `/drive-gourmet/`
- `/higashihiroshima-gourmet/`
- `/hiroshima-gourmet/`
- `/iroha-sushi-akitsu-menu/`
- `/konomiseoishii/`
- `/sanin-sightseeing/`
- `/tottori-drive/`
- `/tougorouiwashi/`
- `/trout-cooking/`
- `/hanabiramenn/`
