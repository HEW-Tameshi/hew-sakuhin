"""
会員ランク機能 ビジネスロジック（サービス層）モジュール（app/ranks/service.py）

【このファイルの役割】
- m_member_rank テーブルのランク定義登録・一覧取得を行う。
- t_point_history の累計獲得ポイント（point > 0 の合計）からユーザーの該当ランクを自動判定し、
  m_profile.delivery_rank_id を最新に同期する。
- ランクが昇格した際は、t_notification にランクアップ通知を自動作成する。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.notifications.service import add_notification_record
from app.points.models import PointHistory
from app.users.models import MemberRank, Profile, User


def list_member_ranks(db: Session) -> list[MemberRank]:
    """登録されている会員ランクマスタを必要ポイント昇順で取得する。"""
    return list(
        db.scalars(
            select(MemberRank).order_by(
                MemberRank.required_point.asc(),
                MemberRank.rank_id.asc(),
            )
        ).all()
    )


def create_member_rank(
    db: Session,
    rank_name: str,
    required_point: int,
) -> MemberRank:
    """会員ランクマスタ（m_member_rank）に新しいランクを登録する。"""
    try:
        existing = db.scalar(
            select(MemberRank).where(MemberRank.rank_name == rank_name)
        )
        if existing is not None:
            raise ValueError("同じ名前の会員ランクが既に登録されています")

        rank = MemberRank(
            rank_name=rank_name,
            required_point=required_point,
        )
        db.add(rank)
        db.commit()
        db.refresh(rank)
        return rank

    except Exception:
        db.rollback()
        raise


def get_user_total_earned_points(db: Session, user_id: int) -> int:
    """
    指定ユーザーの累計獲得ポイント（t_point_history.point > 0 の合計）を返す。
    ※ポイント消費（マイナス）ではランクが下がらないよう、獲得分のみを集計する。
    """
    total = db.scalar(
        select(func.coalesce(func.sum(PointHistory.point), 0)).where(
            PointHistory.user_id == user_id,
            PointHistory.point > 0,
        )
    )
    return int(total or 0)


def sync_user_rank_in_tx(
    db: Session,
    user_id: int,
) -> tuple[int, MemberRank | None, MemberRank | None]:
    """
    現在のトランザクション内でユーザーの累計獲得ポイントからランクを再計算し、
    m_profile.delivery_rank_id を更新する（昇格時はランクアップ通知を追加）。
    ※コミットは呼び出し元で行う。

    戻り値: (total_earned_points, current_rank, next_rank)
    """
    total_earned = get_user_total_earned_points(db=db, user_id=user_id)
    ranks = list_member_ranks(db=db)

    current_rank: MemberRank | None = None
    next_rank: MemberRank | None = None

    for rank in ranks:
        if rank.required_point <= total_earned:
            current_rank = rank
        elif next_rank is None:
            next_rank = rank

    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is not None and current_rank is not None:
        previous_rank_id = profile.delivery_rank_id
        if previous_rank_id != current_rank.rank_id:
            profile.delivery_rank_id = current_rank.rank_id

            # 既に何らかのランクを持っていた状態からの昇格、または上位ランク（required_point > 0）到達時に通知
            if previous_rank_id is not None or current_rank.required_point > 0:
                add_notification_record(
                    db=db,
                    user_id=user_id,
                    notification_type=4,  # 4: ランクアップ・お知らせ
                    title=f"ランクが「{current_rank.rank_name}」にアップしました！",
                    message=(
                        f"累計獲得ポイントが {total_earned}pt に到達し、"
                        f"会員ランクが「{current_rank.rank_name}」になりました。"
                    ),
                )

    return total_earned, current_rank, next_rank


def get_and_sync_user_rank_progress(
    db: Session,
    user: User,
) -> dict:
    """
    ログイン中ユーザーのランクを同期・確定し、次ランクまでの残りポイントと進捗率（%）を算出して返す。
    """
    try:
        total_earned, current_rank, next_rank = sync_user_rank_in_tx(
            db=db,
            user_id=user.user_id,
        )
        db.commit()

        points_to_next = None
        progress_percent = 100

        if next_rank is not None:
            base_point = current_rank.required_point if current_rank is not None else 0
            span = max(1, next_rank.required_point - base_point)
            earned_in_level = max(0, total_earned - base_point)
            points_to_next = max(0, next_rank.required_point - total_earned)
            progress_percent = min(100, int((earned_in_level * 100) / span))
        elif current_rank is None:
            progress_percent = 0

        return {
            "user_code": user.user_code,
            "total_earned_points": total_earned,
            "current_rank_id": current_rank.rank_id if current_rank else None,
            "current_rank_name": current_rank.rank_name if current_rank else None,
            "next_rank_id": next_rank.rank_id if next_rank else None,
            "next_rank_name": next_rank.rank_name if next_rank else None,
            "next_required_point": next_rank.required_point if next_rank else None,
            "points_to_next_rank": points_to_next,
            "progress_percent": progress_percent,
        }

    except Exception:
        db.rollback()
        raise
