"""
データベース接続確認用スクリプト（check_db.py）

【このファイルの役割】
- 開発用データベース（kokoro_mail）に正しく接続できるか、
  および基本テーブル（m_user, m_profile, m_member_rank）が存在するかを単体で確認する。
"""

from app.core.database import check_database_connection

if __name__ == "__main__":
    # スクリプトが直接実行された場合にDB接続テストを実行する
    check_database_connection()
