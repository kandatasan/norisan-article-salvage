# つりくえ！河川図鑑：GitHub → Xserver 導入手順

## 目的と重要な前提

現在の公開ソースはXserverにあり、GitHub内の旧ビルダーは `xserver-release-v028` までです。v0.28を誤って再公開しないよう、先にXserverの現行版をGitHubに取り込む仕組みを作りました。

導入は2段階です。

1. **bootstrap-pr**：Xserverの選択フォルダを読み取ってGitHubにドラフトPRを作る。サーバーは変更しない。
2. **deploy-staging**：PRの内容をレビューしてmainにマージした後、GitHubのソースをXserverの専用テストフォルダに自動転送。

**本番 `public_html/river-fish-atlas` は変更しません。** WordPressと `biota` も変更しません。本番切り替えは別PRで、バックアップ・復旧・ブラウザ実動作確認を追加してから行います。

## 最初の1回だけ必要な設定

XserverでSSHを有効にし、公開鍵認証の鍵ペアを用意してください。Xserverの現行マニュアルでSSHホスト・ユーザー・ポートを確認してください。本Workflowの接続ポートは **10022** です。

GitHubリポジトリ `kandatasan/norisan-article-salvage` の「Settings → Secrets and variables → Actions」に次の4つを設定してください。

- `XSERVER_SSH_HOST`：SSHホスト名（ポートは含めない）
- `XSERVER_SSH_USER`：SSHユーザー
- `XSERVER_SSH_PRIVATE_KEY`：鍵の秘密鍵全文（改行を保ったまま）
- `XSERVER_SSH_KNOWN_HOSTS`：事前に指紋を確認したSSHホスト鍵のknown_hostsエントリ（10022番のときは `[host]:10022` 形式）

秘密鍵はチャット・GitHub Issue・PR・公開リポジトリへ貼り付けないでください。known_hostsは無検証のssh-keyscanをそのまま登録せず、ホスト鍵の指紋をXserverの信頼できる情報と照合してください。

GitHub ActionsによるPRの作成がリポジトリ設定で禁止されている場合、`bootstrap-pr` は最後に停止します。作成権限の有効化は設定を理解してから行ってください。

任意でGitHub `Settings → Environments` に `river-atlas-staging` を作成し、main以外からの実行を制限してください。Workflow自体もmainからの手動実行に限定されています。GitHubプランによって一部の承認機能は異なります。

## 1. Xserverの現行版をGitHubに取り込む

1. mainへの導入PRをマージする。
2. リポジトリのActionsで「River atlas Xserver GitHub staging」を開き、「Run workflow」。
3. `operation = bootstrap-pr` を指定。
4. `source_dir` は実際の現行版を見て `river-fish-atlas` または `river-fish-atlas-v0291` を選択。ファイル名だけで最新版と決めつけない。
5. Workflowはソースを読み取り、JSON・HTML・XMLサイトマップ・ファイル種別・容量を検証した後、**ドラフトPR**を作ります。
6. データの著作権・出典情報・公開してよいファイルか・差分を人が確認してからmainへマージしてください。

注意：このリポジトリは公開設定です。インポートすると静的ファイルが公開GitHubのPRに載ります。サイト上で既に公開済みのファイルだけが対象か点検してください。取り込むのはHTML/JSON/XML/TXT/CSVだけで、PHPやdotfileは取り込みません。

## 2. GitHubからテスト用フォルダへ自動転送

1. 取り込みPRを確認後にmainへマージ。
2. 同じActionsで `operation = deploy-staging` を選択し手動実行。
3. `river-fish/xserver-git/source/` の静的ファイルを検証し、Xserverの **`$HOME/tsurikue.com/public_html/river-fish-atlas-ci-preview/`** だけを同期します。
4. previewのHTML・XMLサイトマップ・JSONをHTTPSから取得してスモークテストします。

確認URL：

https://tsurikue.com/river-fish-atlas-ci-preview/index.html

previewにはX-Robots-Tag `noindex, nofollow` を付与します。テスト先のHTML内に本番canonicalが残る場合でも、テスト結果を本番SEO完了の証拠とは扱いません。

## 3. 次の段階

- 都道府県・川名・魚名の3タブをブラウザで実際に動作検査
- 全国の原資料・出典URLの404を監査し、同一資料の移転先が確認できたものだけ修正
- ページとサイトマップのcanonical整合性検証
- 旧公開版バックアップ、ロールバック、本番切り替え用の手動承認
- WordPress内にある検索ツールと独立版の更新ルートを分離して確認

## 停止条件

SSH接続不可、ホスト鍵検証失敗、rsyncがXserverで使えない、ソースの構造不一致、JSON破損、フォルダ名が想定外の場合は止まります。自動で本番に切り替える機能は含まれていません。
