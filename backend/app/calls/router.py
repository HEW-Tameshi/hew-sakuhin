"""
通話機能 API・WebSocketルーター定義モジュール（app/calls/router.py）

【このファイルの役割】
- /api/calls 配下のREST APIとWebRTC通話シグナリング用WebSocketを受け付ける：
  1. POST /api/calls/start                    : 通話開始（t_call 登録・通話中通知）
  2. POST /api/calls/{call_code}/end          : 通話終了（ended_at と duration(秒) 記録）
  3. GET  /api/calls/matching/{matching_code} : マッチングごとの通話履歴一覧取得
  4. GET  /api/calls/{call_code}              : 通話詳細取得
  5. WS   /api/calls/ws/{matching_code}       : 通話申請・応答・WebRTCシグナリング中継（?token=<JWT> で認証）
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calls.models import Call
from app.calls.schemas import CallResponse, CallStartRequest
from app.calls.service import (
    CallAlreadyActiveError,
    CallAlreadyEndedError,
    CallNotAllowedError,
    end_call,
    get_call_by_code,
    list_calls_by_matching,
    start_call,
)
from app.calls.ws_manager import call_ws_manager
from app.core.auth import authenticate_jwt_token, get_current_user
from app.core.database import get_db
from app.purchases.models import Matching
from app.users.models import User

router = APIRouter(
    prefix="/api/calls",
    tags=["Calls"],
)

# WebRTC通話シグナリングで中継を許可するイベント種別
ALLOWED_SIGNAL_TYPES = (
    "call_request",    # 通話申請
    "call_accept",     # 通話了承
    "call_reject",     # 通話拒否
    "offer",           # WebRTC SDP Offer
    "answer",          # WebRTC SDP Answer
    "ice_candidate",   # WebRTC ICE Candidate
    "call_end",        # 通話終了通知
)


def _to_call_response(call: Call, matching: Matching) -> CallResponse:
    """Call モデルと Matching モデルを CallResponse に変換する。"""
    return CallResponse(
        call_code=call.call_code,
        matching_code=matching.matching_code,
        communication_type=call.communication_type,
        started_at=call.started_at,
        ended_at=call.ended_at,
        duration=call.duration,
        is_active=(call.ended_at is None),
    )


@router.post(
    "/start",
    response_model=CallResponse,
    status_code=status.HTTP_201_CREATED,
    summary="通話開始API",
)
async def start_call_endpoint(
    request: CallStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    通話を開始し、t_call テーブルへ記録する（HTTP 201 Created）。
    同時に、対象マッチングのシグナリング WebSocket 接続中の当事者へ通話開始イベントを通知する。
    """
    try:
        result = start_call(
            db=db,
            matching_code=request.matching_code,
            current_user=current_user,
            communication_type=request.communication_type,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたマッチングが見つかりません",
            )

        call, matching = result
        response_data = _to_call_response(call, matching)

        await call_ws_manager.broadcast_event(
            matching_code=matching.matching_code,
            payload={
                "type": "call_started",
                "call_code": call.call_code,
                "matching_code": matching.matching_code,
                "communication_type": call.communication_type,
                "started_by": current_user.user_code,
                "started_at": call.started_at.isoformat(),
            },
        )

        return response_data

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except (CallNotAllowedError, CallAlreadyActiveError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/{call_code}/end",
    response_model=CallResponse,
    status_code=status.HTTP_200_OK,
    summary="通話終了API",
)
async def end_call_endpoint(
    call_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    進行中の通話を終了し、終了時刻（ended_at）と通話時間（duration: 秒）を保存する（HTTP 200 OK）。
    """
    try:
        result = end_call(
            db=db,
            call_code=call_code,
            current_user=current_user,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された通話が見つかりません",
            )

        call, matching = result
        response_data = _to_call_response(call, matching)

        await call_ws_manager.broadcast_event(
            matching_code=matching.matching_code,
            payload={
                "type": "call_ended",
                "call_code": call.call_code,
                "matching_code": matching.matching_code,
                "ended_by": current_user.user_code,
                "ended_at": call.ended_at.isoformat() if call.ended_at else None,
                "duration": call.duration,
            },
        )

        return response_data

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except CallAlreadyEndedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/matching/{matching_code}",
    response_model=list[CallResponse],
    status_code=status.HTTP_200_OK,
    summary="マッチング別通話履歴一覧取得API",
)
def get_calls_by_matching(
    matching_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """指定されたマッチングで行われた通話履歴一覧を新しい順で取得する。"""
    try:
        result = list_calls_by_matching(
            db=db,
            matching_code=matching_code,
            current_user=current_user,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたマッチングが見つかりません",
            )

        calls, matching = result
        return [_to_call_response(call, matching) for call in calls]

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get(
    "/{call_code}",
    response_model=CallResponse,
    status_code=status.HTTP_200_OK,
    summary="通話詳細取得API",
)
def get_call_detail(
    call_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """指定された通話コード（call_code）の通話詳細を取得する。"""
    try:
        result = get_call_by_code(
            db=db,
            call_code=call_code,
            current_user=current_user,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された通話が見つかりません",
            )

        call, matching = result
        return _to_call_response(call, matching)

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.websocket("/ws/{matching_code}")
async def call_signaling_websocket(
    websocket: WebSocket,
    matching_code: str,
    token: str = Query(..., description="ログイン時に発行されたJWTアクセストークン"),
    db: Session = Depends(get_db),
):
    """
    通話申請・応答およびWebRTCシグナリング中継用 WebSocket（WS /api/calls/ws/{matching_code}?token=<JWT>）

    【処理の流れ】
    1. JWT トークンを検証し、有効なユーザーか確認する（失敗時は 4401 で切断）。
    2. マッチング存在確認および当事者確認を行う（未存在 4404 / 第三者 4403 で切断）。
    3. 接続を受け入れ、許可されたシグナリング種別（call_request, call_accept, call_reject,
       offer, answer, ice_candidate, call_end）を受信したら、相手当事者へ転送する。
    """
    current_user = authenticate_jwt_token(token=token, db=db)
    if current_user is None:
        await websocket.close(code=4401, reason="認証に失敗しました")
        return

    matching = db.scalar(
        select(Matching).where(Matching.matching_code == matching_code)
    )
    if matching is None:
        await websocket.close(code=4404, reason="マッチングが見つかりません")
        return

    if current_user.user_id not in (matching.seller_id, matching.buyer_id):
        await websocket.close(code=4403, reason="アクセス権限がありません")
        return

    await call_ws_manager.connect(
        matching_code=matching_code,
        websocket=websocket,
        user_code=current_user.user_code,
    )

    try:
        while True:
            data = await websocket.receive_json()
            signal_type = data.get("type")

            if signal_type not in ALLOWED_SIGNAL_TYPES:
                await websocket.send_json({
                    "type": "error",
                    "detail": "サポートされていないシグナリング種別です",
                })
                continue

            await call_ws_manager.relay_to_peer(
                matching_code=matching_code,
                sender_websocket=websocket,
                payload={
                    **data,
                    "from_user_code": current_user.user_code,
                    "matching_code": matching_code,
                },
            )
    except WebSocketDisconnect:
        call_ws_manager.disconnect(matching_code=matching_code, websocket=websocket)
