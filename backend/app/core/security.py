"""
セキュリティ・JWTトークン管理モジュール（app/core/security.py）

【このファイルの役割】
- ログイン成功時に発行する JWT（JSON Web Token）アクセストークンの生成を行う。
- クライアントから送られてきた JWT アクセストークンの署名・有効期限を検証し、中身（ペイロード）を取り出す。
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from app.core.config import settings

# JWTの署名アルゴリズム（HMAC-SHA256）
ALGORITHM = "HS256"


def create_access_token(user_code: str) -> str:
    """
    指定された会員コード（user_code）に対するJWTアクセストークンを生成する。

    【処理の流れ】
    1. 現在時刻（UTC）と有効期限（現在時刻 + 設定分数）を計算する。
    2. トークンに含める情報（sub: 会員コード, jti: トークン固有ID, iat: 発行時刻, exp: 有効期限）を作成する。
    3. 秘密鍵（jwt_secret_key）で署名して文字列のトークンを返す。
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=settings.jwt_expire_minutes
    )

    payload = {
        "sub": user_code,       # 誰のトークンかを表す識別子（会員コード）
        "jti": str(uuid4()),    # ログアウト時の失効管理に使う一意のトークンID
        "iat": now,             # 発行日時（Issued At）
        "exp": expires_at,      # 有効期限（Expiration Time）
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """
    JWTアクセストークンを検証・復号し、ペイロード（辞書）を返す。
    ※改ざんされている場合や有効期限切れの場合は jwt.InvalidTokenError（または派生例外）が発生する。
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[ALGORITHM],
    )
