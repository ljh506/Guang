# -*- coding: utf-8 -*-
"""
拾光Agent · Day15 全模块回归检查（成员B 最终检查）
====================================================
任务来源：项目计划书 Day 15 行，成员B 当日任务「最终检查 AI 识别 / 估价 / 匹配 算法，
准备手动兜底」。

本脚本对成员B 全链路做最终回归：
  A. 复用 Day11 algorithm_check.run_all_checks（8 项核心检查）
  B. 跨日链路冒烟（识别->估价->匹配->解释->协议->提示）
  C. Day13 演示数据回归（3 组交换全部 >= 0.5 可匹配）

运行：python final_regression.py
输出：控制台逐项 PASS/FAIL + 汇总 JSON 结构 {checks, passed, failed, summary}
依赖：仅标准库 + 注入历史交付目录。
"""
import os
import sys

BASE = r"C:\Users\LENOVO\Desktop\拾光Agent"
HIST = [
    r"%s\成员B_Day5_交付" % BASE,
    r"%s\成员B_Day7_交付" % BASE,
    r"%s\成员B_Day8_交付" % BASE,
    r"%s\成员B_Day9_交付" % BASE,
    r"%s\成员B_Day10_11_交付" % BASE,
    r"%s\成员B_Day12_15_交付\Day12_交付" % BASE,
    r"%s\成员B_Day12_15_交付\Day13_交付" % BASE,
    r"%s\成员B_Day12_15_交付\Day14_交付" % BASE,
]
for p in HIST:
    if os.path.isdir(p):
        sys.path.insert(0, p)


def run_all_checks():
    """全模块回归，返回 {checks, passed, failed, summary}。"""
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "passed": bool(ok), "detail": detail})

    # ---------- A. 复用 Day11 核心检查框架 ----------
    try:
        from algorithm_check import run_all_checks as run_day11
    except ModuleNotFoundError:
        run_day11 = None
    if run_day11 is None:
        add("Day11 algorithm_check 可加载", False, "ModuleNotFoundError")
    else:
        add("Day11 algorithm_check 可加载", True)
        r11 = run_day11()
        for c in r11.get("checks", []):
            add("Day11核心项[%s]" % c.get("name", "?"), c.get("passed", False),
                c.get("detail", ""))
        add("Day11 汇总全过", r11.get("failed", 1) == 0,
            "passed=%s failed=%s" % (r11.get("passed"), r11.get("failed")))

    # ---------- B. 跨日链路冒烟 ----------
    # B1 识别：无 backend -> fallback + 全类别列表
    try:
        from recognition_pipeline import RecognitionPipeline, build_available_categories
        pipe = RecognitionPipeline()
        r = pipe.recommend()
        add("识别：无 backend 走 fallback",
            r.get("status") == "fallback" and r.get("fallback"))
        add("识别：兜底提供 10 个类别",
            len(build_available_categories()) == 10)
        add("识别：fallback_reason 非空", bool(r.get("fallback_reason")))
    except Exception as e:
        add("识别链路冒烟", False, repr(e))

    # B2 估价：正常/免费/异常
    try:
        from price_engine_day7 import estimate_price, ERROR_CODES
        r = estimate_price(original_price=50, category_id="textbook",
                           condition="good")
        add("估价：教材50元良好区间合理",
            r.get("estimated_min") <= r.get("estimated_max") and
            r.get("estimated_min") is not None)
        r = estimate_price(category_id="textbook", condition="good",
                           original_price=None, is_free=True)
        add("估价：免费赠送 0 元",
            r.get("estimated_min") == 0 and r.get("estimated_max") == 0)
        r = estimate_price(category_id="textbook", condition="good",
                           original_price=None, is_free=False)
        add("估价：原价缺失返回错误码",
            isinstance(r.get("error"), dict)
            and r["error"].get("error_code") == "PRICE_ORIGINAL_REQUIRED")
    except Exception as e:
        add("估价链路冒烟", False, repr(e))

    # B3 匹配：示例高匹配/边界
    try:
        from match_engine import match_score, recommend_level
        a = {"category_id": "textbook", "wish_category_id": "physics",
             "asking_price": 30, "school_id": 1, "status": "on_sale"}
        b = {"category_id": "physics", "wish_category_id": "textbook",
             "asking_price": 32, "school_id": 1, "status": "on_sale"}
        m = match_score(a, b)
        add("匹配：计划书示例 >= 0.75 高匹配",
            m is not None and m["match_score"] >= 0.75)
        add("匹配：分级函数 high/normal/low",
            recommend_level(0.80) == "high" and recommend_level(0.60) == "normal"
            and recommend_level(0.40) == "low")
        bad = {"category_id": "textbook", "asking_price": 30,
               "school_id": 1, "status": "on_sale"}
        add("匹配：缺失字段返回 None 不崩",
            match_score(bad, {"category_id": "x", "asking_price": 1}) is None)
    except Exception as e:
        add("匹配链路冒烟", False, repr(e))

    # B4 解释/协议/提示
    try:
        from match_explanation import (build_match_explanation,
                                       build_exchange_protocol_text,
                                       validate_protocol)
        expl = build_match_explanation(a, b, m) if m else None
        add("解释：高匹配生成解释文本", bool(expl) and "匹配度" in str(expl))
        user_a = {"nickname": "用户A", "school_name": "清华大学"}
        user_b = {"nickname": "用户B", "school_name": "清华大学"}
        proto = build_exchange_protocol_text(a, user_a, b, user_b) if m else None
        add("协议：交换协议文本生成", bool(proto))
        v = validate_protocol(a, b, state="negotiating",
                              confirm_a=True, confirm_b=True)
        add("协议：negotiating->confirmed 合法", v.get("valid") is True)
    except Exception as e:
        add("解释/协议冒烟", False, repr(e))

    try:
        from user_prompt import (build_recognition_tip, build_price_tip)
        rec_res = {"status": "fallback", "fallback_reason": "AI识别服务不可用",
                   "raw_label": None, "confidence": None,
                   "available_categories": [], "fallback": True}
        t1 = build_recognition_tip(rec_res)
        add("提示：识别兜底提示非空", bool(t1) and t1.get("level") == "error")
        price_err = {"error": {"error_code": "PRICE_ORIGINAL_REQUIRED",
                               "message": "请填写参考原价"}}
        t2 = build_price_tip(price_err)
        add("提示：估价错误码提示非空", bool(t2) and t2.get("error_code")
            == "PRICE_ORIGINAL_REQUIRED")
    except Exception as e:
        add("提示链路冒烟", False, repr(e))

    # ---------- C. Day13 演示数据回归 ----------
    try:
        from demo_data import build_demo_db
        import sqlite3
        tmp_db = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "regression_demo_tmp.db")
        if os.path.exists(tmp_db):
            os.remove(tmp_db)
        counts = build_demo_db(tmp_db)
        add("演示：数据库生成（20商品/5用户/3交换）",
            counts["goods"] == 20 and counts["users"] == 5
            and counts["exchanges"] == 3)
        add("演示：聊天记录 >= 9", counts.get("chats", 0) >= 9)
        conn = sqlite3.connect(tmp_db)
        goods_rows = {}
        for g in conn.execute(
                "SELECT g.id, g.user_id, g.category_id, g.asking_price, "
                "u.school_id, g.status FROM goods g JOIN user u "
                "ON g.user_id = u.id"):
            goods_rows[g[0]] = g
        wish_rows = {}
        for uid, cid in conn.execute(
                "SELECT user_id, wish_category_id FROM user_wish"):
            wish_rows.setdefault(uid, []).append(cid)
        all_ok = True
        for ex in conn.execute(
                "SELECT id, goods_a_id, goods_b_id FROM exchange"):
            ex_id, ga_id, gb_id = ex
            ga = goods_rows[ga_id]
            gb = goods_rows[gb_id]
            da = {"category_id": ga[2], "asking_price": ga[3],
                  "school_id": ga[4], "status": ga[5],
                  "wish_category_id": wish_rows.get(ga[1], [])}
            db = {"category_id": gb[2], "asking_price": gb[3],
                  "school_id": gb[4], "status": gb[5],
                  "wish_category_id": wish_rows.get(gb[1], [])}
            mm = match_score(da, db)
            if mm is None or mm["match_score"] < 0.5:
                all_ok = False
        conn.close()
        if os.path.exists(tmp_db):
            os.remove(tmp_db)
        add("演示：3 组交换全部 >= 0.5 可匹配", all_ok)
    except Exception as e:
        add("Day13 演示数据回归", False, repr(e))

    # ---------- 汇总 ----------
    passed = sum(1 for c in checks if c["passed"])
    failed = len(checks) - passed
    return {
        "checks": checks,
        "passed": passed,
        "failed": failed,
        "summary": "Day15 全模块回归：PASS %d / FAIL %d（共 %d 项）"
                   % (passed, failed, len(checks)),
    }


def main():
    print("=== Day15 全模块回归检查（成员B 最终检查）===")
    report = run_all_checks()
    for c in report["checks"]:
        print("  [%s] %s%s" % ("PASS" if c["passed"] else "FAIL", c["name"],
                               "（%s）" % c["detail"] if c["detail"] else ""))
    print("结果：PASS %d / FAIL %d / 共 %d 项" % (
        report["passed"], report["failed"], len(report["checks"])))
    print(report["summary"])
    return report


if __name__ == "__main__":
    main()
