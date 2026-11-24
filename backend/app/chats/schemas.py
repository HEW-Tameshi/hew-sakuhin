"""
チャット機能 入出力スキーマ定義モジュール（app/chats/schemas.py）

【このファイルの役割】
- Pydantic を用いて、チャットルームの作成/取得およびメッセージ送受信APIのリクエスト・レスポンスを定義する。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatCreateRequest(BaseModel):
    """
    チャットルーム作成・取得API（POST /api/chats）のリクエストスキーマ
    """

    matching_code: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="チャットを開始するマッチングコード（M + 9文字）",
    )

    @field_validator("matching_code")
    @classmethod
    def validate_matching_code(cls, value: str) -> str:
        """マッチングコードの前後空白を除去し、空文字でないことを確認する。"""
        value = value.strip()
        if not value:
            raise ValueError("マッチングコードを指定してください")
        return value


class ChatRoomResponse(BaseModel):
    """
    チャットルーム情報（作成・一覧・詳細）のレスポンススキーマ
    """

    chat_code: str
    matching_code: str
    letter_code: str
    title: str
    seller_code: str
    seller_nickname: str
    buyer_code: str
    buyer_nickname: str
    matching_status: int
    user_role: str  # "seller" または "buyer"
    created_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "chat_code": "C000000001",
                    "matching_code": "M000000001",
                    "letter_code": "L000000001",
                    "title": "ちょっとだけ話を聞いてほしい",
                    "seller_code": "U000001",
                    "seller_nickname": "出品者ユーザー",
                    "buyer_code": "U000002",
                    "buyer_nickname": "購入者ユーザー",
                    "matching_status": 1,
                    "user_role": "buyer",
                    "created_at": "2026-11-19T15:00:00",
                }
            ]
        }
    )


class MessageCreateRequest(BaseModel):
    """
    チャットメッセージ送信API（POST /api/chats/{chat_code}/messages）のリクエストスキーマ
    chat-room.html の maxlength="500" に合わせて 1〜500 文字で検証する。
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="送信するメッセージ本文（1〜500文字）",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        """メッセージの前後空白を除去し、空文字でないことを確認する。"""
        value = value.strip()
        if not value:
            raise ValueError("メッセージを入力してください")
        return value


class MessageResponse(BaseModel):
    """
    チャットメッセージ1件分のレスポンススキーマ
    """

    message_code: str
    chat_code: str
    sender_code: str
    sender_nickname: str
    message: str
    is_mine: bool
    sent_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message_code": "MSG000000001",
                    "chat_code": "C000000001",
                    "sender_code": "U000002",
                    "sender_nickname": "購入者ユーザー",
                    "message": "こんにちは！よろしくお願いいたします。",
                    "is_mine": True,
                    "sent_at": "2026-11-19T15:02:00",
                }
            ]
        }
    )
