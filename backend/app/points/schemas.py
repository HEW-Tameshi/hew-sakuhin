"""
ポイント・決済・サブスクリプション機能 入出力スキーマ定義モジュール（app/points/schemas.py）

【このファイルの役割】
- Pydantic を用いて、ポイント残高確認・履歴取得・ポイントチャージ・プレミアムサブスク管理の
  リクエストおよびレスポンスを定義する。
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# point.html の画面仕様に一致するポイントチャージプラン（ポイント数 -> 料金円）
POINT_CHARGE_PLANS: dict[int, int] = {
    100: 100,
    500: 500,
    1000: 950,
    5000: 4800,
}

# point.html のプレミアムポイントサブスク仕様
PREMIUM_SUBSCRIPTION_PLAN_NAME = "プレミアムポイントサブスク"
PREMIUM_SUBSCRIPTION_PRICE = 700
PREMIUM_SUBSCRIPTION_GRANT_POINTS = 700

# point_type の日本語ラベル
POINT_TYPE_LABELS: dict[int, str] = {
    1: "ポイントチャージ",
    2: "プレミアムサブスク付与",
    3: "レター購入",
    4: "レター売上",
    5: "チップ送付",
    6: "チップ受取",
}


class PointPlanItem(BaseModel):
    """ポイントチャージ1プラン分の情報"""

    points: int
    price_yen: int


class SubscriptionPlanInfo(BaseModel):
    """プレミアムサブスクプラン情報"""

    plan_name: str
    price_yen: int
    monthly_points: int


class PointPlansResponse(BaseModel):
    """ポイント購入プラン＆サブスク案内（GET /api/points/plans）レスポンス"""

    charge_plans: list[PointPlanItem]
    subscription_plan: SubscriptionPlanInfo


class PointBalanceResponse(BaseModel):
    """所持ポイント残高（GET /api/points/balance）レスポンス"""

    user_code: str
    balance: int
    has_active_subscription: bool


class PointHistoryItemResponse(BaseModel):
    """ポイント増減履歴1件分（GET /api/points/history）レスポンス"""

    point_history_code: str
    point: int
    point_type: int
    point_type_label: str
    created_at: datetime


class PointChargeRequest(BaseModel):
    """
    ポイントチャージAPI（POST /api/points/charge）のリクエストスキーマ
    point.html にある 100 / 500 / 1000 / 5000 ポイントのいずれかを指定する。
    """

    points: int = Field(
        ...,
        description="購入するポイント数（100, 500, 1000, 5000 のいずれか）",
    )

    payment_method: int = Field(
        default=1,
        description="決済手段（1: クレジットカード / 2: コンビニ決済 / 3: キャリア決済）",
    )

    @field_validator("points")
    @classmethod
    def validate_points(cls, value: int) -> int:
        if value not in POINT_CHARGE_PLANS:
            allowed = ", ".join(str(p) for p in POINT_CHARGE_PLANS)
            raise ValueError(f"購入ポイントは {allowed} のいずれかを指定してください")
        return value

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, value: int) -> int:
        if value not in (1, 2, 3):
            raise ValueError("決済手段は 1〜3 の整数を指定してください")
        return value


class PointChargeResponse(BaseModel):
    """ポイントチャージ完了（POST /api/points/charge）レスポンス"""

    payment_code: str
    point_history_code: str
    charged_points: int
    paid_amount_yen: int
    balance_after: int
    paid_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "payment_code": "PAY00000001",
                    "point_history_code": "PT00000001",
                    "charged_points": 1000,
                    "paid_amount_yen": 950,
                    "balance_after": 1130,
                    "paid_at": "2026-11-20T12:20:00",
                }
            ]
        }
    )


class SubscriptionCreateRequest(BaseModel):
    """プレミアムサブスク登録API（POST /api/points/subscription）のリクエストスキーマ"""

    payment_method: int = Field(
        default=1,
        description="決済手段（1: クレジットカード / 2: コンビニ決済 / 3: キャリア決済）",
    )

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, value: int) -> int:
        if value not in (1, 2, 3):
            raise ValueError("決済手段は 1〜3 の整数を指定してください")
        return value


class SubscriptionResponse(BaseModel):
    """サブスク契約・詳細・解約レスポンススキーマ"""

    subscription_code: str
    plan_name: str
    price: int
    start_date: date
    end_date: date | None = None
    status: int
    granted_points: int = 0
    balance_after: int | None = None
