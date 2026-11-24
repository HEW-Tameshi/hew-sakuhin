"""
会員ランク機能パッケージ（app/ranks）
- schemas.py : ランクマスタ登録・一覧・現在ランク＆次ランク進捗取得のPydanticスキーマ
- service.py : 累計獲得ポイント計算、ランク自動判定・m_profile.delivery_rank_id同期、ランクアップ通知ロジック
- router.py  : /api/ranks 配下のFastAPIエンドポイント定義
※ DBモデル MemberRank（m_member_rank）は app/users/models.py の定義を共有する。
"""
