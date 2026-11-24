"""
ポイント・決済・サブスクリプション機能 APIルーター定義モジュール（app/points/router.py）

【このファイルの役割】
- /api/points 配下のエンドポイントを受け付ける：
  1. GET    /api/points/plans        : ポイント購入プラン＆プレミアムサブスク一覧取得
  2. GET    /api/points/balance      : ログイン中ユーザーの所持ポイント残高取得
  3. GET    /api/points/history      : ログイン中ユーザーのポイント増減履歴一覧取得
  4. POST   /api/points/charge       : ポイントチャージ実行（t_payment + t_point_history）
  5. GET    /api/points/subscription : 現在の有効なサブスク契約情報取得
  6. POST   /api/points/subscription : プレミアムサブスク加入（月額700円・700pt付与）
  7. DELETE /api/points/subscription : プレミアムサブスク解約
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.points.schemas import (
    POINT_CHARGE_PLANS,
    POINT_TYPE_LABELS,
    PREMIUM_SUBSCRIPTION_GRANT_POINTS,
    PREMIUM_SUBSCRIPTION_PLAN_NAME,
    PREMIUM_SUBSCRIPTION_PRICE,
    PointBalanceResponse,
    PointChargeRequest,
    PointChargeResponse,
    PointHistoryItemResponse,
    PointPlanItem,
    PointPlansResponse,
    SubscriptionCreateRequest,
    SubscriptionPlanInfo,
    SubscriptionResponse,
)
from app.points.service import (
    SubscriptionAlreadyActiveError,
    cancel_subscription,
    charge_points,
    create_subscription,
    get_active_subscription,
    get_user_point_balance,
    list_point_histories,
)
from app.users.models import User

router = APIRouter(
    prefix="/api/points",
    tags=["Points & Payments"],
)


@router.get(
    "/plans",
    response_model=PointPlansResponse,
    status_code=status.HTTP_200_OK,
    summary="ポイント購入プラン・サブスク一覧取得API",
)
def get_point_plans():
    """point.html で表示するポイント購入プランとプレミアムサブスクの定義を返す。"""
    return PointPlansResponse(
        charge_plans=[
            PointPlanItem(points=pts, price_yen=yen)
            for pts, yen in POINT_CHARGE_PLANS.items()
        ],
        subscription_plan=SubscriptionPlanInfo(
            plan_name=PREMIUM_SUBSCRIPTION_PLAN_NAME,
            price_yen=PREMIUM_SUBSCRIPTION_PRICE,
            monthly_points=PREMIUM_SUBSCRIPTION_GRANT_POINTS,
        ),
    )


@router.get(
    "/balance",
    response_model=PointBalanceResponse,
    status_code=status.HTTP_200_OK,
    summary="所持ポイント残高取得API",
)
def get_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ログイン中ユーザーの現在のポイント残高とサブスク加入状態を返す。"""
    balance = get_user_point_balance(db=db, user_id=current_user.user_id)
    active_sub = get_active_subscription(db=db, user_id=current_user.user_id)
    return PointBalanceResponse(
        user_code=current_user.user_code,
        balance=balance,
        has_active_subscription=(active_sub is not None),
    )


@router.get(
    "/history",
    response_model=list[PointHistoryItemResponse],
    status_code=status.HTTP_200_OK,
    summary="ポイント増減履歴一覧取得API",
)
def get_point_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ログイン中ユーザーのポイントチャージ・消費・受取履歴を新しい順で返す。"""
    records = list_point_histories(db=db, user=current_user)
    return [
        PointHistoryItemResponse(
            point_history_code=r.point_history_code,
            point=r.point,
            point_type=r.point_type,
            point_type_label=POINT_TYPE_LABELS.get(r.point_type, "その他"),
            created_at=r.created_at,
        )
        for r in records
    ]


@router.post(
    "/charge",
    response_model=PointChargeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="ポイントチャージAPI",
)
def charge_user_points(
    request: PointChargeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """選択したプランのポイントを購入・チャージする（HTTP 201 Created）。"""
    payment, history, balance_after = charge_points(
        db=db,
        user=current_user,
        points=request.points,
        payment_method=request.payment_method,
    )
    return PointChargeResponse(
        payment_code=payment.payment_code,
        point_history_code=history.point_history_code,
        charged_points=history.point,
        paid_amount_yen=payment.amount,
        balance_after=balance_after,
        paid_at=payment.paid_at,
    )


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="契約中サブスクリプション取得API",
)
def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ログイン中ユーザーの有効なプレミアムサブスク契約を取得する（未契約時は 404）。"""
    sub = get_active_subscription(db=db, user_id=current_user.user_id)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="現在有効なサブスクリプション契約はありません",
        )
    balance = get_user_point_balance(db=db, user_id=current_user.user_id)
    return SubscriptionResponse(
        subscription_code=sub.subscription_code,
        plan_name=sub.plan_name,
        price=sub.price,
        start_date=sub.start_date,
        end_date=sub.end_date,
        status=sub.status,
        granted_points=0,
        balance_after=balance,
    )


@router.post(
    "/subscription",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="プレミアムポイントサブスク加入API",
)
def subscribe_premium(
    request: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """プレミアムポイントサブスク（月額700円）に加入し、700ptを付与する（HTTP 201 Created）。"""
    try:
        sub, _, history, balance_after = create_subscription(
            db=db,
            user=current_user,
            payment_method=request.payment_method,
        )
        return SubscriptionResponse(
            subscription_code=sub.subscription_code,
            plan_name=sub.plan_name,
            price=sub.price,
            start_date=sub.start_date,
            end_date=sub.end_date,
            status=sub.status,
            granted_points=history.point,
            balance_after=balance_after,
        )
    except SubscriptionAlreadyActiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.delete(
    "/subscription",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="プレミアムポイントサブスク解約API",
)
def unsubscribe_premium(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """有効なプレミアムサブスクを解約する（HTTP 200 OK、未契約時は 404）。"""
    sub = cancel_subscription(db=db, user=current_user)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="解約対象の有効なサブスクリプション契約がありません",
        )
    balance = get_user_point_balance(db=db, user_id=current_user.user_id)
    return SubscriptionResponse(
        subscription_code=sub.subscription_code,
        plan_name=sub.plan_name,
        price=sub.price,
        start_date=sub.start_date,
        end_date=sub.end_date,
        status=sub.status,
        granted_points=0,
        balance_after=balance,
    )
