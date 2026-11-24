"""
チャット用 WebSocket 接続管理モジュール（app/chats/ws_manager.py）

【このファイルの役割】
- チャットルーム（chat_code）ごとに、現在オンラインで接続している WebSocket クライアント一覧を管理する。
- 新しいメッセージが送信された際、同じチャットルームに参加している出品者・購入者へ即座に配信（ブロードキャスト）する。
"""

from collections import defaultdict

from fastapi import WebSocket


class ChatConnectionManager:
    """チャットルーム単位の WebSocket 接続マネージャー"""

    def __init__(self) -> None:
        # key: chat_code, value: (WebSocket, user_code) のリスト
        self._rooms: dict[str, list[tuple[WebSocket, str]]] = defaultdict(list)

    async def connect(self, chat_code: str, websocket: WebSocket, user_code: str) -> None:
        """WebSocket 接続を受け入れ、対象チャットルームへ登録する。"""
        await websocket.accept()
        self._rooms[chat_code].append((websocket, user_code))

    def disconnect(self, chat_code: str, websocket: WebSocket) -> None:
        """切断された WebSocket を対象チャットルームから除外する。"""
        if chat_code not in self._rooms:
            return
        self._rooms[chat_code] = [
            (ws, code) for ws, code in self._rooms[chat_code] if ws is not websocket
        ]
        if not self._rooms[chat_code]:
            del self._rooms[chat_code]

    async def broadcast_message(self, chat_code: str, payload: dict) -> None:
        """
        対象チャットルームに接続中の全クライアントへ JSON ペイロードを送信する。
        受信者ごとに `is_mine`（自分の送信かどうか）を自動で付け分けて配信する。
        """
        connections = list(self._rooms.get(chat_code, []))
        sender_code = payload.get("sender_code")
        disconnected: list[WebSocket] = []

        for ws, user_code in connections:
            personalized = {
                **payload,
                "is_mine": (user_code == sender_code),
            }
            try:
                await ws.send_json(personalized)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(chat_code, ws)


# アプリ全体で共有するチャット接続マネージャーのシングルトンインスタンス
chat_ws_manager = ChatConnectionManager()
