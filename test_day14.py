# -*- coding: utf-8 -*-
"""
Day14 自测：验证《拾光Agent_成员B算法原理说明.md》完整性及关键数值与代码一致。
- 文档存在、章节齐全、核心常量（权重/阈值/折扣/错误码/类别数）与代码模块一致。
运行：python test_day14.py
"""
import os
import re
import sys

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "拾光Agent_成员B算法原理说明.md")

# 注入历史模块用于常量比对
sys.path.insert(0, r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day5_交付")
sys.path.insert(0, r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day7_交付")
sys.path.insert(0, r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day9_交付")

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def main():
    assert os.path.isfile(DOC), "原理文档不存在"
    with open(DOC, encoding="utf-8") as f:
        text = f.read()

    # 1. 文档结构与章节
    required_sections = [
        "1. AI 识别原理", "2. 估价规则原理", "3. 匹配算法原理",
        "4. 匹配解释与交换协议", "5. 交易状态机衔接",
        "6. 用户提示优化", "7. 模块依赖与接口约定", "8. 阈值与错误码速查",
    ]
    for sec in required_sections:
        check("文档含章节「%s」" % sec, sec in text)

    # 2. 关键常量与代码一致
    from recognition_pipeline import (THRESHOLD_AUTO_FILL,
                                      THRESHOLD_MANUAL_CONFIRM)
    from price_engine_day7 import (DISCOUNT_TABLE, ERROR_CODES,
                                   MAX_ORIGINAL_PRICE)
    from match_engine import (WEIGHT_CATEGORY_WISH, WEIGHT_PRICE, WEIGHT_SCHOOL,
                              THRESHOLD_HIGH, THRESHOLD_NORMAL)

    check("识别阈值 0.80 一致", "0.80" in text and THRESHOLD_AUTO_FILL == 0.80)
    check("识别阈值 0.60 一致", "0.60" in text and THRESHOLD_MANUAL_CONFIRM == 0.60)
    check("权重 0.50/0.30/0.20 一致",
          all(w in text for w in ("0.50", "0.30", "0.20"))
          and WEIGHT_CATEGORY_WISH == 0.5 and WEIGHT_PRICE == 0.3
          and WEIGHT_SCHOOL == 0.2)
    check("高匹配阈值 0.75 一致", "0.75" in text and THRESHOLD_HIGH == 0.75)
    check("普通匹配阈值 0.50 一致", "0.50" in text and THRESHOLD_NORMAL == 0.50)
    check("原价上限 100000 一致",
          "100000" in text and MAX_ORIGINAL_PRICE == 100000)

    # 3. 核心折扣表数值（教材 0.6~0.8 / 0.4~0.6 / 0.2~0.4）
    tb = DISCOUNT_TABLE["textbook"]
    check("教材折扣 new_like 0.60~0.80",
          tb["new_like"] == (0.60, 0.80) and "0.60 ~ 0.80" in text)
    check("教材折扣 good 0.40~0.60",
          tb["good"] == (0.40, 0.60) and "0.40 ~ 0.60" in text)
    check("教材折扣 fair 0.20~0.40",
          tb["fair"] == (0.20, 0.40) and "0.20 ~ 0.40" in text)

    # 4. 错误码速查
    for code in ("PRICE_ORIGINAL_REQUIRED", "PRICE_INVALID_FORMAT",
                 "PRICE_OUT_OF_RANGE", "CONDITION_REQUIRED",
                 "CONDITION_INVALID", "CATEGORY_INVALID"):
        check("错误码 %s 一致" % code,
              code in text and code in ERROR_CODES)

    # 5. 其他关键要点
    check("公式 MatchScore 权重公式", "MatchScore" in text)
    check("阈值分流 auto_fill 说明", "auto_fill" in text)
    check("sys.path 注入约定", "sys.path.insert" in text)
    check("10 类统一体系", "10" in text)
    check("免费赠送规则", "免费赠送" in text)
    check("asking_price 与估价分离", "asking_price" in text and "手填" in text)

    # 输出汇总
    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print("=== Day14 test: 原理文档完整性 ===")
    for name, ok, detail in results:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               "（%s）" % detail if detail else ""))
    print("结果：PASS %d / FAIL %d" % (passed, failed))
    assert failed == 0, "存在 FAIL 项"
    print("Day14 test 全部通过")


if __name__ == "__main__":
    main()
