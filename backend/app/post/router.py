"""
出品機能 APIルーター定義モジュール（app/post/router.py）

【このファイルの役割】
- /api/posts 配下のエンドポイントを受け付ける：
  1. POST   /api/posts               : 出品登録
  2. GET    /api/posts               : 出品一覧取得（キーワード検索・感情/ポイント/時間絞り込み・並び替え対応）
  3. GET    /api/posts/me            : 自分の出品履歴一覧取得（出品中・取引中・完了・取り下げ含む）
  4. GET    /api/posts/{letter_code} : 出品詳細取得
  5. PUT    /api/posts/{letter_code} : 出品編集
  6. DELETE /api/posts/{letter_code} : 出品取り下げ
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_optional_current_user
from app.core.database import get_db
from app.post.schemas import (
    EMOTION_CODE_MAP,
    PostCreateRequest,
    PostCreateResponse,
    PostDeleteResponse,
    PostDetailResponse,
    PostUpdateRequest,
)
from app.post.service import (
    cancel_emotion_letter,
    create_emotion_letter,
    get_emotion_letter_by_code,
    list_emotion_letters,
    list_my_emotion_letters,
    update_emotion_letter,
)
from app.users.models import User

# /api/posts プレフィックスを持つルーターを生成
router = APIRouter(
    prefix="/api/posts",
    tags=["Posts"],
)


def _to_post_detail_response(
    row: tuple,
    current_user: User | None,
) -> PostDetailResponse:
    """(EmotionLetter, User, Profile, EmotionCategory) タプルを PostDetailResponse へ変換する。"""
    letter, seller, profile, category = row
    return PostDetailResponse(
        letter_code=letter.letter_code,
        seller_code=seller.user_code,
        seller_nickname=profile.nickname,
        category_code=category.category_code,
        category_name=category.category_name,
        title=letter.title,
        content=letter.content,
        desired_duration=letter.desired_duration,
        point=letter.point,
        status=letter.status,
        created_at=letter.created_at,
        is_owner=(
            current_user is not None
            and letter.seller_id == current_user.user_id
        ),
    )


@router.post(
    "",
    response_model=PostCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="出品登録API",
)
def create_post(
    request: PostCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新規出品登録API（POST /api/posts）"""
    try:
        letter, emotion_category = create_emotion_letter(
            db=db,
            seller=current_user,
            category_code=request.emotion,
            title=request.title,
            content=request.content,
            desired_duration=request.time,
            point=request.point,
        )

        return PostCreateResponse(
            letter_code=letter.letter_code,
            seller_code=current_user.user_code,
            category_code=emotion_category.category_code,
            title=letter.title,
            content=letter.content,
            desired_duration=letter.desired_duration,
            point=letter.point,
            status=letter.status,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="出品情報が重複しているか、データベース制約に違反しています。",
        ) from exc


@router.get(
    "",
    response_model=list[PostDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="出品一覧・検索・絞り込みAPI",
)
def get_posts(
    q: str | None = Query(
        default=None,
        description="キーワード検索（見出し・本文に部分一致）",
    ),
    emotion: str | None = Query(
        default=None,
        description="感情カテゴリ絞り込み（joy/angry/sad/fun または E01〜E04）",
    ),
    min_point: int | None = Query(
        default=None,
        ge=0,
        description="最小ポイント",
    ),
    max_point: int | None = Query(
        default=None,
        ge=0,
        description="最大ポイント",
    ),
    min_duration: int | None = Query(
        default=None,
        ge=1,
        description="最小希望時間（分）",
    ),
    max_duration: int | None = Query(
        default=None,
        ge=1,
        description="最大希望時間（分）",
    ),
    sort: str = Query(
        default="newest",
        description="並び替え（newest: 新着順 / point_asc: ポイント安い順 / point_desc: ポイント高い順）",
    ),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    出品一覧・検索・絞り込みAPI（GET /api/posts）

    【処理の実行順序】
    1. クエリパラメータの感情指定（emotion）や並び替え（sort）を検証・正規化する。
    2. list_emotion_letters サービスを呼び出し、条件に一致する出品中レターを取得する。
    3. 各レコードに is_owner を付与して返す（HTTP 200 OK）。
    """
    keyword = q.strip() if q else None

    category_code = None
    if emotion is not None and emotion.strip():
        category_code = EMOTION_CODE_MAP.get(emotion.strip())
        if category_code is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="正しい感情カテゴリを指定してください（joy, angry, sad, fun または E01〜E04）",
            )

    if sort not in ("newest", "point_asc", "point_desc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="並び替えには newest, point_asc, point_desc のいずれかを指定してください",
        )

    rows = list_emotion_letters(
        db=db,
        keyword=keyword,
        category_code=category_code,
        min_point=min_point,
        max_point=max_point,
        min_duration=min_duration,
        max_duration=max_duration,
        sort=sort,
    )

    return [_to_post_detail_response(row, current_user) for row in rows]


@router.get(
    "/me",
    response_model=list[PostDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="自分の出品履歴一覧取得API",
)
def get_my_posts(
    letter_status: int | None = Query(
        default=None,
        alias="status",
        ge=1,
        le=4,
        description="出品状態での絞り込み（1:出品中 / 2:取引中 / 3:完了 / 4:取り下げ・停止）",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    自分の出品履歴一覧取得API（GET /api/posts/me）
    profile.html の「出品履歴」画面向けに、ログイン中ユーザー自身の出品を全ステータス含めて返す。
    ※ /{letter_code} より前に定義することで "me" がレターコードと誤認されるのを防ぐ。
    """
    rows = list_my_emotion_letters(
        db=db,
        seller=current_user,
        letter_status=letter_status,
    )
    return [_to_post_detail_response(row, current_user) for row in rows]


@router.get(
    "/{letter_code}",
    response_model=PostDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="出品詳細取得API",
)
def get_post_detail(
    letter_code: str,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """出品詳細取得API（GET /api/posts/{letter_code}）"""
    result = get_emotion_letter_by_code(
        db=db,
        letter_code=letter_code,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定された出品が見つかりません",
        )

    return _to_post_detail_response(result, current_user)


@router.put(
    "/{letter_code}",
    response_model=PostCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="出品編集API",
)
def update_post(
    letter_code: str,
    request: PostUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """出品編集API（PUT /api/posts/{letter_code}）"""
    try:
        result = update_emotion_letter(
            db=db,
            letter_code=letter_code,
            current_user=current_user,
            category_code=request.emotion,
            title=request.title,
            content=request.content,
            desired_duration=request.time,
            point=request.point,
        )

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された出品が見つかりません",
            )

        letter, emotion_category = result

        return PostCreateResponse(
            letter_code=letter.letter_code,
            seller_code=current_user.user_code,
            category_code=emotion_category.category_code,
            title=letter.title,
            content=letter.content,
            desired_duration=letter.desired_duration,
            point=letter.point,
            status=letter.status,
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{letter_code}",
    response_model=PostDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="出品取り下げAPI",
)
def delete_post(
    letter_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """出品取り下げAPI（DELETE /api/posts/{letter_code}）"""
    try:
        letter = cancel_emotion_letter(
            db=db,
            letter_code=letter_code,
            current_user=current_user,
        )

        if letter is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された出品が見つかりません",
            )

        return PostDeleteResponse(
            message="出品を取り下げました",
            letter_code=letter.letter_code,
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
