
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_current_token_payload
from app.core.security import create_access_token
from app.database import get_db
from app.models.token import RevokedToken
from app.models.user import User, Profile
from app.schemas.user import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    UserLoginResponse,
)
from app.services.user import (
    register_user,
    authenticate_user,
    delete_user_account,
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
    """新規会員登録API"""

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
    """メールアドレスとパスワードでログインする。"""

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
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="ログアウトAPI",
)
def logout_user(
    payload: dict = Depends(get_current_token_payload),
    db: Session = Depends(get_db),
):
    """現在のアクセストークンを失効させる。"""

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

    return {"message": "ログアウトしました"}



@router.get(
    "/me",
    summary="ログイン中のユーザー情報取得API",
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    return {
        "user_code": current_user.user_code,
        "profile_code": profile.profile_code,
        "email": current_user.email,
        "nickname": profile.nickname,
    }




@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="アカウント削除API",
)
def delete_me(
    current_user: User = Depends(get_current_user),
    payload: dict = Depends(get_current_token_payload),
    db: Session = Depends(get_db),
):
    """ログイン中のアカウントを論理削除し、現在のトークンを失効させる。"""

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

    return {"message": "アカウントを削除しました"}

