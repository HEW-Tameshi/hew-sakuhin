"""
プロフィール編集・パスワード変更/設定・退会連動APIテストモジュール（tests/test_user_settings_api.py）

【このファイルの役割】
- PATCH /api/users/me（プロフィール・メール編集・重複拒否409）
- PUT /api/users/me/password（パスワード変更・現在パスワード不一致400・同一パスワード拒否400）
- PUT /api/users/me/password/google（Google登録会員のパスワード新規設定・別アカウント拒否403）
- DELETE /api/users/me（退会時の有効サブスク自動解約＆未終了通話の自動クローズ）
を検証する。
"""

import uuid
from unittest.mock import patch

from sqlalchemy import select

from app.calls.models import Call
from app.core.google_auth import GoogleUserInfo
from app.points.models import Subscription
from app.post.models import EmotionCategory


def _register_and_login(client, prefix: str, nickname: str, password: str = "Test1234") -> dict:
    email = f"{prefix}_{uuid.uuid4().hex}@example.com"
    reg = client.post(
        "/api/users/register",
        json={"email": email, "password": password, "nickname": nickname},
    )
    assert reg.status_code == 201
    login = client.post(
        "/api/users/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {
        "email": email,
        "password": password,
        "user_code": reg.json()["user_code"],
        "headers": {"Authorization": f"Bearer {token}"},
    }


def test_update_profile_and_email_duplicate_conflict(client):
    """プロフィール（ニックネーム・画像・自己紹介・メール）の部分更新とメール重複拒否（409）"""
    user1 = _register_and_login(client, "prof1", "変更前ニックネーム")
    user2 = _register_and_login(client, "prof2", "別ユーザー")

    # 1. ニックネーム・画像・自己紹介を更新
    res = client.patch(
        "/api/users/me",
        headers=user1["headers"],
        json={
            "nickname": "変更後ニックネーム",
            "profile_image": "images/custom.png",
            "introduction": "よろしくお願いします！",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["nickname"] == "変更後ニックネーム"
    assert data["profile_image"] == "images/custom.png"
    assert data["introduction"] == "よろしくお願いします！"
    assert data["email"] == user1["email"]

    # 2. 他ユーザーのメールアドレスへ変更しようとすると HTTP 409 Conflict
    dup_res = client.patch(
        "/api/users/me",
        headers=user1["headers"],
        json={"email": user2["email"]},
    )
    assert dup_res.status_code == 409

    # 3. 未使用のメールアドレスへ変更し、空文字で自己紹介を削除できること
    new_email = f"updated_{uuid.uuid4().hex}@example.com"
    res2 = client.patch(
        "/api/users/me",
        headers=user1["headers"],
        json={"email": new_email, "introduction": "   "},
    )
    assert res2.status_code == 200
    assert res2.json()["email"] == new_email
    assert res2.json()["introduction"] is None

    # GET /api/users/me でも最新情報が返ること
    me_res = client.get("/api/users/me", headers=user1["headers"])
    assert me_res.status_code == 200
    assert me_res.json()["email"] == new_email
    assert me_res.json()["nickname"] == "変更後ニックネーム"


def test_change_password_flow(client):
    """パスワード変更：不一致400・同一400・強度不足422・正常変更後に新パスワードでログイン可能"""
    user = _register_and_login(client, "pwd", "パスワードテスト", password="OldPassword1")

    # 1. 現在のパスワードが間違っている場合は HTTP 400
    wrong_res = client.put(
        "/api/users/me/password",
        headers=user["headers"],
        json={"current_password": "WrongPassword9", "new_password": "NewPassword2"},
    )
    assert wrong_res.status_code == 400

    # 2. 現在と同じパスワードを指定した場合は HTTP 400
    same_res = client.put(
        "/api/users/me/password",
        headers=user["headers"],
        json={"current_password": "OldPassword1", "new_password": "OldPassword1"},
    )
    assert same_res.status_code == 400

    # 3. 強度不足（数字なし）は HTTP 422
    weak_res = client.put(
        "/api/users/me/password",
        headers=user["headers"],
        json={"current_password": "OldPassword1", "new_password": "OnlyLetters"},
    )
    assert weak_res.status_code == 422

    # 4. 正常変更（HTTP 200）
    ok_res = client.put(
        "/api/users/me/password",
        headers=user["headers"],
        json={"current_password": "OldPassword1", "new_password": "NewPassword2"},
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["message"] == "パスワードを変更しました"

    # 旧パスワードではログイン不可（401）、新パスワードでログイン成功（200）
    assert client.post(
        "/api/users/login",
        json={"email": user["email"], "password": "OldPassword1"},
    ).status_code == 401
    assert client.post(
        "/api/users/login",
        json={"email": user["email"], "password": "NewPassword2"},
    ).status_code == 200


def test_set_password_for_google_registered_user(client):
    """Google登録会員がGoogle再認証でパスワードを新規設定し、メール＋パスワードでログインできること"""
    suffix = uuid.uuid4().hex
    email = f"g_pwd_{suffix}@example.com"
    fake_user = GoogleUserInfo(sub=f"sub-{suffix}", email=email, name="Google会員")
    other_google = GoogleUserInfo(sub=f"sub-other-{suffix}", email=f"other_{suffix}@example.com")

    with patch("app.users.router.verify_google_id_token", return_value=fake_user):
        reg_res = client.post(
            "/api/users/google/register",
            json={"id_token": "dummy-google-token"},
        )
        assert reg_res.status_code == 201
        headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}

    # 別アカウントのGoogleトークンでは HTTP 403 Forbidden
    with patch("app.users.router.verify_google_id_token", return_value=other_google):
        mismatch_res = client.put(
            "/api/users/me/password/google",
            headers=headers,
            json={"id_token": "other-google-token", "new_password": "SetPassword1"},
        )
        assert mismatch_res.status_code == 403

    # 本人のGoogleトークンでパスワード設定（HTTP 200）
    with patch("app.users.router.verify_google_id_token", return_value=fake_user):
        set_res = client.put(
            "/api/users/me/password/google",
            headers=headers,
            json={"id_token": "dummy-google-token", "new_password": "SetPassword1"},
        )
        assert set_res.status_code == 200

    # 設定したパスワードで通常ログインできること
    login_res = client.post(
        "/api/users/login",
        json={"email": email, "password": "SetPassword1"},
    )
    assert login_res.status_code == 200


def test_delete_account_cancels_subscription_and_ends_active_call(client, test_session_factory):
    """退会時に有効なプレミアムサブスクが自動解約され、進行中の通話も自動終了すること"""
    seller = _register_and_login(client, "del_sub_s", "退会連動出品者")
    buyer = _register_and_login(client, "del_sub_b", "退会連動購入者")

    with test_session_factory() as db:
        cat = db.scalar(
            select(EmotionCategory).where(EmotionCategory.category_code == "E01")
        )
        if cat is None:
            db.add(EmotionCategory(category_code="E01", category_name="喜"))
            db.commit()

    # 購入者がプレミアムサブスク加入（700pt付与）
    sub_res = client.post(
        "/api/points/subscription",
        headers=buyer["headers"],
        json={"payment_method": 1},
    )
    assert sub_res.status_code == 201
    sub_code = sub_res.json()["subscription_code"]

    # 出品→購入→通話開始
    letter_code = client.post(
        "/api/posts",
        headers=seller["headers"],
        json={
            "title": "退会連動テスト",
            "content": "テスト本文",
            "category": "日常・雑談",
            "time": 15,
            "point": 100,
            "emotion": "joy",
            "call": "yes",
            "express": "no",
        },
    ).json()["letter_code"]

    matching_code = client.post(
        "/api/purchases",
        headers=buyer["headers"],
        json={"letter_code": letter_code},
    ).json()["matching_code"]

    call_code = client.post(
        "/api/calls/start",
        headers=buyer["headers"],
        json={"matching_code": matching_code, "communication_type": 1},
    ).json()["call_code"]

    # 購入者が退会
    del_res = client.delete("/api/users/me", headers=buyer["headers"])
    assert del_res.status_code == 200

    # サブスクが自動解約（status=2, end_date設定済み）かつ通話が自動終了していること
    with test_session_factory() as db:
        sub = db.scalar(
            select(Subscription).where(Subscription.subscription_code == sub_code)
        )
        assert sub is not None
        assert sub.status == 2
        assert sub.end_date is not None

        call = db.scalar(select(Call).where(Call.call_code == call_code))
        assert call is not None
        assert call.ended_at is not None
        assert call.duration is not None
