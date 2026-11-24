"""
購入・取引機能パッケージ（app/purchases）
- models.py  : レター購入履歴（t_letter_purchase）・取引マッチング（t_matching）のDBモデル定義
- schemas.py : レター購入・購入履歴取得の入出力データ検証（Pydanticスキーマ）
- service.py : レター購入トランザクション・購入履歴取得のビジネスロジック
- router.py  : /api/purchases 配下のFastAPIエンドポイント定義
"""
