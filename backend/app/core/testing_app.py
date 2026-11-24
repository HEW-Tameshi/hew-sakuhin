"""
テスト環境用 FastAPI アプリケーション定義（app/core/testing_app.py）

【このファイルの役割】
- テスト用DB（kokoro_mail_test）に接続先を切り替えた状態で FastAPI アプリを起動できるようにする。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai_analysis import router as ai_analysis_router
from app.calls import router as calls_router
from app.chats import router as chats_router
from app.core.config import settings
from app.core.database import get_db as production_get_db
from app.core.database_test import get_db as test_get_db
from app.core.database_test import verify_test_database
from app.notifications import router as notifications_router
from app.points import router as points_router
from app.post import router as post_router
from app.purchases import router as purchases_router
from app.ranks import router as ranks_router
from app.reviews import router as reviews_router
from app.users import router as users_router

# 起動時にテストDB（kokoro_mail_test）への接続を検証する
verify_test_database()

app = FastAPI(
    title="CtoC API（テスト環境）",
    description="テストDBを使用するAPI",
    version="1.0.0",
)

# フロントエンドテスト接続用の CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 本番用の get_db をテスト用の test_get_db に差し替える（Dependency Override）
app.dependency_overrides[production_get_db] = test_get_db

# 全機能のルーターを登録
app.include_router(users_router.router)
app.include_router(post_router.router)
app.include_router(purchases_router.router)
app.include_router(chats_router.router)
app.include_router(calls_router.router)
app.include_router(reviews_router.router)
app.include_router(ai_analysis_router.router)
app.include_router(points_router.router)
app.include_router(notifications_router.router)
app.include_router(ranks_router.router)


@app.get("/")
def read_root():
    return {"message": "CtoC API test environment is running"}
