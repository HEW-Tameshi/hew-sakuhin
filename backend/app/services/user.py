
import secrets
import string

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from app.models.user import User, Profile
from app.models.market import EmotionLetter, LetterPurchase, Matching

from datetime import datetime, timezone
from app.models.token import RevokedToken

password_hash = PasswordHash.recommended()


def generate_code(prefix: str) -> str:
    """7文字の一意コードを生成する。"""
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
    """会員とプロフィールを1トランザクションで登録する。"""

    try:
        # メールアドレスの重複確認
        existing_user = db.scalar(
            select(User).where(User.email == email)
        )

        if existing_user:
            raise ValueError("このメールアドレスは既に登録されています")

        # パスワードをハッシュ化
        hashed_password = password_hash.hash(password)

        # 一意コードを生成
        user_code = generate_code("U")
        profile_code = generate_code("P")

        # コードの重複を確認
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

        # 会員情報を登録
        user = User(
            user_code=user_code,
            email=email,
            password=hashed_password,
        )

        db.add(user)
        db.flush()

        # プロフィール情報を登録
        profile = Profile(
            profile_code=profile_code,
            user_id=user.user_id,
            nickname=nickname,
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




def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> tuple[User, Profile] | None:
    """有効な会員のメールアドレスとパスワードを検証する。"""

    user = db.scalar(
        select(User).where(User.email == email)
    )

    # ユーザーが存在しない、または退会済みの場合は認証失敗
    if user is None or user.account_status != 1:
        return None

    # 登録済みのハッシュ値と入力パスワードを照合
    if not password_hash.verify(password, user.password):
        return None

    # 対応するプロフィールを取得
    profile = db.scalar(
        select(Profile).where(Profile.user_id == user.user_id)
    )

    if profile is None:
        return None

    return user, profile



def delete_user_account(
    db: Session,
    user: User,
) -> None:
    """会員を論理削除し、出品停止・取引キャンセル・匿名化を行う。"""

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 退会者が関係する進行中の取引IDを先に取得する
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

    # キャンセル対象の取引に紐づく感情レターIDを先に取得する
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
            .where(
                Matching.matching_id.in_(affected_matching_ids)
            )
            .values(status=5)
        )

    # 退会者自身の出品中レターを停止（status = 4）
    db.execute(
        update(EmotionLetter)
        .where(
            EmotionLetter.seller_id == user.user_id,
            EmotionLetter.status == 1,
        )
        .values(status=4)
    )

    # キャンセル対象取引に紐づくレターも停止
    if affected_letter_ids:
        db.execute(
            update(EmotionLetter)
            .where(
                EmotionLetter.letter_id.in_(affected_letter_ids)
            )
            .values(status=4)
        )

    # アカウントを退会済みに変更
    user.account_status = 2
    user.deleted_at = now

    # メールアドレスを一意な退会用アドレスに置換
    user.email = f"deleted_{user.user_id}@invalid.local"

    # パスワードをランダムな値に置き換える
    user.password = password_hash.hash(secrets.token_urlsafe(48))

    # プロフィールを匿名化
    profile = db.scalar(
        select(Profile).where(Profile.user_id == user.user_id)
    )

    if profile is not None:
        profile.nickname = "退会済みユーザー"
        profile.profile_image = None
        profile.introduction = None
