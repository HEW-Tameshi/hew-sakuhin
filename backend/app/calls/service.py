"""
通話機能 ビジネスロジック（サービス層）モジュール（app/calls/service.py）

【このファイルの役割】
- マッチング（t_matching）に紐づく通話（t_call）の開始・終了（通話時間計算）・履歴取得を担当する。
- 当事者確認、終了済み取引での通話禁止、二重通話開始の防止、およびトランザクション管理を行う。
"""

from datetime import datetime, timezone
import secrets
import string

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calls.models import Call
from app.purchases.models import Matching
from app.users.models import User


def generate_call_code() -> str:
    """t_call.call_code 用の10文字の一意コード（'CL' + 英大文字・数字8文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "CL" + "".join(secrets.choice(characters) for _ in range(8))


class CallNotAllowedError(ValueError):
    """完了またはキャンセルされた取引で通話を開始しようとした場合の例外"""
    pass


class CallAlreadyActiveError(ValueError):
    """同じマッチングで既に進行中の通話がある場合の例外"""
    pass


class CallAlreadyEndedError(ValueError):
    """既に終了済みの通話を再度終了しようとした場合の例外"""
    pass


def start_call(
    db: Session,
    matching_code: str,
    current_user: User,
    communication_type: int = 1,
) -> tuple[Call, Matching] | None:
    """
    通話を開始し、t_call テーブルへ記録する。

    【処理の実行順序】
    1. matching_code で t_matching を検索する（未存在なら None）。
    2. 当事者（seller_id または buyer_id）であることを確認する（第三者なら PermissionError）。
    3. 取引が進行中（status in [1, 2, 3]）であることを確認する（完了・キャンセル済みは CallNotAllowedError）。
    4. 同じマッチングに未終了（ended_at IS NULL）の通話が存在しないか確認する（重複時は CallAlreadyActiveError）。
    5. call_code（CL + 8文字）を採番して t_call を登録し、matching.status が 1 または 2 なら 3（対話中）に更新する。
    6. db.commit() で確定し、(Call, Matching) を返す（例外時は db.rollback()）。
    """
    try:
        matching = db.scalar(
            select(Matching).where(Matching.matching_code == matching_code)
        )
        if matching is None:
            return None

        if current_user.user_id not in (matching.seller_id, matching.buyer_id):
            raise PermissionError("この取引の当事者ではないため通話を開始できません")

        if matching.status not in (1, 2, 3):
            raise CallNotAllowedError("完了またはキャンセルされた取引では通話を開始できません")

        active_call = db.scalar(
            select(Call).where(
                Call.matching_id == matching.matching_id,
                Call.ended_at.is_(None),
            )
        )
        if active_call is not None:
            raise CallAlreadyActiveError("この取引では既に通話が進行中です")

        call_code = generate_call_code()
        if db.scalar(select(Call.call_id).where(Call.call_code == call_code)):
            call_code = generate_call_code()

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        call = Call(
            call_code=call_code,
            matching_id=matching.matching_id,
            communication_type=communication_type,
            started_at=now,
            ended_at=None,
            duration=None,
        )
        db.add(call)

        # 通話開始に伴い、取引ステータスを「3（対話中）」へ更新
        if matching.status in (1, 2):
            matching.status = 3

        db.commit()
        db.refresh(call)
        db.refresh(matching)

        return call, matching

    except Exception:
        db.rollback()
        raise


def end_call(
    db: Session,
    call_code: str,
    current_user: User,
) -> tuple[Call, Matching] | None:
    """
    進行中の通話を終了し、終了日時（ended_at）と通話時間（duration: 秒）を自動計算して保存する。

    【処理の実行順序】
    1. call_code で t_call と t_matching を結合して検索する（未存在なら None）。
    2. 当事者確認を行う（第三者なら PermissionError）。
    3. 既に ended_at が記録されている場合は CallAlreadyEndedError を送出する。
    4. ended_at に現在時刻を設定し、duration = max(0, int((ended_at - started_at).total_seconds())) を計算する。
    5. db.commit() で確定し、(Call, Matching) を返す。
    """
    try:
        row = db.execute(
            select(Call, Matching)
            .join(Matching, Call.matching_id == Matching.matching_id)
            .where(Call.call_code == call_code)
        ).first()

        if row is None:
            return None

        call, matching = row

        if current_user.user_id not in (matching.seller_id, matching.buyer_id):
            raise PermissionError("この通話の当事者ではないため操作できません")

        if call.ended_at is not None:
            raise CallAlreadyEndedError("この通話は既に終了しています")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        elapsed_seconds = max(0, int((now - call.started_at).total_seconds()))

        call.ended_at = now
        call.duration = elapsed_seconds

        db.commit()
        db.refresh(call)

        return call, matching

    except Exception:
        db.rollback()
        raise


def list_calls_by_matching(
    db: Session,
    matching_code: str,
    current_user: User,
) -> tuple[list[Call], Matching] | None:
    """指定されたマッチングの通話履歴一覧を新しい順（call_id 降順）で取得する。"""
    matching = db.scalar(
        select(Matching).where(Matching.matching_code == matching_code)
    )
    if matching is None:
        return None

    if current_user.user_id not in (matching.seller_id, matching.buyer_id):
        raise PermissionError("この取引の当事者ではないため通話履歴を閲覧できません")

    calls = list(
        db.scalars(
            select(Call)
            .where(Call.matching_id == matching.matching_id)
            .order_by(Call.call_id.desc())
        ).all()
    )

    return calls, matching


def get_call_by_code(
    db: Session,
    call_code: str,
    current_user: User,
) -> tuple[Call, Matching] | None:
    """指定された call_code の通話詳細を1件取得する（当事者以外は PermissionError）。"""
    row = db.execute(
        select(Call, Matching)
        .join(Matching, Call.matching_id == Matching.matching_id)
        .where(Call.call_code == call_code)
    ).first()

    if row is None:
        return None

    call, matching = row

    if current_user.user_id not in (matching.seller_id, matching.buyer_id):
        raise PermissionError("この通話の当事者ではないため閲覧できません")

    return call, matching
