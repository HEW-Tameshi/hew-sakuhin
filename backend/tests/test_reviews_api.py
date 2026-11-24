"""
レビュー＆チップ機能 APIテストモジュール（tests/test_reviews_api.py）

【このファイルの役割】
- レビュー投稿（チップ同時送信含む）、重複レビュー拒否（409）、第三者拒否（403）、
  評価範囲不正（422）、キャンセル済み取引へのレビュー拒否（409）、
  およびユーザー別平均評価サマリー取得を検証する。
"""

import uuid

from sqlalchemy import select

from app.post.models import EmotionCategory
from app.reviews.models import Tip


def _setup_matching_users(client, test_session_factory):
    suffix = uuid.uuid4().hex
    password = "Test1234"
    users = {}

    for role, nickname in (
        ("seller", "レビュー出品者"),
        ("buyer", "レビュー購入者"),
        ("third", "レビュー第三者"),
    ):
        email = f"rev_{role}_{suffix}@example.com"
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
            "title": "レビューテスト用の手紙",
            "content": "相談を聞いてほしいです。",
            "category": "日常・雑談",
            "time": 20,
            "point": 100,
            "emotion": "joy",
            "call": "yes",
            "express": "no",
        },
    )
    letter_code = post_res.json()["letter_code"]

    # 購入・チップ送信に備えてポイントをチャージ
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
    matching_code = buy_res.json()["matching_code"]

    return users, matching_code


def test_create_review_with_tip_and_summary(client, test_session_factory):
    """レビュー＋チップ投稿 → 重複拒否(409) → 第三者拒否(403) → ユーザー平均評価取得"""
    users, matching_code = _setup_matching_users(client, test_session_factory)

    # 1. 第三者はレビューを投稿できない（403）
    third_res = client.post(
        "/api/reviews",
        headers=users["third"]["headers"],
        json={"matching_code": matching_code, "rating": 5, "comment": "割り込み"},
    )
    assert third_res.status_code == 403

    # 2. 評価が範囲外（6や0）の場合は HTTP 422
    invalid_rating = client.post(
        "/api/reviews",
        headers=users["buyer"]["headers"],
        json={"matching_code": matching_code, "rating": 6},
    )
    assert invalid_rating.status_code == 422

    # 3. 購入者が出品者へ 星5 + チップ100pt を送信（201）
    review_res = client.post(
        "/api/reviews",
        headers=users["buyer"]["headers"],
        json={
            "matching_code": matching_code,
            "rating": 5,
            "comment": "親身になって寄り添って話を聞いてくれた。",
            "tip_amount": 100,
        },
    )
    assert review_res.status_code == 201
    data = review_res.json()
    assert data["review_code"].startswith("R")
    assert len(data["review_code"]) == 10
    assert data["reviewer_code"] == users["buyer"]["user_code"]
    assert data["reviewee_code"] == users["seller"]["user_code"]
    assert data["rating"] == 5
    assert data["tip_code"].startswith("T")
    assert data["tip_amount"] == 100

    # DB の t_tip にチップが保存されていること
    with test_session_factory() as db:
        saved_tip = db.scalar(
            select(Tip).where(Tip.tip_code == data["tip_code"])
        )
        assert saved_tip is not None
        assert saved_tip.amount == 100

    # 4. 同じ購入者が同じ取引に二重レビューしようとすると HTTP 409 Conflict
    dup_res = client.post(
        "/api/reviews",
        headers=users["buyer"]["headers"],
        json={"matching_code": matching_code, "rating": 4},
    )
    assert dup_res.status_code == 409

    # 5. 出品者から購入者へのレビュー（チップなし = 0pt）も投稿可能（201）
    seller_review = client.post(
        "/api/reviews",
        headers=users["seller"]["headers"],
        json={
            "matching_code": matching_code,
            "rating": 4,
            "comment": "丁寧にお話ししていただきました。",
            "tip_amount": 0,
        },
    )
    assert seller_review.status_code == 201
    assert seller_review.json()["tip_code"] is None
    assert seller_review.json()["tip_amount"] == 0

    # 6. マッチング別レビュー一覧（2件取得できること）
    match_reviews = client.get(
        f"/api/reviews/matching/{matching_code}",
        headers=users["seller"]["headers"],
    )
    assert match_reviews.status_code == 200
    assert len(match_reviews.json()) == 2

    # 7. ユーザー別評価サマリー取得（認証不要で取得可能、平均評価が 5.0）
    summary_res = client.get(f"/api/reviews/user/{users['seller']['user_code']}")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["review_count"] == 1
    assert summary["average_rating"] == 5.0
    assert summary["reviews"][0]["comment"] == "親身になって寄り添って話を聞いてくれた。"


def test_review_canceled_matching_returns_409(client, test_session_factory):
    """キャンセルされた取引（status=5）にはレビュー投稿できず HTTP 409 になること"""
    users, matching_code = _setup_matching_users(client, test_session_factory)

    cancel_res = client.patch(
        f"/api/purchases/matchings/{matching_code}/status",
        headers=users["buyer"]["headers"],
        json={"status": 5},
    )
    assert cancel_res.status_code == 200

    review_res = client.post(
        "/api/reviews",
        headers=users["buyer"]["headers"],
        json={"matching_code": matching_code, "rating": 3},
    )
    assert review_res.status_code == 409
