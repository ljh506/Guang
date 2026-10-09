# -*- coding: utf-8 -*-
"""Day4 后端 API 验收测试：商品发布 → 漂流墙列表 → 详情（含估价落库）。"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
PASS, FAIL = 0, 0


def _req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json",
                                          "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "null")


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("[PASS]", name)
    else:
        FAIL += 1
        print("[FAIL]", name, "->", detail)


# 0. 类别列表（Day4 十类）
code, cats = _req("GET", "/goods/categories")
check("GET /goods/categories 返回 10 类", code == 200 and len(cats) == 10, (code, cats))
check("首类为教材", cats and cats[0]["category_id"] == "textbook", cats[:1])

# 1. ★ Day4 核心验收：发布一件商品（计划书示例：68 元教材 / 良好）
code, r = _req("POST", "/goods", {
    "user_id": 1,             # 拾光少女小鹿（清华大学）
    "name": "高等数学（上册）第2版",
    "category": "textbook",
    "condition": "good",
    "original_price": 68,
    "asking_price": 30,
    "description": "九成新，无笔记",
    "trade_type": "sell",
})
g = r.get("goods", {}) if isinstance(r, dict) else {}
check("发布商品 201", code == 201, (code, r))
check("建议估价 27~41（计划书示例）",
      g.get("estimated_min") == 27 and g.get("estimated_max") == 41, g)
check("估价依据含折扣 0.4~0.6", "0.4~0.6" in (g.get("reason_text") or ""), g.get("reason_text"))
check("price_tip 为空（标价 30 在区间内）", r.get("price_tip") is None, r.get("price_tip"))
check("category_name=教材", g.get("category_name") == "教材", g.get("category_name"))
check("school_id 自动取用户学校(1)", g.get("school_id") == 1, g.get("school_id"))
gid = g.get("id")

# 2. 标价偏离区间 → 有提示但不阻断
code, r2 = _req("POST", "/goods", {
    "user_id": 2, "name": "测试高价书", "category": "textbook",
    "condition": "good", "original_price": 50, "asking_price": 999,
})
g2 = r2.get("goods", {})
check("高价发布成功（不阻断）", code == 201 and g2.get("id"), (code, r2))
check("高价提示 price_tip 非空", bool(r2.get("price_tip")), r2.get("price_tip"))
gid2 = g2.get("id")

# 3. 免费赠送 → 估价 0~0
code, r3 = _req("POST", "/goods", {
    "user_id": 3, "name": "免费送台灯", "category": "life_goods",
    "condition": "fair", "original_price": 45, "trade_type": "free",
})
g3 = r3.get("goods", {})
check("免费赠送估价 0~0",
      g3.get("estimated_min") == 0 and g3.get("estimated_max") == 0, g3)
gid3 = g3.get("id")

# 4. ★ Day4 核心验收：漂流墙列表能看到刚发布的商品
code, lst = _req("GET", "/goods?school_id=1")
ids = [it["id"] for it in lst.get("items", [])]
check("漂流墙(school_id=1) 列表 200", code == 200, (code, lst))
check("漂流墙能看到刚发布的商品", gid in ids, ids)
check("列表含 total/page/page_size", all(k in lst for k in ("total", "page", "page_size")), lst)

# 5. 类别过滤
code, lst2 = _req("GET", "/goods?category=textbook")
check("category=textbook 过滤", all(it["category"] == "textbook" for it in lst2["items"]), lst2)

# 6. 详情
code, d = _req("GET", f"/goods/{gid}")
check("商品详情 200", code == 200 and d["id"] == gid, (code, d))
check("详情含估价依据", bool(d.get("reason_text")), d)

# 7. 更新（改品相 → 自动重算估价）
code, u = _req("PATCH", f"/goods/{gid}", {"condition": "new_like"})
check("PATCH 品相→全新/较新，估价重算为 41~54",
      code == 200 and u["estimated_min"] == 41 and u["estimated_max"] == 54, u)

# 8. 状态流转
code, u2 = _req("PATCH", f"/goods/{gid2}", {"status": "reserved"})
check("PATCH status=reserved", code == 200 and u2["status"] == "reserved", u2)

# 9. 错误路径
code, _ = _req("POST", "/goods", {"user_id": 9999, "name": "x", "category": "textbook",
                                   "condition": "good", "original_price": 10})
check("user_id 不存在 → 400", code == 400, code)
code, _ = _req("POST", "/goods", {"user_id": 1, "name": "x", "category": "bad_cat",
                                  "condition": "good", "original_price": 10})
check("类别非法 → 422（B 校验）", code == 422, code)
code, _ = _req("POST", "/goods", {"user_id": 1, "name": "x", "category": "textbook",
                                  "condition": "???", "original_price": 10})
check("品相非法 → 422（B 校验）", code == 422, code)
code, _ = _req("GET", "/goods/999999")
check("商品不存在 → 404", code == 404, code)

# 10. 清理
for i in (gid, gid2, gid3):
    code, _ = _req("DELETE", f"/goods/{i}")
    check(f"删除商品 {i} → 204", code == 204, code)

print()
print(f"===== 结果汇总：PASS={PASS} FAIL={FAIL} =====")
sys.exit(0 if FAIL == 0 else 1)
