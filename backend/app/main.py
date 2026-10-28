
from fastapi import FastAPI
from app.routers import users

app = FastAPI(
    title="CtoC API",
    description="感情CtoCプラットフォームのAPI",
    version="1.0.0",
)

app.include_router(users.router)


@app.get("/")
def read_root():
    return {"message": "CtoC API is running"}
