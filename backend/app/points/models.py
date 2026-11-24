"""
ポイント・決済・サブスクリプション機能 DBテーブル定義（ORMモデル）モジュール（app/points/models.py）

【このファイルの役割】
- SQLAlchemy を用いて、以下の3つのDBテーブルを定義する（開発DB kokoro_mail の実測DDLと完全一致）：
  1. t_subscription  （サブスクリプション契約テーブル）
  2. t_payment       （決済トランザクションテーブル：CHECK制約付き）
  3. t_point_history （ポイント増減履歴トランザクションテーブル）
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    text,
)

from app.users.models import Base


class Subscription(Base):
    """
    サブスクリプションテーブル（t_subscription）
    プレミアムポイントサブスク（月額700円・毎月700pt付与）の契約状態を管理する。

    【status の値】
    - 1: 有効（契約中）
    - 2: 解約済み
    """

    __tablename__ = "t_subscription"

    # 主キー（自動採番）
    subscription_id = Column(Integer, primary_key=True, autoincrement=True)

    # サブスクコード（SUB + 英大文字・数字8文字 = 11文字、ユニーク）
    subscription_code = Column(String(11), nullable=False, unique=True)

    # 契約会員ID（m_user.user_id への外部キー）
    user_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # プラン名（最大50文字）
    plan_name = Column(String(50), nullable=False)

    # 月額料金（円）
    price = Column(Integer, nullable=False)

    # 契約開始日
    start_date = Column(Date, nullable=False)

    # 契約終了・解約日（契約中はNULL）
    end_date = Column(Date, nullable=True)

    # 契約ステータス（1: 有効 / 2: 解約済み）
    status = Column(
        Integer,
        nullable=False,
        server_default=text("1"),
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


class Payment(Base):
    """
    決済テーブル（t_payment）
    ポイントチャージ、サブスクリプション、レター購入の決済履歴を記録する。

    【payment_type と CHECK 制約（t_payment_chk_1）】
    - 1: レター購入決済（purchase_id NOT NULL, subscription_id NULL）
    - 2: サブスク決済（purchase_id NULL, subscription_id NOT NULL）
    - 3: ポイントチャージ決済（purchase_id NULL, subscription_id NULL）

    【payment_method の値】
    - 1: クレジットカード
    - 2: コンビニ決済
    - 3: キャリア決済
    """

    __tablename__ = "t_payment"
    __table_args__ = (
        CheckConstraint(
            "(payment_type = 1 AND purchase_id IS NOT NULL AND subscription_id IS NULL) OR "
            "(payment_type = 2 AND purchase_id IS NULL AND subscription_id IS NOT NULL) OR "
            "(payment_type = 3 AND purchase_id IS NULL AND subscription_id IS NULL)",
            name="t_payment_chk_1",
        ),
    )

    # 主キー（自動採番）
    payment_id = Column(Integer, primary_key=True, autoincrement=True)

    # 決済コード（PAY + 英大文字・数字8文字 = 11文字、ユニーク）
    payment_code = Column(String(11), nullable=False, unique=True)

    # 決済ユーザーID（m_user.user_id への外部キー）
    user_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # 決済種別（1: 購入 / 2: サブスク / 3: ポイントチャージ）
    payment_type = Column(Integer, nullable=False)

    # レター購入ID（payment_type=1 のみ設定）
    purchase_id = Column(
        Integer,
        ForeignKey("t_letter_purchase.purchase_id"),
        nullable=True,
    )

    # サブスクID（payment_type=2 のみ設定）
    subscription_id = Column(
        Integer,
        ForeignKey("t_subscription.subscription_id"),
        nullable=True,
    )

    # 決済手段（1: クレジットカード / 2: コンビニ / 3: キャリア）
    payment_method = Column(Integer, nullable=False)

    # 決済金額（円）
    amount = Column(Integer, nullable=False)

    # 決済ステータス（1: 決済完了）
    payment_status = Column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    # 決済完了日時
    paid_at = Column(DateTime, nullable=True)

    # 作成日時
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class PointHistory(Base):
    """
    ポイント履歴テーブル（t_point_history）
    全ポイントの増減（チャージ・サブスク付与・レター購入消費・売上獲得・チップ送受信）を記録する。
    ユーザーの現在残高は SUM(point) で算出する。

    【point_type の値】
    - 1: ポイントチャージ（加算）
    - 2: サブスクリプション付与（加算）
    - 3: レター購入消費（減算）
    - 4: レター売上獲得（加算）
    - 5: チップ送付消費（減算）
    - 6: チップ受取獲得（加算）
    """

    __tablename__ = "t_point_history"

    # 主キー（自動採番）
    point_history_id = Column(Integer, primary_key=True, autoincrement=True)

    # ポイント履歴コード（PT + 英大文字・数字8文字 = 10文字、ユニーク）
    point_history_code = Column(String(10), nullable=False, unique=True)

    # 対象ユーザーID（m_user.user_id への外部キー）
    user_id = Column(
        Integer,
        ForeignKey("m_user.user_id"),
        nullable=False,
    )

    # ポイント変動量（付与は正の整数、消費は負の整数）
    point = Column(Integer, nullable=False)

    # ポイント増減種別（1〜6）
    point_type = Column(Integer, nullable=False)

    # 関連レター購入ID（任意）
    related_purchase_id = Column(
        Integer,
        ForeignKey("t_letter_purchase.purchase_id"),
        nullable=True,
    )

    # 関連マッチングID（任意）
    related_matching_id = Column(
        Integer,
        ForeignKey("t_matching.matching_id"),
        nullable=True,
    )

    # 関連決済ID（任意）
    related_payment_id = Column(
        Integer,
        ForeignKey("t_payment.payment_id"),
        nullable=True,
    )

    # 関連チップID（任意）
    related_tip_id = Column(
        Integer,
        ForeignKey("t_tip.tip_id"),
        nullable=True,
    )

    # 履歴記録日時
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
