"""
レビュー＆チップ機能パッケージ（app/reviews）
- models.py  : レビュー（t_review）・チップ/投げ銭（t_tip）のDBモデル定義
- schemas.py : レビュー投稿・チップ送信・評価一覧の入出力データ検証（Pydanticスキーマ）
- service.py : レビューとチップの1トランザクション登録、重複チェック、平均評価集計ロジック
- router.py  : /api/reviews 配下のFastAPIエンドポイント定義
"""
