
# CtoC Backend

## 開発環境
- Python
- FastAPI
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

5. `.env` に自分のMySQL接続情報を設定する

## 起動方法

`uvicorn app.main:app --reload`

## APIドキュメント

起動後に `/docs` を開く。
