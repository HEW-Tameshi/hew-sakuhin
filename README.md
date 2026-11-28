# こころのめぇ～る便

気持ちを手紙にのせて、相談したい人と話を聞きたい人をつなぐWebプロジェクトです。画面の表示言語は日本語です。

## プロジェクトの概要

このリポジトリには、ログイン、ホーム、出品、チャット、ポイント、プロフィール、レビューなどの画面があります。各画面はHTMLを入口に、`css/`のスタイル、`js/`の動作、`images/`の画像を読み込みます。

主な画面:

| ファイル | 内容 |
| --- | --- |
| `index.html` | ホーム。手紙の一覧、詳細、購入確認を表示 |
| `login.html` | ログインと新規登録 |
| `post.html` | 手紙の作成・出品 |
| `chat-room.html` | チャット画面 |
| `chat-record.html` | チャット履歴 |
| `point.html` | ポイント購入 |
| `profile.html` | プロフィール |
| `purchase-history.html` | 購入履歴 |
| `review1.html`、`review2.html` | レビューとレビュー結果 |
| `Settings.html` | 設定 |

## 起動方法（VS Code）

このプロジェクトは、まずフロントエンドをローカルWebサーバーで表示します。HTMLファイルを直接開く `file://` ではなく、Live Serverを使ってください。

1. VS Codeでこのリポジトリのフォルダーを開きます。
2. 拡張機能「Live Server」（Ritwick Dey）をインストールします。
3. `index.html`を開き、右下の **Go Live** を選びます。
4. ブラウザーでホームが開きます。通常のURLは `http://127.0.0.1:5501/index.html` です。
5. ログイン画面を確認するときは `http://127.0.0.1:5501/login.html` を開きます。

`.vscode/settings.json`でLive Serverのポートを`5501`に設定しています。Live Serverが起動中なら、HTML、CSS、JavaScriptの編集はブラウザーに自動反映されます。

### 自動起動を依頼するとき

Copilotなどの自動実行機能に起動を依頼する場合は、次のように伝えてください。

> このプロジェクトのルートでLive Serverを起動し、`http://127.0.0.1:5501/index.html`をブラウザーで開いてください。`file://`では開かないでください。

Live Serverが使えない場合は、Python 3がインストールされた環境で、プロジェクトのルートから次のコマンドを実行できます。

```powershell
python -m http.server 5501
```

その後、ブラウザーで `http://127.0.0.1:5501/index.html` を開きます。終了するときはサーバーを実行しているターミナルで `Ctrl+C` を押してください。

## バックエンドについて

現在の画面を表示するために、Flaskのサーバー起動は必要ありません。`requirements.txt`にはPythonのCIチェック用パッケージ（Flask、Ruff、pytest）が記載されていますが、このリポジトリには起動手順を定義したバックエンドのアプリケーションファイルはありません。バックエンドが追加された場合は、その実際の起動方法と設定を確認してから利用してください。

## 開発時のチェック

GitHub Actionsでは、HTML、CSS、JavaScript、およびPythonのチェックを行います。主なコマンドは次のとおりです。

```powershell
npx --yes htmlhint "**/*.html"
npx --yes stylelint "css/**/*.css"
Get-ChildItem js -Filter *.js | ForEach-Object { node --check $_.FullName }
python -m compileall -q .
ruff check .
```

CIではNode.js 22とPython 3.13を使用します。Pythonのチェックをローカルで行う場合は、先に依存パッケージをインストールしてください。

```powershell
python -m pip install -r requirements.txt
```

## 作業時の注意

- 画面ごとのCSSは`css/`、JavaScriptは`js/`にあります。
- 画像は`images/`にあります。既存の相対パスを保ってください。
- ホームからログイン、出品、レビューなどへのリンクは各HTMLファイル間を移動します。
- 依存関係や起動手順を変更した場合は、このREADMEも更新してください。
