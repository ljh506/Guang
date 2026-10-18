# -*- coding: utf-8 -*-
"""Day12 后端 API 验收测试：用户提示模块（AI识别/估价异常提示）。

对应计划书 Day12 成员A 任务「集成成员B 提示模块到识别/估价接口」（当天目标：UI与交互优化）。

覆盖：
1. ★ 验收链路：识别失败/估价异常时，接口返回用户可直接渲染的 tips 提示
2. recognize：无 backend -> fallback，data.tips.level=error + action 可执行
3. recognize：缺少图片 -> 400 系统级错误
4. estimate 成功 -> data + tips.level=good（区间展示）
5. estimate 标价低于/高于建议区间 -> tips.level=warn（参考建议价）
6. estimate 失败（原价缺失/类别非法）-> error + tips 携带 error_code
7. 成员B user_prompt 模块适配：auto_fill / manual_confirm / manual_select / fallback 分支

运行：C:\\Users\\HUAWEI\\mini\\envs\\shiguang\\python.exe backend/tests/test_day12_prompt_api.py
"""
import io
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.user_prompt import (  # noqa: E402
    build_price_tip, build_recognition_tip)

PASS, FAIL = 0, 0
client = TestClient(app)


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("[PASS]", name)
    else:
        FAIL += 1
        print("[FAIL]", name, "->", detail)


# ---------- 1. recognize：无 backend -> fallback + tips ----------
r = client.post("/api/v1/recognize",
                files={"image": ("test.jpg", b"fake-image-bytes",
                                 "image/jpeg")})
body = r.json()
check("识别：HTTP 200 不阻断发布", r.status_code == 200, r.status_code)
check("识别：data.status=fallback", body.get("data", {}).get("status") == "fallback")
check("识别：data.fallback=True", body.get("data", {}).get("fallback") is True)
check("识别：fallback_reason 非空", bool(body.get("data", {}).get("fallback_reason")))
tips = body.get("data", {}).get("tips", {})
check("识别：tips 存在", bool(tips))
check("识别：tips.level=error", tips.get("level") == "error", tips)
check("识别：tips.title/message/action 可渲染",
      bool(tips.get("title")) and bool(tips.get("message")) and bool(tips.get("action")))

# ---------- 2. recognize：缺少图片 -> 400 ----------
r2 = client.post("/api/v1/recognize")
check("识别：缺少图片返回 400", r2.status_code == 400, r2.status_code)
check("识别：400 错误含 code/message",
      isinstance(r2.json().get("detail"), dict)
      and r2.json()["detail"].get("code") == 40001)

# ---------- 3. estimate：成功 -> data + tips(good) ----------
r3 = client.post("/api/v1/estimate", json={
    "category": "textbook", "condition": "good", "original_price": 50})
b3 = r3.json()
check("估价：成功 success=true", b3.get("success") is True)
check("估价：建议区间合理",
      b3["data"].get("estimated_min") <= b3["data"].get("estimated_max")
      and b3["data"].get("estimated_min") is not None)
check("估价：reason_text 含折扣", "0.4~0.6" in b3["data"].get("reason_text", ""))
t3 = b3.get("tips", {})
check("估价：成功 tips 存在且 level=good", t3.get("level") == "good", t3)
check("估价：成功 tips 展示区间", "50" in t3.get("message", "") or "40" in t3.get("message", ""))

# ---------- 4. estimate：标价低于建议区间 -> tips(warn) ----------
r4 = client.post("/api/v1/estimate", json={
    "category": "textbook", "condition": "good", "original_price": 50,
    "asking_price": 1})
t4 = r4.json().get("tips", {})
check("估价：标价低于区间 tips.level=warn", t4.get("level") == "warn", t4)
check("估价：warn 提示含建议参考",
      "参考" in t4.get("message", "") and bool(t4.get("action")))

# ---------- 5. estimate：失败（原价缺失）-> error + tips 携带 error_code ----------
r5 = client.post("/api/v1/estimate", json={
    "category": "textbook", "condition": "good", "original_price": None,
    "is_free": False})
b5 = r5.json()
check("估价：原价缺失 success=false", b5.get("success") is False)
check("估价：error.error_code 正确",
      b5.get("error", {}).get("error_code") == "PRICE_ORIGINAL_REQUIRED")
t5 = b5.get("tips", {})
check("估价：失败 tips.level=error", t5.get("level") == "error", t5)
check("估价：失败 tips.error_code 与 error 一致",
      t5.get("error_code") == "PRICE_ORIGINAL_REQUIRED", t5)
check("估价：失败 tips 提供修正动作", bool(t5.get("action")))

# ---------- 6. estimate：免费赠送 0~0 ----------
r6 = client.post("/api/v1/estimate", json={
    "category": "textbook", "condition": "good", "original_price": None,
    "is_free": True})
b6 = r6.json()
check("估价：免费赠送 0~0", b6.get("success") is True
      and b6["data"].get("estimated_min") == 0
      and b6["data"].get("estimated_max") == 0)

# ---------- 7. 成员B user_prompt 模块适配分支 ----------
rec_auto = {"status": "auto_fill", "confidence": 0.95,
            "category_name": "教材", "raw_label": "textbook", "fallback_reason": None}
t = build_recognition_tip(rec_auto)
check("提示模块：auto_fill -> good 且含类别",
      t.get("level") == "good" and "教材" in t.get("message", ""))

rec_confirm = {"status": "manual_confirm", "confidence": 0.70,
               "category_name": "篮球", "raw_label": "basketball", "fallback_reason": None}
t = build_recognition_tip(rec_confirm)
check("提示模块：manual_confirm -> warn 且要求确认",
      t.get("level") == "warn" and "确认" in t.get("title", ""))

rec_select = {"status": "manual_select", "confidence": 0.4,
              "category_name": None, "raw_label": "x", "fallback_reason": None}
t = build_recognition_tip(rec_select)
check("提示模块：manual_select -> warn 且手动选择",
      t.get("level") == "warn" and "手动选择" in t.get("message", ""))

rec_fb = {"status": "fallback", "fallback_reason": "AI识别服务不可用/超时/失败，请手动选择类别",
          "raw_label": None, "confidence": None, "available_categories": [],
          "fallback": True}
t = build_recognition_tip(rec_fb)
check("提示模块：fallback -> error 且按原因给动作",
      t.get("level") == "error" and "手动选择" in t.get("action", ""))

price_ok = {"estimated_min": 27, "estimated_max": 41, "price_tip": None,
            "reason_text": "x"}
t = build_price_tip(price_ok)
check("提示模块：估价成功无标价提示 -> good 区间",
      t.get("level") == "good" and "27~41" in t.get("message", ""))

price_low = {"estimated_min": 27, "estimated_max": 41, "price_tip": "您的标价低于建议区间（27~41 元）"}
t = build_price_tip(price_low)
check("提示模块：标价低于区间 -> warn",
      t.get("level") == "warn" and t.get("title") == "标价建议"
      and bool(t.get("action")))

price_err = {"error": {"error_code": "PRICE_ORIGINAL_REQUIRED", "message": "请填写参考原价"}}
t = build_price_tip(price_err)
check("提示模块：估价错误码 -> error + error_code",
      t.get("level") == "error" and t.get("error_code") == "PRICE_ORIGINAL_REQUIRED")

# ---------- 汇总 ----------
print("")
print("Day12 提示接口验收：PASS %d / FAIL %d" % (PASS, FAIL))
if FAIL:
    raise SystemExit(1)
