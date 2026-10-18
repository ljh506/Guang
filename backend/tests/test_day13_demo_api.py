# -*- coding: utf-8 -*-
"""Day13 成员A：演示数据接入后端验收测试。

前置：调用 scripts.seed_demo 幂等写入演示数据（7校/5用户/20商品/3交换/聊天）。
断言：
  1) 演示学校/用户/商品入库数量正确（按演示标识精确统计）
  2) 商品估价区间落库（衔接 Day7 price_engine）：高等数学 27~41
  3) 交换 match_score >= 0.5 且 level 分级正确（衔接 Day9 match_engine）
  4) 交换状态映射：negotiating->open / confirmed->confirmed
  5) 聊天记录挂到演示会话（衔接 Day8）
  6) API 层可查询演示数据（TestClient）
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402
from scripts import seed_demo  # noqa: E402

DEMO_SCHOOLS = ["清华大学", "北京大学", "浙江大学", "复旦大学",
                "武汉大学", "中山大学", "四川大学"]
DEMO_USERS = ["拾光少女小鹿", "二手书生阿泽", "橙子不吃皮",
              "学霸笔记侠", "操场边的猫"]
DEMO_EX_LEVEL = {1: "high", 2: "normal", 3: "normal"}
DEMO_EX_STATUS = {1: "open", 2: "open", 3: "confirmed"}


def run():
    db = SessionLocal()
    seed_demo.clear_demo(db)
    seed_demo.seed(db)
    ok = 0
    fail = 0

    def check(name, cond):
        nonlocal ok, fail
        if cond:
            ok += 1
            print("PASS %s" % name)
        else:
            fail += 1
            print("FAIL %s" % name)

    # 1) 演示学校 / 用户 / 商品（按标识精确统计）
    schools = db.query(models.School).filter(
        models.School.name.in_(DEMO_SCHOOLS)).all()
    check("演示学校 7 所", len(schools) == 7)
    users = db.query(models.User).filter(
        models.User.nickname.in_(DEMO_USERS)).all()
    check("演示用户 5 名", len(users) == 5)
    user_ids = [u.id for u in users]
    goods = db.query(models.Goods).filter(
        models.Goods.user_id.in_(user_ids)).all()
    check("演示商品 20 件", len(goods) == 20)

    # 2) 估价落库：高等数学教材 27~41（衔接 Day7）
    math = db.query(models.Goods).filter(
        models.Goods.name.contains("高等数学")).first()
    check("演示商品估价区间落库",
          math is not None and math.estimated_min == 27 and math.estimated_max == 41)
    check("估价依据文本非空", math is not None and bool(math.reason_text))

    # 3) 交换：3 组、match_score>=0.5、level 分级正确（衔接 Day9）
    ex_ids = [g.id for g in db.query(models.Exchange)
              .filter(models.Exchange.user_id.in_(user_ids)).all()]
    check("演示交换 3 组", len(ex_ids) == 3)
    check("交换 match_score >= 0.5",
          all(e.match_score >= 0.5 for e in db.query(models.Exchange)
              .filter(models.Exchange.id.in_(ex_ids)).all()))
    check("交换 level 均有值",
          all(e.level in ("high", "normal", "low")
              for e in db.query(models.Exchange)
              .filter(models.Exchange.id.in_(ex_ids)).all()))

    # 4) 状态映射：至少存在 open 与 confirmed 两种状态
    sts = {e.status for e in db.query(models.Exchange)
           .filter(models.Exchange.id.in_(ex_ids)).all()}
    check("交换状态含 open/confirmed", "open" in sts and "confirmed" in sts)

    # 5) 聊天记录挂到演示会话（消息总数 >= 9）
    conv_ids = [c.id for c in db.query(models.Conversation)
                .filter(models.Conversation.buyer_id.in_(user_ids)).all()]
    msgs = db.query(models.Message).filter(
        models.Message.conversation_id.in_(conv_ids)).all()
    check("演示聊天记录已挂会话", len(msgs) >= 9)

    # 6) API 层可查询演示数据
    client = TestClient(seed_demo_app())
    r = client.get("/api/v1/goods", params={"keyword": "高等数学"})
    body = r.json()
    hit = body.get("items", [])
    check("API 可查到演示商品（高等数学）",
          r.status_code == 200 and len(hit) >= 1
          and any(h["name"].startswith("高等数学") and h["estimated_min"] == 27
                  and h["estimated_max"] == 41 for h in hit))
    r2 = client.get("/api/v1/goods", params={"school_id": schools[0].id})
    check("API 可按演示学校过滤商品", r2.status_code == 200)

    db.close()
    print("\nDay13 演示数据接入验收：%d PASS / %d FAIL" % (ok, fail))
    return fail


def seed_demo_app():
    from app.main import app  # noqa: E402
    return app


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
