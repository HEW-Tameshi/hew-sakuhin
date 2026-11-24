import uuid

from sqlalchemy import delete, select

from app.core.security import decode_access_token
from app.post.models import EmotionCategory, EmotionLetter
from app.purchases.models import LetterPurchase, Matching
from app.users.models import Profile, RevokedToken, User


def test_register_and_login(client, test_session_factory):
    """新規会員登録とログインの正常系を確認する"""

    email = f"test_{uuid.uuid4().hex}@example.com"
    password = "Test1234"
    user_code = None

    try:
        # 新規会員登録
        register_response = client.post(
            "/api/users/register",
            json={
                "email": email,
                "password": password,
                "nickname": "自動テストユーザー",
            },
        )

        assert register_response.status_code == 201

        register_data = register_response.json()
        user_code = register_data["user_code"]

        assert register_data["email"] == email
        assert register_data["nickname"] == "自動テストユーザー"
        assert user_code
        assert register_data["profile_code"]

        # 同じメールアドレスでの重複登録
        duplicate_response = client.post(
            "/api/users/register",
            json={
                "email": email,
                "password": password,
                "nickname": "重複テスト",
            },
        )

        assert duplicate_response.status_code == 409

        # 正しいパスワードでログイン
        login_response = client.post(
            "/api/users/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert login_response.status_code == 200

        login_data = login_response.json()

        assert login_data["user_code"] == user_code
        assert login_data["access_token"]
        assert login_data["token_type"] == "bearer"

        # 間違ったパスワードでログイン
        invalid_response = client.post(
            "/api/users/login",
            json={
                "email": email,
                "password": "WrongPassword123",
            },
        )

        assert invalid_response.status_code == 401

    finally:
        # テストで作成したデータだけをテスト用DBから削除する
        if user_code is not None:
            with test_session_factory() as db:
                user = db.query(User).filter(
                    User.user_code == user_code
                ).first()

                if user is not None:
                    db.execute(
                        delete(Profile).where(
                            Profile.user_id == user.user_id
                        )
                    )
                    db.delete(user)
                    db.commit()


def test_get_me_with_valid_token(client, test_session_factory):
    """有効なアクセストークンで自分のユーザー情報を取得できる"""

    email = f"test_{uuid.uuid4().hex}@example.com"
    password = "Test1234"
    user_code = None

    try:
        # テストユーザーを登録
        register_response = client.post(
            "/api/users/register",
            json={
                "email": email,
                "password": password,
                "nickname": "認証テストユーザー",
            },
        )

        assert register_response.status_code == 201
        user_code = register_response.json()["user_code"]

        # ログインしてアクセストークンを取得
        login_response = client.post(
            "/api/users/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # トークンを使って自分の情報を取得
        me_response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert me_response.status_code == 200

        me_data = me_response.json()
        assert me_data["user_code"] == user_code
        assert me_data["email"] == email
        assert me_data["nickname"] == "認証テストユーザー"

    finally:
        # このテストで作成したユーザーだけを削除
        if user_code is not None:
            with test_session_factory() as db:
                user = db.query(User).filter(
                    User.user_code == user_code
                ).first()

                if user is not None:
                    db.query(Profile).filter(
                        Profile.user_id == user.user_id
                    ).delete(synchronize_session=False)
                    db.delete(user)
                    db.commit()


def test_logout_revokes_token(client, test_session_factory):
    """ログアウト後は同じトークンを使用できず、テストデータも後片付けする。"""
    email = f"{uuid.uuid4().hex}@example.com"
    password = "Test1234"
    nickname = "logout_test"
    jti = None

    try:
        register_response = client.post(
            "/api/users/register",
            json={
                "email": email,
                "password": password,
                "nickname": nickname,
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/api/users/login",
            json={
                "email": email,
                "password": password,
            },
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        jti = decode_access_token(token)["jti"]

        logout_response = client.post(
            "/api/users/logout",
            headers=headers,
        )
        assert logout_response.status_code == 200

        with test_session_factory() as db:
            revoked = db.scalar(
                select(RevokedToken).where(
                    RevokedToken.jti == jti
                )
            )
            assert revoked is not None

        me_response = client.get(
            "/api/users/me",
            headers=headers,
        )
        assert me_response.status_code == 401

    finally:
        # テスト用DBのデータを後片付けする
        with test_session_factory() as db:
            if jti is not None:
                revoked = db.scalar(
                    select(RevokedToken).where(
                        RevokedToken.jti == jti
                    )
                )
                if revoked is not None:
                    db.delete(revoked)

            user = db.scalar(
                select(User).where(User.email == email)
            )
            if user is not None:
                profile = db.scalar(
                    select(Profile).where(
                        Profile.user_id == user.user_id
                    )
                )
                if profile is not None:
                    db.delete(profile)
                db.delete(user)

            db.commit()


def test_delete_account(client, test_session_factory):
    """退会後はログインと既存トークンの利用が拒否され、プロフィールが匿名化される。"""
    email = f"{uuid.uuid4().hex}@example.com"
    password = "Test1234"

    # 会員登録
    register_response = client.post(
        "/api/users/register",
        json={
            "email": email,
            "password": password,
            "nickname": "delete_test",
        },
    )
    assert register_response.status_code == 201

    # ログインしてトークンを取得
    login_response = client.post(
        "/api/users/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # アカウント削除
    delete_response = client.delete(
        "/api/users/me",
        headers=headers,
    )
    assert delete_response.status_code == 200

    # 退会後は既存トークンも使用できない
    me_response = client.get(
        "/api/users/me",
        headers=headers,
    )
    assert me_response.status_code == 401

    # 退会後はログインもできない
    relogin_response = client.post(
        "/api/users/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert relogin_response.status_code == 401

    # 退会状態とプロフィール匿名化を確認
    with test_session_factory() as db:

        # メールアドレスには user_id を使用しているため、user_code では検索しない
        user = db.scalar(
            select(User).where(User.user_code == register_response.json()["user_code"])
        )
        assert user is not None
        assert user.account_status == 2
        assert user.deleted_at is not None

        profile = db.scalar(
            select(Profile).where(Profile.user_id == user.user_id)
        )
        assert profile is not None
        assert profile.nickname == "退会済みユーザー"
        assert profile.profile_image is None
        assert profile.introduction is None

        # テストデータを後片付け
        db.delete(profile)
        db.delete(user)
        db.commit()


def test_delete_account_twice_returns_401(client, test_session_factory):
    """退会後に同じトークンで再度退会しようとすると401になる。"""
    email = f"{uuid.uuid4().hex}@example.com"
    password = "Test1234"

    register_response = client.post(
        "/api/users/register",
        json={
            "email": email,
            "password": password,
            "nickname": "delete_twice_test",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/users/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    first_response = client.delete(
        "/api/users/me",
        headers=headers,
    )
    assert first_response.status_code == 200

    second_response = client.delete(
        "/api/users/me",
        headers=headers,
    )
    assert second_response.status_code == 401

    # テスト用DBのデータを後片付けする
    with test_session_factory() as db:
        user = db.scalar(
            select(User).where(User.user_code == register_response.json()["user_code"])
        )

        if user is not None:
            profile = db.scalar(
                select(Profile).where(Profile.user_id == user.user_id)
            )

            if profile is not None:
                db.delete(profile)

            db.delete(user)
            db.commit()


def test_get_me_without_token(client):
    """トークンなしでは会員情報を取得できない。"""
    response = client.get("/api/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "認証が必要です"


def test_delete_account_cancels_active_matching(
    client,
    test_session_factory,
):
    """退会時に進行中の取引をキャンセルし、出品を停止する。"""
    suffix = uuid.uuid4().hex
    seller_email = f"seller_{suffix}@example.com"
    buyer_email = f"buyer_{suffix}@example.com"
    password = "Test1234"

    seller_code = None
    buyer_code = None
    category_id = None
    letter_ids = []
    purchase_ids = []
    matching_ids = []

    try:
        # テスト用の出品者・購入者を登録
        seller_response = client.post(
            "/api/users/register",
            json={
                "email": seller_email,
                "password": password,
                "nickname": "退会テスト出品者",
            },
        )
        assert seller_response.status_code == 201
        seller_code = seller_response.json()["user_code"]

        buyer_response = client.post(
            "/api/users/register",
            json={
                "email": buyer_email,
                "password": password,
                "nickname": "退会テスト購入者",
            },
        )
        assert buyer_response.status_code == 201
        buyer_code = buyer_response.json()["user_code"]

        # 出品者としてログインし、退会用トークンを取得
        seller_login = client.post(
            "/api/users/login",
            json={
                "email": seller_email,
                "password": password,
            },
        )
        assert seller_login.status_code == 200
        seller_token = seller_login.json()["access_token"]

        # テストデータを作成
        with test_session_factory() as db:
            category = EmotionCategory(
                category_code=f"C{suffix[:4]}",
                category_name="テスト",
            )
            db.add(category)
            db.flush()
            category_id = category.category_id

            seller = db.scalar(
                select(User).where(User.user_code == seller_code)
            )
            buyer = db.scalar(
                select(User).where(User.user_code == buyer_code)
            )
            assert seller is not None
            assert buyer is not None

            active_letter = EmotionLetter(
                letter_code=f"L{suffix[:9]}",
                seller_id=seller.user_id,
                category_id=category.category_id,
                title="進行中テスト",
                content="テスト内容",
                desired_duration=30,
                point=10,
                status=1,
            )
            completed_letter = EmotionLetter(
                letter_code=f"M{suffix[:9]}",
                seller_id=seller.user_id,
                category_id=category.category_id,
                title="完了済みテスト",
                content="テスト内容",
                desired_duration=30,
                point=10,
                status=1,
            )
            db.add_all([active_letter, completed_letter])
            db.flush()

            letter_ids = [
                active_letter.letter_id,
                completed_letter.letter_id,
            ]

            active_purchase = LetterPurchase(
                purchase_code=f"P{suffix[:10]}",
                letter_id=active_letter.letter_id,
                buyer_id=buyer.user_id,
                purchase_point=10,
            )
            completed_purchase = LetterPurchase(
                purchase_code=f"Q{suffix[:10]}",
                letter_id=completed_letter.letter_id,
                buyer_id=buyer.user_id,
                purchase_point=10,
            )
            db.add_all([active_purchase, completed_purchase])
            db.flush()

            purchase_ids = [
                active_purchase.purchase_id,
                completed_purchase.purchase_id,
            ]

            active_matching = Matching(
                matching_code=f"A{suffix[:9]}",
                purchase_id=active_purchase.purchase_id,
                seller_id=seller.user_id,
                buyer_id=buyer.user_id,
                status=3,
            )
            completed_matching = Matching(
                matching_code=f"B{suffix[:9]}",
                purchase_id=completed_purchase.purchase_id,
                seller_id=seller.user_id,
                buyer_id=buyer.user_id,
                status=4,
            )
            db.add_all([active_matching, completed_matching])
            db.flush()

            matching_ids = [
                active_matching.matching_id,
                completed_matching.matching_id,
            ]
            db.commit()

        # 出品者が退会
        delete_response = client.delete(
            "/api/users/me",
            headers={"Authorization": f"Bearer {seller_token}"},
        )
        assert delete_response.status_code == 200

        # 取引・出品・会員状態を確認
        with test_session_factory() as db:
            active_matching = db.get(Matching, matching_ids[0])
            completed_matching = db.get(Matching, matching_ids[1])
            active_letter = db.get(EmotionLetter, letter_ids[0])
            completed_letter = db.get(EmotionLetter, letter_ids[1])
            seller = db.scalar(
                select(User).where(User.user_code == seller_code)
            )

            assert active_matching.status == 5
            assert completed_matching.status == 4
            assert active_letter.status == 4
            assert completed_letter.status == 4
            assert seller.account_status == 2

    finally:
        # 作成したテストデータだけを外部キーの依存順に削除
        with test_session_factory() as db:
            if seller_code is not None:
                seller = db.scalar(
                    select(User).where(User.user_code == seller_code)
                )
            else:
                seller = None

            if buyer_code is not None:
                buyer = db.scalar(
                    select(User).where(User.user_code == buyer_code)
                )
            else:
                buyer = None

            if matching_ids:
                db.query(Matching).filter(
                    Matching.matching_id.in_(matching_ids)
                ).delete(synchronize_session=False)

            if purchase_ids:
                db.query(LetterPurchase).filter(
                    LetterPurchase.purchase_id.in_(purchase_ids)
                ).delete(synchronize_session=False)

            if letter_ids:
                db.query(EmotionLetter).filter(
                    EmotionLetter.letter_id.in_(letter_ids)
                ).delete(synchronize_session=False)

            if category_id is not None:
                category = db.get(EmotionCategory, category_id)
                if category is not None:
                    db.delete(category)

            for user in (seller, buyer):
                if user is not None:

                    profile = db.scalar(
                        select(Profile).where(
                            Profile.user_id == user.user_id
                        )
                    )
                    if profile is not None:
                        db.delete(profile)
                    db.delete(user)

            db.commit()


def test_delete_buyer_account_cancels_active_matching(
    client,
    test_session_factory,
):
    """購入者の退会時に取引をキャンセルし、購入履歴を保持する。"""
    suffix = uuid.uuid4().hex
    seller_email = f"seller_{suffix}@example.com"
    buyer_email = f"buyer_{suffix}@example.com"
    password = "Test1234"

    seller_code = None
    buyer_code = None
    category_id = None
    letter_ids = []
    purchase_ids = []
    matching_ids = []

    try:
        # 出品者を登録
        response = client.post(
            "/api/users/register",
            json={
                "email": seller_email,
                "password": password,
                "nickname": "購入者退会テスト出品者",
            },
        )
        assert response.status_code == 201
        seller_code = response.json()["user_code"]

        # 購入者を登録
        response = client.post(
            "/api/users/register",
            json={
                "email": buyer_email,
                "password": password,
                "nickname": "購入者退会テスト購入者",
            },
        )
        assert response.status_code == 201
        buyer_code = response.json()["user_code"]

        # 購入者としてログイン
        response = client.post(
            "/api/users/login",
            json={
                "email": buyer_email,
                "password": password,
            },
        )
        assert response.status_code == 200
        buyer_token = response.json()["access_token"]

        # 取引データを作成
        with test_session_factory() as db:
            category = EmotionCategory(
                category_code=f"C{suffix[:4]}",
                category_name=f"テスト{suffix[:4]}",
            )
            db.add(category)
            db.flush()
            category_id = category.category_id

            seller = db.scalar(
                select(User).where(User.user_code == seller_code)
            )
            buyer = db.scalar(
                select(User).where(User.user_code == buyer_code)
            )
            assert seller is not None
            assert buyer is not None

            letter = EmotionLetter(
                letter_code=f"L{suffix[:9]}",
                seller_id=seller.user_id,
                category_id=category_id,
                title="購入者退会テスト",
                content="テスト内容",
                desired_duration=30,
                point=10,
                status=1,
            )
            db.add(letter)
            db.flush()
            letter_ids.append(letter.letter_id)

            purchase = LetterPurchase(
                purchase_code=f"P{suffix[:10]}",
                letter_id=letter.letter_id,
                buyer_id=buyer.user_id,
                purchase_point=10,
            )
            db.add(purchase)
            db.flush()
            purchase_ids.append(purchase.purchase_id)

            matching = Matching(
                matching_code=f"A{suffix[:9]}",
                purchase_id=purchase.purchase_id,
                seller_id=seller.user_id,
                buyer_id=buyer.user_id,
                status=3,
            )
            db.add(matching)
            db.flush()
            matching_ids.append(matching.matching_id)

            seller_id = seller.user_id
            buyer_id = buyer.user_id
            db.commit()

        # 購入者が退会
        response = client.delete(
            "/api/users/me",
            headers={"Authorization": f"Bearer {buyer_token}"},
        )
        assert response.status_code == 200

        # 取引・購入履歴・双方の会員状態を確認
        with test_session_factory() as db:
            matching = db.get(Matching, matching_ids[0])
            purchase = db.get(LetterPurchase, purchase_ids[0])
            letter = db.get(EmotionLetter, letter_ids[0])
            seller = db.get(User, seller_id)
            buyer = db.get(User, buyer_id)

            assert matching is not None
            assert matching.status == 5

            # 購入履歴は削除されない
            assert purchase is not None
            assert purchase.buyer_id == buyer_id

            # 取引対象のレターは停止される
            assert letter is not None
            assert letter.status == 4

            # 出品者は有効なまま
            assert seller is not None
            assert seller.account_status == 1

            # 購入者は退会済み
            assert buyer is not None
            assert buyer.account_status == 2

    finally:
        # このテストで作成したデータだけを削除
        with test_session_factory() as db:
            if matching_ids:
                db.query(Matching).filter(
                    Matching.matching_id.in_(matching_ids)
                ).delete(synchronize_session=False)

            if purchase_ids:
                db.query(LetterPurchase).filter(
                    LetterPurchase.purchase_id.in_(purchase_ids)
                ).delete(synchronize_session=False)

            if letter_ids:
                db.query(EmotionLetter).filter(
                    EmotionLetter.letter_id.in_(letter_ids)
                ).delete(synchronize_session=False)

            if category_id is not None:
                category = db.get(EmotionCategory, category_id)
                if category is not None:
                    db.delete(category)

            for user_code in (seller_code, buyer_code):
                if user_code is None:
                    continue

                user = db.scalar(
                    select(User).where(User.user_code == user_code)
                )
                if user is None:
                    continue

                profile = db.scalar(
                    select(Profile).where(Profile.user_id == user.user_id)
                )
                if profile is not None:
                    db.delete(profile)

                db.delete(user)

            db.commit()
