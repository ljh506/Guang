# -*- coding: utf-8 -*-
"""收藏/想要请求 API（Day 7 成员A）。

计划书 Day7 成员A 任务：「完成收藏/想要请求 API 和状态字段」。
当天验收：用户A发布 → 用户B浏览 → 点击我想要 → 产生请求。

接口：
  POST   /api/v1/goods/{goods_id}/want    发起想要请求（初始状态 pending）
  GET    /api/v1/goods/{goods_id}/wants   商品收到的想要请求列表（卖家视角）
  GET    /api/v1/users/{user_id}/wants    我发出的想要请求（「我想要的」列表）
  PATCH  /api/v1/wants/{want_id}          更新请求状态（pending/accepted/rejected/cancelled）

状态字段语义：
  pending   已提交（默认）
  accepted  卖家接受 → 商品状态 available -> reserved（被保留）
  rejected  卖家拒绝（终态）
  cancelled 买家取消（终态）
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Goods, User, Want
from ..schemas import WantCreate, WantListOut, WantOut, WantStatusUpdate

router = APIRouter()

WANT_STATUSES = {"pending", "accepted", "rejected", "cancelled"}
FINAL_STATUSES = {"rejected", "cancelled"}   # 终态：不可再变更
GOODS_ACCEPTABLE = {"available"}             # 仅可售/可交换商品可被接受保留


def _want_to_out(w: Want, db: Session) -> WantOut:
    g = db.get(Goods, w.goods_id)
    requester = db.get(User, w.requester_id)
    return WantOut(
        id=w.id, goods_id=w.goods_id, requester_id=w.requester_id,
        status=w.status, message=w.message,
        goods_name=g.name if g else None,
        requester_nickname=requester.nickname if requester else None,
        created_at=w.created_at, updated_at=w.updated_at,
    )


@router.post("/goods/{goods_id}/want", status_code=status.HTTP_201_CREATED)
def create_want(goods_id: int, payload: WantCreate, db: Session = Depends(get_db)):
    """用户点击「我想要」：对指定商品发起想要请求（状态 pending）。"""
    g = db.get(Goods, goods_id)
    if not g:
        raise HTTPException(status_code=404, detail="商品不存在")
    if g.status == "removed":
        raise HTTPException(status_code=400, detail="商品已下架，无法发起想要")
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=400, detail="user_id 不存在")
    if g.user_id == payload.user_id:
        raise HTTPException(status_code=400, detail="不能对自己的商品发起想要")

    dup = (db.query(Want)
           .filter(Want.goods_id == goods_id,
                   Want.requester_id == payload.user_id,
                   Want.status == "pending")
           .first())
    if dup:
        raise HTTPException(status_code=400, detail="已提交过想要请求，请勿重复发起")

    want = Want(goods_id=goods_id, requester_id=payload.user_id,
                status="pending", message=payload.message)
    db.add(want)
    db.commit()
    db.refresh(want)
    return {"want": _want_to_out(want, db)}


@router.get("/goods/{goods_id}/wants", response_model=WantListOut)
def list_goods_wants(goods_id: int,
                     status_: str | None = Query(None, alias="status"),
                     page: int = Query(1, ge=1),
                     page_size: int = Query(20, ge=1, le=100),
                     db: Session = Depends(get_db)):
    """商品收到的想要请求列表（卖家查看请求者）。"""
    if not db.get(Goods, goods_id):
        raise HTTPException(status_code=404, detail="商品不存在")
    q = db.query(Want).filter(Want.goods_id == goods_id)
    if status_ is not None:
        if status_ not in WANT_STATUSES:
            raise HTTPException(
                status_code=400,
                detail="status 非法（pending/accepted/rejected/cancelled）")
        q = q.filter(Want.status == status_)
    total = q.count()
    items = (q.order_by(Want.created_at.desc(), Want.id.desc())
              .offset((page - 1) * page_size).limit(page_size).all())
    return WantListOut(total=total, page=page, page_size=page_size,
                       items=[_want_to_out(w, db) for w in items])


@router.get("/users/{user_id}/wants", response_model=WantListOut)
def list_user_wants(user_id: int, db: Session = Depends(get_db)):
    """我发出的想要请求（「我想要的」列表，含商品名）。"""
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="用户不存在")
    items = (db.query(Want).filter(Want.requester_id == user_id)
             .order_by(Want.created_at.desc(), Want.id.desc()).all())
    return WantListOut(total=len(items), page=1, page_size=100,
                       items=[_want_to_out(w, db) for w in items])


@router.patch("/wants/{want_id}")
def update_want_status(want_id: int, payload: WantStatusUpdate,
                       db: Session = Depends(get_db)):
    """更新想要请求状态（卖家接受/拒绝；买家取消）。"""
    want = db.get(Want, want_id)
    if not want:
        raise HTTPException(status_code=404, detail="想要请求不存在")
    if payload.status not in WANT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="status 非法（pending/accepted/rejected/cancelled）")
    if want.status in FINAL_STATUSES:
        raise HTTPException(status_code=400,
                            detail=f"请求已处于终态（{want.status}），无法变更")
    if want.status == "accepted" and payload.status == "accepted":
        raise HTTPException(status_code=400, detail="请求已接受，不可重复接受")
    if want.status == "accepted" and payload.status == "rejected":
        raise HTTPException(status_code=400,
                            detail="请求已接受，仅可取消（cancelled）或保持")

    if payload.status == "accepted":
        g = db.get(Goods, want.goods_id)
        if not g:
            raise HTTPException(status_code=400, detail="商品不存在")
        if g.status not in GOODS_ACCEPTABLE:
            raise HTTPException(status_code=400,
                                detail=f"商品当前状态为 {g.status}，无法接受想要请求")
        # 商品状态流转：available -> reserved（被想要方保留）
        g.status = "reserved"
    want.status = payload.status
    db.commit()
    db.refresh(want)
    return {"want": _want_to_out(want, db)}
