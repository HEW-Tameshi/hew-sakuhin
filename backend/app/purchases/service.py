"""
購入・取引（マッチング）機能 ビジネスロジック（サービス層）モジュール（app/purchases/service.py）

【このファイルの役割】
- 感情レターの購入処理と、それに伴うマッチング（t_matching）の生成を
  1トランザクション（flush / commit / rollback）で実行する。
- マッチング一覧取得（出品者視点・購入者視点）、マッチング詳細取得、および
  マッチングの状態遷移（対話開始 → 取引完了 / キャンセル）を担当する。
"""

from datetime import datetime, timezone
import secrets
import string

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.notifications.service import add_notification_record
from app.points.service import (
    InsufficientPointsError,
    add_point_history_record,
    get_user_point_balance,
)
from app.post.models import EmotionCategory, EmotionLetter
from app.purchases.models import LetterPurchase, Matching
from app.ranks.service import sync_user_rank_in_tx
from app.users.models import Profile, User


def generate_purchase_code() -> str:
    """t_letter_purchase.purchase_code 用の11文字の一意コード（'P' + 英大文字・数字10文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "P" + "".join(secrets.choice(characters) for _ in range(10))


def generate_matching_code() -> str:
    """t_matching.matching_code 用の10文字の一意コード（'M' + 英大文字・数字9文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "M" + "".join(secrets.choice(characters) for _ in range(9))


class SelfPurchaseError(ValueError):
    """自分の出品を自分で購入しようとした場合の例外"""
    pass


class LetterNotAvailableError(ValueError):
    """既に取り下げ済み・または購入済みの出品を購入しようとした場合の例外"""
    pass


class MatchingStateError(ValueError):
    """既に完了またはキャンセル済みのマッチング状態を変更しようとした場合の例外"""
    pass


def purchase_emotion_letter(
    db: Session,
    buyer: User,
    letter_code: str,
) -> tuple[LetterPurchase, Matching, EmotionLetter, User] | None:
    """
    感情レターを購入し、購入履歴（t_letter_purchase）と取引マッチング（t_matching）を
    1トランザクションで登録する。

    【処理の実行順序】
    1. 指定された letter_code で t_emotion_letter と出品者（m_user）を検索する（存在しなければ None）。
    2. 出品者が退会済みでないか、またレターが出品中（status == 1）かを確認する（購入不可なら LetterNotAvailableError）。
    3. 購入者（buyer.user_id）が出品者（letter.seller_id）自身でないか確認する（同一なら SelfPurchaseError）。
    4. 購入コード（P+10文字）とマッチングコード（M+9文字）を生成し重複確認する。
    5. t_emotion_letter の status を 2（購入済み・取引中）に更新する。
    6. t_letter_purchase に購入情報を追加し、db.flush() で自動採番された purchase_id を取得する。
    7. 取得した purchase_id を使って t_matching に取引マッチング情報を追加する。
    8. db.commit() で3テーブルすべての変更を同時に確定する（例外発生時は db.rollback() で取り消す）。
    """
    try:
        # 1. 購入対象の感情レターと出品者を検索
        row = db.execute(
            select(EmotionLetter, User)
            .join(User, EmotionLetter.seller_id == User.user_id)
            .where(EmotionLetter.letter_code == letter_code)
        ).first()

        if row is None:
            return None

        letter, seller = row

        # 2. 出品者が退会済み、またはレターが出品中（status == 1）でない場合は購入不可
        if seller.account_status != 1 or letter.status != 1:
            raise LetterNotAvailableError("この出品は現在購入できません")

        # 3. 自分の出品を自分で購入することはできない
        if letter.seller_id == buyer.user_id:
            raise SelfPurchaseError("自分の出品を購入することはできません")

        # 3-2. 購入者のポイント残高チェック
        buyer_balance = get_user_point_balance(db=db, user_id=buyer.user_id)
        if buyer_balance < letter.point:
            raise InsufficientPointsError("ポイント残高が不足しています")

        # 4. 一意コードの生成と重複確認（衝突時は1回再生成）
        purchase_code = generate_purchase_code()
        if db.scalar(
            select(LetterPurchase.purchase_id).where(
                LetterPurchase.purchase_code == purchase_code
            )
        ):
            purchase_code = generate_purchase_code()

        matching_code = generate_matching_code()
        if db.scalar(
            select(Matching.matching_id).where(
                Matching.matching_code == matching_code
            )
        ):
            matching_code = generate_matching_code()

        # 5. レターの状態を「2（購入済み・取引中）」に更新
        letter.status = 2

        # 6. レター購入履歴（t_letter_purchase）を追加し、flush()で purchase_id を取得
        purchase = LetterPurchase(
            purchase_code=purchase_code,
            letter_id=letter.letter_id,
            buyer_id=buyer.user_id,
            purchase_point=letter.point,
        )
        db.add(purchase)
        db.flush()

        # 7. 取引・マッチング（t_matching）を追加し、flush()で matching_id を取得
        matching = Matching(
            matching_code=matching_code,
            purchase_id=purchase.purchase_id,
            seller_id=seller.user_id,
            buyer_id=buyer.user_id,
            status=1,  # 1: マッチング成立（進行中）
        )
        db.add(matching)
        db.flush()

        # 7-2. ポイント履歴（購入者: -point / 出品者: +point）を1トランザクションで記録
        add_point_history_record(
            db=db,
            user_id=buyer.user_id,
            point=-letter.point,
            point_type=3,  # 3: レター購入消費
            related_purchase_id=purchase.purchase_id,
            related_matching_id=matching.matching_id,
        )
        add_point_history_record(
            db=db,
            user_id=seller.user_id,
            point=letter.point,
            point_type=4,  # 4: レター売上獲得
            related_purchase_id=purchase.purchase_id,
            related_matching_id=matching.matching_id,
        )

        # 7-3. 出品者へ購入・マッチング成立通知を作成し、累計獲得ポイントに応じてランクを同期する
        add_notification_record(
            db=db,
            user_id=seller.user_id,
            notification_type=1,  # 1: 購入・マッチング成立
            title="出品した手紙が購入されました",
            message=f"「{letter.title}」が購入され、マッチングが成立しました（+{letter.point}pt）。",
        )
        db.flush()
        sync_user_rank_in_tx(db=db, user_id=seller.user_id)

        # 8. トランザクションを確定する
        db.commit()

        db.refresh(purchase)
        db.refresh(matching)
        db.refresh(letter)

        return purchase, matching, letter, seller

    except Exception:
        db.rollback()
        raise


def list_user_purchases(
    db: Session,
    buyer: User,
) -> list[tuple[LetterPurchase, Matching, EmotionLetter, User, Profile, EmotionCategory]]:
    """
    ログイン中の購入者（buyer）が購入したレター履歴一覧を新しい順（purchase_id 降順）で取得する。
    """
    stmt = (
        select(
            LetterPurchase,
            Matching,
            EmotionLetter,
            User,
            Profile,
            EmotionCategory,
        )
        .join(Matching, Matching.purchase_id == LetterPurchase.purchase_id)
        .join(EmotionLetter, EmotionLetter.letter_id == LetterPurchase.letter_id)
        .join(User, EmotionLetter.seller_id == User.user_id)
        .join(Profile, User.user_id == Profile.user_id)
        .join(
            EmotionCategory,
            EmotionLetter.category_id == EmotionCategory.category_id,
        )
        .where(LetterPurchase.buyer_id == buyer.user_id)
        .order_by(LetterPurchase.purchase_id.desc())
    )

    return list(db.execute(stmt).all())


def get_purchase_by_code(
    db: Session,
    purchase_code: str,
    current_user: User,
) -> tuple[LetterPurchase, Matching, EmotionLetter, User, Profile, EmotionCategory] | None:
    """
    指定された購入コード（purchase_code）の購入詳細を1件取得する。
    ※購入者本人または出品者本人以外は閲覧不可（PermissionError を送出）。
    """
    stmt = (
        select(
            LetterPurchase,
            Matching,
            EmotionLetter,
            User,
            Profile,
            EmotionCategory,
        )
        .join(Matching, Matching.purchase_id == LetterPurchase.purchase_id)
        .join(EmotionLetter, EmotionLetter.letter_id == LetterPurchase.letter_id)
        .join(User, EmotionLetter.seller_id == User.user_id)
        .join(Profile, User.user_id == Profile.user_id)
        .join(
            EmotionCategory,
            EmotionLetter.category_id == EmotionCategory.category_id,
        )
        .where(LetterPurchase.purchase_code == purchase_code)
    )

    row = db.execute(stmt).first()
    if row is None:
        return None

    purchase, matching, letter, seller, seller_profile, category = row

    # 購入者本人または出品者本人のみ閲覧可能
    if current_user.user_id not in (purchase.buyer_id, seller.user_id):
        raise PermissionError("他のユーザーの購入履歴は閲覧できません")

    return purchase, matching, letter, seller, seller_profile, category


def list_user_matchings(
    db: Session,
    current_user: User,
    role: str | None = None,
    status_filter: str | None = None,
) -> list[tuple[Matching, LetterPurchase, EmotionLetter, User, Profile, User, Profile, EmotionCategory]]:
    """
    ログイン中のユーザーが「出品者（seller）」または「購入者（buyer）」として関わっている
    マッチング（取引）一覧を新しい順（matching_id 降順）で取得する。

    【絞り込み条件（任意）】
    - role == "seller": 自分が出品者のマッチングのみ
    - role == "buyer" : 自分が購入者のマッチングのみ
    - status_filter == "active"   : 進行中（status が 1, 2, 3）のみ
    - status_filter == "completed": 取引完了（status == 4）のみ
    - status_filter == "canceled" : キャンセル（status == 5）のみ
    """
    SellerUser = aliased(User)
    SellerProfile = aliased(Profile)
    BuyerUser = aliased(User)
    BuyerProfile = aliased(Profile)

    stmt = (
        select(
            Matching,
            LetterPurchase,
            EmotionLetter,
            SellerUser,
            SellerProfile,
            BuyerUser,
            BuyerProfile,
            EmotionCategory,
        )
        .join(LetterPurchase, Matching.purchase_id == LetterPurchase.purchase_id)
        .join(EmotionLetter, LetterPurchase.letter_id == EmotionLetter.letter_id)
        .join(SellerUser, Matching.seller_id == SellerUser.user_id)
        .join(SellerProfile, SellerUser.user_id == SellerProfile.user_id)
        .join(BuyerUser, Matching.buyer_id == BuyerUser.user_id)
        .join(BuyerProfile, BuyerUser.user_id == BuyerProfile.user_id)
        .join(
            EmotionCategory,
            EmotionLetter.category_id == EmotionCategory.category_id,
        )
    )

    # 役割（出品者 / 購入者）による絞り込み
    if role == "seller":
        stmt = stmt.where(Matching.seller_id == current_user.user_id)
    elif role == "buyer":
        stmt = stmt.where(Matching.buyer_id == current_user.user_id)
    else:
        stmt = stmt.where(
            or_(
                Matching.seller_id == current_user.user_id,
                Matching.buyer_id == current_user.user_id,
            )
        )

    # 取引状態による絞り込み
    if status_filter == "active":
        stmt = stmt.where(Matching.status.in_([1, 2, 3]))
    elif status_filter == "completed":
        stmt = stmt.where(Matching.status == 4)
    elif status_filter == "canceled":
        stmt = stmt.where(Matching.status == 5)

    stmt = stmt.order_by(Matching.matching_id.desc())

    return list(db.execute(stmt).all())


def get_matching_by_code(
    db: Session,
    matching_code: str,
    current_user: User,
) -> tuple[Matching, LetterPurchase, EmotionLetter, User, Profile, User, Profile, EmotionCategory] | None:
    """
    指定されたマッチングコード（matching_code）のマッチング詳細を1件取得する。
    ※当事者（出品者または購入者）以外は閲覧不可（PermissionError を送出）。
    """
    SellerUser = aliased(User)
    SellerProfile = aliased(Profile)
    BuyerUser = aliased(User)
    BuyerProfile = aliased(Profile)

    stmt = (
        select(
            Matching,
            LetterPurchase,
            EmotionLetter,
            SellerUser,
            SellerProfile,
            BuyerUser,
            BuyerProfile,
            EmotionCategory,
        )
        .join(LetterPurchase, Matching.purchase_id == LetterPurchase.purchase_id)
        .join(EmotionLetter, LetterPurchase.letter_id == EmotionLetter.letter_id)
        .join(SellerUser, Matching.seller_id == SellerUser.user_id)
        .join(SellerProfile, SellerUser.user_id == SellerProfile.user_id)
        .join(BuyerUser, Matching.buyer_id == BuyerUser.user_id)
        .join(BuyerProfile, BuyerUser.user_id == BuyerProfile.user_id)
        .join(
            EmotionCategory,
            EmotionLetter.category_id == EmotionCategory.category_id,
        )
        .where(Matching.matching_code == matching_code)
    )

    row = db.execute(stmt).first()
    if row is None:
        return None

    (
        matching,
        purchase,
        letter,
        seller,
        seller_profile,
        buyer,
        buyer_profile,
        category,
    ) = row

    # 当事者（出品者・購入者）以外は閲覧不可
    if current_user.user_id not in (matching.seller_id, matching.buyer_id):
        raise PermissionError("このマッチングの当事者ではないため閲覧できません")

    return (
        matching,
        purchase,
        letter,
        seller,
        seller_profile,
        buyer,
        buyer_profile,
        category,
    )


def update_matching_status(
    db: Session,
    matching_code: str,
    current_user: User,
    new_status: int,
) -> tuple[Matching, LetterPurchase, EmotionLetter, User, Profile, User, Profile, EmotionCategory] | None:
    """
    進行中のマッチング（status が 1, 2, 3）の状態を更新する。

    【処理の実行順序】
    1. get_matching_by_code で対象マッチングと関連データを取得し、当事者確認を行う（未存在は None、第三者は PermissionError）。
    2. 現在の matching.status が既に完了（4）またはキャンセル（5）の場合は MatchingStateError を送出する。
    3. new_status に応じてステータスと関連テーブルを更新する：
       - new_status == 2 または 3（対話準備・対話中）：matching.status を更新する。
       - new_status == 4（取引完了）：matching.status = 4、matching.completed_at = 現在時刻、letter.status = 3（取引完了）に更新する。
       - new_status == 5（取引キャンセル）：matching.status = 5、letter.status = 4（停止）に更新する。
    4. db.commit() で確定し、更新後のタプルを返す（例外時は db.rollback()）。
    """
    try:
        result = get_matching_by_code(
            db=db,
            matching_code=matching_code,
            current_user=current_user,
        )

        if result is None:
            return None

        (
            matching,
            purchase,
            letter,
            seller,
            seller_profile,
            buyer,
            buyer_profile,
            category,
        ) = result

        # 既に完了（4）またはキャンセル（5）している取引は状態変更不可
        if matching.status in (4, 5):
            raise MatchingStateError("既に完了またはキャンセルされた取引の状態は変更できません")

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if new_status == 4:
            # 取引完了：完了日時を記録し、レターも取引完了（3）にする
            matching.status = 4
            matching.completed_at = now
            letter.status = 3
        elif new_status == 5:
            # 取引キャンセル：レターを停止（4）にする（退会時キャンセルルールと統一）
            matching.status = 5
            letter.status = 4
        else:
            # 2（対話準備中）または 3（対話中）への遷移
            matching.status = new_status

        db.commit()
        db.refresh(matching)
        db.refresh(letter)

        return (
            matching,
            purchase,
            letter,
            seller,
            seller_profile,
            buyer,
            buyer_profile,
            category,
        )

    except Exception:
        db.rollback()
        raise
