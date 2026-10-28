
from fastapi import FastAPI
from app.routers.users import router as users_router

app = FastAPI(
    title="CtoC Backend API",
    description="CtoCサイトのバックエンドAPI",
    version="1.0.0",
)

# 会員登録APIを登録
app.include_router(users_router)


@app.get("/")
def read_root():
    return {
        "message": "CtoC Backend API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }