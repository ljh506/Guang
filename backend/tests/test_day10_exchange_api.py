# -*- coding: utf-8 -*-
"""Day10 后端 API 验收测试：交换状态流转（待确认/已确认/取消）+ 协议卡片。

对应计划书 Day10 成员A 任务「完成交换状态流转 API：待确认/已确认/取消」、
当天验收「匹配 → 发起交换 → 双方确认 → 生成协议卡片」：

1. ★ 验收链路：A 教材(30,想换运动器材) / B 篮球(32,想换教材) 同校
   → match 高匹配 → accept 落 open（待确认）→ confirm A/B → confirmed
   → GET protocol 返回协议卡片（协议文本/匹配解释/校验通过）
2. 单方确认：confirm 后 confirm_a/confirm_b 标记逐步置位，仍为待确认
3. 取消：另一对 accept 后 cancel → cancelled（终态）；取消后商品可再次匹配
4. 终态保护：confirmed/cancelled 后不可再 confirm/cancel；非参与者操作 400
5. ExchangeOut 输出 confirm_a/confirm_b 字段

运行：shiguang python backend/tests/test_day10_exchange_api.py
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


# ---------- 前置：school + 用户 ----------
uniq = int(time.time() * 1000)
school1 = client.post("/api/v1/schools", json={
    "name": f"Day10测试大学-{uniq}", "latitude": 39.9, "longitude": 116.4}).json()["id"]
user_a = client.post("/api/v1/users", json={
    "nickname": f"甲A-{uniq}", "school_id": school1}).json()["id"]
user_b = client.post("/api/v1/users", json={
    "nickname": f"乙B-{uniq}", "school_id": school1}).json()["id"]
user_x = client.post("/api/v1/users", json={
    "nickname": f"无关X-{uniq}", "school_id": school1}).json()["id"]
check("前置 school/用户 创建成功", school1 and user_a and user_b and user_x,
      (school1, user_a, user_b, user_x))

# A 教材30 想换运动器材；B 篮球32 想换教材（同校双向意愿）
r = client.post("/api/v1/goods", json={
    "user_id": user_a, "name": "高等数学（上册）", "category": "textbook",
    "condition": "good", "original_price": 68, "asking_price": 30,
    "trade_type": "exchange", "wish_category_id": "sports_equipment"})
g_a = r.json().get("goods", {})
check("A发布教材 201", r.status_code == 201 and g_a.get("id"), (r.status_code, r.text))

r = client.post("/api/v1/goods", json={
    "user_id": user_b, "name": "篮球（八成新）", "category": "sports_equipment",
    "condition": "good", "original_price": 72, "asking_price": 32,
    "trade_type": "exchange", "wish_category_id": "textbook"})
g_b = r.json().get("goods", {})
check("B发布篮球 201", r.status_code == 201 and g_b.get("id"), (r.status_code, r.text))

# ---------- 1) ★ 验收链路：匹配 → 发起交换 → 双方确认 → 协议卡片 ----------
r = client.post("/api/v1/exchange/match", json={"user_id": user_a, "goods_id": g_a["id"]})
data = r.json()["data"]
top = data[0] if data else {}
check("match 高匹配推荐 top1=B",
      r.status_code == 200 and top.get("target_goods_id") == g_b["id"]
      and top.get("level") == "high", (r.status_code, top))

r = client.post("/api/v1/exchange/accept", json={
    "user_id": user_a, "goods_id": g_a["id"], "target_goods_id": g_b["id"]})
ex = r.json().get("exchange", {})
check("accept 落 open（待确认）且确认标记均为 false",
      r.status_code == 201 and ex.get("status") == "open"
      and ex.get("confirm_a") is False and ex.get("confirm_b") is False,
      (r.status_code, r.text))

# 待确认协议卡片：状态 negotiating / 双方待确认 / 校验通过
r = client.get(f"/api/v1/exchange/{ex['id']}/protocol")
p = r.json()
check("GET protocol 待确认：state_name=negotiating、双方待确认、校验通过",
      r.status_code == 200 and p["status"] == "open"
      and p["state_name"] == "negotiating"
      and p["confirm_a"] is False and p["confirm_b"] is False
      and p["validation"]["valid"] is True,
      (r.status_code, p))
check("协议文本含甲方/乙方/协议编号/交易状态/确认状态",
      p["protocol_text"] and "拾光Agent · 物品交换协议" in p["protocol_text"]
      and f"EX-{ex['id']}" in p["protocol_text"]
      and "甲方" in p["protocol_text"] and "乙方" in p["protocol_text"]
      and "交易状态" in p["protocol_text"] and "确认状态" in p["protocol_text"],
      p["protocol_text"])
check("匹配解释文本可读（含双方意愿/综合匹配度）",
      p["match_explanation"] and "双方意愿" in p["match_explanation"]
      and "综合匹配度" in p["match_explanation"], p["match_explanation"])

# 非参与者 confirm → 400
r = client.post(f"/api/v1/exchange/{ex['id']}/confirm",
                json={"user_id": user_x})
check("非参与者 confirm 400", r.status_code == 400, (r.status_code, r.text))

# A 单方确认 → confirm_a=true，仍待确认
r = client.post(f"/api/v1/exchange/{ex['id']}/confirm", json={"user_id": user_a})
check("A 确认：confirm_a=true / 仍 open",
      r.status_code == 200 and r.json()["confirm_a"] is True
      and r.json()["confirm_b"] is False and r.json()["status"] == "open",
      (r.status_code, r.text))

# B 确认 → confirmed，双方商品 exchanged
r = client.post(f"/api/v1/exchange/{ex['id']}/confirm", json={"user_id": user_b})
check("B 确认：双方确认 → confirmed",
      r.status_code == 200 and r.json()["confirm_a"] is True
      and r.json()["confirm_b"] is True and r.json()["status"] == "confirmed",
      (r.status_code, r.text))
ga2 = client.get(f"/api/v1/goods/{g_a['id']}").json()
gb2 = client.get(f"/api/v1/goods/{g_b['id']}").json()
check("确认后双方商品状态 exchanged（防重复交换）",
      ga2.get("status") == "exchanged" and gb2.get("status") == "exchanged",
      (ga2.get("status"), gb2.get("status")))

# 终态协议卡片：confirmed / 双方已确认 / 终态豁免后校验通过
r = client.get(f"/api/v1/exchange/{ex['id']}/protocol")
p = r.json()
check("GET protocol 已确认：state_name=confirmed、双方已确认、校验通过(终态豁免)",
      r.status_code == 200 and p["status"] == "confirmed"
      and p["state_name"] == "confirmed"
      and p["confirm_a"] is True and p["confirm_b"] is True
      and p["validation"]["valid"] is True,
      (r.status_code, p))
check("终态协议确认状态文案：甲方已确认，乙方已确认",
      "甲方已确认" in p["protocol_text"] and "乙方已确认" in p["protocol_text"],
      p["protocol_text"])

# 终态保护：confirmed 后不可再 confirm / cancel
r = client.post(f"/api/v1/exchange/{ex['id']}/confirm", json={"user_id": user_a})
check("confirmed 后重复 confirm 400", r.status_code == 400, (r.status_code, r.text))
r = client.post(f"/api/v1/exchange/{ex['id']}/cancel", json={"user_id": user_b})
check("confirmed 后 cancel 400", r.status_code == 400, (r.status_code, r.text))

# matches 列表带 confirm 字段
r = client.get("/api/v1/exchange/matches", params={"user_id": user_a})
items = r.json()["items"]
check("GET matches 记录 status=confirmed / confirm 标记为 true",
      r.status_code == 200 and len(items) >= 1
      and items[0]["status"] == "confirmed"
      and items[0]["confirm_a"] is True and items[0]["confirm_b"] is True,
      (r.status_code, items))

# ---------- 2) 取消流转：accept 后 cancel → cancelled，商品回到可交换 ----------
user_d = client.post("/api/v1/users", json={
    "nickname": f"丙C-{uniq}", "school_id": school1}).json()["id"]
r = client.post("/api/v1/goods", json={
    "user_id": user_d, "name": "球拍（七成新）", "category": "sports_equipment",
    "condition": "good", "original_price": 80, "asking_price": 35,
    "trade_type": "exchange", "wish_category_id": "textbook"})
g_d = r.json().get("goods", {})
check("D发布球拍 201", r.status_code == 201 and g_d.get("id"), (r.status_code, r.text))

r = client.post("/api/v1/exchange/match", json={"user_id": user_b, "goods_id": g_b["id"]})
# 注：B 的篮球已 exchanged，不可再发起匹配 → 改用 D 视角/新商品做取消链路
r = client.post("/api/v1/exchange/match", json={"user_id": user_d, "goods_id": g_d["id"]})
data = r.json()["data"]
check("D match 推荐列表可返回（A 已交换商品被剔除）",
      r.status_code == 200 and all(i["target_goods_id"] != g_a["id"] for i in data),
      (r.status_code, data))

# 用新商品对走取消：A 再发布一件商品 X，B 用新商品 Y 匹配 → accept → cancel
r = client.post("/api/v1/goods", json={
    "user_id": user_a, "name": "文学选集", "category": "textbook",
    "condition": "good", "original_price": 45, "asking_price": 20,
    "trade_type": "exchange", "wish_category_id": "sports_equipment"})
g_x = r.json().get("goods", {})
check("A发布第二件商品 201", r.status_code == 201 and g_x.get("id"), (r.status_code, r.text))

r = client.post("/api/v1/exchange/match", json={"user_id": user_a, "goods_id": g_x["id"]})
data = r.json()["data"]
top = data[0] if data else {}
check("第二件商品 match 有推荐", r.status_code == 200 and data, (r.status_code, data))

r = client.post("/api/v1/exchange/accept", json={
    "user_id": user_a, "goods_id": g_x["id"],
    "target_goods_id": top["target_goods_id"]})
ex2 = r.json().get("exchange", {})
check("accept2 落 open", r.status_code == 201 and ex2.get("status") == "open",
      (r.status_code, r.text))

r = client.post(f"/api/v1/exchange/{ex2['id']}/cancel", json={"user_id": user_d})
check("cancel 由乙方触发 → cancelled",
      r.status_code == 200 and r.json()["exchange"]["status"] == "cancelled",
      (r.status_code, r.text))
r = client.get(f"/api/v1/exchange/{ex2['id']}/protocol")
p = r.json()
check("取消后协议：state_name=cancelled、校验通过(终态豁免)",
      r.status_code == 200 and p["status"] == "cancelled"
      and p["state_name"] == "cancelled"
      and p["validation"]["valid"] is True, (r.status_code, p))
r = client.post(f"/api/v1/exchange/{ex2['id']}/confirm", json={"user_id": user_a})
check("cancelled 后 confirm 400", r.status_code == 400, (r.status_code, r.text))

# ---------- 3) 错误分支 ----------
r = client.post("/api/v1/exchange/999999/confirm", json={"user_id": user_a})
check("exchange 不存在 confirm 404", r.status_code == 404, (r.status_code, r.text))
r = client.post("/api/v1/exchange/999999/cancel", json={"user_id": user_a})
check("exchange 不存在 cancel 404", r.status_code == 404, (r.status_code, r.text))
r = client.get("/api/v1/exchange/999999/protocol")
check("exchange 不存在 protocol 404", r.status_code == 404, (r.status_code, r.text))

print("\n===== Day10 交换状态流转接口测试汇总：PASS=%d FAIL=%d =====" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
