"""
ポイント・決済・サブスクリプション機能 APIテストモジュール（tests/test_points_api.py）

【このファイルの役割】
- ポイントプラン一覧取得、残高取得、ポイントチャージ、プレミアムサブスク加入/解約、
  およびレター購入・チップ送信時のポイント残高チェックと増減履歴記録を検証する。
"""

import uuid

from sqlalchemy import select

from app.post.models import EmotionCategory


def _register_and_login(client, prefix: str, nickname: str) -> dict:
    email = f"{prefix}_{uuid.uuid4().hex}@example.com"
    password = "Test1234"
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
        "user_code": reg.json()["user_code"],
        "headers": {"Authorization": f"Bearer {token}"},
    }


def test_point_plans_and_charge_and_subscription_flow(client):
    """プラン一覧→初期残高0→チャージ→履歴確認→サブスク加入/重複拒否/解約の一連の流れ"""
    # 1. プラン一覧取得（認証不要）
    plans_res = client.get("/api/points/plans")
    assert plans_res.status_code == 200
    plans = plans_res.json()
    assert len(plans["charge_plans"]) == 4
    assert plans["subscription_plan"]["price_yen"] == 700
    assert plans["subscription_plan"]["monthly_points"] == 700

    user = _register_and_login(client, "pt_user", "ポイントテスト会員")

    # 2. 初期残高は 0pt、サブスク未加入
    bal0 = client.get("/api/points/balance", headers=user["headers"])
    assert bal0.status_code == 200
    assert bal0.json()["balance"] == 0
    assert bal0.json()["has_active_subscription"] is False

    # 3. 定義外のポイント数（例：300pt）は HTTP 422
    bad_charge = client.post(
        "/api/points/charge",
        headers=user["headers"],
        json={"points": 300, "payment_method": 1},
    )
    assert bad_charge.status_code == 422

    # 4. 1000pt チャージ（950円）→ 残高 1000pt
    charge_res = client.post(
        "/api/points/charge",
        headers=user["headers"],
        json={"points": 1000, "payment_method": 1},
    )
    assert charge_res.status_code == 201
    c_data = charge_res.json()
    assert c_data["payment_code"].startswith("PAY")
    assert c_data["point_history_code"].startswith("PT")
    assert c_data["charged_points"] == 1000
    assert c_data["paid_amount_yen"] == 950
    assert c_data["balance_after"] == 1000

    # 5. プレミアムサブスク加入（月額700円・700pt付与）→ 残高 1700pt
    sub_res = client.post(
        "/api/points/subscription",
        headers=user["headers"],
        json={"payment_method": 1},
    )
    assert sub_res.status_code == 201
    s_data = sub_res.json()
    assert s_data["subscription_code"].startswith("SUB")
    assert s_data["price"] == 700
    assert s_data["status"] == 1
    assert s_data["granted_points"] == 700
    assert s_data["balance_after"] == 1700

    # 6. サブスク重複加入は HTTP 409 Conflict
    dup_sub = client.post(
        "/api/points/subscription",
        headers=user["headers"],
        json={"payment_method": 1},
    )
    assert dup_sub.status_code == 409

    # 7. サブスク契約情報取得＆残高確認
    get_sub = client.get("/api/points/subscription", headers=user["headers"])
    assert get_sub.status_code == 200
    assert get_sub.json()["subscription_code"] == s_data["subscription_code"]

    bal1 = client.get("/api/points/balance", headers=user["headers"])
    assert bal1.json()["balance"] == 1700
    assert bal1.json()["has_active_subscription"] is True

    # 8. ポイント履歴一覧（新しい順に 700pt, 1000pt の2件）
    hist = client.get("/api/points/history", headers=user["headers"]).json()
    assert len(hist) == 2
    assert hist[0]["point"] == 700
    assert hist[0]["point_type"] == 2
    assert hist[1]["point"] == 1000
    assert hist[1]["point_type"] == 1

    # 9. サブスク解約（DELETE /api/points/subscription）
    cancel_res = client.delete("/api/points/subscription", headers=user["headers"])
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == 2
    assert cancel_res.json()["end_date"] is not None

    # 解約後は未契約（404）になること
    assert client.get("/api/points/subscription", headers=user["headers"]).status_code == 404


def test_purchase_and_tip_point_balance_integration(client, test_session_factory):
    """購入時・チップ送信時の残高不足拒否（400）および正常時の双方ポイント増減を検証する"""
    seller = _register_and_login(client, "pt_seller", "ポイント出品者")
    buyer = _register_and_login(client, "pt_buyer", "ポイント購入者")

    with test_session_factory() as db:
        cat = db.scalar(
            select(EmotionCategory).where(EmotionCategory.category_code == "E01")
        )
        if cat is None:
            db.add(EmotionCategory(category_code="E01", category_name="喜"))
            db.commit()

    # 出品（120pt）
    post_res = client.post(
        "/api/posts",
        headers=seller["headers"],
        json={
            "title": "ポイント連動テスト",
            "content": "120ptの手紙です。",
            "category": "趣味",
            "time": 15,
            "point": 120,
            "emotion": "joy",
            "call": "no",
            "express": "no",
        },
    )
    letter_code = post_res.json()["letter_code"]

    # 1. 残高0ptのまま購入しようとすると HTTP 400（残高不足）
    short_buy = client.post(
        "/api/purchases",
        headers=buyer["headers"],
        json={"letter_code": letter_code},
    )
    assert short_buy.status_code == 400
    assert short_buy.json()["detail"] == "ポイント残高が不足しています"

    # 2. 購入者が 500pt チャージして 120pt の手紙を購入 → 購入者 380pt / 出品者 120pt
    client.post(
        "/api/points/charge",
        headers=buyer["headers"],
        json={"points": 500},
    )
    buy_res = client.post(
        "/api/purchases",
        headers=buyer["headers"],
        json={"letter_code": letter_code},
    )
    assert buy_res.status_code == 201
    matching_code = buy_res.json()["matching_code"]

    assert client.get("/api/points/balance", headers=buyer["headers"]).json()["balance"] == 380
    assert client.get("/api/points/balance", headers=seller["headers"]).json()["balance"] == 120

    # 3. 残高(380pt)を超えるチップ(500pt)でレビューしようとすると HTTP 400（残高不足）
    short_tip = client.post(
        "/api/reviews",
        headers=buyer["headers"],
        json={"matching_code": matching_code, "rating": 5, "tip_amount": 500},
    )
    assert short_tip.status_code == 400
    assert short_tip.json()["detail"] == "ポイント残高が不足しています"

    # 4. 100pt チップ付きでレビュー投稿 → 購入者 280pt / 出品者 220pt
    ok_tip = client.post(
        "/api/reviews",
        headers=buyer["headers"],
        json={
            "matching_code": matching_code,
            "rating": 5,
            "comment": "ありがとうございました！",
            "tip_amount": 100,
        },
    )
    assert ok_tip.status_code == 201
    assert client.get("/api/points/balance", headers=buyer["headers"]).json()["balance"] == 280
    assert client.get("/api/points/balance", headers=seller["headers"]).json()["balance"] == 220
