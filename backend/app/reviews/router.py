"""
レビュー＆チップ機能 APIルーター定義モジュール（app/reviews/router.py）

【このファイルの役割】
- /api/reviews 配下のエンドポイントを受け付ける：
  1. POST /api/reviews                          : レビュー投稿（チップ同時送信対応）
  2. GET  /api/reviews/matching/{matching_code} : 取引ごとのレビュー一覧取得
  3. GET  /api/reviews/user/{user_code}         : ユーザー別受信レビュー一覧＆平均評価取得
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.points.service import InsufficientPointsError
from app.reviews.schemas import (
    ReviewCreateRequest,
    ReviewResponse,
    UserReviewSummaryResponse,
)
from app.reviews.service import (
    ReviewAlreadyExistsError,
    ReviewNotAllowedError,
    create_review,
    get_user_review_summary,
    list_reviews_by_matching,
)
from app.users.models import User

router = APIRouter(
    prefix="/api/reviews",
    tags=["Reviews"],
)


def _row_to_review_response(row: tuple) -> ReviewResponse:
    """レビュー一覧クエリの1行タプルを ReviewResponse に変換する。"""
    (
        review,
        matching,
        reviewer,
        reviewer_profile,
        reviewee,
        reviewee_profile,
    ) = row
    return ReviewResponse(
        review_code=review.review_code,
        matching_code=matching.matching_code,
        reviewer_code=reviewer.user_code,
        reviewer_nickname=reviewer_profile.nickname,
        reviewee_code=reviewee.user_code,
        reviewee_nickname=reviewee_profile.nickname,
        rating=review.rating,
        comment=review.comment,
        tip_code=None,
        tip_amount=0,
        created_at=review.created_at,
    )


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="レビュー＆チップ投稿API",
)
def post_review(
    request: ReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取引に対するレビュー（1〜5星・コメント）および任意のチップポイントを投稿する（HTTP 201 Created）。
    """
    try:
        result = create_review(
            db=db,
            matching_code=request.matching_code,
            reviewer=current_user,
            rating=request.rating,
            comment=request.comment,
            tip_amount=request.tip_amount,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたマッチングが見つかりません",
            )

        review, tip, matching, reviewer_profile, reviewee, reviewee_profile = result

        return ReviewResponse(
            review_code=review.review_code,
            matching_code=matching.matching_code,
            reviewer_code=current_user.user_code,
            reviewer_nickname=reviewer_profile.nickname,
            reviewee_code=reviewee.user_code,
            reviewee_nickname=reviewee_profile.nickname,
            rating=review.rating,
            comment=review.comment,
            tip_code=tip.tip_code if tip is not None else None,
            tip_amount=tip.amount if tip is not None else 0,
            created_at=review.created_at,
        )

    except InsufficientPointsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except (ReviewAlreadyExistsError, ReviewNotAllowedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/matching/{matching_code}",
    response_model=list[ReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="マッチング別レビュー一覧取得API",
)
def get_matching_reviews(
    matching_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """指定された取引マッチングに投稿されたレビュー一覧を取得する（当事者のみ閲覧可）。"""
    try:
        rows = list_reviews_by_matching(
            db=db,
            matching_code=matching_code,
            current_user=current_user,
        )
        if rows is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたマッチングが見つかりません",
            )
        return [_row_to_review_response(r) for r in rows]

    except InsufficientPointsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get(
    "/user/{user_code}",
    response_model=UserReviewSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="ユーザー別評価サマリー・レビュー一覧取得API",
)
def get_user_reviews(
    user_code: str,
    db: Session = Depends(get_db),
):
    """指定ユーザーが受け取ったレビュー一覧と平均星評価（小数点1桁）を取得する。"""
    result = get_user_review_summary(db=db, user_code=user_code)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたユーザーが見つかりません",
        )

    target_user, target_profile, rows, avg_rating = result

    return UserReviewSummaryResponse(
        user_code=target_user.user_code,
        nickname=target_profile.nickname,
        review_count=len(rows),
        average_rating=avg_rating,
        reviews=[_row_to_review_response(r) for r in rows],
    )
