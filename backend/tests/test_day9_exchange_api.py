# -*- coding: utf-8 -*-
"""Day9 后端 API 验收测试：Exchange 模型 + 匹配接口（交换匹配）。

覆盖（对应计划书 Day9 成员A 任务「完成 Exchange 模型和匹配接口」、
当天验收「A/B 物品互相匹配出现高匹配推荐」）：
1. ★ 验收链路：A 发教材(30元,想换运动器材) / B 发篮球(32元,想换教材) 同校
   → POST /exchange/match → 高匹配 high ≈0.98（50%意愿+30%价格+20%同校）
2. 意愿表达：发布时带 wish_category_id + POST /exchange/wish 修改 + GET 查询
3. 匹配分级与排序：高匹配优先 / 普通匹配(normal)进列表 / 无交集与低匹配过滤
4. Exchange 模型：accept 落 open 记录；重复 match 去重（不再推荐）；
   GET /exchange/matches 列表
5. 错误分支：user/goods 不存在、匹配他人商品、重复 accept、低匹配 accept、
   设置他人商品意愿、非法类别等

类别使用 Day4 统一十类（textbook / sports_equipment / electronics / clothing ...）。

运行：C:\\Users\\HUAWEI\\mini\\envs\\shiguang\\python.exe backend/tests/test_day9_exchange_api.py
"""
import os
import sys
import time

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


# ---------- 前置：自建 school + 发起方A + 匹配方B + 跨校C + 普通D + 无关E ----------
uniq = int(time.time() * 1000)
school1 = client.post("/api/v1/schools", json={
    "name": f"Day9测试大学A-{uniq}", "latitude": 39.9, "longitude": 116.4}).json()["id"]
school2 = client.post("/api/v1/schools", json={
    "name": f"Day9测试大学B-{uniq}", "latitude": 40.1, "longitude": 116.6}).json()["id"]
user_a = client.post("/api/v1/users", json={
    "nickname": f"成员A-{uniq}", "school_id": school1}).json()["id"]
user_b = client.post("/api/v1/users", json={
    "nickname": f"成员B-{uniq}", "school_id": school1}).json()["id"]
user_c = client.post("/api/v1/users", json={
    "nickname": f"跨校C-{uniq}", "school_id": school2}).json()["id"]
user_d = client.post("/api/v1/users", json={
    "nickname": f"普通D-{uniq}", "school_id": school1}).json()["id"]
user_e = client.post("/api/v1/users", json={
    "nickname": f"无关E-{uniq}", "school_id": school2}).json()["id"]
check("前置 school/用户 创建成功",
      school1 and school2 and user_a and user_b and user_c and user_d and user_e,
      (school1, school2, user_a, user_b, user_c, user_d, user_e))

# A：教材 30 元，想换运动器材（发布时直接带意愿）
r = client.post("/api/v1/goods", json={
    "user_id": user_a, "name": "高等数学（上册）", "category": "textbook",
    "condition": "good", "original_price": 68, "asking_price": 30,
    "trade_type": "exchange", "wish_category_id": "sports_equipment"})
g_a = r.json().get("goods", {})
check("A发布教材(exchange, 带意愿sports_equipment) 201 且落库",
      r.status_code == 201 and g_a.get("wish_category_id") == "sports_equipment",
      (r.status_code, r.text))

# B：篮球 32 元，想换教材（同校，双向意愿）
r = client.post("/api/v1/goods", json={
    "user_id": user_b, "name": "篮球（八成新）", "category": "sports_equipment",
    "condition": "good", "original_price": 72, "asking_price": 32,
    "trade_type": "exchange", "wish_category_id": "textbook"})
g_b = r.json().get("goods", {})
check("B发布篮球(exchange, 带意愿textbook) 201",
      r.status_code == 201 and g_b.get("wish_category_id") == "textbook",
      (r.status_code, r.text))

# C：跨校篮球 32 元，想换教材（跨校 -> 同校 0 分）
r = client.post("/api/v1/goods", json={
    "user_id": user_c, "name": "篮球跨校", "category": "sports_equipment",
    "condition": "good", "original_price": 70, "asking_price": 32,
    "trade_type": "exchange", "wish_category_id": "textbook"})
g_c = r.json().get("goods", {})
check("C发布篮球(跨校) 201", r.status_code == 201 and g_c.get("id"), (r.status_code, r.text))

# D：同校篮球 60 元，想换教材（价格差一倍 -> 总分更低）
r = client.post("/api/v1/goods", json={
    "user_id": user_d, "name": "篮球价高", "category": "sports_equipment",
    "condition": "good", "original_price": 100, "asking_price": 60,
    "trade_type": "exchange", "wish_category_id": "textbook"})
g_d = r.json().get("goods", {})
check("D发布篮球(价格高) 201", r.status_code == 201 and g_d.get("id"), (r.status_code, r.text))

# E：跨校旧耳机 100 元，想换衣物（与 A 无意愿交集且跨校 -> 低匹配被过滤）
r = client.post("/api/v1/goods", json={
    "user_id": user_e, "name": "旧耳机", "category": "electronics",
    "condition": "good", "original_price": 200, "asking_price": 100,
    "trade_type": "exchange", "wish_category_id": "clothing"})
g_e = r.json().get("goods", {})
check("E发布电子(无交集) 201", r.status_code == 201 and g_e.get("id"), (r.status_code, r.text))

# F：同校篮球 50 元，想换文具（单向意愿(仅A想换篮球)+价格差距 -> normal 分级）
r = client.post("/api/v1/goods", json={
    "user_id": user_d, "name": "篮球价中", "category": "sports_equipment",
    "condition": "good", "original_price": 90, "asking_price": 50,
    "trade_type": "exchange", "wish_category_id": "stationery"})
g_f = r.json().get("goods", {})
check("F发布篮球(50元/同校) 201", r.status_code == 201 and g_f.get("id"), (r.status_code, r.text))

# G：同校旧耳机 80 元，想换衣物（与 B 无意愿交集且价格差距大 -> 低匹配）
r = client.post("/api/v1/goods", json={
    "user_id": user_e, "name": "旧耳机2号", "category": "electronics",
    "condition": "good", "original_price": 160, "asking_price": 80,
    "trade_type": "exchange", "wish_category_id": "clothing"})
g_g = r.json().get("goods", {})
check("G发布电子(低匹配候选) 201", r.status_code == 201 and g_g.get("id"), (r.status_code, r.text))

# ---------- 1) ★ 验收链路：A/B 互相匹配出现高匹配推荐 ----------
r = client.post("/api/v1/exchange/match", json={"user_id": user_a, "goods_id": g_a["id"]})
data = r.json()["data"]
check("match 返回 200 + 推荐列表", r.status_code == 200 and isinstance(data, list), (r.status_code, r.text))
top = data[0] if data else {}
check("高匹配推荐 top1 命中 B（同校双向 30/32）≈0.98",
      top.get("target_goods_id") == g_b["id"] and top.get("level") == "high"
      and abs(top.get("match_score", 0) - 0.98125) < 0.01,
      top)
check("score_detail 维度齐全(类别/价格/同校)",
      set(top.get("score_detail", {}).keys()) == {"category_wish", "price", "school"},
      top.get("score_detail"))
check("weights 50/30/20 返回",
      abs(top.get("weights", {}).get("category_wish", 0) - 0.5) < 1e-9 and
      abs(top.get("weights", {}).get("price", 0) - 0.3) < 1e-9 and
      abs(top.get("weights", {}).get("school", 0) - 0.2) < 1e-9,
      top.get("weights"))
check("match_reason 可解释（含双方意愿/接近度/同校/综合）",
      top.get("match_reason") and "双方意愿匹配" in top["match_reason"]
      and "同校" in top["match_reason"] and "综合匹配度" in top["match_reason"],
      top.get("match_reason"))
check("推荐附带展示字段（目标商品名/类别/昵称）",
      top.get("target_goods_name") == "篮球（八成新）" and
      top.get("target_category_name") == "运动器材" and
      top.get("target_asking_price") == 32 and
      top.get("target_user_nickname", "").startswith("成员B"),
      (top.get("target_goods_name"), top.get("target_category_name"),
       top.get("target_asking_price"), top.get("target_user_nickname")))

# 排序：B(0.98125) > D(0.85) > C(0.78125)；E 无交集且低分应被过滤
ids = [i["target_goods_id"] for i in data]
check("推荐列表按匹配度降序且不含无交集低分 E",
      all(data[i]["match_score"] >= data[i + 1]["match_score"]
          for i in range(len(data) - 1)) and g_e["id"] not in ids,
      [(i["target_goods_id"], round(i["match_score"], 4)) for i in data])
check("推荐列表含普通匹配(normal)与高匹配(high)分级",
      any(i["level"] == "high" for i in data) and any(i["level"] == "normal" for i in data),
      [(i["target_goods_id"], i["level"]) for i in data])

# ---------- 2) 意愿表达：POST /exchange/wish 修改 + GET 查询 ----------
r = client.post("/api/v1/exchange/wish", json={
    "user_id": user_a, "goods_id": g_a["id"], "wish_category_id": "clothing"})
check("POST wish 修改 A 商品意愿 -> clothing",
      r.status_code == 200 and r.json()["wish_category_id"] == "clothing", (r.status_code, r.text))
r = client.get(f"/api/v1/exchange/wish/{g_a['id']}")
check("GET wish 查询生效",
      r.status_code == 200 and r.json()["wish_category_id"] == "clothing", (r.status_code, r.text))
# 改回 sports_equipment 保证后续匹配用例稳定
r = client.post("/api/v1/exchange/wish", json={
    "user_id": user_a, "goods_id": g_a["id"], "wish_category_id": "sports_equipment"})
check("POST wish 改回 sports_equipment", r.json()["wish_category_id"] == "sports_equipment", r.text)

# ---------- 3) Exchange 模型：accept 落记录 + 去重 + 列表 ----------
r = client.post("/api/v1/exchange/accept", json={
    "user_id": user_a, "goods_id": g_a["id"], "target_goods_id": g_b["id"]})
ex = r.json().get("exchange", {})
check("accept 高匹配 201 / status=open / level=high",
      r.status_code == 201 and ex.get("status") == "open" and ex.get("level") == "high"
      and abs(ex.get("match_score", 0) - 0.98125) < 0.01,
      (r.status_code, r.text))
check("accept 返回状态机建议（高匹配 chatting->matched）",
      r.json().get("state_advice", {}).get("valid") is True
      and r.json()["state_advice"].get("to_state") == "matched",
      r.json().get("state_advice"))

# 去重：发起方已有 open 记录 → 再次 match 不再返回任何推荐
r = client.post("/api/v1/exchange/match", json={"user_id": user_a, "goods_id": g_a["id"]})
check("已确认交换后 match 去重（不再重复推荐）",
      r.status_code == 200 and r.json()["data"] == [], (r.status_code, r.text))

# 重复 accept → 400
r = client.post("/api/v1/exchange/accept", json={
    "user_id": user_a, "goods_id": g_a["id"], "target_goods_id": g_c["id"]})
check("重复 accept 400（已有进行中交换）", r.status_code == 400, (r.status_code, r.text))

# 匹配记录列表
r = client.get("/api/v1/exchange/matches", params={"user_id": user_a})
items = r.json()["items"]
check("GET matches 列表含 1 条 open 记录（含商品名/目标昵称）",
      r.status_code == 200 and len(items) == 1 and items[0]["status"] == "open"
      and items[0]["goods_name"] == "高等数学（上册）"
      and items[0]["target_goods_name"] == "篮球（八成新）"
      and items[0]["target_user_nickname"].startswith("成员B"),
      (r.status_code, items))

# ---------- 4) 错误分支 ----------
r = client.post("/api/v1/exchange/match", json={"user_id": 999999, "goods_id": g_a["id"]})
check("match user 不存在 400", r.status_code == 400, (r.status_code, r.text))
r = client.post("/api/v1/exchange/match", json={"user_id": user_a, "goods_id": 999999})
check("match goods 不存在 404", r.status_code == 404, (r.status_code, r.text))
r = client.post("/api/v1/exchange/match", json={"user_id": user_b, "goods_id": g_a["id"]})
check("match 他人商品 400", r.status_code == 400, (r.status_code, r.text))
r = client.post("/api/v1/exchange/wish", json={
    "user_id": user_b, "goods_id": g_a["id"], "wish_category_id": "clothing"})
check("wish 设置他人商品 400", r.status_code == 400, (r.status_code, r.text))
r = client.post("/api/v1/exchange/wish", json={
    "user_id": user_a, "goods_id": g_a["id"], "wish_category_id": "ghost"})
check("wish 非法类别 400", r.status_code == 400, (r.status_code, r.text))
r = client.post("/api/v1/exchange/wish", json={
    "user_id": user_a, "goods_id": 999999, "wish_category_id": "clothing"})
check("wish 商品不存在 404", r.status_code == 404, (r.status_code, r.text))
r = client.get("/api/v1/exchange/matches", params={"user_id": 999999})
check("matches 用户不存在 404", r.status_code == 404, (r.status_code, r.text))

# 低匹配 accept → 400：B（篮球32）对 G（耳机80、无意愿交集、跨校）总分 0.3*0.6 = 0.18 < 0.50
r = client.post("/api/v1/exchange/accept", json={
    "user_id": user_b, "goods_id": g_b["id"], "target_goods_id": g_g["id"]})
check("低匹配 accept 400（匹配度不足）",
      r.status_code == 400 and "匹配度不足" in r.json().get("detail", ""),
      (r.status_code, r.text))

# 与自己的商品匹配 → 400
r = client.post("/api/v1/exchange/accept", json={
    "user_id": user_a, "goods_id": g_a["id"], "target_goods_id": g_a["id"]})
check("accept 自己商品 400", r.status_code == 400, (r.status_code, r.text))

print("\n===== Day9 交换匹配接口测试汇总：PASS=%d FAIL=%d =====" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
