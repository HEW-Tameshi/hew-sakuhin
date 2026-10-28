
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import Session


class DatabaseSettings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "kokoro_mail"
    db_user: str
    db_password: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = DatabaseSettings()

database_url = URL.create(
    "mysql+pymysql",
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    query={"charset": "utf8mb4"},
)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
)


def check_database_connection():
    with engine.connect() as connection:
        name = connection.execute(
            text("SELECT DATABASE()")
        ).scalar_one()

        print(f"接続成功: {name}")

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
    """APIで使用するDBセッションを管理する。"""
    with Session(engine) as db:
        yield db