from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """健康检查：服务存活 + 数据库连通。"""
    database = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - 健康检查需捕获所有数据库异常
        database = "error"

    return {
        "status": "ok" if database == "ok" else "degraded",
        "service": "shiguang-agent-backend",
        "database": database,
        "time": datetime.now().isoformat(),
    }
