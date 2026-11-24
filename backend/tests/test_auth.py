from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token


def test_create_access_token():
    """アクセストークンを発行できること"""
    token = create_access_token("U96BZ2F")

    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token():
    """発行したトークンを検証できること"""
    token = create_access_token("U96BZ2F")

    payload = decode_access_token(token)

    assert payload["sub"] == "U96BZ2F"
    assert "exp" in payload
    assert "iat" in payload


def test_invalid_token():
    """無効なトークンを拒否すること"""
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("invalid.token.value")


def test_expired_token():
    """期限切れのトークンを拒否すること"""
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": "U96BZ2F",
            "iat": now - timedelta(minutes=10),
            "exp": now - timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)
