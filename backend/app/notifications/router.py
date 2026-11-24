"""
通知機能 APIルーター定義モジュール（app/notifications/router.py）

【このファイルの役割】
- /api/notifications 配下のエンドポイントを受け付ける：
  1. GET   /api/notifications                          : 通知一覧・未読件数取得（?unread_only=true 対応）
  2. PATCH /api/notifications/read-all                 : 自分の未読通知を一括既読
  3. PATCH /api/notifications/{notification_code}/read : 指定通知1件を既読
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.notifications.models import Notification
from app.notifications.schemas import (
    NOTIFICATION_TYPE_LABELS,
    NotificationItemResponse,
    NotificationListResponse,
    NotificationReadAllResponse,
)
from app.notifications.service import (
    list_user_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)
from app.users.models import User

router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"],
)


def _to_item_response(notif: Notification) -> NotificationItemResponse:
    return NotificationItemResponse(
        notification_code=notif.notification_code,
        notification_type=notif.notification_type,
        notification_type_label=NOTIFICATION_TYPE_LABELS.get(
            notif.notification_type, "お知らせ"
        ),
        title=notif.title,
        message=notif.message,
        is_read=(notif.is_read == 1),
        created_at=notif.created_at,
    )


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="通知一覧・未読件数取得API",
)
def get_notifications(
    unread_only: bool = Query(
        default=False,
        description="true の場合は未読通知のみ取得する",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ログイン中ユーザーの通知一覧と未読件数を取得する。"""
    notifications, unread_count = list_user_notifications(
        db=db,
        user=current_user,
        unread_only=unread_only,
    )
    return NotificationListResponse(
        unread_count=unread_count,
        notifications=[_to_item_response(n) for n in notifications],
    )


@router.patch(
    "/read-all",
    response_model=NotificationReadAllResponse,
    status_code=status.HTTP_200_OK,
    summary="通知一括既読API",
)
def read_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ログイン中ユーザーの未読通知をすべて既読にする。"""
    updated_count = mark_all_notifications_as_read(db=db, user=current_user)
    return NotificationReadAllResponse(
        message="すべての通知を既読にしました",
        updated_count=updated_count,
    )


@router.patch(
    "/{notification_code}/read",
    response_model=NotificationItemResponse,
    status_code=status.HTTP_200_OK,
    summary="通知単体既読API",
)
def read_notification(
    notification_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """指定された通知1件を既読にする。"""
    try:
        notif = mark_notification_as_read(
            db=db,
            notification_code=notification_code,
            user=current_user,
        )
        if notif is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された通知が見つかりません",
            )
        return _to_item_response(notif)

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
