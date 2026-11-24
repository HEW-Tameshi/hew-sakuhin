"""
レビュー＆チップ機能 ビジネスロジック（サービス層）モジュール（app/reviews/service.py）

【このファイルの役割】
- 取引（t_matching）に対するレビュー（t_review）およびチップ（t_tip）を1トランザクションで登録する。
- マッチング別レビュー一覧取得、および特定ユーザーが受け取ったレビューと平均評価の集計を行う。
"""

import secrets
import string

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.notifications.service import add_notification_record
from app.points.service import (
    InsufficientPointsError,
    add_point_history_record,
    get_user_point_balance,
)
from app.purchases.models import Matching
from app.ranks.service import sync_user_rank_in_tx
from app.reviews.models import Review, Tip
from app.users.models import Profile, User


def generate_review_code() -> str:
    """t_review.review_code 用の10文字の一意コード（'R' + 英大文字・数字9文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "R" + "".join(secrets.choice(characters) for _ in range(9))


def generate_tip_code() -> str:
    """t_tip.tip_code 用の10文字の一意コード（'T' + 英大文字・数字9文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "T" + "".join(secrets.choice(characters) for _ in range(9))


class ReviewAlreadyExistsError(ValueError):
    """同一取引に対して同じユーザーが既にレビュー投稿済みの場合の例外"""
    pass


class ReviewNotAllowedError(ValueError):
    """キャンセル済みの取引に対してレビューを投稿しようとした場合の例外"""
    pass


def create_review(
    db: Session,
    matching_code: str,
    reviewer: User,
    rating: int,
    comment: str | None = None,
    tip_amount: int = 0,
) -> tuple[Review, Tip | None, Matching, Profile, User, Profile] | None:
    """
    レビュー（t_review）を登録し、tip_amount > 0 の場合はチップ（t_tip）も1トランザクションで同時登録する。

    【処理の実行順序】
    1. matching_code で t_matching を検索する（未存在なら None）。
    2. 投稿者（reviewer）が当事者（seller_id または buyer_id）か確認する（第三者は PermissionError）。
    3. キャンセル済み取引（status == 5）でないことを確認する（キャンセル済みは ReviewNotAllowedError）。
    4. 同一マッチング×同一投稿者の既存レビューがないか確認する（重複時は ReviewAlreadyExistsError）。
    5. レビュー相手（reviewee_id）を自動特定し、review_code を採番して t_review を追加する。
    6. tip_amount > 0 の場合は tip_code を採番して t_tip にも同時追加する。
    7. db.commit() で確定する（例外時は db.rollback() で取り消す）。
    """
    try:
        # 1. 対象マッチングの検索
        matching = db.scalar(
            select(Matching).where(Matching.matching_code == matching_code)
        )
        if matching is None:
            return None

        # 2. 当事者確認
        if reviewer.user_id not in (matching.seller_id, matching.buyer_id):
            raise PermissionError("この取引の当事者ではないためレビューを投稿できません")

        # 3. キャンセル済み取引はレビュー不可
        if matching.status == 5:
            raise ReviewNotAllowedError("キャンセルされた取引にはレビューを投稿できません")

        # 4. 重複レビュー確認
        existing = db.scalar(
            select(Review.review_id).where(
                Review.matching_id == matching.matching_id,
                Review.reviewer_id == reviewer.user_id,
            )
        )
        if existing is not None:
            raise ReviewAlreadyExistsError("この取引は既にレビュー済みです")

        # 5. レビュー相手（reviewee）の特定
        reviewee_id = (
            matching.buyer_id
            if reviewer.user_id == matching.seller_id
            else matching.seller_id
        )
        reviewee = db.get(User, reviewee_id)
        if reviewee is None:
            raise ValueError("レビュー対象のユーザーが見つかりません")

        reviewer_profile = db.scalar(
            select(Profile).where(Profile.user_id == reviewer.user_id)
        )
        reviewee_profile = db.scalar(
            select(Profile).where(Profile.user_id == reviewee.user_id)
        )
        if reviewer_profile is None or reviewee_profile is None:
            raise ValueError("プロフィール情報が見つかりません")

        # review_code 採番（衝突時は1回再生成）
        review_code = generate_review_code()
        if db.scalar(select(Review.review_id).where(Review.review_code == review_code)):
            review_code = generate_review_code()

        review = Review(
            review_code=review_code,
            matching_id=matching.matching_id,
            reviewer_id=reviewer.user_id,
            reviewee_id=reviewee.user_id,
            rating=rating,
            comment=comment,
        )
        db.add(review)

        # 6. チップが指定（1pt以上）されている場合は残高チェックを行い t_tip と t_point_history に同時登録
        tip = None
        if tip_amount > 0:
            sender_balance = get_user_point_balance(db=db, user_id=reviewer.user_id)
            if sender_balance < tip_amount:
                raise InsufficientPointsError("ポイント残高が不足しています")

            tip_code = generate_tip_code()
            if db.scalar(select(Tip.tip_id).where(Tip.tip_code == tip_code)):
                tip_code = generate_tip_code()

            tip = Tip(
                tip_code=tip_code,
                sender_id=reviewer.user_id,
                receiver_id=reviewee.user_id,
                amount=tip_amount,
                message=comment,
            )
            db.add(tip)
            db.flush()

            # チップ送付（送信者: -tip_amount / 受取人: +tip_amount）をポイント履歴へ記録
            add_point_history_record(
                db=db,
                user_id=reviewer.user_id,
                point=-tip_amount,
                point_type=5,  # 5: チップ送付消費
                related_matching_id=matching.matching_id,
                related_tip_id=tip.tip_id,
            )
            add_point_history_record(
                db=db,
                user_id=reviewee.user_id,
                point=tip_amount,
                point_type=6,  # 6: チップ受取獲得
                related_matching_id=matching.matching_id,
                related_tip_id=tip.tip_id,
            )

        # 6-2. レビュー相手へ通知を作成し、チップ獲得時は相手のランクも同期する
        tip_note = f"（チップ +{tip_amount}pt 付き）" if tip_amount > 0 else ""
        add_notification_record(
            db=db,
            user_id=reviewee.user_id,
            notification_type=3,  # 3: レビュー・チップ受信
            title="レビューが届きました",
            message=f"{reviewer_profile.nickname}さんから星{rating}の評価が届きました{tip_note}。",
        )
        if tip_amount > 0:
            db.flush()
            sync_user_rank_in_tx(db=db, user_id=reviewee.user_id)

        # 7. トランザクション確定
        db.commit()
        db.refresh(review)
        if tip is not None:
            db.refresh(tip)

        return review, tip, matching, reviewer_profile, reviewee, reviewee_profile

    except Exception:
        db.rollback()
        raise


def list_reviews_by_matching(
    db: Session,
    matching_code: str,
    current_user: User,
) -> list[tuple[Review, Matching, User, Profile, User, Profile]] | None:
    """指定されたマッチングのレビュー一覧を取得する（当事者以外は PermissionError）。"""
    matching = db.scalar(
        select(Matching).where(Matching.matching_code == matching_code)
    )
    if matching is None:
        return None

    if current_user.user_id not in (matching.seller_id, matching.buyer_id):
        raise PermissionError("この取引の当事者ではないためレビューを閲覧できません")

    ReviewerUser = aliased(User)
    ReviewerProfile = aliased(Profile)
    RevieweeUser = aliased(User)
    RevieweeProfile = aliased(Profile)

    stmt = (
        select(
            Review,
            Matching,
            ReviewerUser,
            ReviewerProfile,
            RevieweeUser,
            RevieweeProfile,
        )
        .join(Matching, Review.matching_id == Matching.matching_id)
        .join(ReviewerUser, Review.reviewer_id == ReviewerUser.user_id)
        .join(ReviewerProfile, ReviewerUser.user_id == ReviewerProfile.user_id)
        .join(RevieweeUser, Review.reviewee_id == RevieweeUser.user_id)
        .join(RevieweeProfile, RevieweeUser.user_id == RevieweeProfile.user_id)
        .where(Review.matching_id == matching.matching_id)
        .order_by(Review.review_id.desc())
    )

    return [tuple(r) for r in db.execute(stmt).all()]


def get_user_review_summary(
    db: Session,
    user_code: str,
) -> tuple[User, Profile, list[tuple[Review, Matching, User, Profile, User, Profile]], float | None] | None:
    """
    指定された会員コード（user_code）が受け取ったレビュー一覧と平均評価（小数点1桁）を取得する。
    """
    target_user = db.scalar(
        select(User).where(
            User.user_code == user_code,
            User.account_status == 1,
        )
    )
    if target_user is None:
        return None

    target_profile = db.scalar(
        select(Profile).where(Profile.user_id == target_user.user_id)
    )
    if target_profile is None:
        return None

    ReviewerUser = aliased(User)
    ReviewerProfile = aliased(Profile)
    RevieweeUser = aliased(User)
    RevieweeProfile = aliased(Profile)

    stmt = (
        select(
            Review,
            Matching,
            ReviewerUser,
            ReviewerProfile,
            RevieweeUser,
            RevieweeProfile,
        )
        .join(Matching, Review.matching_id == Matching.matching_id)
        .join(ReviewerUser, Review.reviewer_id == ReviewerUser.user_id)
        .join(ReviewerProfile, ReviewerUser.user_id == ReviewerProfile.user_id)
        .join(RevieweeUser, Review.reviewee_id == RevieweeUser.user_id)
        .join(RevieweeProfile, RevieweeUser.user_id == RevieweeProfile.user_id)
        .where(Review.reviewee_id == target_user.user_id)
        .order_by(Review.review_id.desc())
    )

    rows = [tuple(r) for r in db.execute(stmt).all()]
    if rows:
        avg_rating = round(sum(r[0].rating for r in rows) / len(rows), 1)
    else:
        avg_rating = None

    return target_user, target_profile, rows, avg_rating
