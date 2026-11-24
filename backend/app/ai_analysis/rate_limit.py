"""
AI分析用 レート制限（連打・過剰消費防止）モジュール（app/ai_analysis/rate_limit.py）

【このファイルの役割】
- Gemini API の連打や過剰利用を防ぐため、ユーザー（user_id）ごとに
  一定時間内（デフォルト60秒間）の実行回数上限（デフォルト5回）を管理する。
- 上限に達した場合は AIRateLimitError を送出し、ルーター側で HTTP 429 Too Many Requests を返す。
"""

from collections import defaultdict, deque
from threading import Lock
import time

from app.core.config import settings


class AIRateLimitError(RuntimeError):
    """AI分析のレート制限（回数上限）を超過した場合の例外"""
    pass


class SlidingWindowRateLimiter:
    """ユーザー単位のスライディングウィンドウ方式レートリミッター"""

    def __init__(self) -> None:
        self._requests: dict[int, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check_and_record(self, user_id: int) -> None:
        """
        指定ユーザーの直近ウィンドウ内の利用回数を確認し、上限以内であれば今回の実行を記録する。
        上限に達している場合は AIRateLimitError を送出する。
        """
        max_requests = settings.ai_rate_limit_max_requests
        window_seconds = settings.ai_rate_limit_window_seconds
        now = time.monotonic()

        with self._lock:
            timestamps = self._requests[user_id]
            # ウィンドウ期間外の古い実行履歴を削除
            while timestamps and (now - timestamps[0]) >= window_seconds:
                timestamps.popleft()

            if len(timestamps) >= max_requests:
                raise AIRateLimitError(
                    f"AI分析の利用回数上限（{window_seconds}秒あたり{max_requests}回）に達しました。"
                    "しばらく待ってから再度お試しください。"
                )

            timestamps.append(now)

    def reset(self) -> None:
        """記録されている全ユーザーのレート制限履歴をクリアする（主にテスト用）。"""
        with self._lock:
            self._requests.clear()


# アプリ全体で共有するAI分析レートリミッター
ai_rate_limiter = SlidingWindowRateLimiter()
