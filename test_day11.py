# -*- coding: utf-8 -*-
"""
拾光Agent · Day11 算法检查自测脚本 test_day11.py（成员B Day 11 交付）
========================================================
覆盖 algorithm_check.run_all_checks() 全部 8 项算法检查：
- 估价：折扣表与计划书§四一致、计划书示例回归、边界复核（NaN/inf/负/0/布尔/
  超上限/保底/免费）、电子产品年限微调降档
- 匹配：权重 50/30/20 与阈值 0.75/0.50、计划书示例回归、边界复核（缺失/免费/跨校/
  单向/满分）
- AI：识别输出结构与 Day4 统一 10 类一致

另做算法检查模块自身接口回归：
- run_all_checks 返回结构（checks/passed/failed/summary）
- 单检查项字段完整性（name/passed/detail）

运行：python test_day11.py（退出码 0 全部 PASS；非 0 有 FAIL）。
依赖：仅标准库；自动注入 Day4/Day5/Day7/Day9 交付目录。
"""

import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE,
          r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day9_交付",
          r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day7_交付",
          r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day5_交付",
          r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day4_交付"):
    if p not in sys.path:
        sys.path.insert(0, p)

from algorithm_check import run_all_checks, CHECK_FUNCS, UNIFIED_CATEGORIES

PASS = 0
FAIL = 0
FAIL_MSGS = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("[PASS] %s" % name)
    else:
        FAIL += 1
        FAIL_MSGS.append(name + (("：" + detail) if detail else ""))
        print("[FAIL] %s %s" % (name, detail))


report = run_all_checks()

# 1. 报告结构
check("报告含 checks 列表", isinstance(report["checks"], list))
check("报告含 passed/failed/summary 字段",
      "passed" in report and "failed" in report and "summary" in report)
check("passed + failed = 总检查项数",
      report["passed"] + report["failed"] == len(CHECK_FUNCS),
      "passed=%d failed=%d total=%d" % (report["passed"], report["failed"], len(CHECK_FUNCS)))
check("摘要文本格式正确", "算法检查完成" in report["summary"] and "共" in report["summary"])

# 2. 逐检查项
by_name = {c["name"]: c for c in report["checks"]}

check("检查项数量为 8", len(report["checks"]) == 8, "实得 %d" % len(report["checks"]))

for c in report["checks"]:
    check("检查项字段完整（%s）" % c["name"],
          {"name", "passed", "detail"} <= set(c.keys()))

check("估价·折扣表与计划书§四一致",
      by_name["估价·折扣表与计划书§四一致"]["passed"])
check("估价·计划书示例回归（68元/良好/教材=27~41）",
      by_name["估价·计划书示例回归（68元/良好/教材=27~41）"]["passed"])
check("估价·边界复核",
      by_name["估价·边界复核（NaN/inf/负/0/布尔/超上限/保底）"]["passed"])
check("估价·电子产品年限微调/降档",
      by_name["估价·电子产品年限微调/降档"]["passed"])
check("匹配·权重50/30/20与阈值0.75/0.50",
      by_name["匹配·权重50/30/20与阈值0.75/0.50"]["passed"])
check("匹配·计划书示例回归（30/32同校双向=高匹配）",
      by_name["匹配·计划书示例回归（30/32同校双向=高匹配）"]["passed"])
check("匹配·边界复核",
      by_name["匹配·边界复核（缺失/免费/跨校/单向/满分）"]["passed"])
check("AI·识别输出结构与类别表一致性",
      by_name["AI·识别输出结构与类别表一致性"]["passed"])

# 3. 关键断言细节复核
detail = by_name["估价·计划书示例回归（68元/良好/教材=27~41）"]["detail"]
check("示例回归说明含 27~41", "27~41" in detail)
detail = by_name["匹配·计划书示例回归（30/32同校双向=高匹配）"]["detail"]
check("匹配示例回归说明含 high", "high" in detail)
detail = by_name["匹配·权重50/30/20与阈值0.75/0.50"]["detail"]
check("权重说明含 0.5/0.3/0.2 与 0.75/0.50",
      "0.5/0.3/0.2" in detail and "0.75/0.50" in detail)
detail = by_name["AI·识别输出结构与类别表一致性"]["detail"]
check("AI 检查说明含统一10类", "统一 10 类" in detail)

# 4. 全部检查通过
check("全部 8 项算法检查通过", report["failed"] == 0,
      "failed=%d" % report["failed"])
check("AI 类别表常量与 Day4 统一 10 类一致", len(UNIFIED_CATEGORIES) == 10)

# 汇总
print("\n==============================")
print("Day11 算法检查自测汇总：")
print("PASS: %d / FAIL: %d / 总用例: %d" % (PASS, FAIL, PASS + FAIL))
if FAIL_MSGS:
    print("失败用例：")
    for name in FAIL_MSGS:
        print("  - %s" % name)
    sys.exit(1)
print("全部通过")
sys.exit(0)
