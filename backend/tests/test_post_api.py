"""
出品機能 APIテストモジュール（tests/test_post_api.py）

【このファイルの役割】
- FastAPI の TestClient を使用して、出品API（登録・一覧取得・詳細取得・編集・取り下げ）の正常系・異常系を検証する。
- テスト用DB（kokoro_mail_test）を使用し、テスト終了後に作成したテストデータを確実に削除する。
"""

import uuid

from sqlalchemy import delete, select

from app.post.models import EmotionCategory, EmotionLetter
from app.users.models import Profile, User


def test_create_post_success(client, test_session_factory):
    """ログイン中の会員が有効な入力値で出品登録できること（HTTP 201）"""
    suffix = uuid.uuid4().hex
    email = f"seller_{suffix}@example.com"
    password = "Test1234"
    user_code = None
    created_letter_code = None
    created_category_id = None

    try:
        # 1. テスト用出品者を会員登録＆ログインしてJWTトークンを取得
        register_res = client.post(
            "/api/users/register",
            json={
                "email": email,
                "password": password,
                "nickname": "出品APIテストユーザー",
            },
        )
        assert register_res.status_code == 201
        user_code = register_res.json()["user_code"]

        login_res = client.post(
            "/api/users/login",
            json={
                "email": email,
                "password": password,
            },
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. テストDBに感情カテゴリ（E01: 喜）が未登録なら用意する
        with test_session_factory() as db:
            category = db.scalar(
                select(EmotionCategory).where(EmotionCategory.category_code == "E01")
            )
            if category is None:
                category = EmotionCategory(
                    category_code="E01",
                    category_name="喜",
                )
                db.add(category)
                db.commit()
                created_category_id = category.category_id

        # 3. 出品API（POST /api/posts）を呼び出す
        post_res = client.post(
            "/api/posts",
            headers=headers,
            json={
                "title": "嬉しい出来事を聞いてほしい",
                "content": "今日とても良いことがあったのでお話したいです。",
                "category": "日常・雑談",
                "time": 30,
                "point": 150,
                "emotion": "joy",
                "call": "yes",
                "express": "no",
            },
        )

        assert post_res.status_code == 201
        data = post_res.json()

        assert data["letter_code"].startswith("L")
        assert len(data["letter_code"]) == 10
        assert data["seller_code"] == user_code
        assert data["category_code"] == "E01"
        assert data["title"] == "嬉しい出来事を聞いてほしい"
        assert data["content"] == "今日とても良いことがあったのでお話したいです。"
        assert data["desired_duration"] == 30
        assert data["point"] == 150
        assert data["status"] == 1
        created_letter_code = data["letter_code"]

        # 4. DB（t_emotion_letter）に実際に保存されているか検証
        with test_session_factory() as db:
            saved = db.scalar(
                select(EmotionLetter).where(
                    EmotionLetter.letter_code == created_letter_code
                )
            )
            assert saved is not None
            assert saved.title == "嬉しい出来事を聞いてほしい"
            assert saved.desired_duration == 30
            assert saved.point == 150
            assert saved.status == 1

    finally:
        # 作成したテストデータのみ削除
        with test_session_factory() as db:
            if created_letter_code:
                db.execute(
                    delete(EmotionLetter).where(
                        EmotionLetter.letter_code == created_letter_code
                    )
                )
            if created_category_id:
                db.execute(
                    delete(EmotionCategory).where(
                        EmotionCategory.category_id == created_category_id
                    )
                )
            if user_code:
                user = db.scalar(select(User).where(User.user_code == user_code))
                if user is not None:
                    db.execute(delete(Profile).where(Profile.user_id == user.user_id))
                    db.delete(user)
            db.commit()


def test_create_post_without_token_returns_401(client):
    """未ログイン（トークンなし）では出品できず HTTP 401 になること"""
    response = client.post(
        "/api/posts",
        json={
            "title": "テスト見出し",
            "content": "テスト内容",
            "category": "趣味",
            "time": 15,
            "point": 50,
            "emotion": "joy",
            "call": "no",
            "express": "no",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "認証が必要です"


def test_create_post_validation_errors_return_422(client):
    """入力値が不正（空文字・文字数超過・0以下の数値・不正な感情）な場合に HTTP 422 になること"""
    suffix = uuid.uuid4().hex
    email = f"val_{suffix}@example.com"
    password = "Test1234"

    # 会員登録＆ログイン
    client.post(
        "/api/users/register",
        json={"email": email, "password": password, "nickname": "検証テスト"},
    )
    login_res = client.post(
        "/api/users/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    base_payload = {
        "title": "テスト見出し",
        "content": "テスト内容",
        "category": "趣味",
        "time": 15,
        "point": 50,
        "emotion": "joy",
        "call": "no",
        "express": "no",
    }

    # 1. 見出しが空白のみ
    res = client.post("/api/posts", headers=headers, json={**base_payload, "title": "   "})
    assert res.status_code == 422

    # 2. 見出しが50文字超過
    res = client.post("/api/posts", headers=headers, json={**base_payload, "title": "あ" * 51})
    assert res.status_code == 422

    # 3. 希望時間が0以下
    res = client.post("/api/posts", headers=headers, json={**base_payload, "time": 0})
    assert res.status_code == 422

    # 4. ポイントが0以下
    res = client.post("/api/posts", headers=headers, json={**base_payload, "point": -10})
    assert res.status_code == 422

    # 5. 感情が不正
    res = client.post("/api/posts", headers=headers, json={**base_payload, "emotion": "unknown"})
    assert res.status_code == 422


def test_list_and_get_post_detail(client, test_session_factory):
    """出品一覧取得（GET /api/posts）と出品詳細取得（GET /api/posts/{letter_code}）が正しく動作すること"""
    suffix = uuid.uuid4().hex
    email = f"list_{suffix}@example.com"
    password = "Test1234"
    user_code = None
    created_letter_code = None
    created_category_id = None

    try:
        # 1. テスト用出品者を登録＆ログイン
        reg_res = client.post(
            "/api/users/register",
            json={
                "email": email,
                "password": password,
                "nickname": "一覧詳細テスト出品者",
            },
        )
        assert reg_res.status_code == 201
        user_code = reg_res.json()["user_code"]

        login_res = client.post(
            "/api/users/login",
            json={"email": email, "password": password},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 感情カテゴリ（E01: 喜）を確認・準備
        with test_session_factory() as db:
            category = db.scalar(
                select(EmotionCategory).where(EmotionCategory.category_code == "E01")
            )
            if category is None:
                category = EmotionCategory(
                    category_code="E01",
                    category_name="喜",
                )
                db.add(category)
                db.commit()
                created_category_id = category.category_id

        # 3. 出品を1件登録
        create_res = client.post(
            "/api/posts",
            headers=headers,
            json={
                "title": "一覧・詳細取得テスト用見出し",
                "content": "一覧・詳細取得テスト用の本文です。",
                "category": "趣味",
                "time": 20,
                "point": 80,
                "emotion": "joy",
                "call": "yes",
                "express": "yes",
            },
        )
        assert create_res.status_code == 201
        created_letter_code = create_res.json()["letter_code"]

        # 4. 出品一覧取得API（GET /api/posts）を確認
        list_res = client.get("/api/posts")
        assert list_res.status_code == 200
        posts = list_res.json()
        assert isinstance(posts, list)

        # 登録したレターが一覧に含まれているか確認
        matched = [p for p in posts if p["letter_code"] == created_letter_code]
        assert len(matched) == 1
        assert matched[0]["seller_code"] == user_code
        assert matched[0]["seller_nickname"] == "一覧詳細テスト出品者"
        assert matched[0]["category_code"] == "E01"
        assert matched[0]["title"] == "一覧・詳細取得テスト用見出し"

        # 5. 出品詳細取得API（GET /api/posts/{letter_code}）を確認
        # (a) 未ログイン時は is_owner が False になること（編集・取り下げボタン非表示用）
        detail_res = client.get(f"/api/posts/{created_letter_code}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["letter_code"] == created_letter_code
        assert detail["seller_code"] == user_code
        assert detail["seller_nickname"] == "一覧詳細テスト出品者"
        assert detail["category_code"] == "E01"
        assert detail["category_name"] == "喜"
        assert detail["title"] == "一覧・詳細取得テスト用見出し"
        assert detail["content"] == "一覧・詳細取得テスト用の本文です。"
        assert detail["desired_duration"] == 20
        assert detail["point"] == 80
        assert detail["status"] == 1
        assert detail["created_at"]
        assert detail["is_owner"] is False

        # (b) 出品者本人のトークン付きで取得した時は is_owner が True になること（編集・取り下げボタン表示用）
        owner_detail_res = client.get(
            f"/api/posts/{created_letter_code}",
            headers=headers,
        )
        assert owner_detail_res.status_code == 200
        assert owner_detail_res.json()["is_owner"] is True

        # 6. 存在しない letter_code を指定した場合は 404 になること
        not_found_res = client.get("/api/posts/L999999999")
        assert not_found_res.status_code == 404
        assert not_found_res.json()["detail"] == "指定された出品が見つかりません"

    finally:
        with test_session_factory() as db:
            if created_letter_code:
                db.execute(
                    delete(EmotionLetter).where(
                        EmotionLetter.letter_code == created_letter_code
                    )
                )
            if created_category_id:
                db.execute(
                    delete(EmotionCategory).where(
                        EmotionCategory.category_id == created_category_id
                    )
                )
            if user_code:
                user = db.scalar(select(User).where(User.user_code == user_code))
                if user is not None:
                    db.execute(delete(Profile).where(Profile.user_id == user.user_id))
                    db.delete(user)
            db.commit()


def test_update_and_delete_post(client, test_session_factory):
    """出品編集（PUT）と取り下げ（DELETE）、および他ユーザー操作時の権限エラー（403）を確認する"""
    suffix = uuid.uuid4().hex
    seller_email = f"owner_{suffix}@example.com"
    other_email = f"other_{suffix}@example.com"
    password = "Test1234"
    seller_code = None
    other_code = None
    created_letter_code = None
    created_category_ids = []

    try:
        # 1. 出品者本人（owner）と別ユーザー（other）を登録＆ログイン
        reg_seller = client.post(
            "/api/users/register",
            json={"email": seller_email, "password": password, "nickname": "出品者本人"},
        )
        seller_code = reg_seller.json()["user_code"]
        seller_token = client.post(
            "/api/users/login",
            json={"email": seller_email, "password": password},
        ).json()["access_token"]
        seller_headers = {"Authorization": f"Bearer {seller_token}"}

        reg_other = client.post(
            "/api/users/register",
            json={"email": other_email, "password": password, "nickname": "別ユーザー"},
        )
        other_code = reg_other.json()["user_code"]
        other_token = client.post(
            "/api/users/login",
            json={"email": other_email, "password": password},
        ).json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        # 2. 感情カテゴリ（E01: 喜, E04: 楽）を確認・準備
        with test_session_factory() as db:
            for code, name in (("E01", "喜"), ("E04", "楽")):
                cat = db.scalar(
                    select(EmotionCategory).where(EmotionCategory.category_code == code)
                )
                if cat is None:
                    cat = EmotionCategory(category_code=code, category_name=name)
                    db.add(cat)
                    db.flush()
                    created_category_ids.append(cat.category_id)
            db.commit()

        # 3. 出品者本人が出品登録
        create_res = client.post(
            "/api/posts",
            headers=seller_headers,
            json={
                "title": "編集前の見出し",
                "content": "編集前の本文です。",
                "category": "日常・雑談",
                "time": 15,
                "point": 50,
                "emotion": "joy",
                "call": "no",
                "express": "no",
            },
        )
        assert create_res.status_code == 201
        created_letter_code = create_res.json()["letter_code"]

        # 4. 別ユーザーが出品を編集しようとすると HTTP 403 Forbidden になること
        forbidden_update = client.put(
            f"/api/posts/{created_letter_code}",
            headers=other_headers,
            json={
                "title": "乗っ取り見出し",
                "content": "乗っ取り本文",
                "category": "趣味",
                "time": 30,
                "point": 100,
                "emotion": "fun",
                "call": "yes",
                "express": "yes",
            },
        )
        assert forbidden_update.status_code == 403
        assert forbidden_update.json()["detail"] == "他のユーザーの出品は編集できません"

        # 5. 出品者本人が出品を編集すると HTTP 200 OK で更新されること
        update_res = client.put(
            f"/api/posts/{created_letter_code}",
            headers=seller_headers,
            json={
                "title": "編集後の新しい見出し",
                "content": "編集後の新しい本文です。",
                "category": "趣味",
                "time": 45,
                "point": 200,
                "emotion": "fun",
                "call": "yes",
                "express": "yes",
            },
        )
        assert update_res.status_code == 200
        updated_data = update_res.json()
        assert updated_data["letter_code"] == created_letter_code
        assert updated_data["category_code"] == "E04"
        assert updated_data["title"] == "編集後の新しい見出し"
        assert updated_data["content"] == "編集後の新しい本文です。"
        assert updated_data["desired_duration"] == 45
        assert updated_data["point"] == 200

        # 6. 別ユーザーが出品を取り下げようとすると HTTP 403 Forbidden になること
        forbidden_delete = client.delete(
            f"/api/posts/{created_letter_code}",
            headers=other_headers,
        )
        assert forbidden_delete.status_code == 403
        assert forbidden_delete.json()["detail"] == "他のユーザーの出品は取り下げできません"

        # 7. 出品者本人が出品を取り下げると HTTP 200 OK になり、status が 4（出品停止）になること
        delete_res = client.delete(
            f"/api/posts/{created_letter_code}",
            headers=seller_headers,
        )
        assert delete_res.status_code == 200
        assert delete_res.json()["message"] == "出品を取り下げました"
        assert delete_res.json()["letter_code"] == created_letter_code

        with test_session_factory() as db:
            letter = db.scalar(
                select(EmotionLetter).where(
                    EmotionLetter.letter_code == created_letter_code
                )
            )
            assert letter is not None
            assert letter.status == 4

        # 8. 取り下げ後は詳細取得で 404 になり、再度取り下げようとしても 404 になること
        detail_after_delete = client.get(f"/api/posts/{created_letter_code}")
        assert detail_after_delete.status_code == 404

        delete_again = client.delete(
            f"/api/posts/{created_letter_code}",
            headers=seller_headers,
        )
        assert delete_again.status_code == 404

    finally:
        with test_session_factory() as db:
            if created_letter_code:
                db.execute(
                    delete(EmotionLetter).where(
                        EmotionLetter.letter_code == created_letter_code
                    )
                )
            if created_category_ids:
                db.execute(
                    delete(EmotionCategory).where(
                        EmotionCategory.category_id.in_(created_category_ids)
                    )
                )
            for code in (seller_code, other_code):
                if code:
                    u = db.scalar(select(User).where(User.user_code == code))
                    if u is not None:
                        db.execute(delete(Profile).where(Profile.user_id == u.user_id))
                        db.delete(u)
            db.commit()


def test_search_filter_sort_and_my_post_history(client, test_session_factory):
    """出品のキーワード検索・感情/ポイント/時間絞り込み・並び替え・自分の出品履歴取得（GET /api/posts/me）"""
    suffix = uuid.uuid4().hex[:8]
    email = f"search_{suffix}@example.com"
    password = "Test1234"

    client.post(
        "/api/users/register",
        json={"email": email, "password": password, "nickname": "検索履歴出品者"},
    )
    token = client.post(
        "/api/users/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with test_session_factory() as db:
        for code, name in (("E01", "喜"), ("E04", "楽")):
            if db.scalar(
                select(EmotionCategory).where(EmotionCategory.category_code == code)
            ) is None:
                db.add(EmotionCategory(category_code=code, category_name=name))
        db.commit()

    # 2件出品（レターA: joy / 60pt / 10分, レターB: fun / 200pt / 40分）
    res_a = client.post(
        "/api/posts",
        headers=headers,
        json={
            "title": f"カフェ巡り_{suffix}",
            "content": "美味しいコーヒーの話をしたいです。",
            "category": "趣味",
            "time": 10,
            "point": 60,
            "emotion": "joy",
            "call": "no",
            "express": "no",
        },
    )
    assert res_a.status_code == 201
    code_a = res_a.json()["letter_code"]

    res_b = client.post(
        "/api/posts",
        headers=headers,
        json={
            "title": f"映画鑑賞_{suffix}",
            "content": "最近見たおすすめ映画について語りたい。",
            "category": "趣味",
            "time": 40,
            "point": 200,
            "emotion": "fun",
            "call": "yes",
            "express": "yes",
        },
    )
    assert res_b.status_code == 201
    code_b = res_b.json()["letter_code"]

    # 1. キーワード検索（q）
    q_res = client.get(f"/api/posts?q=カフェ巡り_{suffix}")
    assert q_res.status_code == 200
    assert [p["letter_code"] for p in q_res.json()] == [code_a]

    # 2. 感情カテゴリ絞り込み（emotion=fun）＋キーワード併用
    emo_res = client.get(f"/api/posts?q={suffix}&emotion=fun")
    assert emo_res.status_code == 200
    assert [p["letter_code"] for p in emo_res.json()] == [code_b]

    # 不正な感情指定は HTTP 400
    assert client.get("/api/posts?emotion=invalid_emo").status_code == 400

    # 3. ポイント範囲・希望時間絞り込み
    pt_res = client.get(f"/api/posts?q={suffix}&min_point=100&max_point=250&min_duration=30")
    assert pt_res.status_code == 200
    assert [p["letter_code"] for p in pt_res.json()] == [code_b]

    # 4. 並び替え（point_asc / point_desc）
    asc_res = client.get(f"/api/posts?q={suffix}&sort=point_asc")
    assert [p["letter_code"] for p in asc_res.json()] == [code_a, code_b]

    desc_res = client.get(f"/api/posts?q={suffix}&sort=point_desc")
    assert [p["letter_code"] for p in desc_res.json()] == [code_b, code_a]

    # 5. レターAを取り下げ（status = 4）した上で、自分の出品履歴（GET /api/posts/me）を確認
    assert client.delete(f"/api/posts/{code_a}", headers=headers).status_code == 200

    # 未ログインで /api/posts/me は HTTP 401
    assert client.get("/api/posts/me").status_code == 401

    # ログイン中なら出品中（B）と取り下げ済み（A）の両方が返り、すべて is_owner=True
    my_all = client.get("/api/posts/me", headers=headers)
    assert my_all.status_code == 200
    my_codes = {p["letter_code"]: p["status"] for p in my_all.json()}
    assert my_codes[code_a] == 4
    assert my_codes[code_b] == 1
    assert all(p["is_owner"] is True for p in my_all.json())

    # ステータス絞り込み（?status=4 で取り下げ済みのみ）
    my_stopped = client.get("/api/posts/me?status=4", headers=headers)
    assert my_stopped.status_code == 200
    assert [p["letter_code"] for p in my_stopped.json()] == [code_a]


def test_cors_preflight_headers(client):
    """VS Code Live Server（http://127.0.0.1:5501）からのCORSプリフライトが許可されること"""
    res = client.options(
        "/api/posts",
        headers={
            "Origin": "http://127.0.0.1:5501",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://127.0.0.1:5501"
    assert res.headers.get("access-control-allow-credentials") == "true"
