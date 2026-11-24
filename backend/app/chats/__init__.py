"""
チャット機能パッケージ（app/chats）
- models.py     : チャットルーム（t_chat）・メッセージ（t_message）のDBモデル定義
- schemas.py    : チャット作成・メッセージ送受信の入出力データ検証（Pydanticスキーマ）
- service.py    : チャットルーム作成・一覧取得・メッセージ送信/履歴取得のビジネスロジック
- ws_manager.py : リアルタイムチャット用 WebSocket 接続管理マネージャー
- router.py     : /api/chats 配下のREST APIおよびWebSocketエンドポイント定義
"""
