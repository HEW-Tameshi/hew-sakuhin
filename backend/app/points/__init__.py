"""
ポイント・決済・サブスクリプション機能パッケージ（app/points）
- models.py  : サブスク（t_subscription）・決済（t_payment）・ポイント履歴（t_point_history）のDBモデル定義
- schemas.py : ポイントチャージ・残高取得・履歴一覧・サブスク登録/解約のPydanticスキーマ
- service.py : 残高集計・ポイントチャージ・サブスク管理・他機能向けポイント履歴記録ロジック
- router.py  : /api/points 配下のFastAPIエンドポイント定義
"""
