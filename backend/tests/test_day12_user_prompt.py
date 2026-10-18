# -*- coding: utf-8 -*-
"""
拾光Agent · Day12 自测脚本 test_day12.py（成员B Day 12 交付）
================================================================
覆盖 user_prompt.py 全部提示分支：
- AI 识别：auto_fill / manual_confirm / manual_select / fallback（含
  缺少图片、输入无效、服务不可用、超时、无标签、置信度非法、置信度越界、
  数据异常、未知状态、result=None）
- 估价：成功无提示 / 成功标价低于区间 / 成功标价高于区间 / 免费赠送 /
       六个错误码 / 未知错误码 / result=None / 区间异常
- 组合入口 build_publish_tips

运行方式：python test_day12.py
依赖：仅标准库。
"""

import sys
import os

# 注入后端工程根（保证从任意 cwd 运行都能 import app.services.user_prompt）
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.user_prompt import (  # noqa: E402
    build_recognition_tip, build_price_tip, build_publish_tips,
    ERROR_CODE_TIPS, SCENES,
)

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print("  [PASS] %s" % name)
    else:
        _FAIL += 1
        print("  [FAIL] %s %s" % (name, detail))


def main():
    print("=== Day12 test: user_prompt.py ===")

    # ---------- 1. AI 识别提示 ----------
    print("[AI识别提示]")

    # 1.1 auto_fill：自动填入成功，level=good
    r = build_recognition_tip({"status": "auto_fill", "category_name": "教材",
                               "confidence": 0.95, "raw_label": "textbook",
                               "fallback_reason": None})
    check("auto_fill level=good", r["level"] == "good")
    check("auto_fill 含类别名", "教材" in r["message"])
    check("auto_fill 置信度 95%", "95%" in r["message"])
    check("auto_fill action 为空", r["action"] is None)

    # 1.2 manual_confirm：需确认，level=warn
    r = build_recognition_tip({"status": "manual_confirm", "category_name": "衣物",
                               "confidence": 0.72, "raw_label": "t-shirt",
                               "fallback_reason": None})
    check("manual_confirm level=warn", r["level"] == "warn")
    check("manual_confirm 含请确认", "请确认" in r["title"])
    check("manual_confirm 含 72%", "72%" in r["message"])

    # 1.3 manual_select：置信度低手动选择
    r = build_recognition_tip({"status": "manual_select", "category_name": None,
                               "confidence": 0.4, "raw_label": "weird",
                               "fallback_reason": None})
    check("manual_select level=warn", r["level"] == "warn")
    check("manual_select 含手动选择", "手动选择" in r["message"])

    # 1.4 fallback：服务不可用
    r = build_recognition_tip({"status": "fallback", "raw_label": None,
                               "fallback_reason": "AI识别服务不可用"})
    check("fallback level=error", r["level"] == "error")
    check("fallback 服务不可用文案", "AI识别服务暂时不可用" in r["message"])

    # 1.5 fallback：缺少图片输入
    r = build_recognition_tip({"status": "fallback", "raw_label": None,
                               "fallback_reason": "缺少图片输入（image_path 或 image_bytes）"})
    check("fallback 缺少图片文案", "请先上传" in r["message"])

    # 1.6 fallback：图片输入无效
    r = build_recognition_tip({"status": "fallback", "raw_label": None,
                               "fallback_reason": "图片输入无效：文件损坏"})
    check("fallback 图片无效文案", "无法读取" in r["message"])

    # 1.7 fallback：超时
    r = build_recognition_tip({"status": "fallback", "raw_label": None,
                               "fallback_reason": "AI识别服务响应超时"})
    check("fallback 超时文案", "超时" in r["message"])

    # 1.8 fallback：无标签
    r = build_recognition_tip({"status": "fallback", "raw_label": None,
                               "fallback_reason": "AI识别返回数据异常（无标签），请手动选择类别"})
    check("fallback 无标签文案", "未返回结果" in r["message"])

    # 1.9 fallback：置信度非法 / 越界 / 数据异常
    for reason in ("AI识别置信度非法，请手动选择类别",
                   "AI识别置信度越界，请手动选择类别",
                   "AI识别返回数据异常，请手动选择类别"):
        r = build_recognition_tip({"status": "fallback", "raw_label": None,
                                   "fallback_reason": reason})
        check("fallback 归类 %s" % reason[:6], r["level"] == "error")

    # 1.10 fallback：未知原因 -> 通用兜底
    r = build_recognition_tip({"status": "fallback", "raw_label": None,
                               "fallback_reason": "某些奇怪错误"})
    check("fallback 未知原因兜底", "未能完成" in r["message"])

    # 1.11 result=None
    r = build_recognition_tip(None)
    check("result=None 走失败提示", r["level"] == "error")

    # 1.12 未知 status
    r = build_recognition_tip({"status": "unknown_status", "raw_label": "x",
                               "fallback_reason": None})
    check("未知 status 防御", r["level"] == "error")

    # 1.13 场景参数不崩（detail）
    r = build_recognition_tip({"status": "auto_fill", "category_name": "教材",
                               "confidence": 0.9, "raw_label": "textbook",
                               "fallback_reason": None}, scene="detail")
    check("scene=detail 正常", r["level"] == "good")
    check("SCENES 合法", set(SCENES) == {"publish", "detail"})

    # ---------- 2. 估价提示 ----------
    print("[估价提示]")

    # 2.1 成功无 price_tip -> 绿色估价完成
    r = build_price_tip({"estimated_min": 27, "estimated_max": 41,
                         "reason_text": "原价 68 元 × 教材良好折扣 0.4~0.6 = 27~41 元",
                         "price_tip": None})
    check("估价成功 level=good", r["level"] == "good")
    check("估价成功 含区间", "27~41 元" in r["message"] and "27~41" in r["message"])
    check("估价成功 error_code=None", r["error_code"] is None)

    # 2.2 成功标价低于区间 -> 黄色提示
    r = build_price_tip({"estimated_min": 27, "estimated_max": 41,
                         "reason_text": "x", "price_tip": "您的标价低于建议区间（27~41 元）"})
    check("标价低于区间 level=warn", r["level"] == "warn")
    check("标价低于区间 含提示", "标价" in r["title"] or "标价" in r["message"])

    # 2.3 成功标价高于区间 -> 黄色提示
    r = build_price_tip({"estimated_min": 27, "estimated_max": 41,
                         "reason_text": "x", "price_tip": "您的标价高于建议区间（27~41 元）"})
    check("标价高于区间 level=warn", r["level"] == "warn")

    # 2.4 免费赠送 0 元
    r = build_price_tip({"estimated_min": 0, "estimated_max": 0,
                         "reason_text": "该物品选择免费赠送，估价为 0 元。", "price_tip": None})
    check("免费赠送 level=good", r["level"] == "good")
    check("免费赠送 含 0 元", "0 元" in r["message"])

    # 2.5 六个错误码
    codes = ["PRICE_ORIGINAL_REQUIRED", "PRICE_INVALID_FORMAT", "PRICE_OUT_OF_RANGE",
             "CONDITION_REQUIRED", "CONDITION_INVALID", "CATEGORY_INVALID"]
    for code in codes:
        r = build_price_tip({"error": {"error_code": code, "message": "x"}})
        check("错误码 %s" % code, r["level"] == "error" and r["error_code"] == code)
    check("错误码映射覆盖6项", len(ERROR_CODE_TIPS) == 6)

    # 2.6 未知错误码 -> 兜底
    r = build_price_tip({"error": {"error_code": "XXX_UNKNOWN", "message": "x"}})
    check("未知错误码兜底", r["title"] == "估价失败")

    # 2.7 result=None
    r = build_price_tip(None)
    check("估价 result=None", r["level"] == "error")

    # 2.8 区间异常（None 区间）
    r = build_price_tip({"estimated_min": None, "estimated_max": None,
                         "reason_text": "x", "price_tip": None})
    check("区间异常 warn", r["level"] == "warn")

    # ---------- 3. 组合入口 ----------
    print("[组合入口]")
    tips = build_publish_tips(
        {"status": "auto_fill", "category_name": "教材", "confidence": 0.95,
         "raw_label": "textbook", "fallback_reason": None},
        {"estimated_min": 27, "estimated_max": 41, "reason_text": "x", "price_tip": None})
    check("组合入口含两字段", "recognition" in tips and "price" in tips)
    check("组合入口识别为 good", tips["recognition"]["level"] == "good")
    check("组合入口估价为 good", tips["price"]["level"] == "good")

    print()
    print("结果：PASS %d / FAIL %d" % (_PASS, _FAIL))
    if _FAIL:
        raise SystemExit(1)
    print("Day12 test 全部通过")


if __name__ == "__main__":
    main()
