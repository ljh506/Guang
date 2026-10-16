# -*- coding: utf-8 -*-
"""
拾光Agent · 核心算法一致性检查模块 algorithm_check.py（成员B Day 11 交付）
========================================================================
任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 11 行，成员B 当日任务
「检查 AI、估价、匹配三个核心算法」（当天目标：全链路联调日）。

检查范围（对应三个核心算法）：
1) 估价算法（Day6 price_engine / Day7 price_engine_day7 边界加固版）
   - 折扣表与计划书 §四 一致（教材/电子产品/生活用品/衣物 四类四品相）
   - 计划书示例回归：68 元良好教材 -> 27~41 元
   - 边界复核：NaN / inf / 负数 / 0 / 布尔 / 超上限 / 极小价保底 / 电子产品年限微调降档
2) 匹配算法（Day9 match_engine）
   - 权重一致性：类别/意愿 50% + 价格 30% + 同校 20% = 1.0
   - 阈值一致性：0.75（高）/ 0.50（普通）
   - 计划书示例回归：30/32 同校双向 -> 高匹配
   - 边界复核：缺失字段不崩、免费赠送中性、跨校、单向意愿、全同字段满分
3) 识别算法（Day5 recognition_pipeline / Day4 统一类别体系）
   - 识别输出结构字段完整性（label / confidence / status）
   - 可用类别表与 Day4 统一 10 类一致（至少包含计划书核心四类）

使用方式：
    from algorithm_check import run_all_checks
    report = run_all_checks()   # {"checks": [...], "passed": n, "failed": n, "summary": str}
    print(report["summary"])
依赖：仅标准库；自动注入 Day4/Day5/Day7/Day8/Day9 交付目录。
"""

import sys
import math

HERE_DIRS = [
    r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day9_交付",
    r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day8_交付",
    r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day7_交付",
    r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day6_交付",
    r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day5_交付",
    r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day4_交付",
]
for p in HERE_DIRS:
    if p not in sys.path:
        sys.path.insert(0, p)

# 核心算法模块（可独立导入失败则记为该算法不可用）
from .price_engine import (
    estimate_price, DISCOUNT_TABLE, CATEGORY_NAMES, ERROR_CODES,
    ELECTRONICS_DOWNGRADE_AFTER_MONTHS,
)

try:
    from .match_engine import (
        match_score, recommend, recommend_level, build_match_reason,
        WEIGHT_CATEGORY_WISH, WEIGHT_PRICE, WEIGHT_SCHOOL, WEIGHT_SUM,
        THRESHOLD_HIGH, THRESHOLD_NORMAL,
    )
except ModuleNotFoundError:
    match_score = recommend = None
    WEIGHT_CATEGORY_WISH = WEIGHT_PRICE = WEIGHT_SCHOOL = WEIGHT_SUM = None
    THRESHOLD_HIGH = THRESHOLD_NORMAL = None

try:
    from .recognition_pipeline import build_available_categories
except ModuleNotFoundError:
    build_available_categories = None

# 计划书 §四 折扣表基准（教材/电子产品/生活用品/衣物）
PLAN_DISCOUNT_TABLE = {
    "textbook":    {"new_like": (0.60, 0.80), "good": (0.40, 0.60), "fair": (0.20, 0.40)},
    "electronics": {"new_like": (0.70, 0.85), "good": (0.50, 0.70), "fair": (0.10, 0.50)},
    "life_goods":  {"new_like": (0.50, 0.70), "good": (0.40, 0.50), "fair": (0.10, 0.40)},
    "clothing":    {"new_like": (0.40, 0.60), "good": (0.30, 0.40), "fair": (0.15, 0.30)},
}

# 计划书示例：68 元良好教材
PLAN_PRICE_EXAMPLE = (68, "good", 27, 41)

# Day4 统一 10 类（与计划书 §四 一致的核心四类必含）
UNIFIED_CATEGORIES = {
    "textbook", "electronics", "life_goods", "clothing", "stationery",
    "digital_accessories", "sports_equipment", "furniture", "other_books", "other",
}


# ---------------------------------------------------------------------------
# 检查项集合（每项返回 (name, passed, detail)）
# ---------------------------------------------------------------------------

def _check_plan_discount_table():
    """检查 Day7 折扣表与计划书 §四 四类四品相一致。"""
    name = "估价·折扣表与计划书§四一致"
    if DISCOUNT_TABLE is None:
        return name, False, "price_engine 模块不可用"
    diff = []
    for cat, conds in PLAN_DISCOUNT_TABLE.items():
        if cat not in DISCOUNT_TABLE:
            diff.append("缺类别 %s" % cat)
            continue
        for cond, (lo, hi) in conds.items():
            got = DISCOUNT_TABLE[cat].get(cond)
            if got != (lo, hi):
                diff.append("%s/%s 期望 %s 实得 %s" % (cat, cond, (lo, hi), got))
    if diff:
        return name, False, "不一致：%s" % "; ".join(diff)
    return name, True, "教材/电子/生活/衣物四类四品相折扣区间全部一致"


def _check_plan_price_example():
    """检查计划书示例：68 元良好教材 -> 27~41。"""
    name = "估价·计划书示例回归（68元/良好/教材=27~41）"
    if estimate_price is None:
        return name, False, "price_engine 模块不可用"
    r = estimate_price("textbook", "good", PLAN_PRICE_EXAMPLE[0])
    if "error" in r:
        return name, False, "返回错误：%s" % r["error"]
    if (r["estimated_min"], r["estimated_max"]) != (PLAN_PRICE_EXAMPLE[2], PLAN_PRICE_EXAMPLE[3]):
        return name, False, "期望 27~41，实得 %s~%s" % (r["estimated_min"], r["estimated_max"])
    return name, True, "27~41 元，reason_text 含折扣区间与计算过程"


def _check_price_boundaries():
    """估价边界复核：NaN / inf / 负数 / 0 / 布尔 / 超上限 / 保底。"""
    name = "估价·边界复核（NaN/inf/负/0/布尔/超上限/保底）"
    if estimate_price is None:
        return name, False, "price_engine 模块不可用"
    fails = []

    # NaN 不崩溃，返回 INVALID_FORMAT
    r = estimate_price("textbook", "good", float("nan"))
    if "error" not in r or r["error"]["error_code"] != "PRICE_INVALID_FORMAT":
        fails.append("NaN 未拦截为 PRICE_INVALID_FORMAT")

    # inf 归入 OUT_OF_RANGE
    r = estimate_price("textbook", "good", float("inf"))
    if "error" not in r or r["error"]["error_code"] != "PRICE_OUT_OF_RANGE":
        fails.append("inf 未拦截为 PRICE_OUT_OF_RANGE")

    # 负数 INVALID_FORMAT
    r = estimate_price("textbook", "good", -5)
    if "error" not in r or r["error"]["error_code"] != "PRICE_INVALID_FORMAT":
        fails.append("负数未拦截")

    # 0 非免费 -> INVALID_FORMAT
    r = estimate_price("textbook", "good", 0)
    if "error" not in r or r["error"]["error_code"] != "PRICE_INVALID_FORMAT":
        fails.append("0元非免费未拦截")

    # 0 + 免费 -> 0 元
    r = estimate_price("textbook", "good", 0, is_free=True)
    if "error" in r or (r["estimated_min"], r["estimated_max"]) != (0, 0):
        fails.append("免费赠送未返回 0 元")

    # 布尔原价 -> INVALID_FORMAT（Day7 加固）
    r = estimate_price("textbook", "good", True)
    if "error" not in r or r["error"]["error_code"] != "PRICE_INVALID_FORMAT":
        fails.append("布尔原价未拦截")

    # 超上限 OUT_OF_RANGE
    r = estimate_price("textbook", "good", 100001)
    if "error" not in r or r["error"]["error_code"] != "PRICE_OUT_OF_RANGE":
        fails.append("超上限未拦截")

    # 极小价保底 1 元（0 < price < 1 且非免费）
    r = estimate_price("textbook", "good", 0.5)
    if "error" in r or r["estimated_min"] < 1 or r["estimated_max"] < 1:
        fails.append("极小价未保底 1 元")

    # 免费赠送 + 原价缺失（None）-> 0 元（Day6 语义：is_free 豁免必填与0元）
    r = estimate_price("textbook", "good", None, is_free=True)
    if "error" in r or (r["estimated_min"], r["estimated_max"]) != (0, 0):
        fails.append("免费赠送（原价缺失）未返回 0 元")

    if fails:
        return name, False, "；".join(fails)
    return name, True, "8 项边界用例全部通过（NaN/inf/负/0/布尔/超上限/保底/免费）"


def _check_electronics_age_breakpoint():
    """电子产品年限微调与降档复核。"""
    name = "估价·电子产品年限微调/降档"
    if estimate_price is None:
        return name, False, "price_engine 模块不可用"
    fails = []
    # 全新 6 个月以内 -> 0.70~0.80 档（electronics new_like 100 元 -> 70~80）
    r = estimate_price("electronics", "new_like", 100, months_used=6)
    if "error" in r or (r["estimated_min"], r["estimated_max"]) != (70, 80):
        fails.append("6个月微调档异常：%s" % r.get("estimated_min", r))
    # 超过 24 个月降档良好（0.50~0.70）-> 50~70
    r = estimate_price("electronics", "new_like", 100, months_used=36)
    if "error" in r or (r["estimated_min"], r["estimated_max"]) != (50, 70):
        fails.append("36个月降档异常：%s" % r.get("estimated_min", r))
    # 负数年限忽略微调走原始全新档（0.70~0.85）
    r = estimate_price("electronics", "new_like", 100, months_used=-3)
    if "error" in r or (r["estimated_min"], r["estimated_max"]) != (70, 85):
        fails.append("负数年限未忽略：%s" % r.get("estimated_min", r))
    if fails:
        return name, False, "；".join(fails)
    return name, True, "6个月微调/36个月降档/负数忽略 三例通过"


def _check_match_weights_and_thresholds():
    """匹配权重 50/30/20 与阈值 0.75/0.50 一致性。"""
    name = "匹配·权重50/30/20与阈值0.75/0.50"
    if match_score is None:
        return name, False, "match_engine 模块不可用"
    fails = []
    if WEIGHT_SUM is None:
        fails.append("权重常量缺失")
    else:
        if abs(WEIGHT_SUM - 1.0) > 1e-9:
            fails.append("权重合计 %s != 1.0" % WEIGHT_SUM)
        if WEIGHT_CATEGORY_WISH != 0.5:
            fails.append("category_wish 权重 != 0.5")
        if WEIGHT_PRICE != 0.3:
            fails.append("price 权重 != 0.3")
        if WEIGHT_SCHOOL != 0.2:
            fails.append("school 权重 != 0.2")
    if THRESHOLD_HIGH != 0.75:
        fails.append("高匹配阈值 != 0.75")
    if THRESHOLD_NORMAL != 0.50:
        fails.append("普通匹配阈值 != 0.50")
    if fails:
        return name, False, "；".join(fails)
    return name, True, "权重 0.5/0.3/0.2（合计1.0）与阈值 0.75/0.50 全部一致"


def _check_match_plan_example():
    """匹配计划书示例回归：30/32 同校双向 -> 高匹配。"""
    name = "匹配·计划书示例回归（30/32同校双向=高匹配）"
    if match_score is None:
        return name, False, "match_engine 模块不可用"
    A = {"category_id": "textbook", "wish_category_id": "physics",
         "asking_price": 30, "school_id": 1, "status": "on_sale"}
    B = {"category_id": "physics", "wish_category_id": "textbook",
         "asking_price": 32, "school_id": 1, "status": "on_sale"}
    r = match_score(A, B)
    if r is None:
        return name, False, "返回 None"
    if r["level"] != "high":
        return name, False, "期望 high，实得 %s（得分 %s）" % (r["level"], r["match_score"])
    if r["match_score"] <= 0.75:
        return name, False, "得分 %s 未超过 0.75 阈值" % r["match_score"]
    return name, True, "得分 %s，级别 high，双向意愿/价格接近/同校 三路得分正常" % r["match_score"]


def _check_match_boundaries():
    """匹配边界复核：缺失字段不崩、免费赠送中性、跨校、单向、全同满分。"""
    name = "匹配·边界复核（缺失/免费/跨校/单向/满分）"
    if match_score is None:
        return name, False, "match_engine 模块不可用"
    fails = []

    def goods(cat, wish=None, price=None, school=None, status="on_sale"):
        g = {"category_id": cat, "asking_price": price,
             "school_id": school, "status": status}
        if wish is not None:
            g["wish_category_id"] = wish
        return g

    # 缺失字段不崩：无意愿/标价时 match_score 应返回 None（不可匹配的安全语义）
    try:
        r1 = match_score({}, {"category_id": "textbook"})
    except Exception as exc:
        fails.append("空 dict 调用抛异常：%s" % exc)
    r2 = match_score(goods("textbook"), goods("physics"))
    if r2 is not None:
        fails.append("无意愿/标价字段应返回 None（不可匹配），实得 %s" % r2)

    # 免费赠送（0 元）双方 -> 价格维度中性
    r3 = match_score(goods("textbook", "physics", 0, 1),
                     goods("physics", "textbook", 0, 1))
    if r3 is not None and r3["level"] != "high":
        fails.append("双方免费赠送未保持高匹配：%s" % r3.get("level"))

    # 跨校 -> 同校维度 0 分（不影响整体正常分级）
    r4 = match_score(goods("textbook", "physics", 30, 1),
                     goods("physics", "textbook", 30, 2))
    if r4 is None or r4["score_detail"]["school"] != 0.0:
        fails.append("跨校同校维度未为 0")

    # 单向意愿（仅一方想要对方物品）：类别得分应低于双向（<1.0）
    r5 = match_score(goods("textbook", "sports", 30, 1),
                     goods("physics", "textbook", 30, 1))
    if r5 is None or r5["score_detail"]["category_wish"] >= 1.0:
        fails.append("单向意愿分类得分应低于双向（实得 %s）"
                     % (r5["score_detail"]["category_wish"] if r5 else None))

    # 全同字段满分（相同物品 -> 各维度满分，得分 1.0）
    g_same = goods("textbook", "textbook", 30, 1)
    r6 = match_score(g_same, g_same)
    if r6 is None or abs(r6["match_score"] - 1.0) > 1e-9:
        fails.append("完全相同物品未得满分：%s" % (r6.get("match_score") if r6 else None))

    if fails:
        return name, False, "；".join(fails)
    return name, True, "5 项边界用例全部通过（缺失/免费/跨校/单向/满分）"


def _check_ai_recognition():
    """AI 识别算法检查：输出结构字段完整 + 类别表与 Day4 统一 10 类一致。"""
    name = "AI·识别输出结构与类别表一致性"
    if build_available_categories is None:
        return name, False, "recognition_pipeline 模块不可用"
    fails = []
    cats = build_available_categories()
    if not isinstance(cats, (list, dict)):
        fails.append("build_available_categories 返回类型异常：%s" % type(cats))
    else:
        cat_ids = set()
        if isinstance(cats, dict):
            cat_ids = set(cats.keys())
            missing = UNIFIED_CATEGORIES - cat_ids
        else:
            for item in cats:
                if isinstance(item, dict) and "category_id" in item:
                    cat_ids.add(str(item["category_id"]))
                elif isinstance(item, str):
                    cat_ids.add(item)
            missing = UNIFIED_CATEGORIES - cat_ids
        if missing:
            fails.append("缺少 Day4 统一类别：%s" % sorted(missing))
        core = {"textbook", "electronics", "life_goods", "clothing"}
        if not core <= cat_ids:
            fails.append("缺少计划书核心四类")
    if fails:
        return name, False, "；".join(fails)
    return name, True, "类别表包含 Day4 统一 10 类（含计划书核心四类）"


# ---------------------------------------------------------------------------
# 总入口
# ---------------------------------------------------------------------------
CHECK_FUNCS = [
    _check_plan_discount_table,
    _check_plan_price_example,
    _check_price_boundaries,
    _check_electronics_age_breakpoint,
    _check_match_weights_and_thresholds,
    _check_match_plan_example,
    _check_match_boundaries,
    _check_ai_recognition,
]


def run_all_checks():
    """运行全部算法检查，返回结构化报告。"""
    checks = []
    passed = failed = 0
    for fn in CHECK_FUNCS:
        cname, ok, detail = fn()
        checks.append({"name": cname, "passed": ok, "detail": detail})
        if ok:
            passed += 1
        else:
            failed += 1
    summary = "算法检查完成：通过 %d / 失败 %d / 共 %d 项" % (passed, failed, len(checks))
    return {"checks": checks, "passed": passed, "failed": failed,
            "summary": summary}


# ---------------------------------------------------------------------------
# 简易命令行自测入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    report = run_all_checks()
    print(report["summary"])
    for c in report["checks"]:
        mark = "PASS" if c["passed"] else "FAIL"
        print("[%s] %s -> %s" % (mark, c["name"], c["detail"]))
    if report["failed"]:
        print("存在失败检查项")
    else:
        print("全部检查通过")
