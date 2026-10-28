
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """新規会員登録のリクエスト"""

    email: EmailStr = Field(
        ...,
        max_length=254,
        description="メールアドレス",
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="パスワード",
    )

    nickname: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="ニックネーム",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value.isascii():
            raise ValueError("パスワードは半角英数字・記号で入力してください")

        if not re.search(r"[A-Za-z]", value):
            raise ValueError("パスワードには英字を含めてください")

        if not re.search(r"\d", value):
            raise ValueError("パスワードには数字を含めてください")

        return value

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("ニックネームを入力してください")

        return value


class UserRegisterResponse(BaseModel):
    """新規会員登録のレスポンス"""

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
    """ログインAPIのリクエスト"""

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
    """ログインAPIのレスポンス"""
    user_code: str
    profile_code: str
    email: EmailStr
    nickname: str
    access_token: str
    token_type: str = "bearer"