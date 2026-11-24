"""
レビュー＆チップ機能 入出力スキーマ定義モジュール（app/reviews/schemas.py）

【このファイルの役割】
- Pydantic を用いて、レビュー投稿API（チップ同時送信対応）・レビュー一覧・ユーザー評価集計の
  リクエストとレスポンスを定義する。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewCreateRequest(BaseModel):
    """
    レビュー投稿API（POST /api/reviews）のリクエストスキーマ
    review1.html に合わせて、評価（1〜5）・コメント・チップポイント（0以上）を受け取る。
    """

    matching_code: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="レビュー対象のマッチングコード（M + 9文字）",
    )

    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="星評価（1〜5の整数）",
    )

    comment: str | None = Field(
        default=None,
        max_length=1000,
        description="レビューコメント（任意・最大1000文字）",
    )

    tip_amount: int = Field(
        default=0,
        ge=0,
        le=100000,
        description="感謝のチップポイント（0の場合はチップなし）",
    )

    @field_validator("matching_code")
    @classmethod
    def validate_matching_code(cls, value: str) -> str:
        """マッチングコードの前後空白を除去し、空文字でないことを確認する。"""
        value = value.strip()
        if not value:
            raise ValueError("マッチングコードを指定してください")
        return value

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, value: str | None) -> str | None:
        """コメントの前後空白を除去し、空文字のみの場合は None に正規化する。"""
        if value is None:
            return None
        value = value.strip()
        return value if value else None


class ReviewResponse(BaseModel):
    """
    レビュー1件分（投稿直後・一覧取得）のレスポンススキーマ
    """

    review_code: str
    matching_code: str
    reviewer_code: str
    reviewer_nickname: str
    reviewee_code: str
    reviewee_nickname: str
    rating: int
    comment: str | None = None
    tip_code: str | None = None
    tip_amount: int = 0
    created_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "review_code": "R000000001",
                    "matching_code": "M000000001",
                    "reviewer_code": "U000002",
                    "reviewer_nickname": "購入者ユーザー",
                    "reviewee_code": "U000001",
                    "reviewee_nickname": "出品者ユーザー",
                    "rating": 5,
                    "comment": "親身になって寄り添って話を聞いてくれた。",
                    "tip_code": "T000000001",
                    "tip_amount": 100,
                    "created_at": "2026-11-20T11:30:00",
                }
            ]
        }
    )


class UserReviewSummaryResponse(BaseModel):
    """
    ユーザー別評価サマリーAPI（GET /api/reviews/user/{user_code}）のレスポンススキーマ
    平均評価（average_rating）・総件数（review_count）・受信レビュー一覧を返す。
    """

    user_code: str
    nickname: str
    review_count: int
    average_rating: float | None = None
    reviews: list[ReviewResponse]
