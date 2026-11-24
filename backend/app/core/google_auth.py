"""
Google認証（IDトークン検証）モジュール（app/core/google_auth.py）

【このファイルの役割】
- フロントエンド（Google Identity Services 等）から送信された Google ID トークン（JWT）を検証する。
- Google 公式の公開鍵エンドポイント（JWKS）を使用して、署名（RS256）・発行者（iss）・
  対象アプリ（aud = GOOGLE_CLIENT_ID）・有効期限（exp）・メール認証済み（email_verified）を確認する。
"""

from dataclasses import dataclass

import jwt
from jwt import PyJWKClient

from app.core.config import settings

# Google公式の公開鍵（JWKS）URL
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"

# Google IDトークンとして許可する発行者（iss）
GOOGLE_VALID_ISSUERS = (
    "https://accounts.google.com",
    "accounts.google.com",
)

# 公開鍵の取得・キャッシュを行うクライアント
_jwks_client = PyJWKClient(GOOGLE_JWKS_URL, cache_keys=True)


class GoogleAuthConfigError(RuntimeError):
    """サーバー側に GOOGLE_CLIENT_ID が設定されていない場合の例外"""
    pass


class GoogleTokenVerificationError(ValueError):
    """Google IDトークンの検証に失敗した場合（不正・期限切れ・メール未認証など）の例外"""
    pass


@dataclass(frozen=True)
class GoogleUserInfo:
    """検証済みGoogle IDトークンから取り出したユーザー情報"""

    sub: str
    email: str
    name: str | None = None
    picture: str | None = None


def verify_google_id_token(id_token: str) -> GoogleUserInfo:
    """
    Google IDトークン（JWT）を検証し、検証済みのユーザー情報（GoogleUserInfo）を返す。

    【処理の実行順序】
    1. サーバー設定に GOOGLE_CLIENT_ID が設定されているか確認する（未設定時は GoogleAuthConfigError）。
    2. Google の JWKS エンドポイントからトークンの kid に対応する公開鍵を取得する。
    3. RS256 アルゴリズムおよび audience=GOOGLE_CLIENT_ID で署名と有効期限（exp）を検証・デコードする。
    4. 発行者（iss）が Google であることを確認する。
    5. email が存在し、かつ email_verified が True であることを確認する。
    6. GoogleUserInfo を生成して返す。
    """
    if not settings.google_client_id:
        raise GoogleAuthConfigError("Google認証のクライアントID（GOOGLE_CLIENT_ID）が設定されていません")

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(id_token)
        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.google_client_id,
        )
    except Exception as exc:
        raise GoogleTokenVerificationError("Googleトークンの検証に失敗しました") from exc

    issuer = payload.get("iss")
    if issuer not in GOOGLE_VALID_ISSUERS:
        raise GoogleTokenVerificationError("Googleトークンの発行者が不正です")

    sub = payload.get("sub")
    email = payload.get("email")
    email_verified = payload.get("email_verified")

    if not sub or not email:
        raise GoogleTokenVerificationError("Googleアカウントのメールアドレスを取得できませんでした")

    if email_verified is not True:
        raise GoogleTokenVerificationError("Googleアカウントのメールアドレスが認証されていません")

    name = payload.get("name")
    picture = payload.get("picture")

    return GoogleUserInfo(
        sub=str(sub),
        email=str(email),
        name=str(name) if name else None,
        picture=str(picture) if picture else None,
    )
