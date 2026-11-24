"""
FastAPI アプリケーションの起動エントリーポイント（main.py）

【このファイルの役割】
- FastAPI アプリケーション本体（app）を生成し、フロントエンド接続用の CORS ミドルウェアを設定する。
- 全機能フォルダ（users, post, purchases, chats, calls, reviews, ai_analysis, points, notifications, ranks）のルーターを登録する。
- サーバーの稼働確認用エンドポイント（/ と /health）を提供する。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai_analysis.router import router as ai_analysis_router
from app.calls.router import router as calls_router
from app.chats.router import router as chats_router
from app.core.config import settings
from app.notifications.router import router as notifications_router
from app.points.router import router as points_router
from app.post.router import router as post_router
from app.purchases.router import router as purchases_router
from app.ranks.router import router as ranks_router
from app.reviews.router import router as reviews_router
from app.users.router import router as users_router

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI(
    title="CtoC Backend API",
    description="こころのメェ～る便 バックエンドAPI",
    version="1.0.0",
)

# フロントエンド（Live Server 5501 等）からのAPI呼び出しを許可する CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 各機能のAPIルーターを登録
app.include_router(users_router)
app.include_router(post_router)
app.include_router(purchases_router)
app.include_router(chats_router)
app.include_router(calls_router)
app.include_router(reviews_router)
app.include_router(ai_analysis_router)
app.include_router(points_router)
app.include_router(notifications_router)
app.include_router(ranks_router)


@app.get("/")
def read_root():
    """ルートURL（/）へのアクセス時にAPI稼働メッセージを返す。"""
    return {
        "message": "CtoC Backend API is running"
    }


@app.get("/health")
def health_check():
    """ヘルスチェック用URL（/health）：サーバーが正常に動作しているか確認する。"""
    return {
        "status": "ok"
    }
