# つりくえ！全国河川魚類図鑑 v0.26｜実ブラウザQA・スマホ幅対応

2026-10-20。**研究統合ブランチ内限定。WordPress / 公開API / 本番DB / GitHub main への反映は行わない。**

## 目的

v0.24の「魚から川を探す」、v0.25の「川の名前から探す」、v0.23の「中国地方13水系の参考魚図鑑」について、JavaScriptを構文検査するだけでなく、**実際のヘッドレスChromiumで画面操作**まで確認する。

### 確認範囲

- 47都道府県の入口（所在地未確定195河川名グループの区別を含む）
- 「太田川」を川名検索→元の資料河川名グループへ移動
- 「魚名が載った調査資料だけ」フィルター
- 「アユ」を魚名で逆引き→元の川の資料へ移動
- 具体的な魚eDNA検出のラベルを、過去の調査と別に表示
- 中国地方13水系の参考魚記録をクリックして、個別河川の魚と区別する
- 390px幅での横スクロールの有無、巨大になっていた検索用チェックボックスの18px修正、長い河川名を持つボタンの折返し
- ページJavaScript例外と静的JSONのHTTP 404検出

実機Safariをテストしたとは言わない。Chromiumの390px幅による**模擬スマホ画面テスト**であり、iPhone実機・VoiceOver・回転・表示速度は別の公開前QA対象。

### ビルド

v0.25の研究用成果ZIPをSHA照合し、HTMLの一部CSSのみ改善。その他のZIP内容（元魚データ、1,568件の河川資料入口、魚名349件の逆引き、eDNA、中国地方水系参考、元出典リンク等）は**元ZIPとバイト単位で完全一致**する。

出力：

- `outputs/river_fish_browser_review_v26.zip` — 研究用全体プレビュー
- `outputs/river_fish_browser_review_qa_v26.json` — 元ZIP/不変性の検証
- `outputs/chromium_browser_qa_v26.json` — 本物のChromium自動操作結果
- `outputs/desktop-browser-v26.png` — ブラウザによるPC幅サンプル
- `outputs/mobile-width-browser-v26.png` — 390px幅サンプル

GitHub Actionsの研究専用成果物にZIP/JSON/画面キャプチャを添付し、サイト本番にはアップロードしない。
