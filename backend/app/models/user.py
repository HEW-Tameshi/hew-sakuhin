
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemyモデルの基底クラス"""
    pass


class MemberRank(Base):
    """会員ランクテーブル（m_member_rank）"""

    __tablename__ = "m_member_rank"

    rank_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    rank_name = Column(
        String(20),
        nullable=False,
    )

    required_point = Column(
        Integer,
        nullable=False,
        server_default=text("0"),
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


class User(Base):
    """会員情報テーブル（m_user）"""

    __tablename__ = "m_user"

    user_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_code = Column(
        String(7),
        nullable=False,
        unique=True,
    )

    email = Column(
        String(254),
        nullable=False,
        unique=True,
    )

    password = Column(
        String(255),
        nullable=False,
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

    profile = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
    )


    account_status = Column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    deleted_at = Column(
        DateTime,
        nullable=True,
    )


class Profile(Base):
    """プロフィールテーブル（m_profile）"""

    __tablename__ = "m_profile"

    profile_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    profile_code = Column(
        String(7),
        nullable=False,
        unique=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
        unique=True,
    )

    nickname = Column(
        String(50),
        nullable=False,
    )

    profile_image = Column(
        String(255),
        nullable=True,
    )

    introduction = Column(
        Text,
        nullable=True,
    )

    delivery_rank_id = Column(
        Integer,
        ForeignKey("m_member_rank.rank_id"),
        nullable=True,
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

    user = relationship(
        "User",
        back_populates="profile",
    )