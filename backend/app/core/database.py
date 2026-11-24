"""
本番・開発用データベース接続管理モジュール（app/core/database.py）

【このファイルの役割】
- .env ファイルから MySQL（kokoro_mail）の接続情報を読み込む。
- SQLAlchemy の Engine（接続エンジン）を生成する。
- FastAPI の各エンドポイントで利用する DB セッション（get_db）を提供する。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import Session

# backend/ フォルダとプロジェクトルート（c2c-backend/）のパスを取得
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent


class DatabaseSettings(BaseSettings):
    """データベース接続設定クラス（.envから値を読み込む）"""

    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "kokoro_mail"
    db_user: str
    db_password: str

    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 設定を読み込む
settings = DatabaseSettings()

# SQLAlchemy用のMySQL接続URLを構築（文字コードはutf8mb4）
database_url = URL.create(
    "mysql+pymysql",
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    query={"charset": "utf8mb4"},
)

# DB接続エンジンを作成（pool_pre_ping=Trueで切断された接続を自動検知・再接続）
engine = create_engine(
    database_url,
    pool_pre_ping=True,
)


def check_database_connection():
    """
    データベースへの接続と主要テーブル（m_user, m_profile, m_member_rank）の存在を確認する関数。
    """
    with engine.connect() as connection:
        # 現在接続しているDB名を取得
        name = connection.execute(
            text("SELECT DATABASE()")
        ).scalar_one()

        print(f"接続成功: {name}")

        # 主要な3テーブルが作成済みかどうかを information_schema から確認
        for table in ("m_user", "m_profile", "m_member_rank"):
            count = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = :schema
                      AND table_name = :table
                """),
                {"schema": name, "table": table},
            ).scalar_one()

            print(f"{table}: {'存在' if count else '未作成'}")


def get_db():
    """
    FastAPIのDepends()で使用するDBセッション生成ジェネレータ。
    リクエスト開始時にセッションを開き、リクエスト終了時に自動で閉じる。
    """
    with Session(engine) as db:
        yield db
