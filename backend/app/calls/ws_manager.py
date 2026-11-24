"""
通話シグナリング用 WebSocket 接続管理モジュール（app/calls/ws_manager.py）

【このファイルの役割】
- マッチング（matching_code）ごとに、通話待機・通話中の WebSocket 接続を管理する。
- 通話申請（call_request）・了承（call_accept）・拒否（call_reject）・
  WebRTCシグナリング（offer / answer / ice_candidate）・通話終了（call_end）を
  送信者以外の相手当事者へ中継（リレー）する。
"""

from collections import defaultdict

from fastapi import WebSocket


class CallSignalingManager:
    """マッチング単位の通話シグナリング用 WebSocket 接続マネージャー"""

    def __init__(self) -> None:
        # key: matching_code, value: (WebSocket, user_code) のリスト
        self._rooms: dict[str, list[tuple[WebSocket, str]]] = defaultdict(list)

    async def connect(self, matching_code: str, websocket: WebSocket, user_code: str) -> None:
        """WebSocket 接続を受け入れ、対象マッチングの通話ルームへ登録する。"""
        await websocket.accept()
        self._rooms[matching_code].append((websocket, user_code))

    def disconnect(self, matching_code: str, websocket: WebSocket) -> None:
        """切断された WebSocket を対象通話ルームから除外する。"""
        if matching_code not in self._rooms:
            return
        self._rooms[matching_code] = [
            (ws, code) for ws, code in self._rooms[matching_code] if ws is not websocket
        ]
        if not self._rooms[matching_code]:
            del self._rooms[matching_code]

    async def relay_to_peer(
        self,
        matching_code: str,
        sender_websocket: WebSocket,
        payload: dict,
    ) -> None:
        """送信者以外の接続相手（ピア）へシグナリングメッセージを転送する。"""
        connections = list(self._rooms.get(matching_code, []))
        disconnected: list[WebSocket] = []

        for ws, _ in connections:
            if ws is sender_websocket:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(matching_code, ws)

    async def broadcast_event(self, matching_code: str, payload: dict) -> None:
        """対象マッチングに接続中の当事者全員へ通話状態イベントを通知する。"""
        connections = list(self._rooms.get(matching_code, []))
        disconnected: list[WebSocket] = []

        for ws, _ in connections:
            try:
                await ws.send_json(payload)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(matching_code, ws)


# アプリ全体で共有する通話シグナリングマネージャー
call_ws_manager = CallSignalingManager()
