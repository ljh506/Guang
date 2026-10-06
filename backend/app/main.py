from fastapi import FastAPI
from .database import Base, engine
from . import models  # noqa: F401
from .routers import health

Base.metadata.create_all(bind=engine)

app = FastAPI(title="拾光 Agent API", version="0.1.0")

app.include_router(health.router, prefix="/api/v1", tags=["health"])


@app.get("/")
def root():
    return {"message": "拾光 Agent backend is running"}