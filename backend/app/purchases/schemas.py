"""
購入・取引（マッチング）機能 入出力スキーマ定義モジュール（app/purchases/schemas.py）

【このファイルの役割】
- Pydantic を用いて、レター購入APIおよび購入に基づくマッチング管理APIのリクエスト・レスポンスを定義する。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PurchaseCreateRequest(BaseModel):
    """
    レター購入API（POST /api/purchases）のリクエストスキーマ
    """

    # 購入対象の感情レターコード（例：L000000001）
    letter_code: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="購入対象のレターコード（L + 9文字）",
    )

    @field_validator("letter_code")
    @classmethod
    def validate_letter_code(cls, value: str) -> str:
        """レターコードの前後空白を除去し、空文字でないことを確認する。"""
        value = value.strip()
        if not value:
            raise ValueError("購入するレターコードを指定してください")
        return value


class PurchaseCreateResponse(BaseModel):
    """
    レター購入API（POST /api/purchases）のレスポンススキーマ
    購入履歴コードと、購入に基づいて成立したマッチングコードを返す。
    """

    purchase_code: str
    matching_code: str
    letter_code: str
    seller_code: str
    buyer_code: str
    title: str
    purchase_point: int
    matching_status: int
    purchased_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "purchase_code": "P0000000001",
                    "matching_code": "M000000001",
                    "letter_code": "L000000001",
                    "seller_code": "U000001",
                    "buyer_code": "U000002",
                    "title": "嬉しい出来事を聞いてほしい",
                    "purchase_point": 150,
                    "matching_status": 1,
                    "purchased_at": "2026-11-18T16:30:00",
                }
            ]
        }
    )


class PurchaseDetailResponse(BaseModel):
    """
    購入履歴一覧取得API（GET /api/purchases）および
    購入詳細取得API（GET /api/purchases/{purchase_code}）のレスポンススキーマ
    """

    purchase_code: str
    matching_code: str
    letter_code: str
    seller_code: str
    seller_nickname: str
    buyer_code: str
    category_code: str
    category_name: str
    title: str
    content: str
    desired_duration: int
    purchase_point: int
    matching_status: int
    purchased_at: datetime
    completed_at: datetime | None = None


class MatchingDetailResponse(BaseModel):
    """
    マッチング一覧取得API（GET /api/purchases/matchings）および
    マッチング詳細取得API（GET /api/purchases/matchings/{matching_code}）のレスポンススキーマ
    出品者・購入者の双方から取引状況を確認するために使用する。
    """

    matching_code: str
    purchase_code: str
    letter_code: str
    seller_code: str
    seller_nickname: str
    buyer_code: str
    buyer_nickname: str
    category_code: str
    category_name: str
    title: str
    content: str
    desired_duration: int
    purchase_point: int
    matching_status: int
    user_role: str  # "seller"（自分が出品者）または "buyer"（自分が購入者）
    created_at: datetime
    completed_at: datetime | None = None


class MatchingStatusUpdateRequest(BaseModel):
    """
    マッチング状態更新API（PATCH /api/purchases/matchings/{matching_code}/status）のリクエストスキーマ

    【更新可能な status 値】
    - 2: 対話準備中
    - 3: 対話中
    - 4: 取引完了（completed_at を記録）
    - 5: 取引キャンセル
    """

    status: int = Field(
        ...,
        description="更新後のマッチングステータス（2: 準備中, 3: 対話中, 4: 取引完了, 5: キャンセル）",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: int) -> int:
        if value not in (2, 3, 4, 5):
            raise ValueError("ステータスには 2（準備中）、3（対話中）、4（取引完了）、5（キャンセル）のいずれかを指定してください")
        return value
