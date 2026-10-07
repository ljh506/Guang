# -*- coding: utf-8 -*-
"""
拾光Agent · Day2 自测脚本（成员B 交付）
========================================
验证内容：
1. price_engine：计划书示例（68元/良好/教材 -> 27~41 建议区间）+ 边界情况
2. ai_client：mock 验证置信度阈值分流 + 失败兜底
3. 用户手填标价校验（asking_price -> price_tip）

运行方式：
    python test_day2.py
（无第三方依赖，标准库即可）
"""

import os
import sys

# 集成进后端工程后，算法模块位于 app/services/
_SERVICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "app", "services")
sys.path.insert(0, os.path.abspath(_SERVICES_DIR))

from price_engine import (estimate_price, validate_asking_price,
                          build_reason_text, DISCOUNT_TABLE,
                          CATEGORY_NAMES, CONDITION_NAMES)
from ai_client import (MockAIClient, classify_confidence,
                       map_label_to_category, AIClient)

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


def test_price_engine():
    print("\n===== price_engine 测试 =====")

    # 1) 计划书示例：68元/良好/教材 -> 27~41
    r = estimate_price("textbook", "good", 68)
    check("计划书示例 68/良好/教材 -> 27~41",
          r.get("estimated_min") == 27 and r.get("estimated_max") == 41,
          r)
    check("reason_text 含折扣依据",
          "0.4~0.6" in r.get("reason_text", "") and "27~41" in r.get("reason_text", ""),
          r.get("reason_text"))

    # 2) 其他类别抽查：衣物 良好 100 元 -> 30~40
    r2 = estimate_price("clothing", "good", 100)
    check("衣物/良好/100 -> 30~40",
          r2.get("estimated_min") == 30 and r2.get("estimated_max") == 40,
          r2)

    # 3) 边界：原价缺失
    r3 = estimate_price("textbook", "good", None)
    check("原价缺失 -> PRICE_ORIGINAL_REQUIRED",
          r3.get("error", {}).get("error_code") == "PRICE_ORIGINAL_REQUIRED",
          r3)

    # 4) 边界：原价非数字
    r4 = estimate_price("textbook", "good", "abc")
    check("原价非数字 -> PRICE_INVALID_FORMAT",
          r4.get("error", {}).get("error_code") == "PRICE_INVALID_FORMAT",
          r4)

    # 5) 边界：原价超范围
    r5 = estimate_price("textbook", "good", 200000)
    check("原价超范围 -> PRICE_OUT_OF_RANGE",
          r5.get("error", {}).get("error_code") == "PRICE_OUT_OF_RANGE",
          r5)

    # 6) 边界：品相缺省
    r6 = estimate_price("textbook", "", 68)
    check("品相缺省 -> CONDITION_REQUIRED",
          r6.get("error", {}).get("error_code") == "CONDITION_REQUIRED",
          r6)

    # 7) 边界：品相非法
    r7 = estimate_price("textbook", "new", 68)
    check("品相非法 -> CONDITION_INVALID",
          r7.get("error", {}).get("error_code") == "CONDITION_INVALID",
          r7)

    # 8) 边界：类别非法
    r8 = estimate_price("bad_category", "good", 68)
    check("类别非法 -> CATEGORY_INVALID",
          r8.get("error", {}).get("error_code") == "CATEGORY_INVALID",
          r8)

    # 9) 免费赠送：估价 [0,0]
    r9 = estimate_price("textbook", "good", 0, is_free=True)
    check("免费赠送 -> 0~0 且文本正确",
          r9.get("estimated_min") == 0 and r9.get("estimated_max") == 0
          and "免费赠送" in r9.get("reason_text", ""),
          r9)

    # 10) 电子产品年限微调
    r10 = estimate_price("electronics", "new_like", 1000, device_age_months=3)
    check("电子产品/全新/1000/使用3个月 -> 700~780",
          r10.get("estimated_min") == 700 and r10.get("estimated_max") == 780,
          r10)

    # 11) 字符串数字原价
    r11 = estimate_price("textbook", "good", "68")
    check("字符串原价 '68' -> 27~41",
          r11.get("estimated_min") == 27 and r11.get("estimated_max") == 41,
          r11)


def test_asking_price_tip():
    print("\n===== 标价校验（price_tip）测试 =====")

    # 建议区间 27~41
    tip_low = validate_asking_price(10, 27, 41)
    check("标价低于区间 -> 提示", tip_low is not None and "低于" in tip_low, tip_low)

    tip_mid = validate_asking_price(30, 27, 41)
    check("标价在区间内 -> 无提示", tip_mid is None, tip_mid)

    tip_high = validate_asking_price(60, 27, 41)
    check("标价高于区间 -> 提示", tip_high is not None and "高于" in tip_high, tip_high)

    tip_empty = validate_asking_price("", 27, 41)
    check("空标价 -> 无提示", tip_empty is None, tip_empty)


def test_ai_client():
    print("\n===== ai_client 阈值分流测试 =====")

    mock = MockAIClient()
    mock.add_success("textbook", 0.96)   # >= 0.80 -> auto_fill
    mock.add_success("t-shirt", 0.70)    # 0.60~0.80 -> manual_confirm
    mock.add_success("umbrella", 0.40)   # < 0.60 -> manual_select
    mock.add_failure("服务超时")          # 异常 -> fallback
    mock.add_success("unknown_label_x", 0.99)  # 无法映射 -> other + auto_fill

    r1 = mock.recognize("img1.jpg")
    check("0.96 -> auto_fill + textbook",
          r1["status"] == "auto_fill" and r1["category_id"] == "textbook"
          and r1["category_name"] == "教材" and r1["fallback"] is False,
          r1)

    r2 = mock.recognize("img2.jpg")
    check("0.70 -> manual_confirm + clothing",
          r2["status"] == "manual_confirm" and r2["category_id"] == "clothing"
          and r2["fallback"] is False,
          r2)

    r3 = mock.recognize("img3.jpg")
    check("0.40 -> manual_select + life_goods + fallback=True",
          r3["status"] == "manual_select" and r3["category_id"] == "life_goods"
          and r3["fallback"] is True,
          r3)

    r4 = mock.recognize("img4.jpg")
    check("异常 -> fallback + 无类别 + 提示文案",
          r4["status"] == "fallback" and r4["category_id"] is None
          and r4["fallback"] is True and r4["fallback_reason"],
          r4)

    r5 = mock.recognize("img5.jpg")
    check("未知标签 -> other 兜底 + auto_fill",
          r5["status"] == "auto_fill" and r5["category_id"] == "other",
          r5)

    # 单独验证阈值函数
    check("classify_confidence(0.95) -> auto_fill",
          classify_confidence(0.95) == "auto_fill")
    check("classify_confidence(0.65) -> manual_confirm",
          classify_confidence(0.65) == "manual_confirm")
    check("classify_confidence(0.30) -> manual_select",
          classify_confidence(0.30) == "manual_select")
    check("classify_confidence(None) -> manual_select",
          classify_confidence(None) == "manual_select")

    # 标签映射
    check("map_label_to_category('Math Book') -> textbook",
          map_label_to_category("Math Book") == "textbook")
    check("map_label_to_category('zzz') -> other",
          map_label_to_category("zzz") == "other")

    # 真实 AIClient（未配置 backend）-> 默认失败兜底
    real = AIClient()
    r6 = real.recognize("nofile.jpg")
    check("未配置 backend -> fallback 兜底",
          r6["status"] == "fallback" and r6["fallback"] is True,
          r6)


def test_consistency():
    print("\n===== 与 Day1 文档一致性测试 =====")
    check("折扣表 10 个类别全覆盖",
          set(DISCOUNT_TABLE.keys()) == set(CATEGORY_NAMES.keys()),
          set(DISCOUNT_TABLE.keys()) ^ set(CATEGORY_NAMES.keys()))
    check("每个类别 3 个品相全覆盖",
          all(set(CONDITION_NAMES.keys()) == set(d.keys()) for d in DISCOUNT_TABLE.values()))
    check("教材良好折扣 0.4~0.6",
          DISCOUNT_TABLE["textbook"]["good"] == (0.40, 0.60))
    check("电子产品全新折扣 0.7~0.85（视年限）",
          DISCOUNT_TABLE["electronics"]["new_like"] == (0.70, 0.85))


if __name__ == "__main__":
    test_price_engine()
    test_asking_price_tip()
    test_ai_client()
    test_consistency()
    print("\n===== 结果汇总：PASS=%d FAIL=%d =====" % (PASS, FAIL))
    sys.exit(0 if FAIL == 0 else 1)
