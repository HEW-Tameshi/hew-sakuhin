"""
出品機能 ビジネスロジック（サービス層）モジュール（app/post/service.py）

【このファイルの役割】
- 感情レターの出品登録・一覧検索/絞り込み・自分の出品履歴取得・詳細取得・編集・取り下げ（出品停止）を担当する。
- 会員機能（app/users/service.py）と同じ設計パターンで実装する。
"""

import secrets
import string

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.post.models import EmotionCategory, EmotionLetter
from app.users.models import Profile, User


def generate_letter_code() -> str:
    """
    t_emotion_letter.letter_code 用の10文字の一意コード（'L' + 英大文字・数字9文字）を生成する。
    """
    characters = string.ascii_uppercase + string.digits
    return "L" + "".join(
        secrets.choice(characters) for _ in range(9)
    )


def create_emotion_letter(
    db: Session,
    seller: User,
    category_code: str,
    title: str,
    content: str,
    desired_duration: int,
    point: int,
) -> tuple[EmotionLetter, EmotionCategory]:
    """
    感情レター（t_emotion_letter）を1トランザクションで登録する。
    """
    try:
        # 1. 感情カテゴリマスタ（m_emotion_category）の検索
        emotion_category = db.scalar(
            select(EmotionCategory).where(
                EmotionCategory.category_code == category_code
            )
        )

        if emotion_category is None:
            raise ValueError("指定された感情カテゴリが存在しません")

        # 2. レターコード（L + 英大文字・数字9文字）を生成し、重複を確認
        letter_code = generate_letter_code()

        if db.scalar(
            select(EmotionLetter.letter_id).where(
                EmotionLetter.letter_code == letter_code
            )
        ):
            letter_code = generate_letter_code()

        # 3. 感情レター情報（t_emotion_letter）を作成してセッションに追加
        letter = EmotionLetter(
            letter_code=letter_code,
            seller_id=seller.user_id,
            category_id=emotion_category.category_id,
            title=title,
            content=content,
            desired_duration=desired_duration,
            point=point,
            status=1,  # 1: 出品中
        )

        db.add(letter)

        # 4. トランザクションを確定する
        db.commit()
        db.refresh(letter)

        return letter, emotion_category

    except Exception:
        db.rollback()
        raise


def list_emotion_letters(
    db: Session,
    keyword: str | None = None,
    category_code: str | None = None,
    min_point: int | None = None,
    max_point: int | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    sort: str = "newest",
) -> list[tuple[EmotionLetter, User, Profile, EmotionCategory]]:
    """
    出品中（status == 1）の感情レター一覧を、検索・絞り込み・並び替え条件付きで取得する。

    【処理の実行順序】
    1. t_emotion_letter, m_user, m_profile, m_emotion_category を内部結合（JOIN）する。
    2. 出品中（status == 1）かつ有効会員（account_status == 1）に絞り込む。
    3. 指定された任意条件（キーワード、感情コード、ポイント範囲、希望時間範囲）を追加する。
    4. sort 条件（newest: 新着順 / point_asc: ポイント安い順 / point_desc: ポイント高い順）で並べて返す。
    """
    stmt = (
        select(EmotionLetter, User, Profile, EmotionCategory)
        .join(User, EmotionLetter.seller_id == User.user_id)
        .join(Profile, User.user_id == Profile.user_id)
        .join(
            EmotionCategory,
            EmotionLetter.category_id == EmotionCategory.category_id,
        )
        .where(
            EmotionLetter.status == 1,
            User.account_status == 1,
        )
    )

    if keyword:
        like_pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                EmotionLetter.title.like(like_pattern),
                EmotionLetter.content.like(like_pattern),
            )
        )

    if category_code:
        stmt = stmt.where(EmotionCategory.category_code == category_code)

    if min_point is not None:
        stmt = stmt.where(EmotionLetter.point >= min_point)

    if max_point is not None:
        stmt = stmt.where(EmotionLetter.point <= max_point)

    if min_duration is not None:
        stmt = stmt.where(EmotionLetter.desired_duration >= min_duration)

    if max_duration is not None:
        stmt = stmt.where(EmotionLetter.desired_duration <= max_duration)

    if sort == "point_asc":
        stmt = stmt.order_by(EmotionLetter.point.asc(), EmotionLetter.letter_id.desc())
    elif sort == "point_desc":
        stmt = stmt.order_by(EmotionLetter.point.desc(), EmotionLetter.letter_id.desc())
    else:
        stmt = stmt.order_by(EmotionLetter.letter_id.desc())

    return [tuple(row) for row in db.execute(stmt).all()]


def list_my_emotion_letters(
    db: Session,
    seller: User,
    letter_status: int | None = None,
) -> list[tuple[EmotionLetter, User, Profile, EmotionCategory]]:
    """
    ログイン中ユーザー自身の出品履歴一覧（出品中・取引中・完了・停止済みすべて含む）を新着順で取得する。
    letter_status（1〜4）が指定された場合はそのステータスのみで絞り込む。
    """
    stmt = (
        select(EmotionLetter, User, Profile, EmotionCategory)
        .join(User, EmotionLetter.seller_id == User.user_id)
        .join(Profile, User.user_id == Profile.user_id)
        .join(
            EmotionCategory,
            EmotionLetter.category_id == EmotionCategory.category_id,
        )
        .where(EmotionLetter.seller_id == seller.user_id)
    )

    if letter_status is not None:
        stmt = stmt.where(EmotionLetter.status == letter_status)

    stmt = stmt.order_by(EmotionLetter.letter_id.desc())

    return [tuple(row) for row in db.execute(stmt).all()]


def get_emotion_letter_by_code(
    db: Session,
    letter_code: str,
) -> tuple[EmotionLetter, User, Profile, EmotionCategory] | None:
    """
    指定されたレターコード（letter_code）の出品中レター詳細を1件取得する。
    """
    stmt = (
        select(EmotionLetter, User, Profile, EmotionCategory)
        .join(User, EmotionLetter.seller_id == User.user_id)
        .join(Profile, User.user_id == Profile.user_id)
        .join(
            EmotionCategory,
            EmotionLetter.category_id == EmotionCategory.category_id,
        )
        .where(
            EmotionLetter.letter_code == letter_code,
            EmotionLetter.status == 1,
            User.account_status == 1,
        )
    )

    row = db.execute(stmt).first()
    if row is None:
        return None

    letter, seller, profile, category = row
    return letter, seller, profile, category


def update_emotion_letter(
    db: Session,
    letter_code: str,
    current_user: User,
    category_code: str,
    title: str,
    content: str,
    desired_duration: int,
    point: int,
) -> tuple[EmotionLetter, EmotionCategory] | None:
    """
    出品中（status == 1）の感情レターを編集・更新する。
    """
    try:
        letter = db.scalar(
            select(EmotionLetter).where(
                EmotionLetter.letter_code == letter_code,
                EmotionLetter.status == 1,
            )
        )

        if letter is None:
            return None

        if letter.seller_id != current_user.user_id:
            raise PermissionError("他のユーザーの出品は編集できません")

        emotion_category = db.scalar(
            select(EmotionCategory).where(
                EmotionCategory.category_code == category_code
            )
        )

        if emotion_category is None:
            raise ValueError("指定された感情カテゴリが存在しません")

        letter.category_id = emotion_category.category_id
        letter.title = title
        letter.content = content
        letter.desired_duration = desired_duration
        letter.point = point

        db.commit()
        db.refresh(letter)

        return letter, emotion_category

    except Exception:
        db.rollback()
        raise


def cancel_emotion_letter(
    db: Session,
    letter_code: str,
    current_user: User,
) -> EmotionLetter | None:
    """
    出品中（status == 1）の感情レターを取り下げる（status = 4 に更新して論理削除・出品停止にする）。
    """
    try:
        letter = db.scalar(
            select(EmotionLetter).where(
                EmotionLetter.letter_code == letter_code,
                EmotionLetter.status == 1,
            )
        )

        if letter is None:
            return None

        if letter.seller_id != current_user.user_id:
            raise PermissionError("他のユーザーの出品は取り下げできません")

        letter.status = 4

        db.commit()
        db.refresh(letter)

        return letter

    except Exception:
        db.rollback()
        raise
