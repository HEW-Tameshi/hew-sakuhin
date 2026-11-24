"""
会員機能 ビジネスロジック（サービス層）モジュール（app/users/service.py）

【このファイルの役割】
- 会員登録、ログイン認証、Google認証、プロフィール編集、パスワード変更/設定、
  退会（論理削除・関連データ停止・サブスク解約・進行中通話終了・匿名化）の業務処理とDB操作を担当する。
- ルーター（router.py）から呼び出され、トランザクション管理（flush / commit / rollback）を行う。
"""

from datetime import date, datetime, timezone
import secrets
import string

from pwdlib import PasswordHash
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.calls.models import Call
from app.points.models import Subscription
from app.post.models import EmotionLetter
from app.purchases.models import LetterPurchase, Matching
from app.users.models import Profile, User

# Argon2等を用いた推奨設定のパスワードハッシュ化インスタンス
password_hash = PasswordHash.recommended()


class PasswordChangeError(ValueError):
    """パスワード変更時の業務エラー（現在パスワード不一致・同一パスワード指定など）"""
    pass


def generate_code(prefix: str) -> str:
    """
    指定されたプレフィックス（'U' または 'P'）+ ランダム英大文字・数字6文字の
    計7文字の一意コードを生成する。
    """
    characters = string.ascii_uppercase + string.digits
    return prefix + "".join(
        secrets.choice(characters) for _ in range(6)
    )


def register_user(
    db: Session,
    email: str,
    password: str,
    nickname: str,
) -> tuple[User, Profile]:
    """
    会員（m_user）とプロフィール（m_profile）を1トランザクションで登録する。
    """
    try:
        # 1. メールアドレスの重複確認
        existing_user = db.scalar(
            select(User).where(User.email == email)
        )
        if existing_user:
            raise ValueError("このメールアドレスは既に登録されています")

        # 2. パスワードをハッシュ化
        hashed_password = password_hash.hash(password)

        # 3. 一意コードを生成（衝突時は1回再生成）
        user_code = generate_code("U")
        profile_code = generate_code("P")

        if db.scalar(
            select(User.user_id).where(User.user_code == user_code)
        ):
            user_code = generate_code("U")

        if db.scalar(
            select(Profile.profile_id).where(
                Profile.profile_code == profile_code
            )
        ):
            profile_code = generate_code("P")

        # 4. 会員情報（m_user）を登録し、flush()で自動採番された user_id を取得
        user = User(
            user_code=user_code,
            email=email,
            password=hashed_password,
        )
        db.add(user)
        db.flush()

        # 5. プロフィール情報（m_profile）を登録
        profile = Profile(
            profile_code=profile_code,
            user_id=user.user_id,
            nickname=nickname,
            delivery_rank_id=None,
        )
        db.add(profile)

        # 6. トランザクション確定
        db.commit()
        db.refresh(user)
        db.refresh(profile)

        return user, profile

    except Exception:
        db.rollback()
        raise


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> tuple[User, Profile] | None:
    """有効な会員のメールアドレスとパスワードを検証する。"""
    user = db.scalar(select(User).where(User.email == email))

    if user is None or user.account_status != 1:
        return None

    if not password_hash.verify(password, user.password):
        return None

    profile = db.scalar(
        select(Profile).where(Profile.user_id == user.user_id)
    )
    if profile is None:
        return None

    return user, profile


def register_user_with_google(
    db: Session,
    email: str,
    nickname: str | None = None,
    google_name: str | None = None,
    profile_image: str | None = None,
) -> tuple[User, Profile]:
    """
    Google認証で検証済みのメールアドレスを使用して、会員（m_user）とプロフィール（m_profile）を
    1トランザクションで登録する。
    """
    try:
        existing_user = db.scalar(select(User).where(User.email == email))
        if existing_user:
            raise ValueError("このメールアドレスは既に登録されています")

        resolved_nickname = (
            (nickname or "").strip()
            or (google_name or "").strip()
            or email.split("@", 1)[0]
        )[:50]

        resolved_image = (
            profile_image
            if profile_image and len(profile_image) <= 255
            else None
        )

        hashed_password = password_hash.hash(secrets.token_urlsafe(48))

        user_code = generate_code("U")
        profile_code = generate_code("P")

        if db.scalar(select(User.user_id).where(User.user_code == user_code)):
            user_code = generate_code("U")

        if db.scalar(
            select(Profile.profile_id).where(Profile.profile_code == profile_code)
        ):
            profile_code = generate_code("P")

        user = User(
            user_code=user_code,
            email=email,
            password=hashed_password,
        )
        db.add(user)
        db.flush()

        profile = Profile(
            profile_code=profile_code,
            user_id=user.user_id,
            nickname=resolved_nickname,
            profile_image=resolved_image,
            delivery_rank_id=None,
        )
        db.add(profile)
        db.commit()

        db.refresh(user)
        db.refresh(profile)

        return user, profile

    except Exception:
        db.rollback()
        raise


def authenticate_user_with_google(
    db: Session,
    email: str,
) -> tuple[User, Profile] | None:
    """Google認証で検証済みのメールアドレスを使って、有効な会員を検索する。"""
    user = db.scalar(select(User).where(User.email == email))

    if user is None or user.account_status != 1:
        return None

    profile = db.scalar(
        select(Profile).where(Profile.user_id == user.user_id)
    )
    if profile is None:
        return None

    return user, profile


def update_user_profile(
    db: Session,
    user: User,
    fields_to_update: dict,
) -> tuple[User, Profile] | None:
    """
    ログイン中会員のプロフィール（m_profile）およびメールアドレス（m_user.email）を部分更新する。

    【処理の実行順序】
    1. m_profile を取得する（存在しなければ None）。
    2. email の更新が指定された場合、他ユーザーと重複していないか確認する（重複時は ValueError）。
    3. fields_to_update に含まれる項目のみを上書きする。
    4. db.commit() で確定し、最新の (user, profile) を返す（例外時は db.rollback()）。
    """
    try:
        profile = db.scalar(
            select(Profile).where(Profile.user_id == user.user_id)
        )
        if profile is None:
            return None

        if "email" in fields_to_update and fields_to_update["email"] is not None:
            new_email = str(fields_to_update["email"])
            if new_email != user.email:
                duplicate = db.scalar(
                    select(User.user_id).where(
                        User.email == new_email,
                        User.user_id != user.user_id,
                    )
                )
                if duplicate is not None:
                    raise ValueError("このメールアドレスは既に使用されています")
                user.email = new_email

        if "nickname" in fields_to_update and fields_to_update["nickname"] is not None:
            profile.nickname = fields_to_update["nickname"]

        if "profile_image" in fields_to_update:
            profile.profile_image = fields_to_update["profile_image"]

        if "introduction" in fields_to_update:
            profile.introduction = fields_to_update["introduction"]

        db.commit()
        db.refresh(user)
        db.refresh(profile)

        return user, profile

    except Exception:
        db.rollback()
        raise


def change_user_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """
    現在のパスワードを照合したうえで、新しいパスワードへ更新する。

    【処理の実行順序】
    1. 保存済みハッシュと current_password を照合する（不一致時は PasswordChangeError）。
    2. current_password と new_password が同一でないか確認する（同一時は PasswordChangeError）。
    3. new_password をハッシュ化して user.password を上書きし、db.commit() で確定する。
    """
    try:
        if not password_hash.verify(current_password, user.password):
            raise PasswordChangeError("現在のパスワードが正しくありません")

        if current_password == new_password:
            raise PasswordChangeError("現在と同じパスワードは設定できません")

        user.password = password_hash.hash(new_password)
        db.commit()
        db.refresh(user)

    except Exception:
        db.rollback()
        raise


def set_password_with_google(
    db: Session,
    user: User,
    verified_google_email: str,
    new_password: str,
) -> None:
    """
    Google IDトークンで再認証したメールアドレスがログイン中ユーザーと一致することを確認し、
    ログイン用の新パスワードを設定する（Google登録ユーザー向け）。
    """
    try:
        if verified_google_email.lower() != user.email.lower():
            raise PermissionError("ログイン中のアカウントと異なるGoogleアカウントです")

        user.password = password_hash.hash(new_password)
        db.commit()
        db.refresh(user)

    except Exception:
        db.rollback()
        raise


def delete_user_account(
    db: Session,
    user: User,
) -> None:
    """
    会員を退会（論理削除）し、出品停止・進行中取引のキャンセル・未終了通話の終了・
    有効サブスクの自動解約・個人情報の匿名化を行う。

    【処理の実行順序】
    1. 退会者が関係する進行中の取引（t_matching.status in [1, 2, 3]）を取得する。
    2. 対象取引がある場合、紐づくレターIDを取得し、進行中取引をキャンセル（status = 5）にする。
       さらに、対象取引に未終了の通話（t_call.ended_at IS NULL）があれば終了日時・通話時間を記録する。
    3. 退会者自身の出品中レター（t_emotion_letter.status == 1）を停止（status = 4）にする。
    4. キャンセル対象取引に紐づくレターも停止（status = 4）にする。
    5. 有効なサブスクリプション契約（t_subscription.status == 1）があれば自動解約（status = 2, end_date = 今日）にする。
    6. m_user を退会済み（account_status = 2, deleted_at = now）にし、email・password を置換する。
    7. m_profile のニックネーム・画像・自己紹介を匿名化する。
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = date.today()

    # 1. 退会者が関係する進行中の取引IDを先に取得する（status 1, 2, 3 が進行中）
    active_statuses = [1, 2, 3]

    affected_matching_ids = db.scalars(
        select(Matching.matching_id).where(
            (
                (Matching.seller_id == user.user_id)
                | (Matching.buyer_id == user.user_id)
            ),
            Matching.status.in_(active_statuses),
        )
    ).all()

    # 2. キャンセル対象の取引に紐づくレターID取得・取引キャンセル・未終了通話のクローズ
    affected_letter_ids = []

    if affected_matching_ids:
        affected_letter_ids = db.scalars(
            select(LetterPurchase.letter_id)
            .join(
                Matching,
                Matching.purchase_id == LetterPurchase.purchase_id,
            )
            .where(
                Matching.matching_id.in_(affected_matching_ids)
            )
        ).all()

        # 進行中の取引をキャンセル（status = 5）
        db.execute(
            update(Matching)
            .where(Matching.matching_id.in_(affected_matching_ids))
            .values(status=5)
        )

        # 未終了の通話があれば終了時刻と経過秒数を記録してクローズ
        active_calls = db.scalars(
            select(Call).where(
                Call.matching_id.in_(affected_matching_ids),
                Call.ended_at.is_(None),
            )
        ).all()
        for active_call in active_calls:
            active_call.ended_at = now
            active_call.duration = max(
                0, int((now - active_call.started_at).total_seconds())
            )

    # 3. 退会者自身の出品中レターを停止（status = 4）
    db.execute(
        update(EmotionLetter)
        .where(
            EmotionLetter.seller_id == user.user_id,
            EmotionLetter.status == 1,
        )
        .values(status=4)
    )

    # 4. キャンセル対象取引に紐づくレターも停止（status = 4）
    if affected_letter_ids:
        db.execute(
            update(EmotionLetter)
            .where(EmotionLetter.letter_id.in_(affected_letter_ids))
            .values(status=4)
        )

    # 5. 有効なサブスクリプション契約（t_subscription.status == 1）を自動解約
    db.execute(
        update(Subscription)
        .where(
            Subscription.user_id == user.user_id,
            Subscription.status == 1,
        )
        .values(status=2, end_date=today)
    )

    # 6. アカウント状態を退会済み（2）に変更し、退会日時・匿名化email・ランダムパスワードを設定
    user.account_status = 2
    user.deleted_at = now
    user.email = f"deleted_{user.user_id}@invalid.local"
    user.password = password_hash.hash(secrets.token_urlsafe(48))

    # 7. プロフィールを匿名化
    profile = db.scalar(
        select(Profile).where(Profile.user_id == user.user_id)
    )

    if profile is not None:
        profile.nickname = "退会済みユーザー"
        profile.profile_image = None
        profile.introduction = None
