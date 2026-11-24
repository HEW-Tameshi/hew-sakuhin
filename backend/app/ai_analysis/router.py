"""
AI分析機能 APIルーター定義モジュール（app/ai_analysis/router.py）

【このファイルの役割】
- /api/ai 配下のエンドポイントを受け付け、Gemini API による分析処理を提供する：
  1. POST /api/ai/letters/{letter_code}/analyze     : レターのリスク分析（出品者本人のみ・キャッシュ対応・レート制限付き）
  2. GET  /api/ai/letters/{letter_code}             : レターのAI分析履歴一覧を取得
  3. POST /api/ai/matchings/{matching_code}/analyze : チャット会話のAIまとめ・コミュニケーション分析（当事者のみ・レート制限付き）
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.ai_analysis.rate_limit import AIRateLimitError
from app.ai_analysis.schemas import (
    ConversationAnalysisResponse,
    LetterRiskAnalysisResponse,
)
from app.ai_analysis.service import (
    analyze_letter_risk,
    analyze_matching_conversation,
    list_letter_analyses,
)
from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.gemini_client import GeminiAPIError, GeminiConfigError
from app.users.models import User

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Analysis"],
)


@router.post(
    "/letters/{letter_code}/analyze",
    response_model=LetterRiskAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="感情レターAIリスク分析API（Gemini）",
)
def run_letter_risk_analysis(
    letter_code: str,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    指定された感情レターを Gemini API でリスク分析し、t_ai_analysis テーブルへ保存して返す。
    - 出品者本人以外は HTTP 403 Forbidden
    - 同じ内容で既に分析済みの場合は Gemini を再呼び出しせずキャッシュを HTTP 200 OK で返却
    - レート制限超過時は HTTP 429 Too Many Requests
    """
    try:
        result = analyze_letter_risk(
            db=db,
            letter_code=letter_code,
            current_user=current_user,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された出品が見つかりません",
            )

        analysis, letter, created = result
        if not created:
            response.status_code = status.HTTP_200_OK

        return LetterRiskAnalysisResponse(
            ai_analysis_code=analysis.ai_analysis_code,
            letter_code=letter.letter_code,
            risk_level=analysis.risk_level,
            risk_reason=analysis.risk_reason,
            analyzed_at=analysis.analyzed_at,
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AIRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    except GeminiConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except GeminiAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get(
    "/letters/{letter_code}",
    response_model=list[LetterRiskAnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="感情レターAI分析履歴取得API",
)
def get_letter_analyses(
    letter_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """指定された感情レターに対する過去のAI分析結果一覧を新しい順で取得する。"""
    result = list_letter_analyses(db=db, letter_code=letter_code)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定された出品が見つかりません",
        )

    analyses, letter = result
    return [
        LetterRiskAnalysisResponse(
            ai_analysis_code=a.ai_analysis_code,
            letter_code=letter.letter_code,
            risk_level=a.risk_level,
            risk_reason=a.risk_reason,
            analyzed_at=a.analyzed_at,
        )
        for a in analyses
    ]


@router.post(
    "/matchings/{matching_code}/analyze",
    response_model=ConversationAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="チャット会話AIまとめ＆コミュニケーション分析API（Gemini）",
)
def run_conversation_analysis(
    matching_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取引のチャット会話履歴を Gemini API で分析し、review1.html（AIまとめ）および
    review2.html（包容力・共感力・論理性スコア、タイプ、肩書き）用のデータを返す。
    - 取引当事者以外は HTTP 403 Forbidden
    - レート制限超過時は HTTP 429 Too Many Requests
    """
    try:
        result = analyze_matching_conversation(
            db=db,
            matching_code=matching_code,
            current_user=current_user,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたマッチングが見つかりません",
            )

        return ConversationAnalysisResponse(**result)

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AIRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    except GeminiConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except GeminiAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
