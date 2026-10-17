# -*- coding: utf-8 -*-
"""
拾光Agent · 比赛演示脚本 demo_script.py（成员B Day 13 交付）
================================================================
任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 13 行，成员B 当日任务
「准备AI识别和估价演示案例」。

本脚本串联成员B 已交付的全部 AI/算法能力，输出可在比赛现场逐步演示的文案流：

    ① 演示数据加载（Day13 demo_data：20商品/5用户/3交换/聊天记录）
    ② AI 识别演示（Day5 recognition_pipeline + MockBackend 模拟识别，
       输出 Day12 user_prompt 优化后的用户提示）
    ③ 估价演示（Day7 price_engine_day7，输出建议区间与用户提示）
    ④ 匹配演示（Day9 match_engine，3 组交换的匹配得分与原因）
    ⑤ 解释与协议演示（Day10 match_explanation，匹配解释文本与协议卡片）

运行方式：python demo_script.py
依赖：仅标准库；自动注入 Day5/Day7/Day9/Day10/Day12 交付目录。
"""

import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY13_DIR = HERE
DAY12_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day12_15_交付\Day12_交付"
DAY10_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day10_11_交付"
DAY9_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day9_交付"
DAY8_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day8_交付"
DAY7_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day7_交付"
DAY5_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day5_交付"
DAY4_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day4_交付"
for p in (DAY13_DIR, DAY12_DIR, DAY10_DIR, DAY9_DIR, DAY8_DIR, DAY7_DIR,
          DAY5_DIR, DAY4_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from demo_data import build_demo_db, DB_PATH, DEMO_EXCHANGES, DEMO_CHATS  # noqa: E402

try:
    from recognition_pipeline import RecognitionPipeline, MockBackend  # noqa: E402
except ModuleNotFoundError:  # 识别模块缺失时演示降级
    RecognitionPipeline = None
    MockBackend = None

try:
    from price_engine_day7 import estimate_price  # noqa: E402
except ModuleNotFoundError:
    estimate_price = None

try:
    from match_engine import match_score, build_match_reason  # noqa: E402
except ModuleNotFoundError:
    match_score = None
    build_match_reason = None

try:
    from match_explanation import (build_match_explanation,  # noqa: E402
                                   build_exchange_protocol_text,
                                   validate_protocol)
except ModuleNotFoundError:
    build_match_explanation = None
    build_exchange_protocol_text = None
    validate_protocol = None

try:
    from user_prompt import build_recognition_tip, build_price_tip  # noqa: E402
except ModuleNotFoundError:
    build_recognition_tip = None
    build_price_tip = None

DB = os.path.join(DAY13_DIR, "shiguang_demo_full.db")


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------
def load_demo_data(db_path=DB):
    """加载演示数据库，返回 {goods: {id: row}, users: {id: row}, wishes: {uid:set}}。"""
    if not os.path.exists(db_path):
        build_demo_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        goods = {r["id"]: dict(r) for r in conn.execute(
            "SELECT * FROM goods ORDER BY id")}
        users = {r["id"]: dict(r) for r in conn.execute(
            "SELECT * FROM user ORDER BY id")}
        schools = {r["id"]: dict(r) for r in conn.execute(
            "SELECT * FROM school ORDER BY id")}
        wishes = {}
        for r in conn.execute("SELECT * FROM user_wish ORDER BY user_id"):
            wishes.setdefault(r["user_id"], []).append(r["wish_category_id"])
        chats = [dict(r) for r in conn.execute(
            "SELECT * FROM chat ORDER BY id")]
    finally:
        conn.close()

    # 商品 dict 增强（衔接 Day9 匹配算法输入约定）
    for g in goods.values():
        g["school_id"] = users.get(g["user_id"], {}).get("school_id")
        g["wish_category_id"] = wishes.get(g["user_id"], [])
    for u in users.values():
        u["school_name"] = schools.get(u.get("school_id"), {}).get("name", "未知")
    return {"goods": goods, "users": users, "schools": schools,
            "wishes": wishes, "chats": chats}


# ---------------------------------------------------------------------------
# 各演示段落
# ---------------------------------------------------------------------------
def demo_recognition():
    """AI 识别演示：MockBackend 模拟真实识别服务。"""
    lines = ["===== ① AI 识别演示 ====="]
    if RecognitionPipeline is None or MockBackend is None:
        lines.append("（recognition_pipeline 模块不可用，跳过识别演示）")
        return lines

    mock = MockBackend()
    mock.add_success("textbook", 0.95)     # 高置信度 -> 自动填入
    mock.add_success("t-shirt", 0.72)      # 中置信度 -> 需确认
    mock.add_failure("AI识别服务不可用")     # 服务异常 -> 失败兜底

    pipeline = RecognitionPipeline(backend=mock)
    cases = [
        ("教材书.jpg", "textbook 0.95"),
        ("短袖T恤.jpg", "t-shirt 0.72"),
        ("模糊图片.jpg", "服务异常"),
    ]
    for img, desc in cases:
        result = pipeline.recommend(image_path=img)
        lines.append("- 识别 [%s]（模拟 backend: %s）" % (img, desc))
        if build_recognition_tip is not None:
            tip = build_recognition_tip(result)
            lines.append("    -> [%s] %s：%s" % (tip["level"], tip["title"],
                                                tip["message"]))
        else:
            lines.append("    -> status=%s" % result.get("status"))
    return lines


def demo_price(goods_map):
    """估价演示：对演示商品调用估价引擎并给出用户提示。"""
    lines = ["===== ② AI 估价演示 ====="]
    if estimate_price is None:
        lines.append("（price_engine_day7 模块不可用，跳过估价演示）")
        return lines

    pick_ids = [1, 8, 3]  # 高数教材 / LED台灯 / 羽毛球拍
    for gid in pick_ids:
        g = goods_map[gid]
        result = estimate_price(
            category_id=g["category_id"], condition=g["condition"],
            original_price=g["original_price"], months_used=g["months_used"],
            is_free=bool(g["is_free"]), asking_price=g["asking_price"])
        if "error" in result:
            lines.append("- 估价 [%s] -> 失败 %s" % (g["name"],
                                                    result["error"]["error_code"]))
            continue
        lines.append("- 估价 [%s]：建议区间 %s~%s 元（%s）" % (
            g["name"], result["estimated_min"], result["estimated_max"],
            result["reason_text"]))
        if build_price_tip is not None:
            tip = build_price_tip(result)
            if tip["action"]:
                lines.append("    -> [%s] %s：%s（动作：%s）"
                             % (tip["level"], tip["title"], tip["message"],
                                tip["action"]))
    return lines


def demo_match(goods_map, users_map):
    """匹配演示：对 3 组交换关系计算匹配度并解释。"""
    lines = ["===== ③ 匹配算法演示 ====="]
    if match_score is None:
        lines.append("（match_engine 模块不可用，跳过匹配演示）")
        return lines

    for ex in DEMO_EXCHANGES:
        ga = goods_map[ex["goods_a_id"]]
        gb = goods_map[ex["goods_b_id"]]
        ua = users_map.get(ex["user_a_id"], {})
        ub = users_map.get(ex["user_b_id"], {})
        m = match_score(ga, gb)
        if m is None:
            lines.append("- 交换%d [%s ↔ %s]：不可匹配" % (
                ex["id"], ga["name"], gb["name"]))
            continue
        lines.append("- 交换%d [%s ↔ %s]：匹配度 %.1f%%（%s）" % (
            ex["id"], ga["name"], gb["name"],
            m["match_score"] * 100, m["level"]))
        lines.append("    %s" % m["match_reason"])
        if build_match_explanation is not None:
            expl = build_match_explanation(ga, gb, match_result=m)
            first_line = expl.split("\n")[0]
            lines.append("    解释：%s" % first_line)
        # 协议演示（EX1 用匹配结果生成协议文本）
        if ex["id"] == 1 and build_exchange_protocol_text is not None:
            protocol = build_exchange_protocol_text(
                ga, {"user_id": ua.get("id"), "nickname": ua.get("nickname"),
                     "school_name": ua.get("school_name")},
                gb, {"user_id": ub.get("id"), "nickname": ub.get("nickname"),
                     "school_name": ub.get("school_name")},
                exchange_id=ex["id"], state=ex["state"],
                confirm_a=bool(ex["confirm_a"]), confirm_b=bool(ex["confirm_b"]),
                match_result=m)
            lines.append("    --- 交换协议卡片 ---")
            for p in protocol.split("\n"):
                lines.append("    " + p)
    return lines


def demo_chat():
    """聊天记录演示：展示 3 组交换的聊天记录（衔接 Day8 快捷消息）。"""
    lines = ["===== ④ 聊天记录演示 ====="]
    if not DEMO_CHATS:
        lines.append("（无聊天记录）")
        return lines
    for c in DEMO_CHATS:
        lines.append("- [交换%d] 用户%d -> 用户%d：%s"
                     % (c[0], c[1], c[2], c[4]))
    return lines


def demo_summary(data):
    """演示数据概览。"""
    lines = ["===== 演示数据概览 ====="]
    lines.append("- 学校 %d 所 / 用户 %d 人 / 商品 %d 件 / 交换 %d 组 / 聊天 %d 条" % (
        len(data["schools"]), len(data["users"]), len(data["goods"]),
        len(DEMO_EXCHANGES), len(data["chats"])))
    for uid in sorted(data["users"]):
        u = data["users"][uid]
        my_goods = [g["name"] for g in data["goods"].values()
                    if g["user_id"] == uid]
        lines.append("- 用户%d [%s]（%s）：%s" % (
            uid, u["nickname"], u.get("school_name", "未知"),
            "、".join(my_goods[:4]) + ("…" if len(my_goods) > 4 else "")))
    return lines


def run_demo():
    """运行完整演示，返回行列表。"""
    lines = ["拾光Agent · 成员B 算法能力演示（Day13）", "=" * 40]
    data = load_demo_data(DB)
    lines.extend(demo_summary(data))
    lines.append("")
    lines.extend(demo_recognition())
    lines.append("")
    lines.extend(demo_price(data["goods"]))
    lines.append("")
    lines.extend(demo_match(data["goods"], data["users"]))
    lines.append("")
    lines.extend(demo_chat())
    return lines


if __name__ == "__main__":
    for line in run_demo():
        print(line)
    print()
    print("演示脚本运行完成。")
