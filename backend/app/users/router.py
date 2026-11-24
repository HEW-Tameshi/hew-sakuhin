"""
会員機能 APIルーター定義モジュール（app/users/router.py）

【このファイルの役割】
- /api/users 配下のエンドポイントを受け付ける：
  1. POST   /api/users/register          : 新規会員登録
  2. POST   /api/users/login             : ログイン（JWT発行）
  3. POST   /api/users/google/register   : Google認証による新規登録
  4. POST   /api/users/google/login      : Google認証によるログイン
  5. POST   /api/users/logout            : ログアウト（JWT失効）
  6. GET    /api/users/me                : ログイン中会員・プロフィール取得
  7. PATCH  /api/users/me                : プロフィール・メールアドレス編集
  8. PUT    /api/users/me/password       : パスワード変更（現在パスワード確認）
  9. PUT    /api/users/me/password/google: Google登録会員向けパスワード設定
  10. DELETE /api/users/me               : 退会（論理削除・関連取引/出品/通話/サブスク整理・匿名化）
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_token_payload, get_current_user
from app.core.database import get_db
from app.core.google_auth import (
    GoogleAuthConfigError,
    GoogleTokenVerificationError,
    verify_google_id_token,
)
from app.core.security import create_access_token
from app.users.models import MemberRank, Profile, RevokedToken, User
from app.users.schemas import (
    GoogleAuthResponse,
    GoogleLoginRequest,
    GooglePasswordSetRequest,
    GoogleRegisterRequest,
    MessageResponse,
    PasswordChangeRequest,
    UserLoginRequest,
    UserLoginResponse,
    UserMeResponse,
    UserProfileUpdateRequest,
    UserRegisterRequest,
    UserRegisterResponse,
)
from app.users.service import (
    PasswordChangeError,
    authenticate_user,
    authenticate_user_with_google,
    change_user_password,
    delete_user_account,
    register_user,
    register_user_with_google,
    set_password_with_google,
    update_user_profile,
)

router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
)


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    request: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    """新規会員登録API（POST /api/users/register）"""
    try:
        user, profile = register_user(
            db=db,
            email=str(request.email),
            password=request.password,
            nickname=request.nickname,
        )

        return UserRegisterResponse(
            user_code=user.user_code,
            profile_code=profile.profile_code,
            email=user.email,
            nickname=profile.nickname,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="登録情報が重複しているか、データベース制約に違反しています。",
        ) from exc


@router.post(
    "/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="ログインAPI",
)
def login_user(
    request: UserLoginRequest,
    db: Session = Depends(get_db),
):
    """ログインAPI（POST /api/users/login）"""
    result = authenticate_user(
        db=db,
        email=str(request.email),
        password=request.password,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )

    user, profile = result
    access_token = create_access_token(user.user_code)

    return UserLoginResponse(
        user_code=user.user_code,
        profile_code=profile.profile_code,
        email=user.email,
        nickname=profile.nickname,
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/google/register",
    response_model=GoogleAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Google認証による新規会員登録API",
)
def register_with_google(
    request: GoogleRegisterRequest,
    db: Session = Depends(get_db),
):
    """Google認証による新規会員登録API（POST /api/users/google/register）"""
    try:
        google_user = verify_google_id_token(request.id_token)
    except GoogleAuthConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GoogleTokenVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    try:
        user, profile = register_user_with_google(
            db=db,
            email=google_user.email,
            nickname=request.nickname,
            google_name=google_user.name,
            profile_image=google_user.picture,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="登録情報が重複しているか、データベース制約に違反しています。",
        ) from exc

    access_token = create_access_token(user.user_code)

    return GoogleAuthResponse(
        user_code=user.user_code,
        profile_code=profile.profile_code,
        email=user.email,
        nickname=profile.nickname,
        profile_image=profile.profile_image,
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/google/login",
    response_model=GoogleAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Google認証によるログインAPI",
)
def login_with_google(
    request: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    """Google認証によるログインAPI（POST /api/users/google/login）"""
    try:
        google_user = verify_google_id_token(request.id_token)
    except GoogleAuthConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GoogleTokenVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    result = authenticate_user_with_google(
        db=db,
        email=google_user.email,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="このGoogleアカウントは登録されていないか、退会済みです",
        )

    user, profile = result
    access_token = create_access_token(user.user_code)

    return GoogleAuthResponse(
        user_code=user.user_code,
        profile_code=profile.profile_code,
        email=user.email,
        nickname=profile.nickname,
        profile_image=profile.profile_image,
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="ログアウトAPI",
)
def logout_user(
    payload: dict = Depends(get_current_token_payload),
    db: Session = Depends(get_db),
):
    """ログアウトAPI（POST /api/users/logout）"""
    jti = payload["jti"]
    expires_timestamp = payload["exp"]

    expires_at = datetime.fromtimestamp(
        expires_timestamp,
        tz=timezone.utc,
    ).replace(tzinfo=None)

    existing_token = db.scalar(
        select(RevokedToken).where(RevokedToken.jti == jti)
    )

    if existing_token is None:
        db.add(
            RevokedToken(
                jti=jti,
                expires_at=expires_at,
            )
        )
        db.commit()

    return MessageResponse(message="ログアウトしました")


@router.get(
    "/me",
    response_model=UserMeResponse,
    status_code=status.HTTP_200_OK,
    summary="ログイン中のユーザー・プロフィール情報取得API",
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ログイン中ユーザーの会員情報とプロフィール詳細（画像・自己紹介・ランク含む）を取得する。"""
    profile = db.scalar(
        select(Profile).where(
            Profile.user_id == current_user.user_id
        )
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="プロフィールが見つかりません",
        )

    rank = (
        db.get(MemberRank, profile.delivery_rank_id)
        if profile.delivery_rank_id is not None
        else None
    )

    return UserMeResponse(
        user_code=current_user.user_code,
        profile_code=profile.profile_code,
        email=current_user.email,
        nickname=profile.nickname,
        profile_image=profile.profile_image,
        introduction=profile.introduction,
        delivery_rank_id=profile.delivery_rank_id,
        delivery_rank_name=rank.rank_name if rank is not None else None,
    )


@router.patch(
    "/me",
    response_model=UserMeResponse,
    status_code=status.HTTP_200_OK,
    summary="プロフィール・アカウント編集API",
)
def update_me(
    request: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    ログイン中会員のニックネーム・メールアドレス・プロフィール画像・自己紹介を部分更新する（HTTP 200）。
    リクエストに含めた項目のみが更新される。メールアドレス重複時は HTTP 409。
    """
    fields_to_update = request.model_dump(include=request.model_fields_set)

    try:
        result = update_user_profile(
            db=db,
            user=current_user,
            fields_to_update=fields_to_update,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="メールアドレスが既に登録されているか、データベース制約に違反しています。",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="プロフィールが見つかりません",
        )

    user, profile = result

    rank = (
        db.get(MemberRank, profile.delivery_rank_id)
        if profile.delivery_rank_id is not None
        else None
    )

    return UserMeResponse(
        user_code=user.user_code,
        profile_code=profile.profile_code,
        email=user.email,
        nickname=profile.nickname,
        profile_image=profile.profile_image,
        introduction=profile.introduction,
        delivery_rank_id=profile.delivery_rank_id,
        delivery_rank_name=rank.rank_name if rank is not None else None,
    )


@router.put(
    "/me/password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="パスワード変更API",
)
def update_my_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    現在のパスワードを照合したうえで新しいパスワードへ変更する（HTTP 200）。
    現在パスワード不一致や同一パスワード指定時は HTTP 400。
    """
    try:
        change_user_password(
            db=db,
            user=current_user,
            current_password=request.current_password,
            new_password=request.new_password,
        )
    except PasswordChangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return MessageResponse(message="パスワードを変更しました")


@router.put(
    "/me/password/google",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Google登録会員向けパスワード設定API",
)
def set_my_password_with_google(
    request: GooglePasswordSetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Google登録会員が後からメール＆パスワードログイン用パスワードを設定するためのAPI（HTTP 200）。
    Google IDトークンで本人再確認を行い、一致した場合のみ新パスワードを設定する。
    """
    try:
        google_user = verify_google_id_token(request.id_token)
    except GoogleAuthConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GoogleTokenVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    try:
        set_password_with_google(
            db=db,
            user=current_user,
            verified_google_email=google_user.email,
            new_password=request.new_password,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return MessageResponse(message="パスワードを設定しました")


@router.delete(
    "/me",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="アカウント退会（論理削除）API",
)
def delete_me(
    current_user: User = Depends(get_current_user),
    payload: dict = Depends(get_current_token_payload),
    db: Session = Depends(get_db),
):
    """
    退会（アカウント論理削除）API（DELETE /api/users/me）

    【処理の実行順序】
    1. 現在使用しているアクセストークンの jti を t_revoked_token に追加して失効させる。
    2. delete_user_account サービスを呼び出し、進行中取引キャンセル・未終了通話クローズ・
       出品停止・有効サブスク自動解約・会員/プロフィールの匿名化を行う。
    3. db.commit() で全変更を1トランザクションとして確定する（失敗時は rollback()）。
    """
    jti = payload["jti"]
    expires_at = datetime.fromtimestamp(
        payload["exp"],
        tz=timezone.utc,
    ).replace(tzinfo=None)

    existing_token = db.scalar(
        select(RevokedToken).where(RevokedToken.jti == jti)
    )

    if existing_token is None:
        db.add(
            RevokedToken(
                jti=jti,
                expires_at=expires_at,
            )
        )

    try:
        delete_user_account(
            db=db,
            user=current_user,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return MessageResponse(message="アカウントを削除しました")
