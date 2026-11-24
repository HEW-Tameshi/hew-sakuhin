"""
会員ランク機能 APIルーター定義モジュール（app/ranks/router.py）

【このファイルの役割】
- /api/ranks 配下のエンドポイントを受け付ける：
  1. GET  /api/ranks    : 会員ランクマスタ一覧取得
  2. POST /api/ranks    : 会員ランクマスタ登録（ランク設定）
  3. GET  /api/ranks/me : ログイン中ユーザーの現在ランク・次ランクまでの残りポイント・進捗率取得＆同期
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.ranks.schemas import (
    MemberRankCreateRequest,
    MemberRankResponse,
    UserRankProgressResponse,
)
from app.ranks.service import (
    create_member_rank,
    get_and_sync_user_rank_progress,
    list_member_ranks,
)
from app.users.models import User

router = APIRouter(
    prefix="/api/ranks",
    tags=["Member Ranks"],
)


@router.get(
    "",
    response_model=list[MemberRankResponse],
    status_code=status.HTTP_200_OK,
    summary="会員ランク一覧取得API",
)
def get_ranks(db: Session = Depends(get_db)):
    """登録済みの会員ランクマスタ一覧を必要ポイント昇順で返す。"""
    ranks = list_member_ranks(db=db)
    return [
        MemberRankResponse(
            rank_id=r.rank_id,
            rank_name=r.rank_name,
            required_point=r.required_point,
            created_at=r.created_at,
        )
        for r in ranks
    ]


@router.post(
    "",
    response_model=MemberRankResponse,
    status_code=status.HTTP_201_CREATED,
    summary="会員ランク登録（設定）API",
)
def add_rank(
    request: MemberRankCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """会員ランクマスタ（m_member_rank）にランク名と必要ポイントを登録する（HTTP 201）。"""
    try:
        rank = create_member_rank(
            db=db,
            rank_name=request.rank_name,
            required_point=request.required_point,
        )
        return MemberRankResponse(
            rank_id=rank.rank_id,
            rank_name=rank.rank_name,
            required_point=rank.required_point,
            created_at=rank.created_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/me",
    response_model=UserRankProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="ログイン中ユーザーの現在ランク・進捗取得API",
)
def get_my_rank(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    ログイン中ユーザーの累計獲得ポイントから現在ランクを自動判定・同期し、
    次ランクまでの残りポイントと進捗率（%）を返す。
    """
    progress = get_and_sync_user_rank_progress(db=db, user=current_user)
    return UserRankProgressResponse(**progress)
