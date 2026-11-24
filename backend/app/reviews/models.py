"""
レビュー＆チップ機能 DBテーブル定義（ORMモデル）モジュール（app/reviews/models.py）

【このファイルの役割】
- SQLAlchemy を用いて、レビュー（t_review）およびチップ/投げ銭（t_tip）の2テーブルを定義する。
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)

from app.users.models import Base


class Review(Base):
    """
    レビューテーブル（t_review）
    取引（t_matching）の当事者同士が、1〜5段階の評価（rating）とコメントを記録する。
    """

    __tablename__ = "t_review"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="t_review_chk_1"),
    )

    # 主キー（自動採番）
    review_id = Column(Integer, primary_key=True, autoincrement=True)

    # レビューコード（R + 英大文字・数字9文字 = 10文字、ユニーク）
    review_code = Column(String(10), nullable=False, unique=True)

    # 対象の取引マッチングID（t_matching.matching_id への外部キー）
    matching_id = Column(
        Integer,
        ForeignKey("t_matching.matching_id"),
        nullable=False,
    )

    # レビューを書いたユーザーのID（m_user.user_id への外部キー）
    reviewer_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # レビューを受けた相手ユーザーのID（m_user.user_id への外部キー）
    reviewee_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # 評価（1〜5の整数）
    rating = Column(Integer, nullable=False)

    # レビューコメント（任意）
    comment = Column(Text, nullable=True)

    # 投稿日時
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class Tip(Base):
    """
    投げ銭・チップテーブル（t_tip）
    レビュー時などに相手へ感謝のポイントを送る記録を管理する。
    """

    __tablename__ = "t_tip"

    # 主キー（自動採番）
    tip_id = Column(Integer, primary_key=True, autoincrement=True)

    # チップコード（T + 英大文字・数字9文字 = 10文字、ユニーク）
    tip_code = Column(String(10), nullable=False, unique=True)

    # チップを送ったユーザーのID（m_user.user_id への外部キー）
    sender_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # チップを受け取ったユーザーのID（m_user.user_id への外部キー）
    receiver_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # 送付ポイント数
    amount = Column(Integer, nullable=False)

    # チップに添えたメッセージ（任意）
    message = Column(Text, nullable=True)

    # 送付日時
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
