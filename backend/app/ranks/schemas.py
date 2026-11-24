"""
会員ランク機能 入出力スキーマ定義モジュール（app/ranks/schemas.py）

【このファイルの役割】
- Pydantic を用いて、ランクマスタ（m_member_rank）の登録・一覧取得、
  およびログイン中ユーザーの現在ランク＆次ランク進捗（review2.html / profile.html 用）を定義する。
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class MemberRankCreateRequest(BaseModel):
    """
    会員ランクマスタ登録API（POST /api/ranks）のリクエストスキーマ
    """

    rank_name: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="ランク名（最大20文字、例：Lv1, Lv2, ゴールド など）",
    )

    required_point: int = Field(
        ...,
        ge=0,
        description="このランクに到達するために必要な累計獲得ポイント（0以上）",
    )

    @field_validator("rank_name")
    @classmethod
    def validate_rank_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("ランク名を入力してください")
        return value


class MemberRankResponse(BaseModel):
    """会員ランクマスタ1件分のレスポンススキーマ"""

    rank_id: int
    rank_name: str
    required_point: int
    created_at: datetime


class UserRankProgressResponse(BaseModel):
    """
    ログイン中ユーザーのランク進捗API（GET /api/ranks/me）のレスポンススキーマ
    profile.html（ランク表示）および review2.html（Lv1〜Lv2進捗バー・あと〇〇pt）に対応する。
    """

    user_code: str
    total_earned_points: int
    current_rank_id: int | None = None
    current_rank_name: str | None = None
    next_rank_id: int | None = None
    next_rank_name: str | None = None
    next_required_point: int | None = None
    points_to_next_rank: int | None = None
    progress_percent: int = Field(..., ge=0, le=100)
