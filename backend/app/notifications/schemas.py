"""
通知機能 入出力スキーマ定義モジュール（app/notifications/schemas.py）

【このファイルの役割】
- Pydantic を用いて、通知一覧取得（未読件数付き）・既読更新APIのレスポンスを定義する。
"""

from datetime import datetime

from pydantic import BaseModel

NOTIFICATION_TYPE_LABELS: dict[int, str] = {
    1: "購入・マッチング",
    2: "メッセージ",
    3: "レビュー・チップ",
    4: "ランク・お知らせ",
}


class NotificationItemResponse(BaseModel):
    """通知1件分のレスポンススキーマ"""

    notification_code: str
    notification_type: int
    notification_type_label: str
    title: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    """通知一覧取得API（GET /api/notifications）のレスポンススキーマ"""

    unread_count: int
    notifications: list[NotificationItemResponse]


class NotificationReadAllResponse(BaseModel):
    """一括既読API（PATCH /api/notifications/read-all）のレスポンススキーマ"""

    message: str
    updated_count: int
