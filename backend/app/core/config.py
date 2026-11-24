"""
アプリケーション設定管理モジュール（app/core/config.py）

【このファイルの役割】
- .env ファイルから JWT（アクセストークン）設定、Google OAuth クライアントID、
  Gemini API キー・モデル名、および CORS 許可オリジン一覧を読み込む。
- pydantic-settings を使用して、環境変数の型チェックや初期値設定を自動で行う。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ フォルダとプロジェクトルート（c2c-backend/）のパスを取得
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """アプリケーション全体で使用する設定クラス"""

    # JWTの署名に使う秘密鍵（.envのJWT_SECRET_KEYから読み込む必須項目）
    jwt_secret_key: str

    # JWTアクセストークンの有効期限（分単位、デフォルトは30分）
    jwt_expire_minutes: int = 30

    # Google認証（Google Identity Services）のクライアントID（任意）
    google_client_id: str | None = None

    # AI分析機能で使用する Gemini API キー（.envのGEMINI_API_KEYから読み込む）
    gemini_api_key: str | None = None

    # 使用する Gemini モデル名（デフォルト: gemini-4-hydrogen）
    gemini_model: str = "gemini-4-hydrogen"

    # CORS で許可するフロントエンドのオリジン一覧（カンマ区切り、VS Code Live Server 5501/5500 等を標準許可）
    cors_origins: str = (
        "http://127.0.0.1:5501,"
        "http://localhost:5501,"
        "http://127.0.0.1:5500,"
        "http://localhost:5500,"
        "http://127.0.0.1:3000,"
        "http://localhost:3000"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """カンマ区切りの cors_origins を配列に変換して返す。"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # .envファイルの読み込み設定（backend/.env または c2c-backend/.env を参照）
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",  # DB接続設定など、このクラスに定義されていない変数は無視する
    )


# 設定インスタンスを生成（他ファイルから settings.xxx として参照する）
settings = Settings()
