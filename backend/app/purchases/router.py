"""
購入・取引（マッチング）機能 APIルーター定義モジュール（app/purchases/router.py）

【このファイルの役割】
- /api/purchases 配下のエンドポイントを受け付ける：
  1. POST  /api/purchases                                 : レター購入（購入履歴＋マッチングの生成）
  2. GET   /api/purchases                                 : 自分の購入履歴一覧取得
  3. GET   /api/purchases/matchings                       : 自分が関わるマッチング（取引）一覧取得（出品者・購入者双方対応）
  4. GET   /api/purchases/matchings/{matching_code}       : マッチング詳細取得
  5. PATCH /api/purchases/matchings/{matching_code}/status: マッチングの状態更新（対話開始・取引完了・キャンセル）
  6. GET   /api/purchases/{purchase_code}                 : 購入詳細取得
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.points.service import InsufficientPointsError
from app.purchases.schemas import (
    MatchingDetailResponse,
    MatchingStatusUpdateRequest,
    PurchaseCreateRequest,
    PurchaseCreateResponse,
    PurchaseDetailResponse,
)
from app.purchases.service import (
    LetterNotAvailableError,
    MatchingStateError,
    SelfPurchaseError,
    get_matching_by_code,
    get_purchase_by_code,
    list_user_matchings,
    list_user_purchases,
    purchase_emotion_letter,
    update_matching_status,
)
from app.users.models import User

# /api/purchases プレフィックスを持つルーターを生成
router = APIRouter(
    prefix="/api/purchases",
    tags=["Purchases & Matchings"],
)


def _to_matching_response(
    row: tuple,
    current_user: User,
) -> MatchingDetailResponse:
    """サービス層から返されたタプルを MatchingDetailResponse スキーマに変換するヘルパー関数。"""
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

    user_role = (
        "seller" if current_user.user_id == matching.seller_id else "buyer"
    )

    return MatchingDetailResponse(
        matching_code=matching.matching_code,
        purchase_code=purchase.purchase_code,
        letter_code=letter.letter_code,
        seller_code=seller.user_code,
        seller_nickname=seller_profile.nickname,
        buyer_code=buyer.user_code,
        buyer_nickname=buyer_profile.nickname,
        category_code=category.category_code,
        category_name=category.category_name,
        title=letter.title,
        content=letter.content,
        desired_duration=letter.desired_duration,
        purchase_point=purchase.purchase_point,
        matching_status=matching.status,
        user_role=user_role,
        created_at=matching.created_at,
        completed_at=matching.completed_at,
    )


@router.post(
    "",
    response_model=PurchaseCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="レター購入・マッチング成立API",
)
def create_purchase(
    request: PurchaseCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    レター購入API（POST /api/purchases）

    【処理の実行順序】
    1. Depends(get_current_user) によりログイン中の購入者（current_user）を取得する（未ログインは HTTP 401）。
    2. PurchaseCreateRequest スキーマで入力値（letter_code）を検証する（不正時は HTTP 422）。
    3. purchase_emotion_letter サービスを呼び出し、購入履歴（t_letter_purchase）と取引マッチング（t_matching）
       を1トランザクションで登録する。
    4. 対象レターが存在しない場合は HTTP 404、自分の出品の場合は HTTP 400、既に購入済み・停止済みの場合は HTTP 409 を返す。
    5. 成功時は HTTP 201 Created で購入コードとマッチングコードを返す。
    """
    try:
        result = purchase_emotion_letter(
            db=db,
            buyer=current_user,
            letter_code=request.letter_code,
        )

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された出品が見つかりません",
            )

        purchase, matching, letter, seller = result

        return PurchaseCreateResponse(
            purchase_code=purchase.purchase_code,
            matching_code=matching.matching_code,
            letter_code=letter.letter_code,
            seller_code=seller.user_code,
            buyer_code=current_user.user_code,
            title=letter.title,
            purchase_point=purchase.purchase_point,
            matching_status=matching.status,
            purchased_at=purchase.purchased_at,
        )

    except (SelfPurchaseError, InsufficientPointsError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except LetterNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この出品は既に購入されているか、データベース制約に違反しています。",
        ) from exc


@router.get(
    "",
    response_model=list[PurchaseDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="購入履歴一覧取得API",
)
def get_purchases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    購入履歴一覧取得API（GET /api/purchases）

    【処理の実行順序】
    1. Depends(get_current_user) でログイン中の会員を取得する（未ログインは HTTP 401）。
    2. list_user_purchases サービスを呼び出し、自分が購入したレター履歴を新着順で取得する。
    3. PurchaseDetailResponse のリストに変換して返す（HTTP 200 OK）。
    """
    rows = list_user_purchases(
        db=db,
        buyer=current_user,
    )

    return [
        PurchaseDetailResponse(
            purchase_code=purchase.purchase_code,
            matching_code=matching.matching_code,
            letter_code=letter.letter_code,
            seller_code=seller.user_code,
            seller_nickname=seller_profile.nickname,
            buyer_code=current_user.user_code,
            category_code=category.category_code,
            category_name=category.category_name,
            title=letter.title,
            content=letter.content,
            desired_duration=letter.desired_duration,
            purchase_point=purchase.purchase_point,
            matching_status=matching.status,
            purchased_at=purchase.purchased_at,
            completed_at=matching.completed_at,
        )
        for purchase, matching, letter, seller, seller_profile, category in rows
    ]


@router.get(
    "/matchings",
    response_model=list[MatchingDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="マッチング（取引）一覧取得API",
)
def get_matchings(
    role: str | None = Query(
        default=None,
        description="絞り込み役割（seller: 自分が出品者 / buyer: 自分が購入者 / 未指定: 両方）",
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="状態絞り込み（active: 進行中 / completed: 完了 / canceled: キャンセル）",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    マッチング一覧取得API（GET /api/purchases/matchings）
    購入によって成立したマッチング（取引）を、出品者・購入者の双方から一覧確認できる。
    """
    rows = list_user_matchings(
        db=db,
        current_user=current_user,
        role=role,
        status_filter=status_filter,
    )

    return [_to_matching_response(row, current_user) for row in rows]


@router.get(
    "/matchings/{matching_code}",
    response_model=MatchingDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="マッチング（取引）詳細取得API",
)
def get_matching_detail(
    matching_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    マッチング詳細取得API（GET /api/purchases/matchings/{matching_code}）
    当事者（出品者または購入者）のみが取引詳細を取得できる。
    """
    try:
        result = get_matching_by_code(
            db=db,
            matching_code=matching_code,
            current_user=current_user,
        )

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたマッチングが見つかりません",
            )

        return _to_matching_response(result, current_user)

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.patch(
    "/matchings/{matching_code}/status",
    response_model=MatchingDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="マッチング（取引）状態更新API",
)
def change_matching_status(
    matching_code: str,
    request: MatchingStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    マッチング状態更新API（PATCH /api/purchases/matchings/{matching_code}/status）

    【処理の実行順序】
    1. ログイン中の当事者（出品者または購入者）であることを確認する（第三者は HTTP 403）。
    2. 進行中のマッチングの状態を 2（準備中）、3（対話中）、4（取引完了）、5（キャンセル）に更新する。
    3. 4（取引完了）にした場合は completed_at に完了日時が記録され、レターも完了状態（status=3）になる。
    4. 既に完了・キャンセル済みの取引を変更しようとした場合は HTTP 409 Conflict を返す。
    """
    try:
        result = update_matching_status(
            db=db,
            matching_code=matching_code,
            current_user=current_user,
            new_status=request.status,
        )

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたマッチングが見つかりません",
            )

        return _to_matching_response(result, current_user)

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except MatchingStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/{purchase_code}",
    response_model=PurchaseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="購入詳細取得API",
)
def get_purchase_detail(
    purchase_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    購入詳細取得API（GET /api/purchases/{purchase_code}）
    """
    try:
        result = get_purchase_by_code(
            db=db,
            purchase_code=purchase_code,
            current_user=current_user,
        )

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された購入履歴が見つかりません",
            )

        purchase, matching, letter, seller, seller_profile, category = result

        buyer = db.get(User, purchase.buyer_id)
        buyer_code = buyer.user_code if buyer is not None else ""

        return PurchaseDetailResponse(
            purchase_code=purchase.purchase_code,
            matching_code=matching.matching_code,
            letter_code=letter.letter_code,
            seller_code=seller.user_code,
            seller_nickname=seller_profile.nickname,
            buyer_code=buyer_code,
            category_code=category.category_code,
            category_name=category.category_name,
            title=letter.title,
            content=letter.content,
            desired_duration=letter.desired_duration,
            purchase_point=purchase.purchase_point,
            matching_status=matching.status,
            purchased_at=purchase.purchased_at,
            completed_at=matching.completed_at,
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
