
from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User
from app.models.token import RevokedToken

bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """JWTを検証し、ログイン中の有効なユーザーを取得する。"""

    if credentials is None:
        raise unauthorized("認証が必要です")

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise unauthorized("無効または期限切れのアクセストークンです")

    user_code = payload.get("sub")
    jti = payload.get("jti")

    if not user_code or not jti:
        raise unauthorized("無効なアクセストークンです")

    revoked_token = db.scalar(
        select(RevokedToken).where(RevokedToken.jti == jti)
    )
    if revoked_token is not None:
        raise unauthorized("このアクセストークンは失効しています")

    user = db.scalar(
        select(User).where(User.user_code == user_code)
    )

    if user is None:
        raise unauthorized("ユーザーが見つかりません")

    if user.account_status != 1:
        raise unauthorized("退会済みのアカウントです")

    return user


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """認証トークンのペイロードを取得する。"""

    if credentials is None:
        raise unauthorized("認証が必要です")

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise unauthorized("無効または期限切れのアクセストークンです")

    if not payload.get("sub") or not payload.get("jti"):
        raise unauthorized("無効なアクセストークンです")

    return payload
