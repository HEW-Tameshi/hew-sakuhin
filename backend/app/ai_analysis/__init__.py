"""
AI分析機能パッケージ（app/ai_analysis）
- models.py  : AI分析結果（t_ai_analysis）のDBモデル定義
- schemas.py : レターリスク分析・会話コミュニケーション分析の出力データ定義（Pydanticスキーマ）
- service.py : Gemini API を使ったレターリスク分析（DB保存）および会話AIまとめ・スコア分析ロジック
- router.py  : /api/ai 配下のFastAPIエンドポイント定義
"""
