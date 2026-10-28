
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    text,
)
from app.models.user import Base


class EmotionCategory(Base):
    """感情カテゴリテーブル"""

    __tablename__ = "m_emotion_category"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_code = Column(String(5), nullable=False, unique=True)
    category_name = Column(String(10), nullable=False, unique=True)
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class EmotionLetter(Base):
    """感情レターテーブル"""

    __tablename__ = "t_emotion_letter"

    letter_id = Column(Integer, primary_key=True, autoincrement=True)
    letter_code = Column(String(10), nullable=False, unique=True)
    seller_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )
    category_id = Column(
        Integer,
        ForeignKey("m_emotion_category.category_id"),
        nullable=False,
    )
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    desired_duration = Column(Integer, nullable=False)
    point = Column(Integer, nullable=False)
    status = Column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )


class LetterPurchase(Base):
    """感情レター購入履歴テーブル"""

    __tablename__ = "t_letter_purchase"

    purchase_id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_code = Column(String(11), nullable=False, unique=True)
    letter_id = Column(
        Integer,
        ForeignKey("t_emotion_letter.letter_id"),
        nullable=False,
        unique=True,
    )
    buyer_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )
    purchase_point = Column(Integer, nullable=False)
    purchased_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class Matching(Base):
    """取引テーブル"""

    __tablename__ = "t_matching"

    matching_id = Column(Integer, primary_key=True, autoincrement=True)
    matching_code = Column(String(10), nullable=False, unique=True)
    purchase_id = Column(
        Integer,
        ForeignKey("t_letter_purchase.purchase_id"),
        nullable=False,
    )
    seller_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )
    buyer_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )
    status = Column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    completed_at = Column(DateTime, nullable=True)
