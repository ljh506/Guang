# -*- coding: utf-8 -*-
"""
拾光Agent · Day10 匹配解释文本自测脚本 test_day10.py（成员B Day 10 交付）
========================================================
覆盖 match_explanation.py：
- build_match_explanation：高匹配示例完整解释文本（含维度明细、权重、分级）、
  不可匹配返回「暂不推荐」、普通匹配分级提示
- build_exchange_protocol_text：协议卡片文本（甲乙双方、标价、学校、匹配结论、
  状态、确认标记）
- validate_protocol：状态机合法性（negotiating->confirmed）、不可交换拦截、
  不可匹配拦截、确认标记校验、降级内置规则
运行：python test_day10.py（退出码 0 全部 PASS；非 0 有 FAIL）。
依赖：仅标准库；自动注入 Day9 / Day8 / Day7 交付目录。
"""

import sys
import os

# -*- coding: utf-8 -*-
import sys
import os
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from app.services.match_explanation import (
    build_match_explanation, build_exchange_protocol_text, validate_protocol,
    STATE_NAMES, LEVEL_NAMES,
)

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


def goods(category_id="textbook", wish="physics", price=30, school=1,
          status="on_sale", goods_id=None, user_id=None, name=None):
    g = {"category_id": category_id, "asking_price": price,
         "school_id": school, "status": status}
    if wish is not None:
        g["wish_category_id"] = wish
    if goods_id is not None:
        g["goods_id"] = goods_id
    if user_id is not None:
        g["user_id"] = user_id
    if name is not None:
        g["name"] = name
    return g


# 标准高匹配样例
A = goods("textbook", wish="physics", price=30, school=1,
          goods_id=12, user_id=1, name="高等数学")
B = goods("physics", wish="textbook", price=32, school=1,
          goods_id=20, user_id=2, name="大学物理")

# 1. 完整匹配解释文本
exp = build_match_explanation(A, B)
check("解释文本非空", isinstance(exp, str) and len(exp) > 0)
check("解释文本含匹配说明标题", "匹配说明" in exp)
check("解释文本含类别/意愿维度与权重50%", "类别/意愿（权重50%）" in exp)
check("解释文本含价格接近维度与权重30%", "价格接近（权重30%）" in exp)
check("解释文本含同校维度与权重20%", "同校优先（权重20%）" in exp)
check("解释文本含综合匹配度与分级", "综合匹配度" in exp and "高匹配" in exp)
check("解释文本含推荐提示", "推荐优先交换" in exp)
check("解释文本含双方意愿双向命中", "双向命中" in exp or "双向" in exp)
check("解释文本含标价接近度", "接近度" in exp)
check("解释文本含同校文本", "同校" in exp)

# 2. 普通匹配解释文本
A_norm = goods("textbook", wish="physics", price=80, school=1,
               goods_id=13, user_id=1)
B_norm = goods("physics", wish="textbook", price=30, school=3,
               goods_id=21, user_id=2)
exp_norm = build_match_explanation(A_norm, B_norm)
check("普通匹配解释文本含普通匹配", "普通匹配" in exp_norm)
check("普通匹配解释文本含继续沟通提示", "建议继续沟通" in exp_norm)
check("普通匹配解释文本含跨校", "跨校" in exp_norm)

# 2b. 低匹配解释文本（仅单向意愿 + 价格差距大 + 跨校）
A_low = goods("textbook", wish="sports", price=50, school=2,
              goods_id=14, user_id=1)
B_low = goods("physics", wish="textbook", price=20, school=3,
              goods_id=22, user_id=2)
exp_low = build_match_explanation(A_low, B_low)
check("低匹配解释文本含低匹配", "低匹配" in exp_low)
check("低匹配解释文本含暂不推荐提示", "暂不推荐" in exp_low)
check("低匹配解释文本含单向意愿命中", "单向意愿命中" in exp_low)

# 3. 不可匹配返回暂不推荐
A_bad = goods("textbook", wish="sports", price=30, school=1)
B_bad = goods("clothing", wish="sports", price=30, school=1)
exp_bad = build_match_explanation(A_bad, B_bad)
check("不可匹配 -> 暂不推荐", "暂不推荐" in exp_bad)

# 4. 协议卡片文本
proto = build_exchange_protocol_text(
    A, {"user_id": 1, "nickname": "小明", "school_name": "同校大学"},
    B, {"user_id": 2, "nickname": "小红", "school_name": "同校大学"},
    exchange_id=1, state="negotiating", confirm_a=True, confirm_b=True)
check("协议含标题", "物品交换协议" in proto)
check("协议含编号", "EX-1" in proto)
check("协议含甲方物品标价学校", "甲方" in proto and "高等数学" in proto and "30 元" in proto)
check("协议含乙方物品标价学校", "乙方" in proto and "大学物理" in proto and "32 元" in proto)
check("协议含匹配结论", "匹配结论" in proto and "综合匹配度" in proto)
check("协议含交易状态", "交易状态：交换待确认" in proto)
check("协议含双方确认标记", "甲方已确认" in proto and "乙方已确认" in proto)

proto_cancelled = build_exchange_protocol_text(
    A, {"user_id": 1}, B, {"user_id": 2},
    exchange_id=2, state="cancelled", confirm_a=False, confirm_b=False)
check("协议支持取消状态", "交易状态：已取消" in proto_cancelled)
check("协议缺省名称回退", "用户1" in proto_cancelled and "用户2" in proto_cancelled)

# 5. validate_protocol
v_ok = validate_protocol(A, B, state="negotiating", confirm_a=True, confirm_b=True)
check("协议校验通过（negotiating->confirmed 合法）", v_ok["valid"] is True)
check("协议校验返回状态合法标记", v_ok["state_valid"] is True)

v_sold = validate_protocol(goods(status="sold"), B, state="negotiating")
check("任一方不可交换 -> 校验失败", v_sold["valid"] is False and "不可交换" in v_sold["reason"])

v_bad = validate_protocol(A_bad, B_bad, state="negotiating")
check("类别不匹配 -> 校验失败", v_bad["valid"] is False and "未形成匹配" in v_bad["reason"])

v_confirm = validate_protocol(A, B, state="confirmed", confirm_a=True, confirm_b=False)
check("已确认但确认标记不全 -> 校验失败",
      v_confirm["valid"] is False and "确认标记未齐全" in v_confirm["reason"])

v_ok2 = validate_protocol(A, B, state="confirmed", confirm_a=True, confirm_b=True)
check("双方确认后 confirmed 校验通过", v_ok2["valid"] is True)

# 6. 降级内置状态规则（若 chat_rules 可导入则校验真实状态机）
check("状态名表含关键状态",
      set(STATE_NAMES) >= {"requested", "chatting", "matched", "negotiating", "confirmed", "cancelled"})
check("分级名表含 high/normal/low",
      set(LEVEL_NAMES) >= {"high", "normal", "low"})

# 汇总
print("\n==============================")
print("Day10 匹配解释文本自测汇总：")
print("PASS: %d / FAIL: %d / 总用例: %d" % (PASS, FAIL, PASS + FAIL))
if FAIL_MSGS:
    print("失败用例：")
    for name in FAIL_MSGS:
        print("  - %s" % name)
    sys.exit(1)
print("全部通过")
sys.exit(0)
