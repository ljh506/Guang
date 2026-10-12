# -*- coding: utf-8 -*-
"""
拾光Agent · Day7 边界与异常价格处理自测（成员B 交付）
====================================================
任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 7 行，成员B 当日任务
「检查价格规则边界和异常价格处理」。

覆盖：
1. 回归：计划书示例、10 类别 × 3 品相组合、旧 ID 兼容（确认 Day7 加固未破坏 Day6 契约）
2. 异常原价：NaN / inf / "nan" / bool / 空串 / 负值 / 0 非赠送 / 超上限 / 临界值
3. 低价边界：0.01 元保底 1 元、极小原价 min<=max
4. 使用年限极端：负数 / 非数字 / 浮点 / 极大降档 / 仅电子产品生效
5. asking_price 极端：bool / NaN / inf / 负值 / 极大值 / 区间内
6. 免费赠送组合：is_free 与异常原价、asking_price 并存
7. 折扣表静态完整性：10×3 全覆盖、low<=high、数值落在 [0,1]

运行方式：python test_day7.py
依赖：仅标准库。
"""

import math
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.services.price_engine import (estimate_price, validate_asking_price,
                                       CATEGORY_NAMES, DISCOUNT_TABLE,
                                       normalize_category, LEGACY_CATEGORY_MAP,
                                       MAX_ORIGINAL_PRICE)

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print("[PASS]", name)
    else:
        FAIL += 1
        print("[FAIL]", name, "->", detail)


# ---------------------------------------------------------------------------
# 1) 回归：确认 Day7 加固未破坏 Day6 契约
# ---------------------------------------------------------------------------

def test_regression():
    print("\n===== 1) 回归：Day6 核心契约 =====")
    r = estimate_price("textbook", "good", 68)
    check("计划书示例 68/良好/教材 -> 27~41",
          r["estimated_min"] == 27 and r["estimated_max"] == 41, r)
    check("成功返回 5 字段（无 error）",
          set(r.keys()) == {"estimated_min", "estimated_max", "reason_text",
                            "rule_ref", "price_tip"}, r.keys())

    all_ok = True
    for cid in CATEGORY_NAMES:
        for cond in ("new_like", "good", "fair"):
            rr = estimate_price(cid, cond, 100)
            if ("error" in rr or rr["estimated_min"] > rr["estimated_max"]
                    or rr["estimated_min"] < 0):
                all_ok = False
    check("10 类 × 3 品相 30 组合全部区间合法", all_ok)

    r_old = estimate_price("school_supplies", "good", 50)
    check("旧 ID school_supplies 兼容 -> 20~25",
          r_old["estimated_min"] == 20 and r_old["estimated_max"] == 25, r_old)
    r_old2 = estimate_price("electronics", "new_like", 1000, device_age_months=3)
    check("旧参数名 device_age_months 兼容 -> 700~800",
          r_old2["estimated_min"] == 700 and r_old2["estimated_max"] == 800, r_old2)


# ---------------------------------------------------------------------------
# 2) 异常原价
# ---------------------------------------------------------------------------

def test_abnormal_prices():
    print("\n===== 2) 异常原价 =====")
    # Day7 核心修复：NaN 此前崩溃（ValueError），现在必须稳定返回错误码
    try:
        r_nan = estimate_price("textbook", "good", float("nan"))
        ok_nan = ("error" in r_nan
                  and r_nan["error"]["error_code"] == "PRICE_INVALID_FORMAT")
    except Exception as e:  # 崩溃即为 FAIL
        ok_nan = False
        print("   [EXCEPTION]", type(e).__name__, e)
    check("NaN 原价 -> PRICE_INVALID_FORMAT（不崩溃）", ok_nan,
          r_nan if 'r_nan' in dir() else "exception")

    r_inf = estimate_price("textbook", "good", float("inf"))
    check("inf 原价 -> PRICE_OUT_OF_RANGE",
          "error" in r_inf and r_inf["error"]["error_code"] == "PRICE_OUT_OF_RANGE",
          r_inf)

    r_neg_inf = estimate_price("textbook", "good", float("-inf"))
    check("-inf 原价 -> PRICE_INVALID_FORMAT（负数语义）",
          "error" in r_neg_inf and r_neg_inf["error"]["error_code"] == "PRICE_INVALID_FORMAT",
          r_neg_inf)

    r_str_nan = estimate_price("textbook", "good", "nan")
    check("字符串 'nan' -> PRICE_INVALID_FORMAT",
          "error" in r_str_nan and r_str_nan["error"]["error_code"] == "PRICE_INVALID_FORMAT",
          r_str_nan)

    r_bool = estimate_price("textbook", "good", True)
    check("bool 原价 -> PRICE_INVALID_FORMAT",
          "error" in r_bool and r_bool["error"]["error_code"] == "PRICE_INVALID_FORMAT",
          r_bool)

    r_none = estimate_price("textbook", "good", None)
    check("None 原价 -> PRICE_ORIGINAL_REQUIRED",
          "error" in r_none and r_none["error"]["error_code"] == "PRICE_ORIGINAL_REQUIRED",
          r_none)

    r_zero = estimate_price("textbook", "good", 0)
    check("0 原价非赠送 -> PRICE_INVALID_FORMAT",
          "error" in r_zero and r_zero["error"]["error_code"] == "PRICE_INVALID_FORMAT",
          r_zero)

    r_neg = estimate_price("textbook", "good", -1)
    check("负数原价 -> PRICE_INVALID_FORMAT",
          "error" in r_neg and r_neg["error"]["error_code"] == "PRICE_INVALID_FORMAT",
          r_neg)

    r_big = estimate_price("textbook", "good", MAX_ORIGINAL_PRICE + 1)
    check("超上限原价 -> PRICE_OUT_OF_RANGE",
          "error" in r_big and r_big["error"]["error_code"] == "PRICE_OUT_OF_RANGE",
          r_big)

    r_max_edge = estimate_price("textbook", "good", MAX_ORIGINAL_PRICE)
    check("临界 100000 -> 成功估价",
          "error" not in r_max_edge and r_max_edge["estimated_min"] <= r_max_edge["estimated_max"],
          r_max_edge)


# ---------------------------------------------------------------------------
# 3) 低价边界
# ---------------------------------------------------------------------------

def test_low_price_edge():
    print("\n===== 3) 低价边界 =====")
    r1 = estimate_price("life_goods", "fair", 0.01)
    check("0.01 元 / life_goods fair -> 保底 min>=1 且 min<=max",
          r1["estimated_min"] >= 1 and r1["estimated_min"] <= r1["estimated_max"], r1)

    r2 = estimate_price("electronics", "fair", 0.1)
    check("0.1 元 / electronics fair -> 保底 1~1（min<=max）",
          r2["estimated_min"] == 1 and r2["estimated_max"] == 1, r2)

    r3 = estimate_price("textbook", "new_like", 0.5)
    check("0.5 元 / textbook new_like -> 保底 1~1",
          r3["estimated_min"] == 1 and r3["estimated_max"] == 1, r3)

    r4 = estimate_price("clothing", "fair", 1)
    check("1 元 / clothing fair -> 0.15~0.3 四舍五入后 0->保底 1 元",
          r4["estimated_min"] == 1 and r4["estimated_max"] == 1, r4)


# ---------------------------------------------------------------------------
# 4) 使用年限极端
# ---------------------------------------------------------------------------

def test_months_used_extreme():
    print("\n===== 4) 使用年限极端 =====")
    base = estimate_price("electronics", "new_like", 1000)
    m_neg = estimate_price("electronics", "new_like", 1000, months_used=-5)
    check("负数年限 -> 忽略微调（等价无年限 700~850）",
          m_neg["estimated_min"] == base["estimated_min"]
          and m_neg["estimated_max"] == base["estimated_max"], m_neg)

    m_str = estimate_price("electronics", "new_like", 1000, months_used="abc")
    check("非数字年限 -> 忽略微调（700~850）",
          m_str["estimated_min"] == 700 and m_str["estimated_max"] == 850, m_str)

    m_float = estimate_price("electronics", "new_like", 1000, months_used=2.5)
    check("浮点年限 2.5 -> int 后按 2 个月微调（700~800）",
          m_float["estimated_min"] == 700 and m_float["estimated_max"] == 800, m_float)

    m_huge = estimate_price("electronics", "new_like", 1000, months_used=9999)
    check("极大年限 9999 -> 降档良好 500~700",
          m_huge["estimated_min"] == 500 and m_huge["estimated_max"] == 700, m_huge)

    m_24 = estimate_price("electronics", "new_like", 1000, months_used=24)
    check("恰好 24 个月 -> 550~700（未降档）",
          m_24["estimated_min"] == 550 and m_24["estimated_max"] == 700, m_24)

    m_25 = estimate_price("electronics", "new_like", 1000, months_used=25)
    check("25 个月 -> 降档 500~700",
          m_25["estimated_min"] == 500 and m_25["estimated_max"] == 700, m_25)

    r_tb = estimate_price("textbook", "new_like", 100, months_used=36)
    check("非电子产品忽略年限 -> 60~80",
          r_tb["estimated_min"] == 60 and r_tb["estimated_max"] == 80, r_tb)

    r_good = estimate_price("electronics", "good", 1000, months_used=3)
    check("年限仅对 new_like 生效（good 档不微调 -> 500~700）",
          r_good["estimated_min"] == 500 and r_good["estimated_max"] == 700, r_good)


# ---------------------------------------------------------------------------
# 5) asking_price 极端
# ---------------------------------------------------------------------------

def test_asking_price_extreme():
    print("\n===== 5) asking_price 极端 =====")
    r = estimate_price("textbook", "good", 68)
    lo, hi = r["estimated_min"], r["estimated_max"]  # 27~41

    r_bool = estimate_price("textbook", "good", 68, asking_price=True)
    check("bool 标价 -> 无提示（Day7 加固②）", r_bool["price_tip"] is None, r_bool.get("price_tip"))

    r_nan = estimate_price("textbook", "good", 68, asking_price=float("nan"))
    check("NaN 标价 -> 无提示", r_nan["price_tip"] is None, r_nan.get("price_tip"))

    r_inf = estimate_price("textbook", "good", 68, asking_price=float("inf"))
    check("inf 标价 -> 无提示", r_inf["price_tip"] is None, r_inf.get("price_tip"))

    r_neg = estimate_price("textbook", "good", 68, asking_price=-50)
    check("负数标价 -> 提示低于区间",
          r_neg["price_tip"] is not None and "低于建议区间" in r_neg["price_tip"],
          r_neg.get("price_tip"))

    r_huge = estimate_price("textbook", "good", 68, asking_price=5000)
    check("极大标价 -> 提示高于区间",
          r_huge["price_tip"] is not None and "高于建议区间" in r_huge["price_tip"],
          r_huge.get("price_tip"))

    r_mid = estimate_price("textbook", "good", 68, asking_price=35)
    check("区间内标价 -> 无提示", r_mid["price_tip"] is None, r_mid.get("price_tip"))

    r_str = estimate_price("textbook", "good", 68, asking_price="abc")
    check("非数字标价 -> 无提示（表单层拦截）", r_str["price_tip"] is None, r_str.get("price_tip"))

    r_edge_low = estimate_price("textbook", "good", 68, asking_price=lo)
    check("标价 = 区间下限 -> 无提示（小于才提示）", r_edge_low["price_tip"] is None,
          r_edge_low.get("price_tip"))
    r_edge_high = estimate_price("textbook", "good", 68, asking_price=hi)
    check("标价 = 区间上限 -> 无提示（大于才提示）", r_edge_high["price_tip"] is None,
          r_edge_high.get("price_tip"))

    check("独立 validate_asking_price bool -> None",
          validate_asking_price(True, lo, hi) is None)


# ---------------------------------------------------------------------------
# 6) 免费赠送组合
# ---------------------------------------------------------------------------

def test_free_combo():
    print("\n===== 6) 免费赠送组合 =====")
    r1 = estimate_price("textbook", "good", 0, is_free=True)
    check("免费赠送原价 0 -> 0~0",
          r1["estimated_min"] == 0 and r1["estimated_max"] == 0, r1)

    r2 = estimate_price("textbook", "good", None, is_free=True)
    check("免费赠送原价缺失 -> 0~0", r2["estimated_max"] == 0, r2)

    r3 = estimate_price("textbook", "good", "abc", is_free=True)
    check("免费赠送原价非法字符串 -> 0~0", r3["estimated_max"] == 0, r3)

    r4 = estimate_price("textbook", "good", -5, is_free=True)
    check("免费赠送负数原价 -> 0~0", r4["estimated_max"] == 0, r4)

    r5 = estimate_price("textbook", "good", 0, is_free=True, asking_price=100)
    check("免费赠送 + 标价 100 -> 估价 0~0 且标价提示高于区间",
          r5["estimated_min"] == 0 and r5["estimated_max"] == 0
          and r5["price_tip"] is not None, r5)

    r6 = estimate_price("electronics", "new_like", 0, is_free=True, months_used=9999)
    check("免费赠送 + 极大年限 -> 0~0（不崩不降档）",
          r6["estimated_min"] == 0 and r6["estimated_max"] == 0, r6)


# ---------------------------------------------------------------------------
# 7) 折扣表静态完整性
# ---------------------------------------------------------------------------

def test_discount_table_integrity():
    print("\n===== 7) 折扣表静态完整性 =====")
    check("10 类 × 3 品相全覆盖",
          len(DISCOUNT_TABLE) == 10
          and all(set(v.keys()) == {"new_like", "good", "fair"}
                  for v in DISCOUNT_TABLE.values()), DISCOUNT_TABLE.keys())

    bad = []
    for cid, conds in DISCOUNT_TABLE.items():
        for cond, (low, high) in conds.items():
            if not (0.0 <= low <= high <= 1.0):
                bad.append((cid, cond, low, high))
    check("全部折扣 low<=high 且落在 [0,1]", not bad, bad)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_regression()
    test_abnormal_prices()
    test_low_price_edge()
    test_months_used_extreme()
    test_asking_price_extreme()
    test_free_combo()
    test_discount_table_integrity()
    print("\n===== Day7 边界自测结果汇总：PASS=%d FAIL=%d =====" % (PASS, FAIL))
    sys.exit(0 if FAIL == 0 else 1)
