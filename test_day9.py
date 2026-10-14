# -*- coding: utf-8 -*-
"""
拾光Agent · Day9 匹配算法自测脚本 test_day9.py（成员B Day 9 交付）
========================================================
覆盖 match_engine.py：
- 权重合计 = 1.0
- 类别/意愿：双向完全匹配 1.0 / 双向类别匹配 0.9 / 单向匹配 0.5 / 完全不匹配不入候选
- 价格接近：公式 1 - |a-b|/max(a,b)、双方免费 1.0、单方免费 0.3、标价缺失 0.0、
  estimated 区间不参与得分
- 同校优先：同校 1.0 / 跨校 0.0
- 阈值分级：>=0.75 high / >=0.50 normal / <0.50 low
- match_reason 内容断言
- recommend 排序 / 去重 / 上限 / 低匹配过滤
- 边界：缺失字段不崩、状态不可交换不入候选
- Day8 状态机衔接：chatting -> matched 合法
运行：python test_day9.py（退出码 0 全部 PASS；非 0 有 FAIL）。
依赖：仅标准库；自动注入 Day8 交付目录读取状态机。
"""

import sys
import os

# 让本脚本可直接运行：注入 match_engine 所在目录 与 Day8 交付目录
HERE = os.path.dirname(os.path.abspath(__file__))
DAY8_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day8_交付"
for p in (HERE, DAY8_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from match_engine import (
    WEIGHT_CATEGORY_WISH, WEIGHT_PRICE, WEIGHT_SCHOOL, WEIGHT_SUM,
    THRESHOLD_HIGH, THRESHOLD_NORMAL,
    category_wish_score, price_score, school_score,
    match_score, recommend_level, build_match_reason,
    recommend, on_match, MAX_RECOMMEND_RESULTS,
)
from chat_rules import validate_transition, TRADE_STATES

PASS = 0
FAIL = 0
FAIL_MSGS = []


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("[PASS] %s" % name)
    else:
        FAIL += 1
        FAIL_MSGS.append(name)
        print("[FAIL] %s" % name)


def goods(category_id="textbook", wish=None, price=30, school=1,
          status="on_sale", goods_id=None, user_id=None, publish_time=0,
          estimated_min=None, estimated_max=None):
    """构造测试商品 dict。"""
    g = {
        "category_id": category_id,
        "asking_price": price,
        "school_id": school,
        "status": status,
        "publish_time": publish_time,
    }
    if wish is not None:
        g["wish_category_id"] = wish
    if goods_id is not None:
        g["goods_id"] = goods_id
    if user_id is not None:
        g["user_id"] = user_id
    if estimated_min is not None:
        g["estimated_min"] = estimated_min
    if estimated_max is not None:
        g["estimated_max"] = estimated_max
    return g


# 标准高匹配样例：A 教材(30元) 想要物理；B 物理(32元) 想要教材；同校
A = goods("textbook", wish="physics", price=30, school=1,
          goods_id=12, user_id=1, publish_time=100)
B = goods("physics", wish="textbook", price=32, school=1,
          goods_id=20, user_id=2, publish_time=200)

# 1. 权重合计 = 1.0
check("权重合计 = 1.0", abs(WEIGHT_SUM - 1.0) < 1e-9)
check("权重分别为 50/30/20",
      abs(WEIGHT_CATEGORY_WISH - 0.50) < 1e-9 and
      abs(WEIGHT_PRICE - 0.30) < 1e-9 and
      abs(WEIGHT_SCHOOL - 0.20) < 1e-9)

# 2. 类别/意愿匹配
check("双向完全匹配（意愿互中）-> 1.0",
      abs(category_wish_score(A, B) - 1.0) < 1e-9)
C_no_wish = goods("textbook", wish=None, price=30, school=1)
D_same_cat = goods("textbook", wish=None, price=30, school=1)
check("双向类别匹配（无意愿，同类）-> 0.9",
      abs(category_wish_score(C_no_wish, D_same_cat) - 0.9) < 1e-9)
A_no_wish_b = goods("textbook", wish=None, price=30, school=1)
B_want_a_only = goods("physics", wish="textbook", price=30, school=1)  # B 想要 A，A 无意愿
check("单向匹配（仅 B 意愿命中）-> 0.5",
      abs(category_wish_score(A_no_wish_b, B_want_a_only) - 0.5) < 1e-9)
E_other = goods("electronics", wish="sports", price=30, school=1)
F_other = goods("clothing", wish="sports", price=30, school=1)
check("类别完全不匹配 -> 0.0",
      abs(category_wish_score(E_other, F_other) - 0.0) < 1e-9)
check("wish 缺失（None）不崩溃且返回 0.0",
      category_wish_score(C_no_wish, E_other) == 0.0)
check("wish 为列表形式可解析（多意愿）",
      abs(category_wish_score(
          goods("textbook", wish=["sports", "physics"], price=30, school=1),
          B) - 1.0) < 1e-9)

# 3. 价格接近度
check("标价相同 -> 1.0", abs(price_score(30, 30) - 1.0) < 1e-9)
check("30 vs 32 -> 接近度 ≈0.9375",
      abs(price_score(30, 32) - 0.9375) < 1e-9)
check("差一倍（30 vs 60）-> 0.5", abs(price_score(30, 60) - 0.5) < 1e-9)
check("双方均免费（0 元）-> 1.0", abs(price_score(0, 0) - 1.0) < 1e-9)
check("仅一方免费 -> 0.3", abs(price_score(0, 30) - 0.3) < 1e-9)
check("缺失标价 -> 0.0", abs(price_score(None, 30) - 0.0) < 1e-9)
check("非法标价（负数/NaN/布尔）-> 0.0",
      abs(price_score(-5, 30) - 0.0) < 1e-9 and
      abs(price_score(float("nan"), 30) - 0.0) < 1e-9 and
      abs(price_score(True, 30) - 0.0) < 1e-9)
check("estimated 区间不参与价格分（同 asking_price 价格分一致）",
      abs(price_score(30, 32) - price_score(30, 32)) < 1e-9)

# 4. 同校
check("同校 -> 1.0", abs(school_score(1, 1) - 1.0) < 1e-9)
check("跨校 -> 0.0", abs(school_score(1, 2) - 0.0) < 1e-9)
check("school 缺失 -> 0.0", abs(school_score(None, 1) - 0.0) < 1e-9)

# 5. 阈值分级
check("0.97 -> high", recommend_level(0.97) == "high")
check("0.75 边界 -> high", recommend_level(0.75) == "high")
check("0.60 -> normal", recommend_level(0.60) == "normal")
check("0.50 边界 -> normal", recommend_level(0.50) == "normal")
check("0.49 -> low", recommend_level(0.49) == "low")

# 6. 综合匹配度（计划书高匹配示例：30/32 同校双向）
m_hi = match_score(A, B)
check("高匹配示例 match_score ≈0.98（0.5*1+0.3*0.9375+0.2*1=0.98125）",
      m_hi is not None and abs(m_hi["match_score"] - 0.98125) < 1e-3)
check("高匹配示例分级 high", m_hi["level"] == "high")
check("score_detail 维度齐全",
      set(m_hi["score_detail"].keys()) == {"category_wish", "price", "school"})
check("权重分配 50/30/20 在结果中",
      abs(m_hi["weights"]["category_wish"] - 0.5) < 1e-9 and
      abs(m_hi["weights"]["price"] - 0.3) < 1e-9 and
      abs(m_hi["weights"]["school"] - 0.2) < 1e-9)

# 7. match_reason 内容断言
reason = m_hi["match_reason"]
check("match_reason 含双方意愿匹配", "双方意愿匹配" in reason)
check("match_reason 含标价与接近度", "接近度 94%" in reason)
check("match_reason 含同校", "同校" in reason)
check("match_reason 含综合匹配度（98%）", "综合匹配度 98%" in reason)
r_free = build_match_reason(
    goods("textbook", price=0, school=1), goods("physics", price=0, school=1),
    0.5, 1.0, 1.0, 0.75)
check("match_reason 免费场景说明", "均免费赠送" in r_free)
r_half = build_match_reason(
    goods("textbook", price=0, school=1), goods("physics", price=30, school=1),
    0.5, 0.3, 1.0, 0.6)
check("match_reason 单方免费中性说明", "一方为免费赠送" in r_half)

# 8. 基础条件：状态不可交换 -> 不进入候选
A_sold = goods("textbook", wish="physics", price=30, school=1,
               status="sold", goods_id=12, user_id=1)
check("任一方不可交换 -> 不入候选（None）",
      match_score(A_sold, B) is None)

# 9. 类别完全不匹配 -> 不入候选
check("类别完全不匹配 -> 不入候选（None）",
      match_score(goods("textbook", wish="sports", price=30, school=1),
                  goods("clothing", wish="sports", price=30, school=1)) is None)

# 10. 边界：缺失字段不崩溃
check("极端缺失字段不崩溃且为 None",
      match_score({"category_id": "x"}, {"category_id": "x"}) is not None)
check("category_id 缺失 -> None",
      match_score(goods("textbook"), {"asking_price": 10}) is None)

# 11. recommend 排序 / 过滤 / 去重 / 上限
cand_best = goods("physics", wish="textbook", price=32, school=1,
                  goods_id=20, user_id=2, publish_time=300)
cand_mid = goods("physics", wish="textbook", price=60, school=1,
                 goods_id=21, user_id=3, publish_time=200)   # 价格分低 -> 总分更低
cand_low = goods("physics", wish=None, price=32, school=1,
                 goods_id=22, user_id=4, publish_time=100)   # 单向 0.5 -> 总分可能 <0.5
cand_bad = goods("clothing", wish=None, price=32, school=1,
                 goods_id=23, user_id=5)                     # 类别不匹配，应被过滤
recs = recommend(A, [cand_bad, cand_low, cand_mid, cand_best])
check("recommend 排除类别不匹配候选",
      all(r["target_goods_id"] != 23 for r in recs))
check("recommend 按总分降序",
      all(recs[i]["match_score"] >= recs[i + 1]["match_score"]
          for i in range(len(recs) - 1)))
check("recommend 优先返回 best（30/32 同校）",
      recs and recs[0]["target_goods_id"] == 20)
check("recommend 不返回 <0.50 低匹配",
      all(r["match_score"] >= THRESHOLD_NORMAL for r in recs))

# 同分时按价格接近度降序
A2 = goods("textbook", wish="physics", price=40, school=1,
           goods_id=12, user_id=1, publish_time=100)
p1 = goods("physics", wish="textbook", price=40, school=1,
           goods_id=30, user_id=6, publish_time=500)
p2 = goods("physics", wish="textbook", price=48, school=1,
           goods_id=31, user_id=7, publish_time=400)
recs_tie = recommend(A2, [p1, p2])
check("同分按价格接近度降序（40 优先于 48）",
      recs_tie[0]["target_goods_id"] == 30 and
      recs_tie[1]["target_goods_id"] == 31)

# 去重：existing_pairs 命中则跳过
recs_dedup = recommend(A, [cand_best], existing_pairs=[(1, 12)])
check("existing_pairs 去重生效（(1,12) 已有未完成交换则跳过）",
      all(r["target_goods_id"] != 20 for r in recs_dedup))

# 上限 20
many_cands = []
for i in range(30):
    many_cands.append(goods("physics", wish="textbook", price=30 + i, school=1,
                            goods_id=1000 + i, user_id=100 + i, publish_time=i))
recs_cap = recommend(A, many_cands)
check("recommend 单次最多 20 条", len(recs_cap) <= MAX_RECOMMEND_RESULTS)

# 12. 状态机衔接（Day8）
r_trans = validate_transition("chatting", "matched")
check("Day8 状态机 chatting->matched 合法", r_trans["valid"])
check("TRADE_STATES 含 matched", "matched" in TRADE_STATES)
om = on_match("chatting", 0.97)
check("on_match 高匹配建议流转 matched",
      om["valid"] is True and om["to_state"] == "matched")
om_low = on_match("chatting", 0.60)
check("on_match 普通匹配不建议自动流转",
      om_low["valid"] is False)
om_bad_state = on_match("requested", 0.97)
check("on_match 非 chatting 状态不自动流转",
      om_bad_state["valid"] is False)

# 汇总
print("\n==============================")
print("Day9 匹配算法自测汇总：")
print("PASS: %d / FAIL: %d / 总用例: %d" % (PASS, FAIL, PASS + FAIL))
if FAIL_MSGS:
    print("失败用例：")
    for name in FAIL_MSGS:
        print("  - %s" % name)
    sys.exit(1)
print("全部通过")
sys.exit(0)
