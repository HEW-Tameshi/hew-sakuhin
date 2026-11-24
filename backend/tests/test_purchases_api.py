"""
購入・取引（マッチング）機能 APIテストモジュール（tests/test_purchases_api.py）

【このファイルの役割】
- FastAPI の TestClient を使用して、購入APIおよび購入に基づいて成立するマッチング管理APIの正常系・異常系を検証する：
  1. レター購入による購入履歴（t_letter_purchase）・マッチング（t_matching）の同時生成
  2. 自己購入禁止（400）・二重購入禁止（409）・未存在（404）
  3. 出品者視点・購入者視点双方からのマッチング一覧・詳細取得と user_role の判定
  4. マッチングの状態遷移（1:成立 → 3:対話中 → 4:取引完了・completed_at記録）および完了後の再変更拒否（409）
  5. 第三者による購入履歴・マッチング操作の拒否（403）
"""

import uuid

from sqlalchemy import delete, select

from app.post.models import EmotionCategory, EmotionLetter
from app.purchases.models import LetterPurchase, Matching
from app.users.models import Profile, User


def test_purchase_and_matching_lifecycle(client, test_session_factory):
    """
    レター購入 → マッチング成立 → 出品者・購入者双方での確認 → 対話中 → 取引完了までの一連の流れを検証する
    """
    suffix = uuid.uuid4().hex
    seller_email = f"seller_{suffix}@example.com"
    buyer_email = f"buyer_{suffix}@example.com"
    third_email = f"third_{suffix}@example.com"
    password = "Test1234"

    seller_code = None
    buyer_code = None
    third_code = None
    created_letter_code = None
    created_purchase_code = None
    created_matching_code = None
    created_category_id = None

    try:
        # 1. 出品者・購入者・第三者の3名を登録＆ログイン
        reg_seller = client.post(
            "/api/users/register",
            json={"email": seller_email, "password": password, "nickname": "テスト出品者"},
        )
        seller_code = reg_seller.json()["user_code"]
        seller_token = client.post(
            "/api/users/login",
            json={"email": seller_email, "password": password},
        ).json()["access_token"]
        seller_headers = {"Authorization": f"Bearer {seller_token}"}

        reg_buyer = client.post(
            "/api/users/register",
            json={"email": buyer_email, "password": password, "nickname": "テスト購入者"},
        )
        buyer_code = reg_buyer.json()["user_code"]
        buyer_token = client.post(
            "/api/users/login",
            json={"email": buyer_email, "password": password},
        ).json()["access_token"]
        buyer_headers = {"Authorization": f"Bearer {buyer_token}"}

        reg_third = client.post(
            "/api/users/register",
            json={"email": third_email, "password": password, "nickname": "第三者ユーザー"},
        )
        third_code = reg_third.json()["user_code"]
        third_token = client.post(
            "/api/users/login",
            json={"email": third_email, "password": password},
        ).json()["access_token"]
        third_headers = {"Authorization": f"Bearer {third_token}"}

        # 2. 感情カテゴリ（E01: 喜）を確認・準備
        with test_session_factory() as db:
            cat = db.scalar(
                select(EmotionCategory).where(EmotionCategory.category_code == "E01")
            )
            if cat is None:
                cat = EmotionCategory(category_code="E01", category_name="喜")
                db.add(cat)
                db.commit()
                created_category_id = cat.category_id

        # 3. 出品者がレターを出品登録
        post_res = client.post(
            "/api/posts",
            headers=seller_headers,
            json={
                "title": "購入・マッチングテスト用の手紙",
                "content": "購入テストの本文です。",
                "category": "日常・雑談",
                "time": 25,
                "point": 120,
                "emotion": "joy",
                "call": "yes",
                "express": "no",
            },
        )
        assert post_res.status_code == 201
        created_letter_code = post_res.json()["letter_code"]

        # 4. 【異常系】出品者が自分の出品を購入しようとすると HTTP 400 Bad Request になること
        self_buy_res = client.post(
            "/api/purchases",
            headers=seller_headers,
            json={"letter_code": created_letter_code},
        )
        assert self_buy_res.status_code == 400
        assert self_buy_res.json()["detail"] == "自分の出品を購入することはできません"

        # 5. 【異常系】存在しない letter_code を購入しようとすると HTTP 404 Not Found になること
        not_found_buy = client.post(
            "/api/purchases",
            headers=buyer_headers,
            json={"letter_code": "L999999999"},
        )
        assert not_found_buy.status_code == 404
        assert not_found_buy.json()["detail"] == "指定された出品が見つかりません"

        # 6. 【正常系】購入者がポイントをチャージしてからレターを購入する → 購入履歴とマッチングが同時に生成される（HTTP 201）
        charge_res = client.post(
            "/api/points/charge",
            headers=buyer_headers,
            json={"points": 500},
        )
        assert charge_res.status_code == 201

        buy_res = client.post(
            "/api/purchases",
            headers=buyer_headers,
            json={"letter_code": created_letter_code},
        )
        assert buy_res.status_code == 201
        buy_data = buy_res.json()

        assert buy_data["purchase_code"].startswith("P")
        assert len(buy_data["purchase_code"]) == 11
        assert buy_data["matching_code"].startswith("M")
        assert len(buy_data["matching_code"]) == 10
        assert buy_data["letter_code"] == created_letter_code
        assert buy_data["seller_code"] == seller_code
        assert buy_data["buyer_code"] == buyer_code
        assert buy_data["purchase_point"] == 120
        assert buy_data["matching_status"] == 1

        created_purchase_code = buy_data["purchase_code"]
        created_matching_code = buy_data["matching_code"]

        # 7. 【異常系】既に購入されたレターを別ユーザーが再度購入しようとすると HTTP 409 Conflict になること
        double_buy_res = client.post(
            "/api/purchases",
            headers=third_headers,
            json={"letter_code": created_letter_code},
        )
        assert double_buy_res.status_code == 409
        assert double_buy_res.json()["detail"] == "この出品は現在購入できません"

        # 8. 【マッチング確認】出品者側からマッチング一覧（GET /api/purchases/matchings?role=seller）を確認できること
        seller_matchings = client.get(
            "/api/purchases/matchings?role=seller&status=active",
            headers=seller_headers,
        )
        assert seller_matchings.status_code == 200
        s_list = seller_matchings.json()
        assert len(s_list) == 1
        assert s_list[0]["matching_code"] == created_matching_code
        assert s_list[0]["buyer_nickname"] == "テスト購入者"
        assert s_list[0]["user_role"] == "seller"
        assert s_list[0]["matching_status"] == 1

        # 9. 【マッチング確認】購入者側からマッチング詳細（GET /api/purchases/matchings/{matching_code}）を確認できること
        buyer_matching_detail = client.get(
            f"/api/purchases/matchings/{created_matching_code}",
            headers=buyer_headers,
        )
        assert buyer_matching_detail.status_code == 200
        b_detail = buyer_matching_detail.json()
        assert b_detail["seller_nickname"] == "テスト出品者"
        assert b_detail["user_role"] == "buyer"

        # 10. 【異常系】無関係な第三者がマッチング詳細や状態更新を行おうとすると HTTP 403 Forbidden になること
        forbidden_matching = client.get(
            f"/api/purchases/matchings/{created_matching_code}",
            headers=third_headers,
        )
        assert forbidden_matching.status_code == 403

        forbidden_patch = client.patch(
            f"/api/purchases/matchings/{created_matching_code}/status",
            headers=third_headers,
            json={"status": 3},
        )
        assert forbidden_patch.status_code == 403

        # 11. 【マッチング状態遷移】対話中（status = 3）へ更新できること
        active_patch = client.patch(
            f"/api/purchases/matchings/{created_matching_code}/status",
            headers=seller_headers,
            json={"status": 3},
        )
        assert active_patch.status_code == 200
        assert active_patch.json()["matching_status"] == 3
        assert active_patch.json()["completed_at"] is None

        # 12. 【マッチング完了】取引完了（status = 4）へ更新すると completed_at が記録され、レターも完了（status = 3）になること
        complete_patch = client.patch(
            f"/api/purchases/matchings/{created_matching_code}/status",
            headers=buyer_headers,
            json={"status": 4},
        )
        assert complete_patch.status_code == 200
        comp_data = complete_patch.json()
        assert comp_data["matching_status"] == 4
        assert comp_data["completed_at"] is not None

        with test_session_factory() as db:
            letter = db.scalar(
                select(EmotionLetter).where(
                    EmotionLetter.letter_code == created_letter_code
                )
            )
            assert letter is not None
            assert letter.status == 3

        # 13. 【異常系】完了済みのマッチングを再度変更しようとすると HTTP 409 Conflict になること
        re_patch = client.patch(
            f"/api/purchases/matchings/{created_matching_code}/status",
            headers=buyer_headers,
            json={"status": 5},
        )
        assert re_patch.status_code == 409
        assert re_patch.json()["detail"] == "既に完了またはキャンセルされた取引の状態は変更できません"

    finally:
        # 作成したテストデータの後片付けは conftest.py の cleanup_test_data に任せる
        pass


def test_purchase_without_token_returns_401(client):
    """未ログイン（トークンなし）では購入やマッチング取得ができず HTTP 401 になること"""
    post_res = client.post("/api/purchases", json={"letter_code": "L000000001"})
    assert post_res.status_code == 401

    get_res = client.get("/api/purchases/matchings")
    assert get_res.status_code == 401
