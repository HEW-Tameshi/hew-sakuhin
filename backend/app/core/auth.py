"""
認証・認可（ログイン状態チェック）モジュール（app/core/auth.py）

【このファイルの役割】
- HTTPリクエストの Authorization ヘッダー（Bearer トークン）から JWT を取り出す。
- トークンが有効か、ログアウト済み（失効済み）でないか、退会済みユーザーでないかを検証する。
- ログイン必須のAPI用の `get_current_user` と、未ログインでも閲覧可能なAPI用の `get_optional_current_user` を提供する。
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.users.models import RevokedToken, User

# Authorization: Bearer <token> 形式のヘッダーを取得するスキーム
# auto_error=False にすることで、ヘッダーがない場合も自前の日本語エラーメッセージを返せるようにする
bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized(detail: str) -> HTTPException:
    """HTTP 401 Unauthorized エラーを生成するヘルパー関数。"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    【ログイン必須API用】JWTを検証し、現在ログイン中の有効な会員（Userモデル）を取得する。

    【処理の実行順序】
    1. Authorizationヘッダー（Bearerトークン）があるか確認する（なければ401）。
    2. JWTの署名と有効期限を検証してデコードする（不正・期限切れなら401）。
    3. ペイロードから sub（会員コード）と jti（トークン固有ID）を取得する。
    4. t_revoked_token テーブルを検索し、ログアウト済みのトークンでないか確認する（失効済みなら401）。
    5. m_user テーブルから会員情報を取得し、存在するかつ有効（account_status == 1）か確認する。
    6. 検証を通過した User インスタンスを返す。
    """

    # 1. トークンが送られてきていない場合
    if credentials is None:
        raise unauthorized("認証が必要です")

    # 2. トークンのデコード・署名・有効期限チェック
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise unauthorized("無効または期限切れのアクセストークンです")

    # 3. 必須クレーム（sub: 会員コード, jti: トークンID）の取り出し
    user_code = payload.get("sub")
    jti = payload.get("jti")

    if not user_code or not jti:
        raise unauthorized("無効なアクセストークンです")

    # 4. ログアウト等で失効登録（t_revoked_token）されていないか確認
    revoked_token = db.scalar(
        select(RevokedToken).where(RevokedToken.jti == jti)
    )
    if revoked_token is not None:
        raise unauthorized("このアクセストークンは失効しています")

    # 5. 会員マスタ（m_user）から該当ユーザーを検索
    user = db.scalar(
        select(User).where(User.user_code == user_code)
    )

    if user is None:
        raise unauthorized("ユーザーが見つかりません")

    # 退会済み（account_status != 1）の場合は利用不可
    if user.account_status != 1:
        raise unauthorized("退会済みのアカウントです")

    # 6. ログイン中の会員オブジェクトを返す
    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """
    【任意ログインAPI用（出品一覧・出品詳細など）】
    - トークンが送られてきており有効な場合は、ログイン中の User インスタンスを返す。
    - 未ログイン（トークンなし）や期限切れ・失効済みの場合は、エラーにせず None を返す。
    これにより、画面側で「自分の出品かどうか（編集・取り下げボタンを表示するか）」を判定できる。
    """
    if credentials is None:
        return None

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        return None

    user_code = payload.get("sub")
    jti = payload.get("jti")

    if not user_code or not jti:
        return None

    revoked_token = db.scalar(
        select(RevokedToken).where(RevokedToken.jti == jti)
    )
    if revoked_token is not None:
        return None

    user = db.scalar(
        select(User).where(
            User.user_code == user_code,
            User.account_status == 1,
        )
    )

    return user


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """
    ログアウト処理などで使用するため、認証トークンのペイロード（jti や exp など）を取得する。
    """

    if credentials is None:
        raise unauthorized("認証が必要です")

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise unauthorized("無効または期限切れのアクセストークンです")

    if not payload.get("sub") or not payload.get("jti"):
        raise unauthorized("無効なアクセストークンです")

    return payload


def authenticate_jwt_token(token: str, db: Session) -> User | None:
    """
    【WebSocket認証用】クエリパラメータ等から受け取った生のJWT文字列を検証し、
    有効な会員（User）を返す。無効・期限切れ・失効済み・退会済みの場合は None を返す。
    """
    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        return None

    user_code = payload.get("sub")
    jti = payload.get("jti")
    if not user_code or not jti:
        return None

    revoked_token = db.scalar(
        select(RevokedToken).where(RevokedToken.jti == jti)
    )
    if revoked_token is not None:
        return None

    return db.scalar(
        select(User).where(
            User.user_code == user_code,
            User.account_status == 1,
        )
    )
