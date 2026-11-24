"""
通知機能 ビジネスロジック（サービス層）モジュール（app/notifications/service.py）

【このファイルの役割】
- 他機能（購入・チャット・レビュー・ランクアップ）から呼び出す通知作成ヘルパーを提供する。
- ログイン中ユーザーの通知一覧取得・未読件数集計・単体既読・一括既読処理を担当する。
"""

import secrets
import string

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.notifications.models import Notification
from app.users.models import User


def generate_notification_code() -> str:
    """t_notification.notification_code 用の10文字コード（'N' + 英大文字・数字9文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "N" + "".join(secrets.choice(characters) for _ in range(9))


def add_notification_record(
    db: Session,
    user_id: int,
    notification_type: int,
    title: str,
    message: str,
) -> Notification:
    """
    現在のトランザクション内に通知レコード（t_notification）を1件追加する共通ヘルパー。
    ※コミットは呼び出し元のトランザクションで行う。
    """
    code = generate_notification_code()
    if db.scalar(
        select(Notification.notification_id).where(
            Notification.notification_code == code
        )
    ):
        code = generate_notification_code()

    notif = Notification(
        notification_code=code,
        user_id=user_id,
        notification_type=notification_type,
        title=title[:100],
        message=message,
        is_read=0,
    )
    db.add(notif)
    return notif


def list_user_notifications(
    db: Session,
    user: User,
    unread_only: bool = False,
) -> tuple[list[Notification], int]:
    """
    ログイン中ユーザーの通知一覧（新しい順）と未読件数（unread_count）を返す。
    """
    unread_count = int(
        db.scalar(
            select(func.count(Notification.notification_id)).where(
                Notification.user_id == user.user_id,
                Notification.is_read == 0,
            )
        )
        or 0
    )

    stmt = select(Notification).where(Notification.user_id == user.user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == 0)

    stmt = stmt.order_by(Notification.notification_id.desc())
    notifications = list(db.scalars(stmt).all())

    return notifications, unread_count


def mark_notification_as_read(
    db: Session,
    notification_code: str,
    user: User,
) -> Notification | None:
    """
    指定された通知コード（notification_code）を既読（is_read = 1）に更新する。
    ※他ユーザーの通知の場合は PermissionError を送出する。
    """
    try:
        notif = db.scalar(
            select(Notification).where(
                Notification.notification_code == notification_code
            )
        )
        if notif is None:
            return None

        if notif.user_id != user.user_id:
            raise PermissionError("他のユーザーの通知は操作できません")

        notif.is_read = 1
        db.commit()
        db.refresh(notif)
        return notif

    except Exception:
        db.rollback()
        raise


def mark_all_notifications_as_read(
    db: Session,
    user: User,
) -> int:
    """ログイン中ユーザーの未読通知をすべて既読（is_read = 1）に更新し、更新件数を返す。"""
    try:
        result = db.execute(
            update(Notification)
            .where(
                Notification.user_id == user.user_id,
                Notification.is_read == 0,
            )
            .values(is_read=1)
        )
        db.commit()
        return int(result.rowcount or 0)

    except Exception:
        db.rollback()
        raise
