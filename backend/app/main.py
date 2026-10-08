from fastapi import FastAPI
from .database import Base, engine
from . import models  # noqa: F401
from .routers import health, schools, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="拾光 Agent API", version="0.2.0")

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(schools.router, prefix="/api/v1", tags=["schools"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])


@app.get("/")
def root():
    return {"message": "拾光 Agent backend is running", "version": "0.2.0"}