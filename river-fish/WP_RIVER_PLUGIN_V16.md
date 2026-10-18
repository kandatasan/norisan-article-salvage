# WordPress用・全国河川検索プラグイン v1.6（導入準備版）

## 目的と現状

v1.5で作成したオフライン河川検索を、WordPress / MySQLに対応させる。全国35,449件の10桁コード、水系×調査年度の魚名18,814件、県別資料1,449掲載行を**サーバーの専用DBテーブルに格納**し、読者には20件ずつ表示する。

**現段階はGitHubでZIP制作＋テストのみ。XserverやWordPress本番への設置・有効化・データ投入・記事公開はしない。**

## データ取り扱い

- 取込用のCSVはプラグイン内の `data/` に格納し、Apacheの `.htaccess` で直接公開を拒否する。Webサーバーによってはルールが効かないため、公開データだとしてもサーバー構成を確認する。
- 3テーブル：\`wp_tsr_river_codes\`／\`wp_tsr_river_sources\`／\`wp_tsr_watershed_fish\`（\`wp_\` はサイトの実際のプレフィックスに置換）。
- コード表には県を付けず、魚名表には川のコードや県を付けない。
- 県別の河川名・水系名・整備計画圏域を分け、各資料のURL／調査時点／原表の地域を表示する。
- 公開API：\`GET /wp-json/tsurikue-rivers/v1/search\`、\`mode=codes|local|fish\`、\`q\`、\`page\`、\`per_page\`。必要なモードでは \`prefecture\`, \`kind\`, \`region\`, \`watershed\` も利用可能。
- \`per_page\` は最大25、\`page\` は最大2000。SQLは \`$wpdb->prepare\` でエスケープ。未取込時はHTTP 503。
- \`[tsurikue_river_search]\` でSWELLの下書きページに専用検索UIを設置可能。ライブラリや大きな全件データは公開ページで読み込まない。
- ユーザー入力とデータベース値はJS \`textContent\` で表示。出典URLは \`https\` の \`.jp\` ドメインだけリンクとして表示。
- インポートは **手動で開始**、nonce＋\`manage_options\` を必須、1回300行ずつ。対象世代のCSVのSHA256とDB最終件数が一致した場合だけ新世代に切替。途中切断・更新失敗では旧世代を維持。
- WordPress記事、カテゴリ、スラッグ、既存投稿のメタデータやメディアを一切編集しない。
- \`uninstall.php\` による自動DROPも作らず、無効化ではデータを削除しない。完全削除は別の管理手順で行う。

## 管理者が操作する工程（ZIP検証・同意後）

1. バックアップを確保。
2. 管理画面 → プラグイン → 新規追加 → **プラグインのアップロード** → 同梱ZIP選択 → 有効化。
3. 「ツール → 全国河川DB」で取込開始。約55,712行を分割取込。ブラウザを閉じて停止した場合は再開可能。
4. ステータスが「取込完了」になったら、**非公開の下書き**にショートコード \`[tsurikue_river_search]\` を入れてプレビュー。
5. 「諸木川（全国コード）」「沖縄県・国場川（県別資料）」「アユ（魚類記録）」の出典・誤帰属・画面崩れを確認。
6. 一般公開はライセンス・資料再確認と、ユーザーによる別途公開判断の後。

## GitHubでのZIP生成

\`\`\`bash
python river-fish/build_wp_plugin_v16.py --out /tmp/wp-river-build --zip /tmp/tsurikue-river-search.zip
python -m unittest discover -s river-fish -p 'test_wp_plugin_v16.py' -v
\`\`\`

\`.github/workflows/river-fish-wp-plugin-v16.yml\` がPRとmain反映でパッケージング・PHP構文・データ検査・WordPress実機相当の一時環境確認を行い、インストール用ZIPを30日間Artifactsに添付する予定。

配布ZIPは \`tsurikue-river-search/\` ディレクトリを起点とし、PHPとCSS/JS以外に、データ3CSVとSHA256署名ではない**完全性チェック用ハッシュ**のmanifestを同梱。改ざん検知のための暗号署名ではない。鍵管理は別途必要。

## 現行の未完項目

- 47都道府県の全河川網羅・支流別魚種確認・現在の管理区分は未達。
- 県別名称情報は一次資料の掲載行であって、河川の正確な現行位置の検証ではない。
- Xserverの実際のPHP/MySQLバージョンと利用可能ディスク容量は、設置前に確認が必要。
- 本番ショートコードの表示はサイト上で未検証。SWELLのCSS競合やスマホ実機確認が必要。
- 公的資料の公開利用条件・加工表示はサイト公開前に再監査する。
