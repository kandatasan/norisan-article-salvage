# つりくえ！ 全国河川DB v1.4 — 47都道府県に公式掲載資料の入口

実装：2026-10-18。**研究用GitHubデータ／WordPress本番未公開**。

## 今回の追加は「32都府県の公的名称掲載」439行

前段 v1.3 は北海道・青森・宮城・埼玉・新潟・長野・静岡・奈良・愛媛・福岡の10道県と、中国地方5県の公的資料掲載行を検索可能にした。

今回は**残る32都府県の公式HTMLページ**を確認し、名前の直接掲載が見つかったものから **439件** を出典付きで加えた。これにより、47都道府県すべてに「川・水系・河川整備計画圏域」のいずれかの一次資料掲載名がある。

| 収録した資料の種類 | 今回の掲載行 |
| --- | ---: |
| 川として資料に名前が載る行 | 160 |
| 水系名として載る行 | 269 |
| 河川整備計画の圏域として載る行 | 10 |
| **合計** | **439** |

**注意**：水系名269行は「269本の独立した河川」ではない。群馬県の10件は、河川や水系ではなく**整備計画の10圏域**。千葉県・東京都の河川は、元ページに**指定範囲や計画対象として出た川名**だけで、県全河川の網羅リストではない。

今回の県別の内訳：
岩手3／秋田4／山形6／福島19／茨城15／栃木3／群馬10／千葉35／東京67／神奈川14／富山13／石川10／福井4／山梨2／岐阜13／愛知6／三重7／滋賀7／京都10／大阪13／兵庫18／和歌山19／徳島11／香川14／高知24／佐賀11／長崎12／熊本25／大分16／宮崎2／鹿児島9／沖縄17。

### 検索イメージ

- 東京：都の河川整備計画対象に**神田川、善福寺川、妙正寺川、石神井川**などの川名が登場。
- 沖縄：流域治水計画に**国場川、安謝川、安里川**などの水系名が掲載、別の県資料に河川名も記載。**沖縄の国交省河川版魚類データは未配布**なので、魚がいないとは表示しない。
- 福島：第一級水系3件・二級水系の策定済基本方針16件（公式掲載範囲のみ）。
- 千葉：県の河川指定概要ページにある利根川水系の河川名掲載行35件（県全体の河川指定総数とは別）。
- 熊本：国・県の河川整備方針に掲載される8一級水系＋17二級水系の名称。
- 高知：県公式サイトに掲載される一級・二級水系名の中から24件。
- 長崎：県サイトでは**210の二級水系**について策定作業を進めると記載するが、今回登録したのは同ページで名前を読み取れた12行のみ。210全件を登録したとは言わない。
- 佐賀県の「伊万里川系」、高知県の「貝ノ川川」は**元ページのラベルのまま**。修正・分割・現行正式名への正規化は別審査が必要。

## データの形と安全対策

- `remaining_32pref_source_mentions_v14.csv`：名前・種類・資料で明示された水系名（ないときは空）・出典URL・ページ更新日（確認できるときのみ）・未承認状態。
- `remaining_32pref_manifest_v14.json`：32都府県、44出典グループ、種類別件数、未承認の全国コード・魚類紐付け状態を管理。
- `remaining_prefecture_registry_v14.py`：v1.3から**既存47都道府県枠、全国35,449件コード、全国18,814件の水系年別魚名**と各県資料を読み込んでSQLiteを生成。既存表の名前やキーは変更しない。
- `test_remaining_32pref_v14.py`：新規18の回帰テスト。東京都・千葉・沖縄などの実データ検索、圏域と水系・川の区別、以前の広島／北海道検索、現行コード・個別の魚の誤帰属を防ぐ。

全件「research_only_not_wordpress」なので、確認不足のデータがサイトへ流れ込むことはない。**47都道府県に一つ以上の公式資料名がある＝全国の全河川名を収録した、ではない**。一本ごとの正式な位置・県境・親川・公式10桁コードは、各出典と照合して承認する。名称の一致だけで県内の川として国コードに割り当てない。

全国の国交省魚類18,814件は**水系・年度・魚名表記**の組合せ。支流の魚類観測ではない。今回魚類レコードは増えていない。

## 主な公式出典（全URLは各掲載行に記録）

- [東京都建設局・河川整備計画](https://www.kensetsu.metro.tokyo.lg.jp/river/jigyo/kasenseibikeikaku)
- [千葉県・一級／二級河川](https://www.pref.chiba.lg.jp/kakan/shiryou/)
- [沖縄県・流域治水計画](https://www.pref.okinawa.jp/bosaianzen/bosai/1003493/1003571.html)／[水位周知河川](https://www.pref.okinawa.jp/bosaianzen/bosai/1003493/1003497.html)
- [福島県・策定済み方針と計画](https://www.pref.fukushima.lg.jp/sec/41045a/housinnkeikaku20.html)
- [熊本県・河川整備基本方針](https://www.pref.kumamoto.jp/soshiki/105/5775.html)
- [高知県・河川整備方針](https://www.pref.kochi.lg.jp/doc/kasen-keikaku-housinkeikaku/)
- [長崎県・河川整備方針](https://www.pref.nagasaki.jp/doc/page-714090.html)
- [和歌山県・19水系](https://www.pref.wakayama.lg.jp/prefg/080400/hoshin/kihonhosin.html)
- [岐阜県・河川整備計画](https://www.pref.gifu.lg.jp/page/133.html)
- [京都府・河川整備基本方針](https://www.pref.kyoto.jp/kasen/1297298822071.html)

## 動かし方

```bash
python river-fish/remaining_prefecture_registry_v14.py --build --db /tmp/river47.sqlite
python river-fish/remaining_prefecture_registry_v14.py --db /tmp/river47.sqlite --prefecture 東京都 --name 神田川
python river-fish/remaining_prefecture_registry_v14.py --db /tmp/river47.sqlite --prefecture 沖縄県 --name 国場川
python river-fish/remaining_prefecture_registry_v14.py --db /tmp/river47.sqlite --prefecture 群馬県 --kind planning_region
python -m unittest discover -s river-fish -p 'test_remaining_32pref_v14.py' -v
```

## 次工程

1. PDFでなくHTMLの表とPDF台帳を県ごとに絞り込み、川と水系の**名称候補を更に追加**。書き換え前に出典年月・漢字外字・同名異河川・利用許諾を検査。
2. 国の10桁河川コードとの県内での同一性を、地域台帳・実際の観測所所在地など**第三の出典**で確認。
3. 出典で川そのものを調査した魚の記録だけ個別河川に追加し、希少種の位置は公開しない。
4. 公開前の権利・出典確認が完了した情報をWordPressの検索画面へ段階的に反映。

**GitHubのデータ／検索コードのみ。記事・下書き・スラッグ・画像・WordPress本番DBは未変更。**
