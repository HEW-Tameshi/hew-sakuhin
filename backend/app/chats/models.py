"""
チャット機能 DBテーブル定義（ORMモデル）モジュール（app/chats/models.py）

【このファイルの役割】
- SQLAlchemy を用いて、チャット機能に関わる以下の2つのDBテーブルを定義する。
  1. t_chat    （チャットルーム：マッチングと1対1で紐づく）
  2. t_message （メッセージ履歴：チャットルーム内の送受信メッセージ）
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


class Chat(Base):
    """
    チャットテーブル（t_chat）
    マッチング（t_matching）に対して1対1で作成されるチャットルームを管理する。
    """

    __tablename__ = "t_chat"

    # 主キー（自動採番）
    chat_id = Column(Integer, primary_key=True, autoincrement=True)

    # チャットコード（C + 英大文字・数字9文字 = 10文字、ユニーク）
    chat_code = Column(String(10), nullable=False, unique=True)

    # 紐づくマッチングID（t_matching.matching_id への外部キー、1対1のためユニーク）
    matching_id = Column(
        Integer,
        ForeignKey("t_matching.matching_id"),
        nullable=False,
        unique=True,
    )

    # チャットルーム作成日時
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class Message(Base):
    """
    メッセージテーブル（t_message）
    チャットルーム（t_chat）内で送信された各メッセージを記録する。
    """

    __tablename__ = "t_message"

    # 主キー（自動採番）
    message_id = Column(Integer, primary_key=True, autoincrement=True)

    # メッセージコード（MSG + 英大文字・数字9文字 = 12文字、ユニーク）
    message_code = Column(String(12), nullable=False, unique=True)

    # 所属するチャットルームID（t_chat.chat_id への外部キー）
    chat_id = Column(
        Integer,
        ForeignKey("t_chat.chat_id"),
        nullable=False,
    )

    # 送信者の会員ID（m_user.user_id への外部キー）
    sender_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # メッセージ本文
    message = Column(Text, nullable=False)

    # 送信日時
    sent_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
