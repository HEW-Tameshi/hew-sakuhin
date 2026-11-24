"""
ポイント・決済・サブスクリプション機能 ビジネスロジック（サービス層）モジュール（app/points/service.py）

【このファイルの役割】
- t_point_history の合計（SUM）によるユーザーの正確な現在ポイント残高計算を行う。
- ポイントチャージ（t_payment + t_point_history の1トランザクション登録）を行う。
- プレミアムポイントサブスクの契約（t_subscription + t_payment + t_point_history の1トランザクション登録）・
  状態確認・解約を行う。
- 購入機能（app/purchases）やレビューのチップ機能（app/reviews）からも共通利用できる
  残高チェックおよびポイント履歴記録ヘルパーを提供する。
"""

from datetime import date, datetime, timezone
import secrets
import string

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.points.models import Payment, PointHistory, Subscription
from app.points.schemas import (
    POINT_CHARGE_PLANS,
    PREMIUM_SUBSCRIPTION_GRANT_POINTS,
    PREMIUM_SUBSCRIPTION_PLAN_NAME,
    PREMIUM_SUBSCRIPTION_PRICE,
)
from app.users.models import User


class InsufficientPointsError(ValueError):
    """ポイント残高が不足している場合の例外"""
    pass


class SubscriptionAlreadyActiveError(ValueError):
    """既に有効なプレミアムサブスクに加入済みの場合の例外"""
    pass


def generate_payment_code() -> str:
    """t_payment.payment_code 用の11文字コード（'PAY' + 英大文字・数字8文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "PAY" + "".join(secrets.choice(characters) for _ in range(8))


def generate_subscription_code() -> str:
    """t_subscription.subscription_code 用の11文字コード（'SUB' + 英大文字・数字8文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "SUB" + "".join(secrets.choice(characters) for _ in range(8))


def generate_point_history_code() -> str:
    """t_point_history.point_history_code 用の10文字コード（'PT' + 英大文字・数字8文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "PT" + "".join(secrets.choice(characters) for _ in range(8))


def get_user_point_balance(db: Session, user_id: int) -> int:
    """
    指定ユーザーの現在の所持ポイント残高（t_point_history.point の合計）を返す。
    履歴が1件もない場合は 0 を返す。
    """
    total = db.scalar(
        select(func.coalesce(func.sum(PointHistory.point), 0)).where(
            PointHistory.user_id == user_id
        )
    )
    return int(total or 0)


def add_point_history_record(
    db: Session,
    user_id: int,
    point: int,
    point_type: int,
    related_purchase_id: int | None = None,
    related_matching_id: int | None = None,
    related_payment_id: int | None = None,
    related_tip_id: int | None = None,
) -> PointHistory:
    """
    トランザクション内でポイント履歴（t_point_history）を1件セッションへ追加する共通ヘルパー。
    ※コミットは呼び出し元のトランザクションで行う。
    """
    code = generate_point_history_code()
    if db.scalar(
        select(PointHistory.point_history_id).where(
            PointHistory.point_history_code == code
        )
    ):
        code = generate_point_history_code()

    record = PointHistory(
        point_history_code=code,
        user_id=user_id,
        point=point,
        point_type=point_type,
        related_purchase_id=related_purchase_id,
        related_matching_id=related_matching_id,
        related_payment_id=related_payment_id,
        related_tip_id=related_tip_id,
    )
    db.add(record)
    return record


def list_point_histories(db: Session, user: User) -> list[PointHistory]:
    """ログイン中ユーザーのポイント履歴一覧を新しい順で取得する。"""
    return list(
        db.scalars(
            select(PointHistory)
            .where(PointHistory.user_id == user.user_id)
            .order_by(PointHistory.point_history_id.desc())
        ).all()
    )


def charge_points(
    db: Session,
    user: User,
    points: int,
    payment_method: int = 1,
) -> tuple[Payment, PointHistory, int]:
    """
    ポイントチャージ決済（t_payment: payment_type=3）とポイント付与（t_point_history: point_type=1）を
    1トランザクションで登録する。

    【処理の実行順序】
    1. 選択されたポイント数に対応する料金（円）を POINT_CHARGE_PLANS から取得する。
    2. payment_code を採番して t_payment（payment_type=3）を追加し、db.flush() で payment_id を取得する。
    3. 取得した payment_id を紐づけて t_point_history（point_type=1, +points）を追加する。
    4. db.commit() で確定し、チャージ後の最新残高を計算して返す（例外時は db.rollback()）。
    """
    try:
        price_yen = POINT_CHARGE_PLANS.get(points)
        if price_yen is None:
            raise ValueError("不正なポイントプランが指定されました")

        payment_code = generate_payment_code()
        if db.scalar(
            select(Payment.payment_id).where(Payment.payment_code == payment_code)
        ):
            payment_code = generate_payment_code()

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        payment = Payment(
            payment_code=payment_code,
            user_id=user.user_id,
            payment_type=3,  # 3: ポイントチャージ（purchase_id=NULL, subscription_id=NULL）
            purchase_id=None,
            subscription_id=None,
            payment_method=payment_method,
            amount=price_yen,
            payment_status=1,  # 1: 決済完了
            paid_at=now,
        )
        db.add(payment)
        db.flush()

        history = add_point_history_record(
            db=db,
            user_id=user.user_id,
            point=points,
            point_type=1,  # 1: ポイントチャージ
            related_payment_id=payment.payment_id,
        )

        db.commit()
        db.refresh(payment)
        db.refresh(history)

        balance_after = get_user_point_balance(db=db, user_id=user.user_id)
        return payment, history, balance_after

    except Exception:
        db.rollback()
        raise


def get_active_subscription(db: Session, user_id: int) -> Subscription | None:
    """指定ユーザーの現在有効（status == 1）なサブスクリプション契約を取得する。"""
    return db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == 1,
        )
        .order_by(Subscription.subscription_id.desc())
    )


def create_subscription(
    db: Session,
    user: User,
    payment_method: int = 1,
) -> tuple[Subscription, Payment, PointHistory, int]:
    """
    プレミアムポイントサブスク（月額700円・700pt付与）を1トランザクションで契約する。

    【処理の実行順序】
    1. 既に有効（status == 1）なサブスク契約がないか確認する（あれば SubscriptionAlreadyActiveError）。
    2. t_subscription へ新規契約を追加し、db.flush() で subscription_id を取得する。
    3. t_payment（payment_type=2, subscription_id 設定）を追加し、db.flush() で payment_id を取得する。
    4. t_point_history（point_type=2, +700pt, related_payment_id 設定）を追加する。
    5. db.commit() で確定し、付与後の最新残高とともに返す（例外時は db.rollback()）。
    """
    try:
        existing = get_active_subscription(db=db, user_id=user.user_id)
        if existing is not None:
            raise SubscriptionAlreadyActiveError("既にプレミアムポイントサブスクに加入しています")

        sub_code = generate_subscription_code()
        if db.scalar(
            select(Subscription.subscription_id).where(
                Subscription.subscription_code == sub_code
            )
        ):
            sub_code = generate_subscription_code()

        payment_code = generate_payment_code()
        if db.scalar(
            select(Payment.payment_id).where(Payment.payment_code == payment_code)
        ):
            payment_code = generate_payment_code()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today = date.today()

        subscription = Subscription(
            subscription_code=sub_code,
            user_id=user.user_id,
            plan_name=PREMIUM_SUBSCRIPTION_PLAN_NAME,
            price=PREMIUM_SUBSCRIPTION_PRICE,
            start_date=today,
            end_date=None,
            status=1,  # 1: 有効
        )
        db.add(subscription)
        db.flush()

        payment = Payment(
            payment_code=payment_code,
            user_id=user.user_id,
            payment_type=2,  # 2: サブスク決済（purchase_id=NULL, subscription_id NOT NULL）
            purchase_id=None,
            subscription_id=subscription.subscription_id,
            payment_method=payment_method,
            amount=PREMIUM_SUBSCRIPTION_PRICE,
            payment_status=1,
            paid_at=now,
        )
        db.add(payment)
        db.flush()

        history = add_point_history_record(
            db=db,
            user_id=user.user_id,
            point=PREMIUM_SUBSCRIPTION_GRANT_POINTS,
            point_type=2,  # 2: サブスク付与
            related_payment_id=payment.payment_id,
        )

        db.commit()
        db.refresh(subscription)
        db.refresh(payment)
        db.refresh(history)

        balance_after = get_user_point_balance(db=db, user_id=user.user_id)
        return subscription, payment, history, balance_after

    except Exception:
        db.rollback()
        raise


def cancel_subscription(
    db: Session,
    user: User,
) -> Subscription | None:
    """有効なサブスク契約を解約（status = 2, end_date = 本日）にする。"""
    try:
        sub = get_active_subscription(db=db, user_id=user.user_id)
        if sub is None:
            return None

        sub.status = 2  # 2: 解約済み
        sub.end_date = date.today()

        db.commit()
        db.refresh(sub)
        return sub

    except Exception:
        db.rollback()
        raise
