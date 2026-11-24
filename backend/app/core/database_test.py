"""
テスト専用データベース接続管理モジュール（app/core/database_test.py）

【このファイルの役割】
- .env.test ファイルからテスト用 MySQL（kokoro_mail_test）の接続設定を読み込む。
- 誤って開発用DB（kokoro_mail）のデータを消さないよう、接続先DB名が「kokoro_mail_test」であることを厳密にチェックする。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent


class DatabaseTestSettings(BaseSettings):
    """テスト用データベース接続設定クラス（.env.testから読み込む）"""

    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "kokoro_mail_test"
    db_user: str
    db_password: str

    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env.test", ROOT_DIR / ".env.test"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = DatabaseTestSettings()

# 安全チェック1：設定上のDB名がテスト専用DBでない場合は即座にエラーで停止する
if settings.db_name != "kokoro_mail_test":
    raise RuntimeError("テスト専用DB以外への接続は禁止されています")

database_url = URL.create(
    "mysql+pymysql",
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    query={"charset": "utf8mb4"},
)

# テスト用DBエンジンとセッションファクトリを作成
engine = create_engine(database_url, pool_pre_ping=True)
TestSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def verify_test_database():
    """
    安全チェック2：実際にMySQLへ接続した上で、SELECT DATABASE() の結果が
    「kokoro_mail_test」であることを確認する。
    """
    with engine.connect() as connection:
        current_db = connection.execute(
            text("SELECT DATABASE()")
        ).scalar_one()

        if current_db != "kokoro_mail_test":
            raise RuntimeError(
                f"接続先が想定と異なります: {current_db}"
            )

        print(f"テストDB接続成功: {current_db}")


def get_db():
    """テスト用のDBセッションを提供するジェネレータ。"""
    with Session(engine) as db:
        yield db
