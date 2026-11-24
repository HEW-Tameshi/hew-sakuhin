"""
通知機能パッケージ（app/notifications）
- models.py  : 通知（t_notification）のDBモデル定義
- schemas.py : 通知一覧・未読件数・既読更新の入出力データ検証（Pydanticスキーマ）
- service.py : 通知作成ヘルパー（他機能連動用）・一覧取得・既読更新ロジック
- router.py  : /api/notifications 配下のFastAPIエンドポイント定義
"""
