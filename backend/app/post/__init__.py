"""
出品機能パッケージ（app/post）
- models.py  : 感情カテゴリ（m_emotion_category）・感情レター（t_emotion_letter）のDBモデル定義
- schemas.py : 出品登録時の入出力データ検証（Pydanticスキーマ）
- service.py : 出品登録のビジネスロジック・トランザクション管理
- router.py  : /api/posts 配下のFastAPIエンドポイント定義
"""
