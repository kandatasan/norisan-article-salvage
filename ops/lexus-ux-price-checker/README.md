# つりくえ！ レクサスUX中古車相場価格 v0.3

## 画面・機能
- 4項目のみ：グレード（UX200 / 250h / 300h / 300e、全8種類の特別仕様車等）・年式（2018〜2026年、1年刻み）・走行（1万km幅）・ボディカラー（大分類）
- グレードの発売年前の年式を選べないようにする。初度登録年と発売・生産年のズレを考慮し、上限側は強制制限しない。
- 利用許諾済みレコードのみの支払総額中央値（最低3件）。45日を超えて古いデータは表示しない。
- 価格データがないときは、架空の相場を表示せずGoogleの条件付き検索に誘導。
- 利用者が自分で見つけた掲載車3台以上の支払総額を入力して、手元で中央値を計算する任意の折りたたみ機能を追加（入力は送信されない）。
- 広告と明示したガリバーの既存A8自由テキストリンクを設置。非公開在庫の有無や割安さを保証しない。

## 特別仕様車・年式（レクサス公式発表）
- UX200: Blue Edition(2020), Urban Elegance(2020), F SPORT Style Blue(2021), F SPORT Emotional Explorer(2022), Graceful Explorer(2022)
- UX250h: Brown Edition(2020), Urban Elegance(2020), F SPORT Style Blue(2021), Elegant Black(2021), F SPORT Emotional Explorer(2022), Graceful Explorer(2022)
- UX300h: F SPORT Emotional Explorer(2024), Graceful Explorer(2024), Shining Essence(2026・追加設定グレード)
- UX300e: version C, version L(2020〜)

## データ受け入れ条件
`data/ux-prices.json` の `license_status=approved`, `public_display_allowed=true`, `price_basis=total` と、`updated_at` が45日以内である必要がある。`records` の各要素：
`model` (200/250h/300h/300e), `grade` (base/c/fs/l/特別仕様車ID), `year` (初度登録年), `mileage_km` (整数), `color` (white/black/silver/blue/red/other), `total_price_yen` (支払総額・円), `permission_status=approved`, `price_basis=total`, `source_url` (http(s) URL)。
カタログのメーカー希望小売価格は中古車の掲載販売価格とは異なる。混同しないこと。

## 公開までの保留事項
- グーネット等からの無断スクレイピング・転載はしない。
- 運営元プロトコーポレーションの「自動車データベース」など、契約に基づくBtoC表示許諾を得る。使用料金と許諾範囲は未確認。
- 外部API・データ供給契約が成立しない限り「条件別の中古車相場金額を自動表示する機能」は稼働しない。現行は条件付き検索＋任意手入力比較機能。
- 既存A8自由テキストの広告条件、公開前車両情報への導線が遷移先で利用できることを確認。
- GitHub main・WordPress現状をチェックした後、PR→監査→ステージング検証→本番公開する。河川図鑑の既存自動デプロイ先に混ぜない。

## 公式出典
- https://cpo.lexus.jp/catalog/ux.html
- https://global.toyota/jp/newsroom/lexus/31088353.html
- https://global.toyota/jp/newsroom/lexus/32097951.html
- https://global.toyota/jp/newsroom/lexus/33759881.html
- https://global.toyota/jp/newsroom/lexus/35872760.html
- https://global.toyota/jp/newsroom/lexus/37532287.html
- https://global.toyota/jp/newsroom/lexus/41712619.html
- https://global.toyota/jp/newsroom/lexus/44513119.html
- https://global.toyota/jp/newsroom/lexus/40218670.html
- https://global.toyota/jp/newsroom/lexus/34009601.html
- https://www.proto-g.co.jp/product/mobility/cardb/
- https://221616.com/services/hikokai/