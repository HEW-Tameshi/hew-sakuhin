"""
通知機能 DBテーブル定義（ORMモデル）モジュール（app/notifications/models.py）

【このファイルの役割】
- SQLAlchemy を用いて、通知テーブル（t_notification）をPythonクラスとして定義する。
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)

from app.users.models import Base


class Notification(Base):
    """
    通知テーブル（t_notification）
    購入成立・メッセージ受信・レビュー受信・ランクアップなどのユーザー向け通知を管理する。

    【notification_type の値】
    - 1: 購入・マッチング成立通知
    - 2: チャットメッセージ受信通知
    - 3: レビュー・チップ受信通知
    - 4: ランクアップ・お知らせ通知
    """

    __tablename__ = "t_notification"

    # 主キー（自動採番）
    notification_id = Column(Integer, primary_key=True, autoincrement=True)

    # 通知コード（N + 英大文字・数字9文字 = 10文字、ユニーク）
    notification_code = Column(String(10), nullable=False, unique=True)

    # 通知先ユーザーID（m_user.user_id への外部キー）
    user_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # 通知種別（1〜4）
    notification_type = Column(Integer, nullable=False)

    # 通知タイトル（最大100文字）
    title = Column(String(100), nullable=False)

    # 通知本文
    message = Column(Text, nullable=False)

    # 既読フラグ（0: 未読 / 1: 既読、初期値0）
    is_read = Column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    # 通知作成日時
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
