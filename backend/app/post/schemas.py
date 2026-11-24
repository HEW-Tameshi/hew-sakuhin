"""
出品機能 入出力スキーマ定義モジュール（app/post/schemas.py）

【このファイルの役割】
- Pydantic を用いて、出品API（登録・一覧取得・詳細取得・編集・取り下げ）のリクエスト（入力値検証）とレスポンス（出力形式）を定義する。
- 会員登録（app/users/schemas.py）と同じ設計パターンで、文字数・数値範囲・必須入力・空白除去のチェックを行う。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 画面から送信される感情識別子（joy/angry/sad/fun）またはDBコード（E01〜E04）を
# m_emotion_category.category_code（E01〜E04）に統一する変換マップ
EMOTION_CODE_MAP = {
    "joy": "E01",    # 喜
    "angry": "E02",  # 怒
    "sad": "E03",    # 哀（画面表記：悲）
    "fun": "E04",    # 楽
    "E01": "E01",
    "E02": "E02",
    "E03": "E03",
    "E04": "E04",
}


class PostCreateRequest(BaseModel):
    """
    新規出品登録API（POST /api/posts）のリクエストスキーマ
    """

    # 見出し：1〜50文字
    title: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="見出し（1〜50文字）",
    )

    # 内容：1〜1000文字
    content: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="話したい内容（1〜1000文字）",
    )

    # カテゴリー（日常・雑談、趣味、恋愛・悩み、愚痴・ストレスなど）
    category: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="カテゴリー",
    )

    # 希望時間（分）：1以上の整数
    time: int = Field(
        ...,
        ge=1,
        description="希望時間（1分以上）",
    )

    # ポイント：1以上の整数
    point: int = Field(
        ...,
        ge=1,
        description="ポイント（1pt以上）",
    )

    # 感情（joy / angry / sad / fun または E01〜E04）
    emotion: str = Field(
        ...,
        min_length=1,
        description="感情（joy, angry, sad, fun または E01〜E04）",
    )

    # 通話の有無（yes / no）
    call: str = Field(
        ...,
        min_length=1,
        description="通話の有無（yes / no）",
    )

    # 速達の有無（yes / no）
    express: str = Field(
        ...,
        min_length=1,
        description="速達の有無（yes / no）",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        """見出しの前後空白を除去し、空文字でないことを確認する。"""
        value = value.strip()
        if not value:
            raise ValueError("見出しを入力してください")
        return value

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        """内容の前後空白を除去し、空文字でないことを確認する。"""
        value = value.strip()
        if not value:
            raise ValueError("内容を入力してください")
        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        """カテゴリーの前後空白を除去し、空文字でないことを確認する。"""
        value = value.strip()
        if not value:
            raise ValueError("カテゴリーを選択してください")
        return value

    @field_validator("emotion")
    @classmethod
    def validate_emotion(cls, value: str) -> str:
        """感情が定義済みの値か確認し、DBのcategory_code（E01〜E04）に変換して返す。"""
        value = value.strip()
        category_code = EMOTION_CODE_MAP.get(value)
        if category_code is None:
            raise ValueError("正しい感情を選択してください")
        return category_code

    @field_validator("call")
    @classmethod
    def validate_call(cls, value: str) -> str:
        """通話の有無が 'yes' または 'no' であることを確認する。"""
        value = value.strip()
        if value not in ("yes", "no"):
            raise ValueError("通話の有無を選択してください")
        return value

    @field_validator("express")
    @classmethod
    def validate_express(cls, value: str) -> str:
        """速達の有無が 'yes' または 'no' であることを確認する。"""
        value = value.strip()
        if value not in ("yes", "no"):
            raise ValueError("速達の有無を選択してください")
        return value


class PostUpdateRequest(PostCreateRequest):
    """
    出品編集API（PUT /api/posts/{letter_code}）のリクエストスキーマ
    入力項目と検証ルールは PostCreateRequest と共通。
    """
    pass


class PostCreateResponse(BaseModel):
    """
    新規出品登録API（POST /api/posts）および
    出品編集API（PUT /api/posts/{letter_code}）のレスポンススキーマ
    """

    letter_code: str
    seller_code: str
    category_code: str
    title: str
    content: str
    desired_duration: int
    point: int
    status: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "letter_code": "L000000001",
                    "seller_code": "U000001",
                    "category_code": "E01",
                    "title": "テスト見出し",
                    "content": "話したい内容のサンプルです。",
                    "desired_duration": 30,
                    "point": 100,
                    "status": 1,
                }
            ]
        }
    )


class PostDetailResponse(BaseModel):
    """
    出品一覧取得API（GET /api/posts）および
    出品詳細取得API（GET /api/posts/{letter_code}）のレスポンススキーマ
    """

    letter_code: str
    seller_code: str
    seller_nickname: str
    category_code: str
    category_name: str
    title: str
    content: str
    desired_duration: int
    point: int
    status: int
    created_at: datetime
    # ログイン中のユーザー自身の出品かどうか（画面側で編集・取り下げボタンの表示切替に使用）
    is_owner: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "letter_code": "L000000001",
                    "seller_code": "U000001",
                    "seller_nickname": "サンプルユーザー",
                    "category_code": "E01",
                    "category_name": "喜",
                    "title": "最近ハマっていることを話したい！",
                    "content": "最近すごくハマっている趣味があります！誰かと楽しく話したいです。",
                    "desired_duration": 15,
                    "point": 60,
                    "status": 1,
                    "created_at": "2026-11-18T15:00:00",
                    "is_owner": True,
                }
            ]
        }
    )


class PostDeleteResponse(BaseModel):
    """
    出品取り下げAPI（DELETE /api/posts/{letter_code}）のレスポンススキーマ
    """

    message: str
    letter_code: str
