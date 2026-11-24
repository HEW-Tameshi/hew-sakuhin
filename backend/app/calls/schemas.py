"""
通話機能 入出力スキーマ定義モジュール（app/calls/schemas.py）

【このファイルの役割】
- Pydantic を用いて、通話開始API・通話終了API・通話履歴取得APIのリクエストとレスポンスを定義する。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CallStartRequest(BaseModel):
    """
    通話開始API（POST /api/calls/start）のリクエストスキーマ
    """

    matching_code: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="通話を行うマッチングコード（M + 9文字）",
    )

    communication_type: int = Field(
        default=1,
        description="通話種別（1: 音声通話 / 2: ビデオ通話）",
    )

    @field_validator("matching_code")
    @classmethod
    def validate_matching_code(cls, value: str) -> str:
        """マッチングコードの前後空白を除去し、空文字でないことを確認する。"""
        value = value.strip()
        if not value:
            raise ValueError("マッチングコードを指定してください")
        return value

    @field_validator("communication_type")
    @classmethod
    def validate_communication_type(cls, value: int) -> int:
        """通話種別が 1（音声通話）または 2（ビデオ通話）であることを確認する。"""
        if value not in (1, 2):
            raise ValueError("通話種別は 1（音声通話）または 2（ビデオ通話）を指定してください")
        return value


class CallResponse(BaseModel):
    """
    通話情報（開始・終了・詳細・履歴一覧）のレスポンススキーマ
    """

    call_code: str
    matching_code: str
    communication_type: int
    started_at: datetime
    ended_at: datetime | None = None
    duration: int | None = None
    is_active: bool

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "call_code": "CL00000001",
                    "matching_code": "M000000001",
                    "communication_type": 1,
                    "started_at": "2026-11-19T15:30:00",
                    "ended_at": "2026-11-19T15:45:00",
                    "duration": 900,
                    "is_active": False,
                }
            ]
        }
    )
