"""
会員機能 入出力スキーマ定義モジュール（app/users/schemas.py）

【このファイルの役割】
- Pydantic を用いて、会員登録・ログイン・Google認証・プロフィール取得/編集・パスワード変更/設定の
  リクエスト（入力値検証）とレスポンス（出力形式）を定義する。
- ルーター（router.py）で処理が始まる前に、文字数・メールアドレス形式・パスワード条件のチェックを自動で行う。
"""

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_password_strength(value: str) -> str:
    """
    パスワードの共通強度バリデーション：
    1. ASCII文字（半角英数字・記号）のみであること
    2. 英字（A-Z, a-z）を1文字以上含むこと
    3. 数字（0-9）を1文字以上含むこと
    """
    if not value.isascii():
        raise ValueError("パスワードは半角英数字・記号で入力してください")

    if not re.search(r"[A-Za-z]", value):
        raise ValueError("パスワードには英字を含めてください")

    if not re.search(r"\d", value):
        raise ValueError("パスワードには数字を含めてください")

    return value


class UserRegisterRequest(BaseModel):
    """
    新規会員登録API（POST /api/users/register）のリクエストスキーマ
    """

    email: EmailStr = Field(
        ...,
        max_length=254,
        description="メールアドレス",
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="パスワード（8〜128文字・半角英字と数字を各1文字以上含む）",
    )

    nickname: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="ニックネーム（1〜50文字）",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password_strength(value)

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("ニックネームを入力してください")
        return value


class UserRegisterResponse(BaseModel):
    """
    新規会員登録API（POST /api/users/register）のレスポンススキーマ
    ※会員登録時点ではJWTアクセストークンは発行しない。
    """

    user_code: str
    profile_code: str
    email: EmailStr
    nickname: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_code": "U000001",
                    "profile_code": "P000001",
                    "email": "sample@example.com",
                    "nickname": "サンプル",
                }
            ]
        }
    )


class UserLoginRequest(BaseModel):
    """
    ログインAPI（POST /api/users/login）のリクエストスキーマ
    """

    email: EmailStr = Field(
        ...,
        max_length=254,
        description="登録済みのメールアドレス",
    )

    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="ログインパスワード",
    )


class UserLoginResponse(BaseModel):
    """
    ログインAPI（POST /api/users/login）のレスポンススキーマ
    """

    user_code: str
    profile_code: str
    email: EmailStr
    nickname: str
    access_token: str
    token_type: str = "bearer"


class GoogleRegisterRequest(BaseModel):
    """
    Google認証による新規会員登録API（POST /api/users/google/register）のリクエストスキーマ
    """

    id_token: str = Field(
        ...,
        min_length=1,
        description="Google IDトークン",
    )

    nickname: str | None = Field(
        default=None,
        max_length=50,
        description="ニックネーム（任意・最大50文字）",
    )

    @field_validator("id_token")
    @classmethod
    def validate_id_token(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Google IDトークンを指定してください")
        return value

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("ニックネームを入力してください")
        return value


class GoogleLoginRequest(BaseModel):
    """
    Google認証によるログインAPI（POST /api/users/google/login）のリクエストスキーマ
    """

    id_token: str = Field(
        ...,
        min_length=1,
        description="Google IDトークン",
    )

    @field_validator("id_token")
    @classmethod
    def validate_id_token(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Google IDトークンを指定してください")
        return value


class GoogleAuthResponse(BaseModel):
    """
    Google新規登録API・GoogleログインAPIの共通レスポンススキーマ
    """

    user_code: str
    profile_code: str
    email: EmailStr
    nickname: str
    profile_image: str | None = None
    access_token: str
    token_type: str = "bearer"


class UserMeResponse(BaseModel):
    """
    ログイン中ユーザー情報取得API（GET /api/users/me）および
    プロフィール編集API（PATCH /api/users/me）のレスポンススキーマ
    """

    user_code: str
    profile_code: str
    email: EmailStr
    nickname: str
    profile_image: str | None = None
    introduction: str | None = None
    delivery_rank_id: int | None = None
    delivery_rank_name: str | None = None


class UserProfileUpdateRequest(BaseModel):
    """
    プロフィール・アカウント編集API（PATCH /api/users/me）のリクエストスキーマ
    Settings.html やプロフィール編集画面から、指定された項目だけを部分更新できる。
    """

    nickname: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="ニックネーム（1〜50文字）",
    )

    email: EmailStr | None = Field(
        default=None,
        max_length=254,
        description="メールアドレス（最大254文字）",
    )

    profile_image: str | None = Field(
        default=None,
        max_length=255,
        description="プロフィール画像URL・パス（最大255文字、空文字で削除）",
    )

    introduction: str | None = Field(
        default=None,
        max_length=1000,
        description="自己紹介文（最大1000文字、空文字で削除）",
    )

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("ニックネームを入力してください")
        return value

    @field_validator("profile_image")
    @classmethod
    def validate_profile_image(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value if value else None

    @field_validator("introduction")
    @classmethod
    def validate_introduction(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value if value else None


class PasswordChangeRequest(BaseModel):
    """
    パスワード変更API（PUT /api/users/me/password）のリクエストスキーマ
    """

    current_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="現在のパスワード",
    )

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="新しいパスワード（8〜128文字・半角英字と数字を各1文字以上含む）",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password_strength(value)


class GooglePasswordSetRequest(BaseModel):
    """
    Google登録会員向けパスワード設定API（PUT /api/users/me/password/google）のリクエストスキーマ
    Google IDトークンで本人再確認を行ったうえで、ログイン用パスワードを新規設定する。
    """

    id_token: str = Field(
        ...,
        min_length=1,
        description="本人再確認用のGoogle IDトークン",
    )

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="新しく設定するパスワード（8〜128文字・半角英字と数字を各1文字以上含む）",
    )

    @field_validator("id_token")
    @classmethod
    def validate_id_token(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Google IDトークンを指定してください")
        return value

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password_strength(value)


class MessageResponse(BaseModel):
    """完了メッセージ返却用の共通レスポンススキーマ"""

    message: str
