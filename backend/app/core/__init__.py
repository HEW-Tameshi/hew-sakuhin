"""
共通基盤パッケージ（app/core）
- config.py        : 環境変数（.env）の読み込み管理
- database.py      : 開発・本番用DB（kokoro_mail）接続とセッション管理
- database_test.py : テスト専用DB（kokoro_mail_test）接続管理
- security.py      : JWTアクセストークンの生成・検証
- auth.py          : ログイン中ユーザーの認証・失効トークンチェック
- google_auth.py   : Google IDトークンの署名・発行者・メール認証検証
- gemini_client.py : Gemini API を呼び出してJSON構造化分析を行うクライアント
- testing_app.py   : テストDB接続済みのFastAPIアプリ定義
"""
