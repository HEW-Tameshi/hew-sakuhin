"""
Google認証（新規登録・ログイン）APIテストモジュール（tests/test_google_auth_api.py）

【このファイルの役割】
- POST /api/users/google/register（Google新規登録API）と
  POST /api/users/google/login（GoogleログインAPI）の正常系・異常系を検証する。
- verify_google_id_token をモックし、外部のGoogleサーバーへ通信せずに高速・確実にテストする。
"""

import uuid
from unittest.mock import patch

from sqlalchemy import delete, select

from app.core.google_auth import (
    GoogleAuthConfigError,
    GoogleTokenVerificationError,
    GoogleUserInfo,
)
from app.users.models import Profile, User


def test_google_register_and_login_success(client, test_session_factory):
    """Google認証での新規登録 → 重複登録拒否（409） → Googleログイン → /me 認証確認"""
    suffix = uuid.uuid4().hex
    email = f"google_{suffix}@example.com"
    user_code = None

    fake_google_user = GoogleUserInfo(
        sub=f"google-sub-{suffix}",
        email=email,
        name="Googleテストユーザー",
        picture="https://example.com/avatar.png",
    )

    try:
        with patch(
            "app.users.router.verify_google_id_token",
            return_value=fake_google_user,
        ):
            # 1. Google新規登録（nickname未指定時はGoogle表示名が使われる）
            reg_res = client.post(
                "/api/users/google/register",
                json={"id_token": "dummy-google-id-token"},
            )
            assert reg_res.status_code == 201
            reg_data = reg_res.json()

            user_code = reg_data["user_code"]
            assert user_code.startswith("U")
            assert reg_data["profile_code"].startswith("P")
            assert reg_data["email"] == email
            assert reg_data["nickname"] == "Googleテストユーザー"
            assert reg_data["profile_image"] == "https://example.com/avatar.png"
            assert reg_data["access_token"]
            assert reg_data["token_type"] == "bearer"

            # 2. 同じGoogleアカウントで再度新規登録しようとすると HTTP 409 Conflict になること
            dup_res = client.post(
                "/api/users/google/register",
                json={"id_token": "dummy-google-id-token"},
            )
            assert dup_res.status_code == 409
            assert dup_res.json()["detail"] == "このメールアドレスは既に登録されています"

            # 3. Googleログイン（HTTP 200 OK）
            login_res = client.post(
                "/api/users/google/login",
                json={"id_token": "dummy-google-id-token"},
            )
            assert login_res.status_code == 200
            login_data = login_res.json()
            assert login_data["user_code"] == user_code
            assert login_data["email"] == email
            assert login_data["access_token"]

            # 4. 発行されたJWTアクセストークンで GET /api/users/me が使えること
            me_res = client.get(
                "/api/users/me",
                headers={"Authorization": f"Bearer {login_data['access_token']}"},
            )
            assert me_res.status_code == 200
            assert me_res.json()["user_code"] == user_code

    finally:
        if user_code:
            with test_session_factory() as db:
                user = db.scalar(select(User).where(User.user_code == user_code))
                if user is not None:
                    db.execute(delete(Profile).where(Profile.user_id == user.user_id))
                    db.delete(user)
                    db.commit()


def test_google_login_unregistered_and_deleted_user_returns_401(client, test_session_factory):
    """未登録アカウントおよび退会済みアカウントのGoogleログインは HTTP 401 になること"""
    suffix = uuid.uuid4().hex
    email = f"google_del_{suffix}@example.com"
    user_code = None

    fake_google_user = GoogleUserInfo(
        sub=f"google-sub-{suffix}",
        email=email,
        name="退会テストGoogleユーザー",
    )

    try:
        with patch(
            "app.users.router.verify_google_id_token",
            return_value=fake_google_user,
        ):
            # 1. 未登録状態でGoogleログインすると 401
            unregistered_res = client.post(
                "/api/users/google/login",
                json={"id_token": "dummy-google-id-token"},
            )
            assert unregistered_res.status_code == 401

            # 2. Google新規登録して退会する
            reg_res = client.post(
                "/api/users/google/register",
                json={
                    "id_token": "dummy-google-id-token",
                    "nickname": "カスタムニックネーム",
                },
            )
            assert reg_res.status_code == 201
            assert reg_res.json()["nickname"] == "カスタムニックネーム"
            user_code = reg_res.json()["user_code"]
            token = reg_res.json()["access_token"]

            del_res = client.delete(
                "/api/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert del_res.status_code == 200

            # 3. 退会後に再度Googleログインしようとすると 401
            after_delete_login = client.post(
                "/api/users/google/login",
                json={"id_token": "dummy-google-id-token"},
            )
            assert after_delete_login.status_code == 401

    finally:
        if user_code:
            with test_session_factory() as db:
                user = db.scalar(select(User).where(User.user_code == user_code))
                if user is not None:
                    db.execute(delete(Profile).where(Profile.user_id == user.user_id))
                    db.delete(user)
                    db.commit()


def test_google_auth_invalid_token_and_missing_config(client):
    """無効なGoogleトークン時は 401、GOOGLE_CLIENT_ID未設定時は 503 を返すこと"""
    with patch(
        "app.users.router.verify_google_id_token",
        side_effect=GoogleTokenVerificationError("Googleトークンの検証に失敗しました"),
    ):
        res_reg = client.post(
            "/api/users/google/register",
            json={"id_token": "invalid-token"},
        )
        assert res_reg.status_code == 401

        res_login = client.post(
            "/api/users/google/login",
            json={"id_token": "invalid-token"},
        )
        assert res_login.status_code == 401

    with patch(
        "app.users.router.verify_google_id_token",
        side_effect=GoogleAuthConfigError("Google認証のクライアントID（GOOGLE_CLIENT_ID）が設定されていません"),
    ):
        res_cfg = client.post(
            "/api/users/google/login",
            json={"id_token": "any-token"},
        )
        assert res_cfg.status_code == 503
