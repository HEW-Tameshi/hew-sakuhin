"""
通話機能 DBテーブル定義（ORMモデル）モジュール（app/calls/models.py）

【このファイルの役割】
- SQLAlchemy を用いて、通話履歴テーブル（t_call）をPythonクラスとして定義する。
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from app.users.models import Base


class Call(Base):
    """
    通話履歴テーブル（t_call）
    マッチング（t_matching）に紐づく音声通話・ビデオ通話の開始日時、終了日時、通話時間（秒）を記録する。

    【communication_type の値】
    - 1: 音声通話
    - 2: ビデオ通話
    """

    __tablename__ = "t_call"

    # 主キー（自動採番）
    call_id = Column(Integer, primary_key=True, autoincrement=True)

    # 通話コード（CL + 英大文字・数字8文字 = 10文字、ユニーク）
    call_code = Column(String(10), nullable=False, unique=True)

    # 紐づくマッチングID（t_matching.matching_id への外部キー）
    matching_id = Column(
        Integer,
        ForeignKey("t_matching.matching_id"),
        nullable=False,
    )

    # 通話種別（1: 音声通話 / 2: ビデオ通話）
    communication_type = Column(Integer, nullable=False)

    # 通話開始日時
    started_at = Column(DateTime, nullable=False)

    # 通話終了日時（通話中はNULL）
    ended_at = Column(DateTime, nullable=True)

    # 通話時間（秒単位、通話中はNULL）
    duration = Column(Integer, nullable=True)
