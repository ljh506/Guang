# -*- coding: utf-8 -*-
"""Day11 后端全链路联调验收测试：主流程 + 数据库数据一致性。

对应计划书 Day11 成员A 任务「解决所有接口联调问题，检查数据库数据一致性」、
当天验收硬性标准「主流程 选校→发布→AI→估价→漂流→想要→聊天→交换→协议
完整跑通」：

1. ★ 全链路：选校 → 发布 → AI识别(缺图/非法文件容错 400) → 估价(计划书示例
   68元/良好/教材=27~41) → 漂流(商品列表/详情) → 想要 → 聊天(会话/消息/状态机
   requested→chatting→matched→negotiating) → 交换(match→accept→confirm×2→
   confirmed) → 协议卡片(校验通过)
2. 数据一致性（DB 直接核查 + API 交叉验证）：
   - Exchange 确认后 exchanges.confirm_a/confirm_b/status 落库正确
   - 双方 goods.status → exchanged，匹配推荐不再出现已交换商品
   - 已确认交换不可重复发起（同一对再次 accept 被拦截）
   - conversation 状态机 negotiating→confirmed 合法衔接
   - wants 记录与 exchange 数据同库存在

运行：shiguang python backend/tests/test_day11_full_flow_api.py
"""
import os
import sys
import time
import sqlite3

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.database import SQLALCHEMY_DATABASE_URL  # noqa: E402

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


def db_rows(sql, args=()):
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "").replace("./", "")
    if not os.path.isabs(db_path):
        db_path = os.path.join(BACKEND_DIR, db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(sql, args)
        return cur.fetchall()
    finally:
        conn.close()


uniq = int(time.time() * 1000)

# ---------- 1) 选校 ----------
school_id = client.post("/api/v1/schools", json={
    "name": f"Day11联调大学-{uniq}", "latitude": 31.2, "longitude": 121.5}).json()["id"]
schools = client.get("/api/v1/schools", params={"keyword": "Day11联调大学"}).json()
schools = schools.get("items", schools) if isinstance(schools, dict) else schools
check("选校：新大学创建并可检索", school_id and any(
    str(s.get("id", s if isinstance(s, int) else -1)) == str(school_id)
    for s in schools), (school_id, schools))

# ---------- 2) 发布（双方商品） ----------
user_a = client.post("/api/v1/users", json={
    "nickname": f"成员甲-{uniq}", "school_id": school_id}).json()["id"]
user_b = client.post("/api/v1/users", json={
    "nickname": f"成员乙-{uniq}", "school_id": school_id}).json()["id"]
check("发布前置：两名同校用户创建成功", bool(user_a and user_b), (user_a, user_b))

r = client.post("/api/v1/goods", json={
    "user_id": user_a, "name": "高等数学（上册）", "category": "textbook",
    "condition": "good", "original_price": 68, "asking_price": 30,
    "trade_type": "exchange", "wish_category_id": "sports_equipment"})
g_a = r.json().get("goods", {})
check("发布：A发布教材(30,想换运动器材) 201",
      r.status_code == 201 and g_a.get("status") in ("available", "on_sale"),
      (r.status_code, r.text))

r = client.post("/api/v1/goods", json={
    "user_id": user_b, "name": "篮球（八成新）", "category": "sports_equipment",
    "condition": "good", "original_price": 72, "asking_price": 32,
    "trade_type": "exchange", "wish_category_id": "textbook"})
g_b = r.json().get("goods", {})
check("发布：B发布篮球(32,想换教材) 201",
      r.status_code == 201 and g_b.get("status") in ("available", "on_sale"),
      (r.status_code, r.text))

# ---------- 3) AI 识别（容错：缺图/非法文件 400；真实图片由前端上传） ----------
r = client.post("/api/v1/recognize")
check("AI识别：缺少图片 400（系统级校验正常）",
      r.status_code == 400 and "code" in r.json().get("detail", {}),
      (r.status_code, r.text))
r = client.post("/api/v1/recognize",
                files={"image": ("fake.txt", b"not an image", "text/plain")})
check("AI识别：非法文件格式 400", r.status_code == 400, (r.status_code, r.text))

# ---------- 4) 估价（计划书示例回归：68元/良好/教材=27~41） ----------
r = client.post("/api/v1/estimate", json={
    "category": "textbook", "condition": "good", "original_price": 68})
est = r.json()
check("估价：68元/良好/教材 → 27~41 区间（计划书§四示例）",
      r.status_code == 200 and est.get("success") is True
      and abs(est["data"]["estimated_min"] - 27) <= 2
      and abs(est["data"]["estimated_max"] - 41) <= 2,
      (r.status_code, est))

# ---------- 5) 漂流（商品列表/详情） ----------
r = client.get("/api/v1/goods", params={"page_size": 50})
items = r.json().get("items", [])
ids = [i.get("id") for i in items]
check("漂流：列表含双方商品", g_a.get("id") in ids and g_b.get("id") in ids,
      (r.status_code, len(items)))
r = client.get(f"/api/v1/goods/{g_a['id']}")
check("漂流：商品详情可读", r.status_code == 200
      and r.json().get("name") == "高等数学（上册）", (r.status_code, r.text))

# ---------- 6) 想要 ----------
r = client.post(f"/api/v1/goods/{g_a['id']}/want", json={
    "user_id": user_b, "message": "想用篮球换你的教材！"})
want = r.json().get("want", {})
check("想要：B对A教材发起想要 201/pending",
      r.status_code == 201 and want.get("status") == "pending",
      (r.status_code, r.text))
r = client.get(f"/api/v1/goods/{g_a['id']}/wants")
check("想要：A查看商品收到的想要列表",
      r.status_code == 200 and any(w["id"] == want["id"] for w in r.json().get("items", [])),
      (r.status_code, r.text))

# ---------- 7) 聊天（会话/消息/状态机） ----------
r = client.post("/api/v1/conversations", json={
    "goods_id": g_a["id"], "buyer_id": user_b, "seller_id": user_a,
    "want_id": want["id"]})
conv = r.json().get("conversation", {})
check("聊天：创建会话 requested",
      r.status_code == 201 and conv.get("trade_state") == "requested",
      (r.status_code, r.text))
r = client.post(f"/api/v1/conversations/{conv['id']}/messages", json={
    "sender_id": user_b, "content": "篮球八成新，同校可以当面交换！"})
check("聊天：发送消息 → chatting",
      r.status_code == 201 and r.json().get("trade_state") == "chatting",
      (r.status_code, r.text))
for target in ("matched", "negotiating"):
    r = client.patch(f"/api/v1/conversations/{conv['id']}/state",
                     json={"trade_state": target})
    check(f"聊天：状态流转 {target}",
          r.status_code == 200 and r.json()["conversation"]["trade_state"] == target,
          (r.status_code, r.text))

# ---------- 8) 交换（match→accept→confirm×2→confirmed→协议） ----------
r = client.post("/api/v1/exchange/match", json={"user_id": user_a, "goods_id": g_a["id"]})
data = r.json()["data"]
top = data[0] if data else {}
check("交换：match 高匹配 top1=B",
      r.status_code == 200 and top.get("target_goods_id") == g_b["id"]
      and top.get("level") == "high", (r.status_code, top))

r = client.post("/api/v1/exchange/accept", json={
    "user_id": user_a, "goods_id": g_a["id"], "target_goods_id": g_b["id"]})
ex = r.json().get("exchange", {})
check("交换：accept 落 open（待确认）",
      r.status_code == 201 and ex.get("status") == "open", (r.status_code, r.text))

r = client.post(f"/api/v1/exchange/{ex['id']}/confirm", json={"user_id": user_a})
check("交换：A确认 confirm_a=true", r.status_code == 200
      and r.json()["confirm_a"] is True, (r.status_code, r.text))
r = client.post(f"/api/v1/exchange/{ex['id']}/confirm", json={"user_id": user_b})
check("交换：B确认 → confirmed", r.status_code == 200
      and r.json()["status"] == "confirmed", (r.status_code, r.text))

r = client.get(f"/api/v1/exchange/{ex['id']}/protocol")
p = r.json()
check("协议：confirmed 协议卡片生成且校验通过",
      r.status_code == 200 and p["status"] == "confirmed"
      and p["validation"]["valid"] is True
      and "拾光Agent · 物品交换协议" in p["protocol_text"],
      (r.status_code, p))

# ---------- 9) 数据一致性（DB 直接核查 + API 交叉验证） ----------
rows = db_rows("SELECT status, confirm_a, confirm_b FROM exchanges WHERE id = ?",
               (ex["id"],))
check("DB：exchanges 记录 status=confirmed 且 confirm_a/b=1",
      rows and rows[0][0] == "confirmed" and rows[0][1] == 1 and rows[0][2] == 1,
      rows)

rows = db_rows("SELECT status FROM goods WHERE id IN (?, ?)", (g_a["id"], g_b["id"]))
check("DB：双方 goods.status → exchanged（防重复交换）",
      rows and set(r0[0] for r0 in rows) == {"exchanged"}, rows)

rows = db_rows("SELECT status FROM wants WHERE id = ?", (want["id"],))
check("DB：wants 记录仍存在（历史保留）", bool(rows), rows)

r = client.post("/api/v1/exchange/match", json={"user_id": user_a, "goods_id": g_a["id"]})
check("一致性：已交换商品不可再发起匹配（防重复交换）",
      r.status_code == 400, (r.status_code, r.text))

r = client.post("/api/v1/exchange/accept", json={
    "user_id": user_a, "goods_id": g_a["id"], "target_goods_id": g_b["id"]})
check("一致性：同一对已确认交换不可重复 accept（去重）",
      r.status_code in (400, 409), (r.status_code, r.text))

r = client.patch(f"/api/v1/conversations/{conv['id']}/state",
                 json={"trade_state": "confirmed"})
check("一致性：交换确认后 conversation 可流转 negotiating→confirmed",
      r.status_code == 200
      and r.json()["conversation"]["trade_state"] == "confirmed",
      (r.status_code, r.text))

# 交换记录与聊天会话同库交叉：exchanges 目标用户 = 会话买家
rows = db_rows("SELECT target_user_id FROM exchanges WHERE id = ?", (ex["id"],))
check("一致性：exchange.target_user_id == 会话 buyer（同库闭环）",
      rows and rows[0][0] == user_b, (rows, user_b))

print("\n===== Day11 全链路联调与数据一致性测试汇总：PASS=%d FAIL=%d =====" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
