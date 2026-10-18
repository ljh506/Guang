# -*- coding: utf-8 -*-
"""Day13 成员A：演示数据种子脚本（衔接后端 FastAPI + SQLite）。

任务来源：计划书 Day 13 行「比赛Demo数据」，成员A 当日任务：
把成员B Day13 交付的演示数据（7 校 / 5 用户 / 20 商品 / 3 交换 / 聊天记录）
幂等写入后端 shiguang.db，使比赛演示时 API 可直接查询演示数据。

设计：
- 复用成员B `demo_data.py` 的常量（脚本目录内副本，DAY3 CSV 不可用时走内置回退）。
- **固定 id 契约**：演示学校/用户/商品使用演示常量自带的固定 id
  （学校 1-7、用户 1-5、商品 1-20），与 Day3 种子数据（学校 id=1..7、
  Demo 用户 id=1..5）保持一致，保证 Day3/Day4 验收脚本的固定 id 引用有效。
- 商品状态映射：成员B on_sale -> 后端 available（后端状态集 available/reserved/exchanged/removed）。
- 估价落库：逐商品调用后端 price_engine.estimate_price 生成建议区间（演示「估价」能力）。
- 匹配落库：逐组交换调用后端 match_engine.match_score 计算匹配度与分级（衔接 Day9）。
- 幂等：先清除既有演示种子（按固定 id + 名称双重标识），再重建，可重复运行。

运行：cd backend && python scripts/seed_demo.py
依赖：后端环境（Anaconda shiguang）+ 仅标准库。
"""
import datetime
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (BACKEND_DIR, SCRIPT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from demo_data import (  # noqa: E402
    FALLBACK_SCHOOLS, FALLBACK_USERS, DEMO_GOODS,
    DEMO_WISHES, DEMO_EXCHANGES, DEMO_CHATS,
)
from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402
from app.services.price_engine import estimate_price  # noqa: E402
from app.services.match_engine import match_score  # noqa: E402

# 演示状态 -> 后端状态
STATUS_MAP = {"on_sale": "available"}

# 固定 id 契约（与 Day3 种子 / 演示常量一致）
SCHOOL_FIXED_IDS = {s["name"]: i + 1 for i, s in enumerate(FALLBACK_SCHOOLS)}
USER_FIXED_IDS = {u["nickname"]: i + 1 for i, u in enumerate(FALLBACK_USERS)}
GOODS_FIXED_IDS = {g[2]: g[0] for g in DEMO_GOODS}  # name -> gid


def parse_dt(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def clear_demo(db):
    """清除既有演示种子（按名称标识 + 固定 id 兜底），保证幂等。"""
    school_names = {s["name"] for s in FALLBACK_SCHOOLS}
    user_nicks = {u["nickname"] for u in FALLBACK_USERS}

    # 1) 名称命中（含历史漂移实体）
    school_ids = [r.id for r in db.query(models.School)
                  .filter(models.School.name.in_(school_names)).all()]
    user_ids = [r.id for r in db.query(models.User)
                .filter(models.User.nickname.in_(user_nicks)).all()]
    # 2) 固定 id 兜底（防止名称被改名后残留）
    for sid in set(SCHOOL_FIXED_IDS.values()):
        if sid not in school_ids and db.query(models.School).get(sid):
            school_ids.append(sid)
    for uid in set(USER_FIXED_IDS.values()):
        if uid not in user_ids and db.query(models.User).get(uid):
            user_ids.append(uid)

    # 3) 商品：演示用户发布的 + 演示固定 gid（1..20）
    goods_ids = []
    if user_ids:
        goods_ids += [g.id for g in db.query(models.Goods)
                      .filter(models.Goods.user_id.in_(user_ids)).all()]
    for gid in sorted(GOODS_FIXED_IDS.values()):
        g = db.query(models.Goods).get(gid)
        if g and g.id not in goods_ids:
            goods_ids.append(g.id)

    # 逆依赖序删除：消息 -> 会话 -> 交换 -> 想要 -> 商品 -> 用户 -> 学校
    if goods_ids:
        conv_ids = [c.id for c in db.query(models.Conversation)
                    .filter(models.Conversation.goods_id.in_(goods_ids)).all()]
        if conv_ids:
            db.query(models.Message).filter(
                models.Message.conversation_id.in_(conv_ids)).delete(
                synchronize_session=False)
        db.query(models.Conversation).filter(
            models.Conversation.goods_id.in_(goods_ids)).delete(
            synchronize_session=False)
        db.query(models.Exchange).filter(
            (models.Exchange.goods_id.in_(goods_ids))
            | (models.Exchange.target_goods_id.in_(goods_ids))).delete(
            synchronize_session=False)
        db.query(models.Want).filter(
            models.Want.goods_id.in_(goods_ids)).delete(
            synchronize_session=False)
        db.query(models.Goods).filter(
            models.Goods.id.in_(goods_ids)).delete(
            synchronize_session=False)
    if user_ids:
        db.query(models.User).filter(models.User.id.in_(user_ids)).delete(
            synchronize_session=False)
    if school_ids:
        db.query(models.School).filter(models.School.id.in_(school_ids)).delete(
            synchronize_session=False)
    db.commit()


def seed(db):
    # 1) 学校（显式固定 id 1..7，与 Day3 种子一致）
    for i, s in enumerate(FALLBACK_SCHOOLS):
        obj = models.School(id=i + 1, name=s["name"],
                            latitude=s["latitude"], longitude=s["longitude"])
        db.add(obj)
        db.flush()

    # 2) 用户（显式固定 id 1..5，school_id 直接引用固定 id）
    for i, u in enumerate(FALLBACK_USERS):
        obj = models.User(id=i + 1, nickname=u["nickname"], avatar=u["avatar"],
                          school_id=u["school_id"])
        db.add(obj)
        db.flush()

    # 3) 商品（20 个：gid 显式固定 1..20 + 估价落库 + 状态映射）
    goods_by_gid = {}
    for g in DEMO_GOODS:
        gid, uid, name, category, condition, original_price, months_used, \
            is_free, asking_price, status, pub_min, desc = g
        user = models.User(id=uid)  # 仅用于取 school_id
        del user
        est = estimate_price(category, condition, original_price,
                             months_used=months_used, is_free=bool(is_free))
        if "error" in est:
            est = {"estimated_min": None, "estimated_max": None,
                   "reason_text": "估价暂不可用"}
        obj = models.Goods(
            id=gid, user_id=uid,
            school_id=USER_FIXED_IDS[FALLBACK_USERS[uid - 1]["nickname"]]
                     and FALLBACK_USERS[uid - 1]["school_id"],
            name=name, category=category, description=desc,
            original_price=original_price,
            estimated_min=est.get("estimated_min"),
            estimated_max=est.get("estimated_max"),
            reason_text=est.get("reason_text"),
            asking_price=asking_price,
            wish_category_id=(DEMO_WISHES.get(uid) or [None])[0],
            condition=condition, trade_type="sell",
            status=STATUS_MAP.get(status, status),
        )
        db.add(obj)
        db.flush()
        goods_by_gid[gid] = obj

    # 4) 交换（3 组：match_score 计算落库 + 状态映射）
    exch_by_eid = {}
    for ex in DEMO_EXCHANGES:
        ga = goods_by_gid[ex["goods_a_id"]]
        gb = goods_by_gid[ex["goods_b_id"]]
        user_a = models.User(id=ex["user_a_id"])
        user_b = models.User(id=ex["user_b_id"])
        m = match_score(
            {"category_id": ga.category,
             "wish_category_id": ga.wish_category_id,
             "asking_price": ga.asking_price, "school_id": ga.school_id,
             "status": ga.status},
            {"category_id": gb.category,
             "wish_category_id": gb.wish_category_id,
             "asking_price": gb.asking_price, "school_id": gb.school_id,
             "status": gb.status},
        )
        score = m["match_score"] if m else 0.5
        level = m["level"] if m else "normal"
        obj = models.Exchange(
            goods_id=ga.id, user_id=ex["user_a_id"],
            target_goods_id=gb.id, target_user_id=ex["user_b_id"],
            match_score=score, level=level,
            status="confirmed" if ex["state"] == "confirmed" else "open",
            confirm_a=ex["confirm_a"], confirm_b=ex["confirm_b"],
        )
        db.add(obj)
        db.flush()
        exch_by_eid[ex["id"]] = obj

    # 5) 会话（3 组交换各 1 条，衔接 Day8 状态机）
    convs_by_eid = {}
    for ex in DEMO_EXCHANGES:
        ga = goods_by_gid[ex["goods_a_id"]]
        conv = models.Conversation(
            goods_id=ga.id, want_id=None,
            buyer_id=ex["user_b_id"], seller_id=ex["user_a_id"],
            trade_state="negotiating" if ex["state"] == "negotiating" else "confirmed",
        )
        db.add(conv)
        db.flush()
        convs_by_eid[ex["id"]] = conv.id

    # 6) 消息（聊天记录落库，会话归属交换）
    for ex_id, sender, receiver, key, text, created in DEMO_CHATS:
        db.add(models.Message(
            conversation_id=convs_by_eid[ex_id],
            sender_id=sender,
            content=text, is_read=1, created_at=parse_dt(created)))

    # 7) 想要请求（EX1 演示链路：买家 user_b 想要 商品 goods_a）
    ex1 = DEMO_EXCHANGES[0]
    db.add(models.Want(goods_id=goods_by_gid[ex1["goods_a_id"]].id,
                       requester_id=ex1["user_b_id"],
                       status="accepted", message="你好，我想要这个，还在吗？"))

    db.commit()

    # 8) 汇报
    print("演示数据已写入后端 shiguang.db：")
    print("  schools  = %d" % db.query(models.School).count())
    print("  users    = %d" % db.query(models.User).count())
    print("  goods    = %d" % db.query(models.Goods).count())
    print("  wants    = %d" % db.query(models.Want).count())
    print("  convs    = %d" % db.query(models.Conversation).count())
    print("  msgs     = %d" % db.query(models.Message).count())
    print("  exchanges= %d" % db.query(models.Exchange).count())
    for ex in DEMO_EXCHANGES:
        e = exch_by_eid[ex["id"]]
        print("  EX%d: match_score=%.3f level=%s status=%s confirm_a/b=%d/%d"
              % (ex["id"], e.match_score, e.level, e.status, e.confirm_a, e.confirm_b))


if __name__ == "__main__":
    db = SessionLocal()
    try:
        clear_demo(db)
        seed(db)
    finally:
        db.close()
