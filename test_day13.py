# -*- coding: utf-8 -*-
"""
拾光Agent · Day13 自测脚本 test_day13.py（成员B Day 13 交付）
================================================================
覆盖：
- 演示数据生成：school=7 / user=5 / goods=20 / exchange=3 / chat>=9 / 意愿>=5
- 演示数据与 Day3 数据衔接：优先使用 Day3 CSV 的学校/用户
- 演示脚本 demo_script 可完整运行且含关键段落
- 3 组交换均能匹配（match_score 非 None 且 >=0.5，衔接 Day9）
- 估价演示衔接 Day7（教材 68 元良好 -> 27~41 元）
- 解释/协议/提示模块可被演示引用（衔接 Day10/Day12）

运行方式：python test_day13.py
依赖：仅标准库。
"""

import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

DAY12_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day12_15_交付\Day12_交付"
DAY10_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day10_11_交付"
DAY9_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day9_交付"
DAY7_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day7_交付"
DAY5_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day5_交付"
for p in (DAY12_DIR, DAY10_DIR, DAY9_DIR, DAY7_DIR, DAY5_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from demo_data import build_demo_db, DEMO_EXCHANGES  # noqa: E402
from demo_script import load_demo_data, run_demo  # noqa: E402

try:
    from match_engine import match_score  # noqa: E402
except ModuleNotFoundError:
    match_score = None

try:
    from price_engine_day7 import estimate_price  # noqa: E402
except ModuleNotFoundError:
    estimate_price = None

try:
    from match_explanation import build_match_explanation  # noqa: E402
except ModuleNotFoundError:
    build_match_explanation = None

try:
    from user_prompt import build_recognition_tip, build_price_tip  # noqa: E402
except ModuleNotFoundError:
    build_recognition_tip = None
    build_price_tip = None

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print("  [PASS] %s" % name)
    else:
        _FAIL += 1
        print("  [FAIL] %s %s" % (name, detail))


def main():
    print("=== Day13 test: 演示数据 + 演示脚本 ===")

    # ---------- 1. 演示数据生成 ----------
    print("[演示数据生成]")
    db_path = os.path.join(HERE, "shiguang_demo_full.db")
    counts = build_demo_db(db_path)
    check("数据库生成成功", os.path.exists(db_path), db_path)
    check("学校 7 所", counts["schools"] == 7, counts["schools"])
    check("用户 5 人", counts["users"] == 5, counts["users"])
    check("商品 20 件", counts["goods"] == 20, counts["goods"])
    check("交换 3 组", counts["exchanges"] == 3, counts["exchanges"])
    check("聊天记录 >=9", counts["chats"] >= 9, counts["chats"])
    check("意愿记录 >=5", counts["wishes"] >= 5, counts["wishes"])

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        schools = [dict(r) for r in conn.execute("SELECT * FROM school")]
        users = [dict(r) for r in conn.execute("SELECT * FROM user")]
        goods = [dict(r) for r in conn.execute("SELECT * FROM goods")]
        exchanges = [dict(r) for r in conn.execute("SELECT * FROM exchange")]
        chats = [dict(r) for r in conn.execute("SELECT * FROM chat")]
    finally:
        conn.close()

    # 类别覆盖（教材/电子/生活/衣物/文具/数码配件/运动/家具等）
    cats = {g["category_id"] for g in goods}
    need = {"textbook", "electronics", "life_goods", "clothing",
            "digital_accessories", "sports_equipment", "furniture"}
    check("商品类别覆盖核心集合", need <= cats, cats)

    # 每个用户至少 3 件商品，保证演示分布
    per_user = {}
    for g in goods:
        per_user[g["user_id"]] = per_user.get(g["user_id"], 0) + 1
    check("每用户商品数合理", all(v >= 3 for v in per_user.values()), per_user)

    # 用户/商品外键一致
    user_ids = {u["id"] for u in users}
    check("商品 user_id 均存在", {g["user_id"] for g in goods} <= user_ids)
    goods_ids = {g["id"] for g in goods}
    check("交换 goods 均存在", all(
        ex["goods_a_id"] in goods_ids and ex["goods_b_id"] in goods_ids
        for ex in exchanges))
    check("交换状态合法", all(ex["state"] in ("negotiating", "confirmed")
                              for ex in exchanges))

    # Day3 衔接：学校/用户取自 Day3 CSV 时应与 Day3 数据一致（至少存在 7 校）
    check("学校含清华大学", any(s["name"] == "清华大学" for s in schools))
    check("用户 5 人昵称完整", all(u["nickname"] for u in users))

    # ---------- 2. 匹配衔接 ----------
    print("[匹配衔接 Day9]")
    data = load_demo_data(db_path)
    if match_score is None:
        check("match_engine 可注入", False, "match_engine 缺失")
    else:
        ok_all = True
        details = []
        for ex in DEMO_EXCHANGES:
            ga = data["goods"][ex["goods_a_id"]]
            gb = data["goods"][ex["goods_b_id"]]
            m = match_score(ga, gb)
            if m is None or m["match_score"] < 0.5:
                ok_all = False
                details.append("交换%d 得分=%s" % (ex["id"],
                                                m and m["match_score"]))
            else:
                details.append("交换%d 得分=%.3f (%s)" % (
                    ex["id"], m["match_score"], m["level"]))
        check("3 组交换全部可匹配(>=0.5)", ok_all, " | ".join(details))
        for ex in DEMO_EXCHANGES:
            ga = data["goods"][ex["goods_a_id"]]
            gb = data["goods"][ex["goods_b_id"]]
            m = match_score(ga, gb)
            if m:
                check("交换%d 原因非空" % ex["id"], bool(m["match_reason"]))

    # ---------- 3. 估价衔接 ----------
    print("[估价衔接 Day7]")
    if estimate_price is None:
        check("price_engine 可注入", False, "price_engine_day7 缺失")
    else:
        r = estimate_price(category_id="textbook", condition="good",
                           original_price=68, months_used=None, is_free=False,
                           asking_price=30)
        check("教材68元良好 -> 27~41", not ("error" in r) and
              r["estimated_min"] == 27 and r["estimated_max"] == 41,
              str(r))
        r2 = estimate_price(category_id="clothing", condition="good",
                            original_price=299, months_used=None, is_free=False,
                            asking_price=150)
        check("衣物299元良好 -> 区间存在且合理",
              "error" not in r2 and 0 <= r2["estimated_min"] <= r2["estimated_max"])

    # ---------- 4. 解释/协议/提示模块衔接 ----------
    print("[解释/协议/提示衔接 Day10/Day12]")
    if build_match_explanation is not None:
        ga = data["goods"][1]
        gb = data["goods"][6]
        m = match_score(ga, gb)
        if m:
            expl = build_match_explanation(ga, gb, match_result=m)
            check("解释文本生成", isinstance(expl, str) and len(expl) > 20)
    if build_recognition_tip is not None:
        tip = build_recognition_tip({"status": "auto_fill", "category_name": "教材",
                                     "confidence": 0.95, "raw_label": "textbook",
                                     "fallback_reason": None})
        check("识别提示可生成", tip["level"] == "good")
    if build_price_tip is not None:
        r = estimate_price(category_id="textbook", condition="good",
                           original_price=68, months_used=None, is_free=False,
                           asking_price=30)
        tip = build_price_tip(r)
        check("估价提示可生成", tip["level"] in ("good", "warn", "error"))

    # ---------- 5. 演示脚本整体运行 ----------
    print("[演示脚本运行]")
    lines = run_demo()
    text = "\n".join(lines)
    check("演示脚本可运行", len(lines) > 10)
    for kw in ("AI 识别演示", "AI 估价演示", "匹配算法演示",
               "聊天记录演示", "演示数据概览", "交换协议卡片"):
        check("演示含段落「%s」" % kw, kw in text)

    print()
    print("结果：PASS %d / FAIL %d" % (_PASS, _FAIL))
    if _FAIL:
        raise SystemExit(1)
    print("Day13 test 全部通过")


if __name__ == "__main__":
    main()
