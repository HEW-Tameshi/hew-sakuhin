"""
チャット機能 API・WebSocketルーター定義モジュール（app/chats/router.py）

【このファイルの役割】
- /api/chats 配下のREST APIとリアルタイム通信用WebSocketを受け付ける：
  1. POST /api/chats                      : マッチングに紐づくチャットルーム作成・取得
  2. GET  /api/chats                      : ログイン中ユーザーのチャットルーム一覧取得
  3. GET  /api/chats/{chat_code}          : チャットルーム詳細取得
  4. GET  /api/chats/{chat_code}/messages : メッセージ履歴一覧取得
  5. POST /api/chats/{chat_code}/messages : メッセージ送信（DB保存＋WebSocketリアルタイム配信）
  6. WS   /api/chats/ws/{chat_code}       : リアルタイムチャット WebSocket（?token=<JWT> で認証）
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.orm import Session

from app.chats.schemas import (
    ChatCreateRequest,
    ChatRoomResponse,
    MessageCreateRequest,
    MessageResponse,
)
from app.chats.service import (
    ChatClosedError,
    get_chat_room_by_code,
    get_or_create_chat_room,
    list_chat_messages,
    list_user_chats,
    send_chat_message,
)
from app.chats.ws_manager import chat_ws_manager
from app.core.auth import authenticate_jwt_token, get_current_user
from app.core.database import get_db
from app.users.models import User

router = APIRouter(
    prefix="/api/chats",
    tags=["Chats"],
)


def _to_chat_room_response(row: tuple, current_user: User) -> ChatRoomResponse:
    """サービス層から返されたタプルを ChatRoomResponse に変換する。"""
    (
        chat,
        matching,
        letter,
        seller,
        seller_profile,
        buyer,
        buyer_profile,
    ) = row

    user_role = "seller" if current_user.user_id == matching.seller_id else "buyer"

    return ChatRoomResponse(
        chat_code=chat.chat_code,
        matching_code=matching.matching_code,
        letter_code=letter.letter_code,
        title=letter.title,
        seller_code=seller.user_code,
        seller_nickname=seller_profile.nickname,
        buyer_code=buyer.user_code,
        buyer_nickname=buyer_profile.nickname,
        matching_status=matching.status,
        user_role=user_role,
        created_at=chat.created_at,
    )


@router.post(
    "",
    response_model=ChatRoomResponse,
    status_code=status.HTTP_201_CREATED,
    summary="チャットルーム作成・取得API",
)
def create_or_get_chat(
    request: ChatCreateRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    マッチングコードに対応するチャットルームを作成する（既に存在する場合は既存ルームを 200 OK で返す）。
    """
    try:
        result = get_or_create_chat_room(
            db=db,
            matching_code=request.matching_code,
            current_user=current_user,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたマッチングが見つかりません",
            )

        row, created = result
        if not created:
            response.status_code = status.HTTP_200_OK

        return _to_chat_room_response(row, current_user)

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except ChatClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[ChatRoomResponse],
    status_code=status.HTTP_200_OK,
    summary="チャットルーム一覧取得API",
)
def get_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ログイン中のユーザーが参加しているチャットルーム一覧を取得する。"""
    rows = list_user_chats(db=db, current_user=current_user)
    return [_to_chat_room_response(row, current_user) for row in rows]


@router.get(
    "/{chat_code}",
    response_model=ChatRoomResponse,
    status_code=status.HTTP_200_OK,
    summary="チャットルーム詳細取得API",
)
def get_chat_detail(
    chat_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """指定されたチャットルームの詳細情報を取得する。"""
    try:
        row = get_chat_room_by_code(
            db=db,
            chat_code=chat_code,
            current_user=current_user,
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたチャットルームが見つかりません",
            )
        return _to_chat_room_response(row, current_user)

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get(
    "/{chat_code}/messages",
    response_model=list[MessageResponse],
    status_code=status.HTTP_200_OK,
    summary="チャットメッセージ履歴一覧取得API",
)
def get_messages(
    chat_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """チャットルーム内のメッセージ履歴を古い順（送信日時昇順）で取得する。"""
    try:
        rows = list_chat_messages(
            db=db,
            chat_code=chat_code,
            current_user=current_user,
        )
        if rows is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたチャットルームが見つかりません",
            )

        return [
            MessageResponse(
                message_code=msg.message_code,
                chat_code=chat_code,
                sender_code=sender.user_code,
                sender_nickname=sender_profile.nickname,
                message=msg.message,
                is_mine=(sender.user_id == current_user.user_id),
                sent_at=msg.sent_at,
            )
            for msg, sender, sender_profile in rows
        ]

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/{chat_code}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="チャットメッセージ送信API",
)
async def create_message(
    chat_code: str,
    request: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    チャットルームへメッセージを送信し、DB（t_message）に保存する。
    同時に、該当チャットルームへ WebSocket 接続中のクライアントへリアルタイム配信する。
    """
    try:
        result = send_chat_message(
            db=db,
            chat_code=chat_code,
            current_user=current_user,
            message_text=request.message,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたチャットルームが見つかりません",
            )

        msg, sender, sender_profile = result

        response_data = MessageResponse(
            message_code=msg.message_code,
            chat_code=chat_code,
            sender_code=sender.user_code,
            sender_nickname=sender_profile.nickname,
            message=msg.message,
            is_mine=True,
            sent_at=msg.sent_at,
        )

        # WebSocket接続中の当事者へリアルタイム配信
        await chat_ws_manager.broadcast_message(
            chat_code=chat_code,
            payload={
                "type": "chat_message",
                "message_code": msg.message_code,
                "chat_code": chat_code,
                "sender_code": sender.user_code,
                "sender_nickname": sender_profile.nickname,
                "message": msg.message,
                "sent_at": msg.sent_at.isoformat(),
            },
        )

        return response_data

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except ChatClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.websocket("/ws/{chat_code}")
async def chat_websocket(
    websocket: WebSocket,
    chat_code: str,
    token: str = Query(..., description="ログイン時に発行されたJWTアクセストークン"),
    db: Session = Depends(get_db),
):
    """
    リアルタイムチャット用 WebSocket エンドポイント（WS /api/chats/ws/{chat_code}?token=<JWT>）

    【処理の流れ】
    1. クエリパラメータの JWT トークンを検証し、有効なユーザーか確認する（失敗時は 4401 で切断）。
    2. 指定された chat_code の当事者（出品者または購入者）か確認する（未存在 4404 / 第三者 4403 で切断）。
    3. 接続を受け入れ、クライアントから JSON `{"message": "..."}` を受信するたびに DB へ保存し、
       同ルーム内の接続中クライアント全員へリアルタイム配信する。
    """
    current_user = authenticate_jwt_token(token=token, db=db)
    if current_user is None:
        await websocket.close(code=4401, reason="認証に失敗しました")
        return

    try:
        room = get_chat_room_by_code(
            db=db,
            chat_code=chat_code,
            current_user=current_user,
        )
    except PermissionError:
        await websocket.close(code=4403, reason="アクセス権限がありません")
        return

    if room is None:
        await websocket.close(code=4404, reason="チャットルームが見つかりません")
        return

    await chat_ws_manager.connect(
        chat_code=chat_code,
        websocket=websocket,
        user_code=current_user.user_code,
    )

    try:
        while True:
            data = await websocket.receive_json()
            raw_message = str(data.get("message", "")).strip()

            if not raw_message or len(raw_message) > 500:
                await websocket.send_json({
                    "type": "error",
                    "detail": "メッセージは1〜500文字で入力してください",
                })
                continue

            try:
                result = send_chat_message(
                    db=db,
                    chat_code=chat_code,
                    current_user=current_user,
                    message_text=raw_message,
                )
            except (PermissionError, ChatClosedError) as exc:
                await websocket.send_json({
                    "type": "error",
                    "detail": str(exc),
                })
                continue

            if result is None:
                await websocket.send_json({
                    "type": "error",
                    "detail": "チャットルームが見つかりません",
                })
                continue

            msg, sender, sender_profile = result
            await chat_ws_manager.broadcast_message(
                chat_code=chat_code,
                payload={
                    "type": "chat_message",
                    "message_code": msg.message_code,
                    "chat_code": chat_code,
                    "sender_code": sender.user_code,
                    "sender_nickname": sender_profile.nickname,
                    "message": msg.message,
                    "sent_at": msg.sent_at.isoformat(),
                },
            )
    except WebSocketDisconnect:
        chat_ws_manager.disconnect(chat_code=chat_code, websocket=websocket)
