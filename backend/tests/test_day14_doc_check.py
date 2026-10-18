# -*- coding: utf-8 -*-
"""Day14 成员A：比赛材料（算法原理文档）与后端代码一致性核对。

将成员B《算法原理说明》归档为 docs/算法原理说明.md 后，
以 后端代码为唯一权威来源，核对文档关键常量与后端 services 实现一致：
  识别阈值（recognition_pipeline）、估价折扣/错误码/上限（price_engine）、
  匹配权重与分级阈值（match_engine）、10 类体系（category_normalizer）。
运行：python tests/test_day14_doc_check.py
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, "app", "services"))

DOC = os.path.join(BACKEND_DIR, "..", "docs", "算法原理说明.md")

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def main():
    doc = os.path.abspath(DOC)
    assert os.path.isfile(doc), "原理文档不存在: %s" % doc
    with open(doc, encoding="utf-8") as f:
        text = f.read()

    from recognition_pipeline import (THRESHOLD_AUTO_FILL,
                                      THRESHOLD_MANUAL_CONFIRM)
    from price_engine import (DISCOUNT_TABLE, ERROR_CODES,
                              MAX_ORIGINAL_PRICE)
    from match_engine import (WEIGHT_CATEGORY_WISH, WEIGHT_PRICE, WEIGHT_SCHOOL,
                              THRESHOLD_HIGH, THRESHOLD_NORMAL)
    from category_normalizer import CATEGORY_IDS

    # 1. 章节结构
    for sec in ["1. AI 识别原理", "2. 估价规则原理", "3. 匹配算法原理",
                "4. 匹配解释与交换协议", "5. 交易状态机衔接",
                "6. 用户提示优化", "7. 模块依赖与接口约定",
                "8. 阈值与错误码速查"]:
        check("文档含章节「%s」" % sec, sec in text)

    # 2. 识别阈值
    check("识别阈值 0.80 一致", "0.80" in text and THRESHOLD_AUTO_FILL == 0.80)
    check("识别阈值 0.60 一致", "0.60" in text and THRESHOLD_MANUAL_CONFIRM == 0.60)

    # 3. 匹配权重与阈值
    check("权重 0.50/0.30/0.20 一致",
          all(w in text for w in ("0.50", "0.30", "0.20"))
          and (WEIGHT_CATEGORY_WISH, WEIGHT_PRICE, WEIGHT_SCHOOL) == (0.5, 0.3, 0.2))
    check("高匹配阈值 0.75 一致", "0.75" in text and THRESHOLD_HIGH == 0.75)
    check("普通匹配阈值 0.50 一致", "0.50" in text and THRESHOLD_NORMAL == 0.50)

    # 4. 估价折扣（教材四档）
    tb = DISCOUNT_TABLE["textbook"]
    check("教材折扣 new_like 0.60~0.80",
          tb["new_like"] == (0.60, 0.80) and "0.60 ~ 0.80" in text)
    check("教材折扣 good 0.40~0.60",
          tb["good"] == (0.40, 0.60) and "0.40 ~ 0.60" in text)
    check("教材折扣 fair 0.20~0.40",
          tb["fair"] == (0.20, 0.40) and "0.20 ~ 0.40" in text)

    # 5. 错误码与上限
    for code in ("PRICE_ORIGINAL_REQUIRED", "PRICE_INVALID_FORMAT",
                 "PRICE_OUT_OF_RANGE", "CONDITION_REQUIRED",
                 "CONDITION_INVALID", "CATEGORY_INVALID"):
        check("错误码 %s 一致" % code, code in text and code in ERROR_CODES)
    check("原价上限 100000 一致", "100000" in text and MAX_ORIGINAL_PRICE == 100000)

    # 6. 10 类体系
    check("后端 10 类体系", "10" in text and len(CATEGORY_IDS) == 10)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print("=== Day14 后端版：原理文档与后端代码一致性核对 ===")
    for name, ok, detail in results:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               "（%s）" % detail if detail else ""))
    print("结果：PASS %d / FAIL %d" % (passed, failed))
    return failed


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
