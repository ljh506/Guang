# -*- coding: utf-8 -*-
"""
Day15 自测：验证最终回归脚本可运行、全过，且手动兜底说明文档完整。
运行：python test_day15.py
"""
import os
import sys
import importlib.util

DIR = os.path.dirname(os.path.abspath(__file__))
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def main():
    # 1. 回归脚本可加载并运行
    sys.path.insert(0, DIR)
    spec = importlib.util.spec_from_file_location(
        "final_regression", os.path.join(DIR, "final_regression.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    report = mod.run_all_checks()
    names = [c["name"] for c in report["checks"]]

    check("回归脚本可运行", True)
    check("回归 passed>0 且 failed==0",
          report["passed"] > 0 and report["failed"] == 0,
          "passed=%s failed=%s" % (report["passed"], report["failed"]))

    key_checks = [
        "Day11 algorithm_check 可加载",
        "Day11 汇总全过",
        "识别：无 backend 走 fallback",
        "估价：原价缺失返回错误码",
        "匹配：计划书示例 >= 0.75 高匹配",
        "解释：高匹配生成解释文本",
        "协议：negotiating->confirmed 合法",
        "提示：识别兜底提示非空",
        "演示：3 组交换全部 >= 0.5 可匹配",
    ]
    for k in key_checks:
        check("回归包含「%s」" % k, k in names)

    # 2. 手动兜底说明文档完整
    doc = os.path.join(DIR, "手动兜底处理说明.md")
    check("手动兜底说明文档存在", os.path.isfile(doc))
    if os.path.isfile(doc):
        with open(doc, encoding="utf-8") as f:
            text = f.read()
        for sec in ("AI 识别兜底", "估价异常兜底", "匹配与交换人工介入",
                    "数据回退"):
            check("文档含「%s」" % sec, sec in text)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print("=== Day15 test: 最终检查与手动兜底 ===")
    for name, ok, detail in results:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               "（%s）" % detail if detail else ""))
    print("结果：PASS %d / FAIL %d" % (passed, failed))
    assert failed == 0, "存在 FAIL 项"
    print("Day15 test 全部通过")


if __name__ == "__main__":
    main()
