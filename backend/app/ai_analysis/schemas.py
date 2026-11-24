"""
AI分析機能 入出力スキーマ定義モジュール（app/ai_analysis/schemas.py）

【このファイルの役割】
- Pydantic を用いて、レターのリスク分析APIおよびチャット会話のAIまとめ・コミュニケーション分析APIの
  レスポンス構造を定義する。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LetterRiskAnalysisResponse(BaseModel):
    """
    レターリスク分析API（POST /api/ai/letters/{letter_code}/analyze）および
    分析履歴取得API（GET /api/ai/letters/{letter_code}）のレスポンススキーマ
    """

    ai_analysis_code: str
    letter_code: str
    risk_level: int = Field(..., ge=1, le=3, description="1:低リスク / 2:中リスク / 3:高リスク")
    risk_reason: str | None = None
    analyzed_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ai_analysis_code": "AI00000001",
                    "letter_code": "L000000001",
                    "risk_level": 1,
                    "risk_reason": "日常的な相談内容であり、不適切な表現や個人情報の記載は見られません。",
                    "analyzed_at": "2026-11-20T11:30:00",
                }
            ]
        }
    )


class ConversationAnalysisResponse(BaseModel):
    """
    会話AIまとめ＆コミュニケーション分析API（POST /api/ai/matchings/{matching_code}/analyze）のレスポンススキーマ
    review1.html（AIまとめ）および review2.html（総合評価・包容力・共感力・論理性・タイプ・肩書き）
    の表示項目と1対1で対応する。
    """

    matching_code: str
    summary_points: list[str]
    overall_evaluation: str
    embrace_score: int = Field(..., ge=0, le=100, description="包容力スコア（0〜100）")
    empathy_score: int = Field(..., ge=0, le=100, description="共感力スコア（0〜100）")
    logic_score: int = Field(..., ge=0, le=100, description="論理性スコア（0〜100）")
    personality_type: str
    personality_description: str
    title_badge: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "matching_code": "M000000001",
                    "summary_points": [
                        "相談内容を最後まで丁寧に聞いていました",
                        "相手の気持ちに共感する言葉が多く見られました",
                        "落ち着いた雰囲気で会話を進めていました",
                    ],
                    "overall_evaluation": "とても良い",
                    "embrace_score": 95,
                    "empathy_score": 88,
                    "logic_score": 72,
                    "personality_type": "相手を安心させるタイプ",
                    "personality_description": "相手の気持ちに寄り添い、安心感を与えることができるタイプです。",
                    "title_badge": "言語化の神",
                }
            ]
        }
    )
