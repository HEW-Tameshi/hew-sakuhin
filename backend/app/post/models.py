"""
出品機能 DBテーブル定義（ORMモデル）モジュール（app/post/models.py）

【このファイルの役割】
- SQLAlchemy を用いて、出品機能に関わる以下の2つのDBテーブルをPythonクラスとして定義する。
  1. m_emotion_category （感情カテゴリマスタ：喜・怒・哀・楽）
  2. t_emotion_letter   （感情レタートランザクション：出品されたレター情報）
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


class EmotionCategory(Base):
    """
    感情カテゴリテーブル（m_emotion_category）
    喜（E01）・怒（E02）・哀（E03）・楽（E04）の4種類の感情マスタを管理する。
    """

    __tablename__ = "m_emotion_category"

    # 主キー（自動採番）
    category_id = Column(Integer, primary_key=True, autoincrement=True)

    # カテゴリコード（例：'E01', 'E02', 'E03', 'E04'、ユニーク）
    category_code = Column(String(5), nullable=False, unique=True)

    # カテゴリ名（例：'喜', '怒', '哀', '楽'、ユニーク）
    category_name = Column(String(10), nullable=False, unique=True)

    # 作成日時
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class EmotionLetter(Base):
    """
    感情レターテーブル（t_emotion_letter）
    ユーザーが出品した感情レターの見出し・内容・希望時間・ポイント・出品状態を管理する。
    """

    __tablename__ = "t_emotion_letter"

    # 主キー（自動採番）
    letter_id = Column(Integer, primary_key=True, autoincrement=True)

    # レターコード（L + 英大文字・数字9文字 = 10文字、ユニーク）
    letter_code = Column(String(10), nullable=False, unique=True)

    # 出品者ID（m_user.user_id への外部キー）
    seller_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # 感情カテゴリID（m_emotion_category.category_id への外部キー）
    category_id = Column(
        Integer,
        ForeignKey("m_emotion_category.category_id"),
        nullable=False,
    )

    # 見出し（最大100文字）
    title = Column(String(100), nullable=False)

    # 話したい内容（TEXT）
    content = Column(Text, nullable=False)

    # 希望時間（分単位の整数）
    desired_duration = Column(Integer, nullable=False)

    # 出品ポイント（整数）
    point = Column(Integer, nullable=False)

    # 出品状態（初期値 1: 出品中 / 4: 出品停止 など）
    status = Column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    # 出品日時
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # 更新日時
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )
