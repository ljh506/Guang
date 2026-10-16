# -*- coding: utf-8 -*-
"""交换匹配 API（Day 9 成员A）。

计划书 Day9 成员A 任务：「完成 Exchange 模型和匹配接口」。
当天验收：A/B 物品互相匹配出现高匹配推荐。

集成成员B Day9 交付 match_engine.py（匹配算法，仅标准库）：
    MatchScore = 0.50×类别/意愿 + 0.30×价格接近 + 0.20×同校
    分级：>=0.75 high / >=0.50 normal / <0.50 low（low 不进推荐列表）
    排序：总分降序 → 价格接近度降序 → 发布时间近者优先；单次最多 20 条

接口：
  POST   /api/v1/exchange/match             匹配推荐（按意愿/价格/同校）
  POST   /api/v1/exchange/accept            确认匹配（落 Exchange 记录 open，供去重）
  GET    /api/v1/exchange/matches           匹配记录列表（Exchange 模型展示）
  POST   /api/v1/exchange/wish              设置商品想换的类别（意愿表达）
  GET    /api/v1/exchange/wish/{goods_id}   查看商品想换的类别

集成适配点（成员A）：
  1. match_engine 导入改为 app.services 内相对导入，复用 Day8 chat_rules 状态机；
  2. 后端查询 Goods 时补充「可交换状态过滤」「已参与未完成交换的商品剔除」，
     并把 open Exchange 的 (user_id, goods_id) 作为 existing_pairs 传给引擎去重；
  3. 返回前为每条推荐附带目标商品名/类别名/标价与目标用户昵称，便于前端展示。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Exchange, Goods, User
from ..schemas import (ExchangeAcceptRequest, ExchangeListOut, ExchangeMatchRequest,
                       ExchangeOut, ExchangeWishRequest, MatchItemOut)
from ..services.category_normalizer import CATEGORY_NAMES as DAY4_CATEGORY_NAMES
from ..services.match_engine import (EXCHANGEABLE_STATUS as ENGINE_EXCHANGEABLE,
                                     match_score, on_match, recommend)

router = APIRouter()

# 可交换商品状态（与 match_engine.EXCHANGEABLE_STATUS 对齐 + 本项目 Goods.status 语义）
EXCHANGEABLE_STATUS = ENGINE_EXCHANGEABLE | {"available"}
EXCHANGE_OPEN_STATUS = "open"


def _to_engine_dict(g: Goods) -> dict:
    """把 Goods ORM 对象转为 match_engine 需要的商品 dict（含展示排序字段）。"""
    return {
        "category_id": g.category,
        "wish_category_id": g.wish_category_id,
        "asking_price": g.asking_price,
        "school_id": g.school_id,
        "status": g.status,
        "goods_id": g.id,
        "user_id": g.user_id,
        "publish_time": g.created_at.timestamp() if g.created_at else 0,
    }


def _match_item_out(item: dict, db: Session) -> MatchItemOut:
    """为推荐条目补充展示字段（目标商品名/类别名/标价/目标用户昵称）。"""
    t = db.get(Goods, item["target_goods_id"])
    u = db.get(User, item["target_user_id"]) if t else None
    return MatchItemOut(
        target_goods_id=item["target_goods_id"],
        target_user_id=item["target_user_id"],
        match_score=item["match_score"],
        score_detail=item["score_detail"],
        weights=item["weights"],
        level=item["level"],
        match_reason=item["match_reason"],
        target_goods_name=t.name if t else None,
        target_category_name=DAY4_CATEGORY_NAMES.get(t.category, t.category) if t else None,
        target_asking_price=t.asking_price if t else None,
        target_user_nickname=u.nickname if u else None,
    )


def _exchange_out(ex: Exchange, db: Session) -> ExchangeOut:
    g = db.get(Goods, ex.goods_id)
    t = db.get(Goods, ex.target_goods_id)
    u = db.get(User, ex.target_user_id)
    return ExchangeOut(
        id=ex.id, goods_id=ex.goods_id, user_id=ex.user_id,
        target_goods_id=ex.target_goods_id, target_user_id=ex.target_user_id,
        match_score=ex.match_score, level=ex.level, status=ex.status,
        goods_name=g.name if g else None,
        target_goods_name=t.name if t else None,
        target_user_nickname=u.nickname if u else None,
        created_at=ex.created_at,
    )


@router.post("/exchange/match")
def match_goods(payload: ExchangeMatchRequest, db: Session = Depends(get_db)):
    """匹配推荐：A 物品对全站可交换商品按 意愿/价格/同校 打分并返回推荐列表。"""
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="user_id 不存在")
    g = db.get(Goods, payload.goods_id)
    if not g:
        raise HTTPException(status_code=404, detail="商品不存在")
    if g.user_id != payload.user_id:
        raise HTTPException(status_code=400, detail="只能对自己发布的商品发起匹配")
    if g.status not in EXCHANGEABLE_STATUS:
        raise HTTPException(status_code=400,
                            detail=f"商品当前状态为 {g.status}，不可参与交换匹配")

    # 候选：全站可交换商品（排除自己）
    candidates = (db.query(Goods)
                  .filter(Goods.status.in_(list(EXCHANGEABLE_STATUS)),
                          Goods.id != g.id)
                  .all())

    # 未完成交换记录：发起方商品去重 + 候选侧剔除
    open_exs = db.query(Exchange).filter(Exchange.status == EXCHANGE_OPEN_STATUS).all()
    open_pairs = [(e.user_id, e.goods_id) for e in open_exs]
    occupied_goods = {e.goods_id for e in open_exs} | {e.target_goods_id for e in open_exs}

    user_goods = _to_engine_dict(g)
    cand_dicts = [_to_engine_dict(c) for c in candidates if c.id not in occupied_goods]
    recs = recommend(user_goods, cand_dicts, existing_pairs=open_pairs)

    return {"success": True, "data": [_match_item_out(r, db) for r in recs]}


@router.post("/exchange/accept", status_code=status.HTTP_201_CREATED)
def accept_match(payload: ExchangeAcceptRequest, db: Session = Depends(get_db)):
    """确认匹配：把推荐落为 Exchange 记录（open），后续同一对商品不再重复推荐。"""
    g = db.get(Goods, payload.goods_id)
    if not g:
        raise HTTPException(status_code=404, detail="商品不存在")
    if g.user_id != payload.user_id:
        raise HTTPException(status_code=400, detail="只能对自己的商品确认匹配")
    t = db.get(Goods, payload.target_goods_id)
    if not t:
        raise HTTPException(status_code=404, detail="目标商品不存在")
    if t.user_id == g.user_id:
        raise HTTPException(status_code=400, detail="不能与自己的商品匹配")
    if g.status not in EXCHANGEABLE_STATUS or t.status not in EXCHANGEABLE_STATUS:
        raise HTTPException(status_code=400, detail="参与交换的商品状态不可交换")

    dup = (db.query(Exchange)
           .filter(Exchange.goods_id == g.id, Exchange.user_id == g.user_id,
                   Exchange.status == EXCHANGE_OPEN_STATUS)
           .first())
    if dup:
        raise HTTPException(status_code=400,
                            detail="该商品已有进行中的交换记录，请先完成或取消")

    m = match_score(_to_engine_dict(g), _to_engine_dict(t))
    if m is None or m["match_score"] < 0.5:
        raise HTTPException(status_code=400,
                            detail="匹配度不足（<0.50），不满足确认交换条件")

    ex = Exchange(goods_id=g.id, user_id=g.user_id,
                  target_goods_id=t.id, target_user_id=t.user_id,
                  match_score=m["match_score"], level=m["level"], status="open")
    db.add(ex)
    db.commit()
    db.refresh(ex)

    # Day8 状态机衔接建议：高匹配且会话在 chatting 时建议流转 matched
    advice = on_match("chatting", m["match_score"])
    return {"success": True, "exchange": _exchange_out(ex, db),
            "state_advice": advice}


@router.get("/exchange/matches", response_model=ExchangeListOut)
def list_exchanges(user_id: int,
                   status_: str | None = Query(None, alias="status"),
                   page: int = Query(1, ge=1),
                   page_size: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db)):
    """我发起的交换匹配记录列表（Exchange 模型展示）。"""
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="用户不存在")
    q = db.query(Exchange).filter(Exchange.user_id == user_id)
    if status_ is not None:
        q = q.filter(Exchange.status == status_)
    total = q.count()
    items = (q.order_by(Exchange.created_at.desc(), Exchange.id.desc())
              .offset((page - 1) * page_size).limit(page_size).all())
    return ExchangeListOut(total=total, page=page, page_size=page_size,
                           items=[_exchange_out(e, db) for e in items])


@router.post("/exchange/wish")
def set_goods_wish(payload: ExchangeWishRequest, db: Session = Depends(get_db)):
    """意愿表达：设置商品「想换什么」类别（只能设置自己的商品）。"""
    g = db.get(Goods, payload.goods_id)
    if not g:
        raise HTTPException(status_code=404, detail="商品不存在")
    if g.user_id != payload.user_id:
        raise HTTPException(status_code=400, detail="只能设置自己商品的意愿")
    if not payload.wish_category_id:
        raise HTTPException(status_code=400, detail="wish_category_id 不能为空")
    if payload.wish_category_id not in DAY4_CATEGORY_NAMES:
        raise HTTPException(status_code=400,
                            detail="wish_category_id 非法（Day4 十类之一）")

    g.wish_category_id = payload.wish_category_id
    db.commit()
    db.refresh(g)
    return {"success": True, "goods_id": g.id,
            "wish_category_id": g.wish_category_id}


@router.get("/exchange/wish/{goods_id}")
def get_goods_wish(goods_id: int, db: Session = Depends(get_db)):
    """查看商品当前想换的类别。"""
    g = db.get(Goods, goods_id)
    if not g:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {"success": True, "goods_id": g.id,
            "wish_category_id": g.wish_category_id}
