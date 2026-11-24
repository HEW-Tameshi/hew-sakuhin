# CtoC Backend（こころのメェ～る便）

## 開発環境
- Python 3.13
- FastAPI / SQLAlchemy / Pydantic
- MySQL 8.x

## セットアップ（Windows / PowerShell）

1. Python仮想環境を作成する

   `py -m venv .venv`

2. 仮想環境を有効化する

   `.\.venv\Scripts\Activate.ps1`

3. ライブラリをインストールする

   `python -m pip install -r requirements.txt`

4. 環境設定ファイルを作成する

   `Copy-Item .env.example .env`

5. `.env` に自分のMySQL接続情報・JWT秘密鍵・GoogleクライアントID・Gemini APIキーを設定する

## 起動方法（`backend/` ディレクトリ内で実行）

`uvicorn main:app --reload`

## テスト実行方法（テスト用DB `kokoro_mail_test` を使用）

`pytest`

## APIドキュメント

起動後に `/docs` を開く。
