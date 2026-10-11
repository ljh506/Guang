# -*- coding: utf-8 -*-
"""Day6 后端 API 验收测试：POST /api/v1/estimate + 商品发布价格字段落库。

覆盖（对应计划书 Day6 成员A任务「完成估价接口和 Goods 价格字段保存」）：
1. ★ 计划书验收：68 元教材 + 良好品相 -> 27~41 元（含 reason_text / rule_ref / price_tip）
2. 电子产品 months_used 年限微调 + 降档
3. 免费赠送 -> 0~0
4. asking_price 标价提示（低于/高于区间）
5. 错误分支（缺原价 / 品相非法 / 类别非法 / 旧类别兼容）
6. POST /api/v1/goods 发布时价格字段（estimated_min/max/reason_text）保存并可查回
7. PATCH 修改品相后估价自动重算并保存

运行：C:\\Users\\HUAWEI\\mini\\envs\\shiguang\\python.exe backend/tests/test_day6_estimate_api.py
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

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


def post_estimate(payload):
    return client.post("/api/v1/estimate", json=payload)


def post_goods(payload):
    return client.post("/api/v1/goods", json=payload)


# ---------- 1. 计划书验收：68 元教材 + 良好 -> 27~41 ----------
r = post_estimate({"category": "textbook", "condition": "good",
                   "original_price": 68, "is_free": False})
body = r.json()
check("POST /estimate 200", r.status_code == 200, r.status_code)
check("success=true", body.get("success") is True, body)
d = body.get("data", {})
check("★ 68元良好教材 -> 27~41", d.get("estimated_min") == 27
      and d.get("estimated_max") == 41, d)
check("reason_text 含折扣计算过程",
      "0.4~0.6" in (d.get("reason_text") or "") and "27~41" in (d.get("reason_text") or ""),
      d.get("reason_text"))
check("rule_ref 含 low/high", d.get("rule_ref", {}).get("low") == 0.4
      and d.get("rule_ref", {}).get("high") == 0.6, d.get("rule_ref"))
check("无标价时 price_tip=None", d.get("price_tip") is None, d.get("price_tip"))

# ---------- 2. 电子产品年限微调 ----------
r = post_estimate({"category": "electronics", "condition": "new_like",
                   "original_price": 2000, "months_used": 9, "asking_price": 1200})
d = r.json().get("data", {})
check("电子 new_like 9个月 -> 1300~1500（0.65~0.75）",
      d.get("estimated_min") == 1300 and d.get("estimated_max") == 1500, d)
check("标价低于区间 -> price_tip 提示", "低于建议区间" in (d.get("price_tip") or ""),
      d.get("price_tip"))

# 超过 24 个月降档至良好档（0.50~0.70 -> 1000~1400）
r = post_estimate({"category": "electronics", "condition": "new_like",
                   "original_price": 2000, "months_used": 30})
d = r.json().get("data", {})
check("电子 30个月 降档良好档 -> 1000~1400", d.get("estimated_min") == 1000
      and d.get("estimated_max") == 1400, d)
check("降档原因写入 reason_text", "良好档" in (d.get("reason_text") or ""),
      d.get("reason_text"))

# ---------- 3. 免费赠送 ----------
r = post_estimate({"category": "textbook", "condition": "good",
                   "original_price": 0, "is_free": True})
d = r.json().get("data", {})
check("免费赠送 -> 0~0", d.get("estimated_min") == 0 and d.get("estimated_max") == 0, d)
check("免费赠送 reason_text 说明", "免费赠送" in (d.get("reason_text") or ""),
      d.get("reason_text"))

# ---------- 4. asking_price 高于区间 ----------
r = post_estimate({"category": "textbook", "condition": "good",
                   "original_price": 68, "asking_price": 100})
d = r.json().get("data", {})
check("标价高于区间 -> price_tip 影响成功率", "影响交换成功率" in (d.get("price_tip") or ""),
      d.get("price_tip"))

# ---------- 5. 错误分支 ----------
r = post_estimate({"category": "textbook", "condition": "good",
                   "original_price": None})
b = r.json()
check("缺原价 -> PRICE_ORIGINAL_REQUIRED", b.get("success") is False
      and b.get("error", {}).get("error_code") == "PRICE_ORIGINAL_REQUIRED", b)
r = post_estimate({"category": "textbook", "condition": "unknown",
                   "original_price": 68})
b = r.json()
check("品相非法 -> CONDITION_INVALID", b.get("success") is False
      and b.get("error", {}).get("error_code") == "CONDITION_INVALID", b)
r = post_estimate({"category": "not_a_category", "condition": "good",
                   "original_price": 68})
b = r.json()
check("类别非法 -> CATEGORY_INVALID", b.get("success") is False
      and b.get("error", {}).get("error_code") == "CATEGORY_INVALID", b)
# 字符串原价兼容 + 旧类别 ID 兼容（school_supplies -> stationery 折扣 0.4~0.5）
r = post_estimate({"category": "school_supplies", "condition": "good",
                   "original_price": "100"})
d = r.json().get("data", {})
check("字符串原价 + 旧类别ID兼容 -> 40~50",
      d.get("estimated_min") == 40 and d.get("estimated_max") == 50, d)

# ---------- 6. ★ 发布商品：价格字段保存 ----------
# 前置：自建 school + user（TestClient 独立数据库，不依赖种子数据）
import time
uniq = int(time.time() * 1000)
rs = client.post("/api/v1/schools", json={"name": f"测试大学-{uniq}",
                                          "latitude": 39.9, "longitude": 116.4})
school_id = rs.json().get("id")
ru = client.post("/api/v1/users", json={"nickname": f"测试同学-{uniq}",
                                        "school_id": school_id})
user_id = ru.json().get("id")
check("测试前置 school/user 创建成功", school_id is not None and user_id is not None,
      (rs.status_code, ru.status_code))

r = post_goods({"user_id": user_id, "name": "高等数学（上册）第2版",
                "category": "textbook", "condition": "good",
                "original_price": 68, "asking_price": 30,
                "description": "九成新，无笔记", "trade_type": "sell"})
g = r.json().get("goods", {})
check("发布商品 201", r.status_code == 201, (r.status_code, r.text))
check("发布返回估价 27~41 已保存", g.get("estimated_min") == 27
      and g.get("estimated_max") == 41, g)
check("发布返回 reason_text 已保存", bool(g.get("reason_text")), g.get("reason_text"))
gid = g.get("id")
if gid:
    rr = client.get(f"/api/v1/goods/{gid}")
    gg = rr.json()
    check("GET 详情价格字段落库可查回", gg.get("estimated_min") == 27
          and gg.get("estimated_max") == 41 and gg.get("reason_text") == g.get("reason_text"), gg)

# 免费赠送商品价格字段保存为 0~0（GoodsCreate 约束原价>0，传 0.01，引擎 is_free 分支返回 0~0）
r = post_goods({"user_id": user_id, "name": "旧笔记本", "category": "life_goods",
                "condition": "good", "original_price": 0.01,
                "trade_type": "free"})
g = r.json().get("goods", {})
check("免费赠送发布 -> 0~0 落库", g.get("estimated_min") == 0
      and g.get("estimated_max") == 0, (r.status_code, g))

# ---------- 7. PATCH 修改品相自动重算并保存 ----------
if gid:
    rr = client.patch(f"/api/v1/goods/{gid}", json={"condition": "new_like"})
    gg = rr.json()
    check("PATCH 品相 -> 估价重算 41~54（0.6~0.8）",
          gg.get("estimated_min") == 41 and gg.get("estimated_max") == 54, gg)

print(f"\n===== Day6 估价接口测试完成：PASS={PASS} FAIL={FAIL} =====")
sys.exit(1 if FAIL else 0)
