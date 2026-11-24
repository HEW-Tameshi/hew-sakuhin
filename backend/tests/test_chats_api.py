"""
チャット機能 API・WebSocketテストモジュール（tests/test_chats_api.py）

【このファイルの役割】
- チャットルーム作成・一覧・詳細、メッセージ送信・履歴取得、および WebSocket リアルタイム配信の
  正常系・異常系（未認証401・第三者拒否403・完了済み取引への送信拒否409）を検証する。
"""

import uuid

import pytest
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from app.post.models import EmotionCategory
from app.purchases.models import Matching


def _setup_matching_users(client, test_session_factory):
    """テスト用の出品者・購入者・第三者を登録し、出品→購入（マッチング成立）まで行う共通ヘルパー。"""
    suffix = uuid.uuid4().hex
    password = "Test1234"

    users = {}
    for role, nickname in (
        ("seller", "チャット出品者"),
        ("buyer", "チャット購入者"),
        ("third", "第三者ユーザー"),
    ):
        email = f"{role}_{suffix}@example.com"
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
        users[role] = {
            "user_code": reg.json()["user_code"],
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"},
        }

    with test_session_factory() as db:
        cat = db.scalar(
            select(EmotionCategory).where(EmotionCategory.category_code == "E01")
        )
        if cat is None:
            db.add(EmotionCategory(category_code="E01", category_name="喜"))
            db.commit()

    post_res = client.post(
        "/api/posts",
        headers=users["seller"]["headers"],
        json={
            "title": "チャットテスト用の手紙",
            "content": "話を聞いてほしいです。",
            "category": "恋愛・悩み",
            "time": 20,
            "point": 100,
            "emotion": "joy",
            "call": "yes",
            "express": "no",
        },
    )
    assert post_res.status_code == 201
    letter_code = post_res.json()["letter_code"]

    # 購入前にポイントをチャージ
    assert client.post(
        "/api/points/charge",
        headers=users["buyer"]["headers"],
        json={"points": 500},
    ).status_code == 201

    buy_res = client.post(
        "/api/purchases",
        headers=users["buyer"]["headers"],
        json={"letter_code": letter_code},
    )
    assert buy_res.status_code == 201
    matching_code = buy_res.json()["matching_code"]

    return users, matching_code


def test_chat_room_and_messages_flow(client, test_session_factory):
    """チャットルーム作成→メッセージ送受信→履歴取得→権限・終了後制限までの一連の流れを検証する"""
    users, matching_code = _setup_matching_users(client, test_session_factory)

    # 1. 第三者はチャットルームを作成できない（403）
    third_create = client.post(
        "/api/chats",
        headers=users["third"]["headers"],
        json={"matching_code": matching_code},
    )
    assert third_create.status_code == 403

    # 2. 購入者がチャットルームを作成する（201）
    create_res = client.post(
        "/api/chats",
        headers=users["buyer"]["headers"],
        json={"matching_code": matching_code},
    )
    assert create_res.status_code == 201
    chat_data = create_res.json()
    chat_code = chat_data["chat_code"]
    assert chat_code.startswith("C")
    assert len(chat_code) == 10
    assert chat_data["matching_code"] == matching_code
    assert chat_data["user_role"] == "buyer"

    # 3. 出品者側が同じマッチングで呼ぶと既存の同じチャットルームが返る（200）
    get_again = client.post(
        "/api/chats",
        headers=users["seller"]["headers"],
        json={"matching_code": matching_code},
    )
    assert get_again.status_code == 200
    assert get_again.json()["chat_code"] == chat_code
    assert get_again.json()["user_role"] == "seller"

    # 4. チャット一覧・詳細取得
    list_res = client.get("/api/chats", headers=users["seller"]["headers"])
    assert list_res.status_code == 200
    assert any(c["chat_code"] == chat_code for c in list_res.json())

    detail_res = client.get(f"/api/chats/{chat_code}", headers=users["buyer"]["headers"])
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "チャットテスト用の手紙"

    # 5. メッセージ送信（購入者 → 出品者）
    msg1_res = client.post(
        f"/api/chats/{chat_code}/messages",
        headers=users["buyer"]["headers"],
        json={"message": "こんにちは！ゆっくりお話ししましょう。"},
    )
    assert msg1_res.status_code == 201
    msg1 = msg1_res.json()
    assert msg1["message_code"].startswith("MSG")
    assert len(msg1["message_code"]) == 12
    assert msg1["is_mine"] is True

    # メッセージ送信によりマッチングが自動的に対話中（status == 3）へ遷移していること
    with test_session_factory() as db:
        matching = db.scalar(
            select(Matching).where(Matching.matching_code == matching_code)
        )
        assert matching is not None
        assert matching.status == 3

    # 6. 出品者からも返信
    msg2_res = client.post(
        f"/api/chats/{chat_code}/messages",
        headers=users["seller"]["headers"],
        json={"message": "ありがとうございます！助かります。"},
    )
    assert msg2_res.status_code == 201

    # 7. 出品者視点でメッセージ履歴を取得（1件目 is_mine=False, 2件目 is_mine=True）
    history_res = client.get(
        f"/api/chats/{chat_code}/messages",
        headers=users["seller"]["headers"],
    )
    assert history_res.status_code == 200
    messages = history_res.json()
    assert len(messages) == 2
    assert messages[0]["message"] == "こんにちは！ゆっくりお話ししましょう。"
    assert messages[0]["is_mine"] is False
    assert messages[1]["message"] == "ありがとうございます！助かります。"
    assert messages[1]["is_mine"] is True

    # 8. 第三者は履歴閲覧も送信もできない（403）
    assert client.get(
        f"/api/chats/{chat_code}/messages",
        headers=users["third"]["headers"],
    ).status_code == 403
    assert client.post(
        f"/api/chats/{chat_code}/messages",
        headers=users["third"]["headers"],
        json={"message": "割り込み"},
    ).status_code == 403

    # 9. 取引完了（status = 4）後はメッセージ送信不可（409）
    complete_res = client.patch(
        f"/api/purchases/matchings/{matching_code}/status",
        headers=users["buyer"]["headers"],
        json={"status": 4},
    )
    assert complete_res.status_code == 200

    closed_send = client.post(
        f"/api/chats/{chat_code}/messages",
        headers=users["buyer"]["headers"],
        json={"message": "完了後のメッセージ"},
    )
    assert closed_send.status_code == 409


def test_chat_websocket_realtime_broadcast(client, test_session_factory):
    """WebSocketで送ったメッセージがDB保存され、当事者双方へリアルタイム配信されること"""
    users, matching_code = _setup_matching_users(client, test_session_factory)

    create_res = client.post(
        "/api/chats",
        headers=users["buyer"]["headers"],
        json={"matching_code": matching_code},
    )
    chat_code = create_res.json()["chat_code"]

    # 第三者のWebSocket接続は 4403 で拒否されること
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            f"/api/chats/ws/{chat_code}?token={users['third']['token']}"
        ):
            pass
    assert exc_info.value.code == 4403

    # 出品者と購入者の2名が同時にWebSocket接続してリアルタイム送受信を確認
    with client.websocket_connect(
        f"/api/chats/ws/{chat_code}?token={users['seller']['token']}"
    ) as seller_ws, client.websocket_connect(
        f"/api/chats/ws/{chat_code}?token={users['buyer']['token']}"
    ) as buyer_ws:
        buyer_ws.send_json({"message": "リアルタイムテストです！"})

        buyer_received = buyer_ws.receive_json()
        seller_received = seller_ws.receive_json()

        assert buyer_received["type"] == "chat_message"
        assert buyer_received["message"] == "リアルタイムテストです！"
        assert buyer_received["is_mine"] is True

        assert seller_received["type"] == "chat_message"
        assert seller_received["message"] == "リアルタイムテストです！"
        assert seller_received["is_mine"] is False

    # DB履歴にも保存されていること
    history = client.get(
        f"/api/chats/{chat_code}/messages",
        headers=users["seller"]["headers"],
    ).json()
    assert len(history) == 1
    assert history[0]["message"] == "リアルタイムテストです！"


def test_chat_without_token_returns_401(client):
    """未ログイン時はチャットAPIが HTTP 401 になること"""
    assert client.get("/api/chats").status_code == 401
    assert client.post("/api/chats", json={"matching_code": "M000000001"}).status_code == 401
