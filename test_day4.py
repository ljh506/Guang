# -*- coding: utf-8 -*-
"""
拾光Agent · Day4 自测脚本（成员B 交付）
========================================
覆盖：
1. category_normalizer：同义词/大小写/关键词/未知兜底等 ≥10 用例
2. estimate_params：参数校验各错误码触发等 ≥10 用例

运行方式：python test_day4.py
依赖：仅标准库。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from category_normalizer import (normalize, to_engine_category,
                                 CATEGORY_NAMES, CATEGORY_IDS)
from estimate_params import EstimateParams

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


def test_normalizer():
    print("\n===== category_normalizer 类别标准化测试 =====")

    # 同义词映射
    check("Math Book -> textbook",
          normalize("Math Book")["category_id"] == "textbook",
          normalize("Math Book"))
    check("高数教材 -> textbook",
          normalize("高数教材")["category_id"] == "textbook",
          normalize("高数教材"))
    check("Textbook -> textbook（大小写）",
          normalize("Textbook")["category_id"] == "textbook",
          normalize("Textbook"))
    check("iPhone -> electronics",
          normalize("iPhone")["category_id"] == "electronics",
          normalize("iPhone"))
    check("耳机 -> digital_accessories",
          normalize("耳机")["category_id"] == "digital_accessories",
          normalize("耳机"))
    check("充电宝 -> digital_accessories",
          normalize("充电宝")["category_id"] == "digital_accessories",
          normalize("充电宝"))
    check("T-Shirt -> clothing（大小写+连字符）",
          normalize("T-Shirt")["category_id"] == "clothing",
          normalize("T-Shirt"))
    check("basketball -> sports_equipment",
          normalize("basketball")["category_id"] == "sports_equipment",
          normalize("basketball"))
    check("小说 -> other_books",
          normalize("小说")["category_id"] == "other_books",
          normalize("小说"))
    check("水杯 -> life_goods（带首尾空格）",
          normalize("  水杯  ")["category_id"] == "life_goods",
          normalize("  水杯  "))

    # 关键词包含匹配
    check("高等数学教材第2版 -> textbook（关键词命中）",
          normalize("高等数学教材第2版")["category_id"] == "textbook",
          normalize("高等数学教材第2版"))

    # 未知兜底
    r_fb = normalize("unknown_xyz_123")
    check("未知输入 -> other 兜底",
          r_fb["category_id"] == "other" and r_fb["matched_by"] == "fallback",
          r_fb)
    check("兜底 confidence_adjust 为负",
          r_fb["confidence_adjust"] < 0,
          r_fb)

    # 空/None 兜底
    check("None -> other 兜底",
          normalize(None)["category_id"] == "other",
          normalize(None))

    # 类别名
    check("category_name 中文输出",
          normalize("Textbook")["category_name"] == "教材",
          normalize("Textbook"))

    # 与 Day2 引擎衔接映射
    check("stationery -> school_supplies（Day2 引擎ID）",
          to_engine_category("stationery") == "school_supplies")
    check("digital_accessories -> digital_accessory",
          to_engine_category("digital_accessories") == "digital_accessory")
    check("sports_equipment -> sports",
          to_engine_category("sports_equipment") == "sports")
    check("other_books -> books_other",
          to_engine_category("other_books") == "books_other")

    # 类别体系完整性
    check("10 个一级类别齐全",
          len(CATEGORY_IDS) == 10 and len(CATEGORY_NAMES) == 10,
          CATEGORY_IDS)


def test_estimate_params():
    print("\n===== estimate_params 参数校验测试 =====")

    # 合法输入
    p_ok = EstimateParams(category="textbook", condition="good", original_price=68,
                          asking_price=30, months_used=6, image_path="demo.jpg")
    r_ok = p_ok.validate()
    check("合法输入 -> valid", r_ok["valid"] and len(r_ok["errors"]) == 0, r_ok)

    # 类别错误
    p1 = EstimateParams(category="", condition="good", original_price=68)
    r1 = p1.validate()
    check("类别空 -> CATEGORY_INVALID",
          not r1["valid"] and any(e["error_code"] == "CATEGORY_INVALID" for e in r1["errors"]),
          r1)

    p2 = EstimateParams(category="bad_cat", condition="good", original_price=68)
    r2 = p2.validate()
    check("类别非法 -> CATEGORY_INVALID",
          not r2["valid"] and any(e["error_code"] == "CATEGORY_INVALID" for e in r2["errors"]),
          r2)

    # 品相错误
    p3 = EstimateParams(category="textbook", condition="", original_price=68)
    r3 = p3.validate()
    check("品相空 -> CONDITION_REQUIRED",
          not r3["valid"] and any(e["error_code"] == "CONDITION_REQUIRED" for e in r3["errors"]),
          r3)

    p4 = EstimateParams(category="textbook", condition="new", original_price=68)
    r4 = p4.validate()
    check("品相非法 -> CONDITION_INVALID",
          not r4["valid"] and any(e["error_code"] == "CONDITION_INVALID" for e in r4["errors"]),
          r4)

    # 原价错误
    p5 = EstimateParams(category="textbook", condition="good", original_price=None)
    r5 = p5.validate()
    check("原价缺失 -> PRICE_ORIGINAL_REQUIRED",
          not r5["valid"] and any(e["error_code"] == "PRICE_ORIGINAL_REQUIRED" for e in r5["errors"]),
          r5)

    p6 = EstimateParams(category="textbook", condition="good", original_price="abc")
    r6 = p6.validate()
    check("原价非数字 -> PRICE_INVALID_FORMAT",
          not r6["valid"] and any(e["error_code"] == "PRICE_INVALID_FORMAT" for e in r6["errors"]),
          r6)

    p7 = EstimateParams(category="textbook", condition="good", original_price=0)
    r7 = p7.validate()
    check("原价为0 -> PRICE_INVALID_FORMAT",
          not r7["valid"] and any(e["error_code"] == "PRICE_INVALID_FORMAT" for e in r7["errors"]),
          r7)

    p8 = EstimateParams(category="textbook", condition="good", original_price=200000)
    r8 = p8.validate()
    check("原价超范围 -> PRICE_OUT_OF_RANGE",
          not r8["valid"] and any(e["error_code"] == "PRICE_OUT_OF_RANGE" for e in r8["errors"]),
          r8)

    # 选填字段
    p9 = EstimateParams(category="electronics", condition="new_like", original_price=1000,
                        asking_price="800", months_used=3)
    r9 = p9.validate()
    check("选填字段合法（asking_price/months_used）-> valid",
          r9["valid"], r9)

    p10 = EstimateParams(category="electronics", condition="new_like", original_price=1000,
                         asking_price="abc")
    r10 = p10.validate()
    check("asking_price 非数字 -> PRICE_INVALID_FORMAT",
          not r10["valid"] and any(e["error_code"] == "PRICE_INVALID_FORMAT" for e in r10["errors"]),
          r10)

    p11 = EstimateParams(category="electronics", condition="new_like", original_price=1000,
                         months_used=-1)
    r11 = p11.validate()
    check("months_used 负数 -> PRICE_INVALID_FORMAT",
          not r11["valid"] and any(e["error_code"] == "PRICE_INVALID_FORMAT" for e in r11["errors"]),
          r11)

    # 多错误累积
    p12 = EstimateParams(category="", condition="", original_price=None)
    r12 = p12.validate()
    check("多错误累积（3 个错误码）",
          not r12["valid"] and len(r12["errors"]) == 3,
          r12)

    # Day5 预留字段
    check("预留 image_path/image_bytes 字段存在",
          "image_path" in EstimateParams.__dataclass_fields__
          and "image_bytes" in EstimateParams.__dataclass_fields__)


if __name__ == "__main__":
    test_normalizer()
    test_estimate_params()
    print("\n===== 结果汇总：PASS=%d FAIL=%d =====" % (PASS, FAIL))
    sys.exit(0 if FAIL == 0 else 1)
