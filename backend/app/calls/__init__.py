"""
通話機能パッケージ（app/calls）
- models.py     : 通話履歴（t_call）のDBモデル定義
- schemas.py    : 通話開始・終了・履歴取得の入出力データ検証（Pydanticスキーマ）
- service.py    : 通話開始・通話終了（通話時間計算）・通話履歴取得のビジネスロジック
- ws_manager.py : 通話申請・応答およびWebRTCシグナリング用 WebSocket 接続管理マネージャー
- router.py     : /api/calls 配下のREST APIおよびWebSocketエンドポイント定義
"""
