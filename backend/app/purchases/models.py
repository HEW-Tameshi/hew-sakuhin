"""
購入・取引（マッチング）機能 DBテーブル定義（ORMモデル）モジュール（app/purchases/models.py）

【このファイルの役割】
- SQLAlchemy を用いて、レター購入および購入に基づいて成立するマッチング（取引）の2つのDBテーブルを定義する。
  1. t_letter_purchase （感情レター購入履歴トランザクション）
  2. t_matching        （取引・マッチングトランザクション）
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    text,
)

from app.users.models import Base


class LetterPurchase(Base):
    """
    感情レター購入履歴テーブル（t_letter_purchase）
    どの感情レターを、どの購入者が、何ポイントでいつ購入したかを記録する。
    """

    __tablename__ = "t_letter_purchase"

    # 主キー（自動採番）
    purchase_id = Column(Integer, primary_key=True, autoincrement=True)

    # 購入コード（P + 英数字10文字 = 11文字、ユニーク）
    purchase_code = Column(String(11), nullable=False, unique=True)

    # 購入した感情レターID（t_emotion_letter.letter_id への外部キー、1レター1購入のためユニーク）
    letter_id = Column(
        Integer,
        ForeignKey("t_emotion_letter.letter_id"),
        nullable=False,
        unique=True,
    )

    # 購入者の会員ID（m_user.user_id への外部キー）
    buyer_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # 購入時に消費したポイント数
    purchase_point = Column(Integer, nullable=False)

    # 購入日時
    purchased_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class Matching(Base):
    """
    取引（マッチング）テーブル（t_matching）
    レター購入に基づいて成立する、出品者と購入者の間の取引状態（進行中・完了・キャンセル）を管理する。

    【status の値】
    - 1: マッチング成立（対話開始前）
    - 2: 対話準備中
    - 3: 対話中
    - 4: 取引完了（completed_at に完了日時を記録）
    - 5: 取引キャンセル
    """

    __tablename__ = "t_matching"

    # 主キー（自動採番）
    matching_id = Column(Integer, primary_key=True, autoincrement=True)

    # マッチングコード（M + 英数字9文字 = 10文字、ユニーク）
    matching_code = Column(String(10), nullable=False, unique=True)

    # 紐づく購入履歴ID（t_letter_purchase.purchase_id への外部キー）
    purchase_id = Column(
        Integer,
        ForeignKey("t_letter_purchase.purchase_id"),
        nullable=False,
    )

    # 出品者の会員ID（m_user.user_id への外部キー）
    seller_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # 購入者の会員ID（m_user.user_id への外部キー）
    buyer_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # 取引ステータス（1〜3: 進行中 / 4: 完了 / 5: キャンセル）
    status = Column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    # マッチング成立日時
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # 取引完了日時（未完了時はNULL）
    completed_at = Column(DateTime, nullable=True)
