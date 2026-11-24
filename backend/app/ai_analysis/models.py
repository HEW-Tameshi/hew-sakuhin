"""
AI分析機能 DBテーブル定義（ORMモデル）モジュール（app/ai_analysis/models.py）

【このファイルの役割】
- SQLAlchemy を用いて、AI分析結果テーブル（t_ai_analysis）をPythonクラスとして定義する。
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)

from app.users.models import Base


class AiAnalysis(Base):
    """
    AI分析テーブル（t_ai_analysis）
    感情レター（t_emotion_letter）に対するGemini APIによるリスク分析結果（risk_level, risk_reason）を記録する。

    【risk_level の値】
    - 1: 低リスク（安全）
    - 2: 中リスク（注意・医療専門家ではない旨の配慮が必要等）
    - 3: 高リスク（不適切表現・個人情報・深刻な内容など要確認）
    """

    __tablename__ = "t_ai_analysis"

    # 主キー（自動採番）
    ai_analysis_id = Column(Integer, primary_key=True, autoincrement=True)

    # AI分析コード（AI + 英大文字・数字8文字 = 10文字、ユニーク）
    ai_analysis_code = Column(String(10), nullable=False, unique=True)

    # 分析対象の感情レターID（t_emotion_letter.letter_id への外部キー）
    letter_id = Column(
        Integer,
        ForeignKey("t_emotion_letter.letter_id"),
        nullable=False,
    )

    # リスクレベル（1: 低リスク / 2: 中リスク / 3: 高リスク、初期値1）
    risk_level = Column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    # リスク判定の理由・分析コメント
    risk_reason = Column(Text, nullable=True)

    # 分析実行日時
    analyzed_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
