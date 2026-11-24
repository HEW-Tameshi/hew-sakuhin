"""
会員機能 DBテーブル定義（ORMモデル）モジュール（app/users/models.py）

【このファイルの役割】
- SQLAlchemy を用いて、会員機能に関わる以下の4つのDBテーブルをPythonクラスとして定義する。
  1. m_member_rank   （会員ランクマスタ）
  2. m_user          （ユーザーマスタ）
  3. m_profile       （プロフィールマスタ）
  4. t_revoked_token （失効済みトークントランザクション）
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """全SQLAlchemyモデルが継承する基底クラス"""
    pass


class MemberRank(Base):
    """
    会員ランクテーブル（m_member_rank）
    配達ランク（会員ランク）の名称と必要ポイントを管理するマスタテーブル。
    """

    __tablename__ = "m_member_rank"

    # 主キー（自動採番）
    rank_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ランク名（最大20文字）
    rank_name = Column(
        String(20),
        nullable=False,
    )

    # ランク到達に必要なポイント（初期値0）
    required_point = Column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    # 作成日時
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # 更新日時（更新時に自動更新）
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )


class User(Base):
    """
    会員情報テーブル（m_user）
    ログイン認証に使用するメールアドレス・ハッシュ化パスワード・アカウント状態を管理する。
    """

    __tablename__ = "m_user"

    # 主キー（自動採番）
    user_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # 会員コード（U + 英数字6文字 = 7文字、ユニーク）
    user_code = Column(
        String(7),
        nullable=False,
        unique=True,
    )

    # メールアドレス（最大254文字、ユニーク）
    email = Column(
        String(254),
        nullable=False,
        unique=True,
    )

    # ハッシュ化済みパスワード
    password = Column(
        String(255),
        nullable=False,
    )

    # 登録日時
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

    # 1対1で紐づくプロフィール情報へのリレーション
    profile = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
    )

    # アカウント状態（1: 有効 / 2: 退会済み）
    account_status = Column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    # 退会日時（未退会時はNULL）
    deleted_at = Column(
        DateTime,
        nullable=True,
    )


class Profile(Base):
    """
    プロフィールテーブル（m_profile）
    画面に表示するニックネーム、アイコン画像、自己紹介文、配達ランクを管理する。
    """

    __tablename__ = "m_profile"

    # 主キー（自動採番）
    profile_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # プロフィールコード（P + 英数字6文字 = 7文字、ユニーク）
    profile_code = Column(
        String(7),
        nullable=False,
        unique=True,
    )

    # 紐づく会員ID（m_user.user_id への外部キー、1対1のためユニーク）
    user_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
        unique=True,
    )

    # ニックネーム（最大50文字）
    nickname = Column(
        String(50),
        nullable=False,
    )

    # プロフィール画像パス（任意）
    profile_image = Column(
        String(255),
        nullable=True,
    )

    # 自己紹介文（任意）
    introduction = Column(
        Text,
        nullable=True,
    )

    # 配達ランクID（m_member_rank.rank_id への外部キー、会員登録時はNULL）
    delivery_rank_id = Column(
        Integer,
        ForeignKey("m_member_rank.rank_id"),
        nullable=True,
    )

    # 作成日時
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

    # 親となる会員情報（User）へのリレーション
    user = relationship(
        "User",
        back_populates="profile",
    )


class RevokedToken(Base):
    """
    失効済みアクセストークンテーブル（t_revoked_token）
    ログアウトや退会によって無効化されたJWTトークンのJTI（識別子）を記録し、再利用を防ぐ。
    """

    __tablename__ = "t_revoked_token"

    # 主キー（自動採番）
    revoked_token_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # JWTのユニーク識別子（UUID文字列 36文字）
    jti: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
    )

    # トークン本来の有効期限
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    # 失効登録日時
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
