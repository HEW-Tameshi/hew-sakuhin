"""
通話機能 API・WebRTCシグナリングテストモジュール（tests/test_calls_api.py）

【このファイルの役割】
- 通話開始（POST /api/calls/start）、通話終了・通話時間記録（POST /api/calls/{call_code}/end）、
  通話履歴・詳細取得、および WebRTC 通話シグナリング WebSocket（WS /api/calls/ws/{matching_code}）
  の正常系・異常系を検証する。
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
        ("seller", "通話出品者"),
        ("buyer", "通話購入者"),
        ("third", "通話第三者"),
    ):
        email = f"call_{role}_{suffix}@example.com"
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
            "title": "通話テスト用の手紙",
            "content": "音声通話でお話ししたいです。",
            "category": "日常・雑談",
            "time": 15,
            "point": 80,
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


def test_call_start_end_and_history_flow(client, test_session_factory):
    """通話開始→二重開始拒否→通話終了・通話時間記録→履歴取得→完了後通話不可を検証する"""
    users, matching_code = _setup_matching_users(client, test_session_factory)

    # 1. 第三者は通話を開始できない（403）
    third_start = client.post(
        "/api/calls/start",
        headers=users["third"]["headers"],
        json={"matching_code": matching_code, "communication_type": 1},
    )
    assert third_start.status_code == 403

    # 2. 購入者が音声通話（communication_type=1）を開始する（201）
    start_res = client.post(
        "/api/calls/start",
        headers=users["buyer"]["headers"],
        json={"matching_code": matching_code, "communication_type": 1},
    )
    assert start_res.status_code == 201
    call_data = start_res.json()
    call_code = call_data["call_code"]
    assert call_code.startswith("CL")
    assert len(call_code) == 10
    assert call_data["matching_code"] == matching_code
    assert call_data["communication_type"] == 1
    assert call_data["is_active"] is True
    assert call_data["ended_at"] is None
    assert call_data["duration"] is None

    # 通話開始によりマッチングが対話中（status == 3）に更新されていること
    with test_session_factory() as db:
        matching = db.scalar(
            select(Matching).where(Matching.matching_code == matching_code)
        )
        assert matching is not None
        assert matching.status == 3

    # 3. 既に通話中なのに再度開始しようとすると HTTP 409 Conflict
    dup_start = client.post(
        "/api/calls/start",
        headers=users["seller"]["headers"],
        json={"matching_code": matching_code, "communication_type": 1},
    )
    assert dup_start.status_code == 409

    # 4. 第三者は通話詳細の閲覧も終了もできない（403）
    assert client.get(
        f"/api/calls/{call_code}",
        headers=users["third"]["headers"],
    ).status_code == 403
    assert client.post(
        f"/api/calls/{call_code}/end",
        headers=users["third"]["headers"],
    ).status_code == 403

    # 5. 出品者が通話を終了する（200、ended_at と duration >= 0 が記録される）
    end_res = client.post(
        f"/api/calls/{call_code}/end",
        headers=users["seller"]["headers"],
    )
    assert end_res.status_code == 200
    ended_data = end_res.json()
    assert ended_data["call_code"] == call_code
    assert ended_data["is_active"] is False
    assert ended_data["ended_at"] is not None
    assert ended_data["duration"] is not None
    assert ended_data["duration"] >= 0

    # 6. 既に終了済みの通話を再度終了しようとすると HTTP 409 Conflict
    end_again = client.post(
        f"/api/calls/{call_code}/end",
        headers=users["buyer"]["headers"],
    )
    assert end_again.status_code == 409

    # 7. 通話履歴一覧と通話詳細を取得できること
    history_res = client.get(
        f"/api/calls/matching/{matching_code}",
        headers=users["buyer"]["headers"],
    )
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 1
    assert history[0]["call_code"] == call_code

    detail_res = client.get(
        f"/api/calls/{call_code}",
        headers=users["seller"]["headers"],
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["call_code"] == call_code

    # 8. 取引完了（status = 4）後は新しく通話を開始できない（409）
    client.patch(
        f"/api/purchases/matchings/{matching_code}/status",
        headers=users["buyer"]["headers"],
        json={"status": 4},
    )
    after_complete = client.post(
        "/api/calls/start",
        headers=users["buyer"]["headers"],
        json={"matching_code": matching_code, "communication_type": 1},
    )
    assert after_complete.status_code == 409


def test_call_signaling_websocket_relay(client, test_session_factory):
    """WebRTC通話シグナリング（call_request / call_accept）が当事者間で中継されること"""
    users, matching_code = _setup_matching_users(client, test_session_factory)

    # 第三者はWebSocket接続できない（4403）
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            f"/api/calls/ws/{matching_code}?token={users['third']['token']}"
        ):
            pass
    assert exc_info.value.code == 4403

    # 出品者と購入者が接続し、通話申請→了承が相手に中継されることを確認
    with client.websocket_connect(
        f"/api/calls/ws/{matching_code}?token={users['seller']['token']}"
    ) as seller_ws, client.websocket_connect(
        f"/api/calls/ws/{matching_code}?token={users['buyer']['token']}"
    ) as buyer_ws:
        buyer_ws.send_json({"type": "call_request", "communication_type": 1})
        received_req = seller_ws.receive_json()
        assert received_req["type"] == "call_request"
        assert received_req["from_user_code"] == users["buyer"]["user_code"]

        seller_ws.send_json({"type": "call_accept"})
        received_acc = buyer_ws.receive_json()
        assert received_acc["type"] == "call_accept"
        assert received_acc["from_user_code"] == users["seller"]["user_code"]


def test_call_without_token_returns_401(client):
    """未ログイン時は通話APIが HTTP 401 になること"""
    assert client.post(
        "/api/calls/start",
        json={"matching_code": "M000000001", "communication_type": 1},
    ).status_code == 401
    assert client.get("/api/calls/matching/M000000001").status_code == 401
