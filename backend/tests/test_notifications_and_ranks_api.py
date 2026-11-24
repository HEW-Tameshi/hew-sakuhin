"""
通知機能＆会員ランク機能 APIテストモジュール（tests/test_notifications_and_ranks_api.py）

【このファイルの役割】
- 会員ランクマスタの登録・一覧取得（POST/GET /api/ranks）
- 累計獲得ポイントに応じた自動ランク判定・昇格・次ランク進捗取得（GET /api/ranks/me）および
  GET /api/users/me への delivery_rank_name 反映
- 購入成立・チャットメッセージ送信・レビュー受信・ランクアップ時の自動通知作成と、
  通知一覧・未読件数・単体既読・一括既読・他ユーザー通知操作拒否（403）を検証する。
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


def test_ranks_auto_upgrade_and_notifications_flow(client, test_session_factory):
    """ランクマスタ設定→購入・メッセージ・レビューによる自動通知＆ランクアップ→既読操作を検証"""
    suffix = uuid.uuid4().hex[:4]
    seller = _register_and_login(client, "nr_s", "通知ランク出品者")
    buyer = _register_and_login(client, "nr_b", "通知ランク購入者")

    with test_session_factory() as db:
        if db.scalar(
            select(EmotionCategory).where(EmotionCategory.category_code == "E01")
        ) is None:
            db.add(EmotionCategory(category_code="E01", category_name="喜"))
            db.commit()

    # 1. 会員ランクマスタを設定（Lv1: 0pt / Lv2: 100pt / Lv3: 500pt）
    r1 = client.post(
        "/api/ranks",
        headers=seller["headers"],
        json={"rank_name": f"Lv1_{suffix}", "required_point": 0},
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/api/ranks",
        headers=seller["headers"],
        json={"rank_name": f"Lv2_{suffix}", "required_point": 100},
    )
    assert r2.status_code == 201
    r3 = client.post(
        "/api/ranks",
        headers=seller["headers"],
        json={"rank_name": f"Lv3_{suffix}", "required_point": 500},
    )
    assert r3.status_code == 201

    # 同名ランクの重複登録は HTTP 409
    assert client.post(
        "/api/ranks",
        headers=seller["headers"],
        json={"rank_name": f"Lv1_{suffix}", "required_point": 0},
    ).status_code == 409

    # ランク一覧取得（認証不要）
    ranks_list = client.get("/api/ranks")
    assert ranks_list.status_code == 200
    assert len(ranks_list.json()) >= 3

    # 2. 初期状態の出品者は 0pt → Lv1、次のランク Lv2 まであと 100pt（進捗0%）
    initial_rank = client.get("/api/ranks/me", headers=seller["headers"])
    assert initial_rank.status_code == 200
    ir_data = initial_rank.json()
    assert ir_data["total_earned_points"] == 0
    assert ir_data["current_rank_name"] == f"Lv1_{suffix}"
    assert ir_data["next_rank_name"] == f"Lv2_{suffix}"
    assert ir_data["points_to_next_rank"] == 100
    assert ir_data["progress_percent"] == 0

    # 3. 出品（120pt）→ 購入者がチャージ＆購入 → 出品者が 120pt 獲得し Lv2 へ自動昇格＆購入通知+昇格通知生成
    letter_code = client.post(
        "/api/posts",
        headers=seller["headers"],
        json={
            "title": "通知＆ランクテスト手紙",
            "content": "ランクアップテストです。",
            "category": "趣味",
            "time": 15,
            "point": 120,
            "emotion": "joy",
            "call": "no",
            "express": "no",
        },
    ).json()["letter_code"]

    client.post("/api/points/charge", headers=buyer["headers"], json={"points": 500})
    matching_code = client.post(
        "/api/purchases",
        headers=buyer["headers"],
        json={"letter_code": letter_code},
    ).json()["matching_code"]

    # 出品者の現在ランクが Lv2 になり、GET /api/users/me にも反映されていること
    upgraded_rank = client.get("/api/ranks/me", headers=seller["headers"]).json()
    assert upgraded_rank["total_earned_points"] == 120
    assert upgraded_rank["current_rank_name"] == f"Lv2_{suffix}"
    assert upgraded_rank["next_rank_name"] == f"Lv3_{suffix}"
    assert upgraded_rank["points_to_next_rank"] == 380

    me_res = client.get("/api/users/me", headers=seller["headers"])
    assert me_res.status_code == 200
    assert me_res.json()["delivery_rank_name"] == f"Lv2_{suffix}"

    # 4. 購入者がチャット送信＆レビュー投稿 → 出品者へメッセージ通知・レビュー通知も届く
    chat_code = client.post(
        "/api/chats",
        headers=buyer["headers"],
        json={"matching_code": matching_code},
    ).json()["chat_code"]
    client.post(
        f"/api/chats/{chat_code}/messages",
        headers=buyer["headers"],
        json={"message": "はじめまして！"},
    )
    client.post(
        "/api/reviews",
        headers=buyer["headers"],
        json={
            "matching_code": matching_code,
            "rating": 5,
            "comment": "最高でした！",
            "tip_amount": 50,
        },
    )

    # 5. 出品者の通知一覧を確認（購入通知1 + ランクアップ通知4 + メッセージ通知2 + レビュー通知3 = 計4件未読）
    notif_res = client.get("/api/notifications", headers=seller["headers"])
    assert notif_res.status_code == 200
    notif_data = notif_res.json()
    assert notif_data["unread_count"] == 4
    types_received = {n["notification_type"] for n in notif_data["notifications"]}
    assert types_received == {1, 2, 3, 4}

    first_code = notif_data["notifications"][0]["notification_code"]

    # 他ユーザー（buyer）が出品者の通知を既読にしようとすると HTTP 403
    assert client.patch(
        f"/api/notifications/{first_code}/read",
        headers=buyer["headers"],
    ).status_code == 403

    # 出品者が1件既読にすると unread_count が 3 になること
    read_one = client.patch(
        f"/api/notifications/{first_code}/read",
        headers=seller["headers"],
    )
    assert read_one.status_code == 200
    assert read_one.json()["is_read"] is True

    unread_list = client.get(
        "/api/notifications?unread_only=true",
        headers=seller["headers"],
    ).json()
    assert unread_list["unread_count"] == 3
    assert len(unread_list["notifications"]) == 3

    # 一括既読（PATCH /api/notifications/read-all）で残り3件が既読になること
    read_all = client.patch("/api/notifications/read-all", headers=seller["headers"])
    assert read_all.status_code == 200
    assert read_all.json()["updated_count"] == 3

    after_all = client.get("/api/notifications", headers=seller["headers"]).json()
    assert after_all["unread_count"] == 0
