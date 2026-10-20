# 日本の河川大図鑑 v0.9 — 選んだ河川・分類の生物名だけを高速取得

2026-10-20 JST、研究ブランチ：`research/river-biota-lazy-four-panels-20261020`。  
**本番WordPress・既存API・Xserver/MySQLは変更していない。**

## 目標の操作構造が研究用ローカル画面でつながった

**都道府県 → 水系（生物リストなし） → 河川 → 魚類／底生動物／鳥類／植物の4つの窓**

- 47都道府県を最初の選択肢として表示。
- 県の公式資料名と国の河川コード台帳を照合した **28道府県・80件の水系入口**を表示（全47県に完成したわけではない）。
- 水系を押すと、そこに関連する **生物調査名義の河川名**を表示。元の河川名ベースの428IDと県水系リンク489件を再利用。
- 河川を押したら4つの分類窓が登場。分類を選ぶと **元の生物掲載名を20件ずつ**取得できる。
- 調査年度、文脈記録件数、原典URLが各名前に付属。
- 河川コードなしでも対応。河川の所在地・合流先・都道府県に直接所属することは推測しない。

### 軽さの工夫

前段 v0.8には河川×分類×生物掲載名254,574組・歴史的調査文脈553,351件がある。ただし、**これをスマホへ最初に全部送らない**。

v0.9は localhost 専用の読み取りAPIを追加した：

| 画面操作 | サーバーの応答 |
|---|---|
| 都道府県を開く | 47件の県名・水系掲載数だけ |
| 広島県を押す | 公的資料に根拠のある水系入口だけ |
| 太田川水系を押す | 資料名から照合した河川名だけ |
| 三篠川を押す | 4分類の件数と掲載名数を先に表示 |
| 魚類を押す | **魚類の掲載名20件だけ** |
| 「さらに表示」を押す | 次の20件を表示 |

サーバーは v0.8 の **SQLite索引**を使う。ブラウザへ74MBのDBを配らずに済む。

## 実データを使ったAPIブラックボックス検査

GitHub Actionsで標準PythonのローカルHTTPサーバーを起動し、**6種類のブラックボックス検査を実行して全て成功**。

- 三篠川（広島・太田川水系）の魚類：**25掲載名／67過去調査文脈**。20件＋残り5件のページングを確認。アユなどの実掲載名と元資料のURLも確認。
- 筑後川水系・宝満川：**河川コードなしでも底生動物94掲載名／124文脈**を返す。魚類は記録0件で、不在の断定はしない。
- 根谷川の鳥類：**0件のまま**。太田川水系全体の鳥類は流用しない。
- 広島県の太田川・芦田川という入口を検索できる一方、**熊本県の大野川、愛媛県の渡川**など、同名別水系の誤結合候補を表示しない。
- 存在しない県、存在しない県×水系、無効なIDや分類、過大なページング要求は正常に拒否。
- 画面HTMLのサイズ・JavaScript構文・iframeなし・250k件の埋め込みなしを確認。

QAファイル：`outputs/http_blackbox_qa_v09.json`。
GitHub Actions：https://github.com/kandatasan/norisan-article-salvage/actions/runs/39348284640

### 構成

- `run_local_atlas_v09.py` — 127.0.0.1／localhost 以外にはバインドできない、読み取り専用の試作HTTPサーバー。CORS許可なし、入力制限、`limit<=50`、安全なJSON応答。
- `index.html` — スマホ向け2列カード、パンくず、絞り込み、4分類、20件ずつの「さらに表示」。**iframe・外部JSライブラリなし**。生物の名は DOM の `textContent` で描画。
- `test_local_atlas_v09.py` — 実データを読む6件のHTTPテスト。
- `outputs/http_blackbox_qa_v09.json` — 検証結果の保存。

**HTTP経路（研究用）**

- `GET /api/v1/prefectures`
- `GET /api/v1/watersheds?pref=広島県`
- `GET /api/v1/rivers?pref=広島県&watershed=太田川`
- `GET /api/v1/river/{identityKey}?category=fish&limit=20&offset=0`

### 自分のPCで起動する場合

このGitHubブランチをcheckoutし、標準Python 3.12以降を使う。v0.8保存済みSQLiteをまずSHA照合して復元する。

```bash
python river-fish/research-individual-v08/snapshot_parts_v08.py verify \
 --parts-dir river-fish/research-individual-v08/outputs \
 --db /tmp/river_biota_literal_names_v08.sqlite

python river-fish/research-individual-v09/run_local_atlas_v09.py \
 --db /tmp/river_biota_literal_names_v08.sqlite \
 --nav river-fish/research-individual-v07/outputs/river_atlas_navigation_v07.json \
 --port 8877
```

そのPCで http://127.0.0.1:8877/ を開くと研究画面。**公開サイトではない**。Windows等で `/tmp` の代わりに任意のローカル保存先を指定しても良い。

## 残る課題

- GitHub ActionsでAPIのブラックボックス検査6件とブラウザ用JSの構文検査は完了。**iPhone Safari実機のタップ・PCブラウザの見た目・VoiceOverまでは検証していない**。
- 実際のWordPress環境に置くには、PHPなど別の本番向けAPIを開発・監査する必要がある。localhost Python サーバーをそのまま本番公開しない。
- v0.7時点で県から水系へ進めるのは28道府県。**19都道府県の水系照合、同名水系の15件保留、個々の河川の所在地検証**が引き続き必要。
- 元の生物掲載名は分類学的に正規化していない。属・科などは生物種数にカウントしない。希少種の詳細地点は一切含めないが、公開前には河川名レベルでの機微性や元の調査資料の再配布権限も監査する。
- 水系単位の生物記録を個別河川に流用しない。**県の水系入口があるだけで、その川が県内にあると断定しない**。

**研究用データも既存のWordPress下書きも破壊せず、GitHubの研究枝のみ更新。**
