# -*- coding: utf-8 -*-
"""Goods 发布/列表/详情 API（Day 4）。"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Goods, School, User
from ..schemas import (GoodsCreate, GoodsListOut, GoodsOut, GoodsUpdate)
from ..services.category_normalizer import (CATEGORY_IDS as DAY4_CATEGORIES,
                                            CATEGORY_NAMES as DAY4_CATEGORY_NAMES,
                                            to_engine_category)
from ..services.estimate_params import EstimateParams
from ..services.price_engine import estimate_price, validate_asking_price

router = APIRouter()

TRADE_TYPES = {"sell", "free", "exchange"}
GOODS_STATUSES = {"available", "reserved", "exchanged", "removed"}


def _goods_to_out(g: Goods) -> GoodsOut:
    return GoodsOut(
        id=g.id, user_id=g.user_id, school_id=g.school_id,
        name=g.name, category=g.category,
        category_name=DAY4_CATEGORY_NAMES.get(g.category, g.category),
        description=g.description, image=g.image,
        original_price=g.original_price,
        estimated_min=g.estimated_min, estimated_max=g.estimated_max,
        reason_text=g.reason_text, asking_price=g.asking_price,
        condition=g.condition, trade_type=g.trade_type, status=g.status,
        created_at=g.created_at,
    )


def _compute_estimate(category: str, condition: str, original_price: float,
                      trade_type: str, months_used: int | None):
    """调用 Day2 估价引擎（经 Day4 类别映射），返回 (est_dict, engine_category)。"""
    engine_cat = to_engine_category(category)
    est = estimate_price(engine_cat, condition, original_price,
                         is_free=(trade_type == "free"),
                         device_age_months=months_used)
    return est, engine_cat


@router.get("/goods/categories")
def list_categories():
    """Day4 统一类别体系（10 个），供前端发布页类别选择器使用。"""
    return [{"category_id": cid, "category_name": DAY4_CATEGORY_NAMES[cid]}
            for cid in DAY4_CATEGORIES]


@router.get("/goods", response_model=GoodsListOut)
def list_goods(
    school_id: int | None = None,
    category: str | None = None,
    status_: str | None = Query(None, alias="status"),
    trade_type: str | None = None,
    user_id: int | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """商品列表（漂流墙）：支持按学校/类别/状态/交易方式/发布者过滤 + 分页。"""
    q = db.query(Goods)
    if school_id is not None:
        q = q.filter(Goods.school_id == school_id)
    if category is not None:
        q = q.filter(Goods.category == category)
    if status_ is not None:
        q = q.filter(Goods.status == status_)
    if trade_type is not None:
        q = q.filter(Goods.trade_type == trade_type)
    if user_id is not None:
        q = q.filter(Goods.user_id == user_id)
    if keyword:
        q = q.filter(Goods.name.contains(keyword))

    total = q.count()
    items = (q.order_by(Goods.created_at.desc(), Goods.id.desc())
              .offset((page - 1) * page_size)
              .limit(page_size).all())
    return GoodsListOut(total=total, page=page, page_size=page_size,
                        items=[_goods_to_out(g) for g in items])


@router.get("/goods/{goods_id}", response_model=GoodsOut)
def get_goods(goods_id: int, db: Session = Depends(get_db)):
    """商品详情。"""
    g = db.get(Goods, goods_id)
    if not g:
        raise HTTPException(status_code=404, detail="商品不存在")
    return _goods_to_out(g)


@router.post("/goods", status_code=status.HTTP_201_CREATED)
def create_goods(payload: GoodsCreate, db: Session = Depends(get_db)):
    """
    发布商品（Day4 核心）。

    流程：Day4 类别 → EstimateParams 校验 → Day2 估价引擎生成建议区间 → 落库。
    返回 goods + price_tip（标价偏离建议区间时的提示，不阻断）。
    """
    # 1) 用户存在性
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="user_id 不存在")

    # 2) 学校：默认取用户学校，可显式覆盖
    school_id = payload.school_id or user.school_id
    if school_id is None:
        raise HTTPException(status_code=400, detail="用户未选择学校，请先选校")
    if not db.get(School, school_id):
        raise HTTPException(status_code=400, detail="school_id 不存在")

    # 3) 交易方式
    if payload.trade_type not in TRADE_TYPES:
        raise HTTPException(status_code=400,
                            detail="trade_type 非法，可选 sell/free/exchange")

    # 4) 参数校验（成员B Day4：多错误累积返回）
    params = EstimateParams(
        category=payload.category,
        condition=payload.condition,
        original_price=payload.original_price,
        asking_price=payload.asking_price,
        months_used=payload.months_used,
    )
    v = params.validate()
    if not v["valid"]:
        raise HTTPException(status_code=422, detail={"errors": v["errors"]})

    # 5) 估价（Day2 引擎 + Day4 类别映射）
    est, _ = _compute_estimate(payload.category, payload.condition,
                               payload.original_price, payload.trade_type,
                               payload.months_used)
    if "error" in est:
        raise HTTPException(status_code=422,
                            detail={"errors": [est["error"]]})

    goods = Goods(
        user_id=payload.user_id,
        school_id=school_id,
        name=payload.name,
        category=payload.category,
        description=payload.description,
        image=payload.image,
        original_price=payload.original_price,
        estimated_min=est["estimated_min"],
        estimated_max=est["estimated_max"],
        reason_text=est["reason_text"],
        asking_price=payload.asking_price,
        condition=payload.condition,
        trade_type=payload.trade_type,
        status="available",
    )
    db.add(goods)
    db.commit()
    db.refresh(goods)

    price_tip = validate_asking_price(payload.asking_price,
                                      est["estimated_min"],
                                      est["estimated_max"])
    return {"goods": _goods_to_out(goods), "price_tip": price_tip,
            "estimate": {"estimated_min": est["estimated_min"],
                         "estimated_max": est["estimated_max"],
                         "reason_text": est["reason_text"]}}


@router.patch("/goods/{goods_id}", response_model=GoodsOut)
def update_goods(goods_id: int, payload: GoodsUpdate,
                 db: Session = Depends(get_db)):
    """更新商品（若改了类别/品相/原价/交易方式，自动重算建议估价）。"""
    g = db.get(Goods, goods_id)
    if not g:
        raise HTTPException(status_code=404, detail="商品不存在")

    data = payload.model_dump(exclude_unset=True)

    if "category" in data and data["category"] is not None:
        if data["category"] not in DAY4_CATEGORIES:
            raise HTTPException(status_code=400, detail="category 非法（Day4 十类之一）")
    if "trade_type" in data and data["trade_type"] is not None:
        if data["trade_type"] not in TRADE_TYPES:
            raise HTTPException(status_code=400, detail="trade_type 非法")
    if "status" in data and data["status"] is not None:
        if data["status"] not in GOODS_STATUSES:
            raise HTTPException(status_code=400,
                                detail="status 非法（available/reserved/exchanged/removed）")

    for k, v in data.items():
        setattr(g, k, v)

    # 触发重估价的字段
    if {"category", "condition", "original_price", "trade_type"} & set(data):
        est, _ = _compute_estimate(g.category, g.condition, g.original_price,
                                   g.trade_type, None)
        if "error" not in est:
            g.estimated_min = est["estimated_min"]
            g.estimated_max = est["estimated_max"]
            g.reason_text = est["reason_text"]

    db.commit()
    db.refresh(g)
    return _goods_to_out(g)


@router.delete("/goods/{goods_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goods(goods_id: int, db: Session = Depends(get_db)):
    """删除商品。"""
    g = db.get(Goods, goods_id)
    if not g:
        raise HTTPException(status_code=404, detail="商品不存在")
    db.delete(g)
    db.commit()
