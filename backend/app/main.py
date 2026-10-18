from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from . import models  # noqa: F401
from .routers import chat, estimate, exchange, goods, health, recognize, schools, users, wants

Base.metadata.create_all(bind=engine)

app = FastAPI(title="拾光 Agent API", version="1.2.0")

# CORS：放开跨域，方便前端在浏览器/微信开发者工具中调试
# 联调阶段全放开；正式上线前需收敛为具体 origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(schools.router, prefix="/api/v1", tags=["schools"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(goods.router, prefix="/api/v1", tags=["goods"])
app.include_router(recognize.router, prefix="/api/v1", tags=["recognize"])
app.include_router(estimate.router, prefix="/api/v1", tags=["estimate"])
app.include_router(wants.router, prefix="/api/v1", tags=["wants"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(exchange.router, prefix="/api/v1", tags=["exchange"])


@app.get("/")
def root():
    return {"message": "拾光 Agent backend is running", "version": "1.2.0"}