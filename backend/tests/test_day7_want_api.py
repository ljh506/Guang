# -*- coding: utf-8 -*-
"""Day7 后端 API 验收测试：收藏/想要请求（Want）API + 状态字段 + 商品详情联动。

覆盖（对应计划书 Day7 成员A 任务「完成收藏/想要请求 API 和状态字段」）：
1. ★ 计划书验收链路：用户A发布 → 用户B点击我想要 → 产生请求（pending）
2. 商品详情 wants_count 想要人数展示
3. 重复发起 / 对自己商品发起 / 商品不存在 等错误分支
4. 卖家查看商品收到的想要请求列表
5. 买家查看「我想要的」列表（含商品名）
6. 状态字段流转：pending -> accepted（商品 available -> reserved）/ rejected / cancelled
7. 终态保护与非法状态拦截

运行：C:\\Users\\HUAWEI\\mini\\envs\\shiguang\\python.exe backend/tests/test_day7_want_api.py
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


# ---------- 前置：自建 school + 用户A（卖家） + 用户B（买家） ----------
uniq = int(time.time() * 1000)
school_id = client.post("/api/v1/schools", json={
    "name": f"Day7测试大学-{uniq}", "latitude": 39.9, "longitude": 116.4}).json()["id"]
user_a = client.post("/api/v1/users", json={
    "nickname": f"卖家A-{uniq}", "school_id": school_id}).json()["id"]
user_b = client.post("/api/v1/users", json={
    "nickname": f"买家B-{uniq}", "school_id": school_id}).json()["id"]
check("前置 school/user 创建成功",
      school_id is not None and user_a is not None and user_b is not None,
      (school_id, user_a, user_b))

# 用户A 发布商品（68 元教材良好 -> 27~41，沿用 Day6 验收场景）
r = client.post("/api/v1/goods", json={
    "user_id": user_a, "name": "高等数学（上册）", "category": "textbook",
    "condition": "good", "original_price": 68, "asking_price": 30,
    "description": "九成新", "trade_type": "sell"})
g = r.json().get("goods", {})
goods_id = g.get("id")
check("用户A发布商品 201", r.status_code == 201 and goods_id is not None,
      (r.status_code, r.text))
check("发布商品估价 27~41", g.get("estimated_min") == 27
      and g.get("estimated_max") == 41, g)

# ---------- 1. ★ 用户B 点击「我想要」 -> 产生请求（pending） ----------
r = client.post(f"/api/v1/goods/{goods_id}/want",
                json={"user_id": user_b, "message": "同学你好，这本书我想要！"})
w = r.json().get("want", {})
want_id = w.get("id")
check("★ 点击我想要 -> 201 创建请求", r.status_code == 201 and want_id is not None,
      (r.status_code, r.text))
check("请求初始状态 pending", w.get("status") == "pending", w)
check("请求携带商品ID/买家ID/留言", w.get("goods_id") == goods_id
      and w.get("requester_id") == user_b
      and "我想要" in (w.get("message") or ""), w)

# ---------- 2. 商品详情 wants_count ----------
rr = client.get(f"/api/v1/goods/{goods_id}")
check("详情 wants_count = 1（pending 计入）",
      rr.json().get("wants_count") == 1, rr.json())

# ---------- 3. 错误分支 ----------
r = client.post(f"/api/v1/goods/{goods_id}/want", json={"user_id": user_b})
check("重复发起 -> 400", r.status_code == 400, (r.status_code, r.text))
r = client.post(f"/api/v1/goods/{goods_id}/want", json={"user_id": user_a})
check("对自己商品发起 -> 400", r.status_code == 400, (r.status_code, r.text))
r = client.post("/api/v1/goods/999999/want", json={"user_id": user_b})
check("商品不存在 -> 404", r.status_code == 404, (r.status_code, r.text))
r = client.post(f"/api/v1/goods/{goods_id}/want", json={"user_id": 999999})
check("买家不存在 -> 400", r.status_code == 400, (r.status_code, r.text))

# ---------- 4. 卖家查看商品收到的想要请求 ----------
r = client.get(f"/api/v1/goods/{goods_id}/wants")
body = r.json()
check("卖家查看请求列表 total=1", body.get("total") == 1, body)
check("请求列表含买家昵称与留言",
      body.get("items", [{}])[0].get("requester_nickname") == f"买家B-{uniq}"
      and body.get("items", [{}])[0].get("status") == "pending", body)
r = client.get(f"/api/v1/goods/{goods_id}/wants?status=accepted")
check("按状态过滤 accepted -> total=0", r.json().get("total") == 0, r.json())
r = client.get(f"/api/v1/goods/{goods_id}/wants?status=bogus")
check("非法状态 -> 400", r.status_code == 400, (r.status_code, r.text))

# ---------- 5. 买家查看「我想要的」列表 ----------
r = client.get(f"/api/v1/users/{user_b}/wants")
body = r.json()
check("买家我想要的列表 total=1", body.get("total") == 1, body)
check("列表含商品名", body.get("items", [{}])[0].get("goods_name") == "高等数学（上册）",
      body)

# ---------- 6. ★ 状态字段流转：pending -> accepted（商品 reserved） ----------
r = client.patch(f"/api/v1/wants/{want_id}", json={"status": "accepted"})
check("卖家接受 -> 200", r.status_code == 200, (r.status_code, r.text))
check("请求状态 accepted", r.json().get("want", {}).get("status") == "accepted",
      r.json())
rr = client.get(f"/api/v1/goods/{goods_id}")
check("接受后商品状态 available -> reserved", rr.json().get("status") == "reserved",
      rr.json())
check("详情 wants_count 仍计 accepted = 1", rr.json().get("wants_count") == 1,
      rr.json())

# 已接受后再次接受 / 拒绝 被拦截
r = client.patch(f"/api/v1/wants/{want_id}", json={"status": "accepted"})
check("已接受重复接受 -> 400", r.status_code == 400, (r.status_code, r.text))
r = client.patch(f"/api/v1/wants/{want_id}", json={"status": "rejected"})
check("已接受后拒绝 -> 400", r.status_code == 400, (r.status_code, r.text))

# ---------- 7. 终态保护 / 非法状态 / 取消 ----------
r = client.patch(f"/api/v1/wants/{want_id}", json={"status": "cancelled"})
check("已接受后取消 -> 200 cancelled", r.status_code == 200
      and r.json().get("want", {}).get("status") == "cancelled", (r.status_code, r.text))
r = client.patch(f"/api/v1/wants/{want_id}", json={"status": "pending"})
check("终态 cancelled 不可变更 -> 400", r.status_code == 400, (r.status_code, r.text))
r = client.patch("/api/v1/wants/999999", json={"status": "accepted"})
check("请求不存在 -> 404", r.status_code == 404, (r.status_code, r.text))
r = client.patch(f"/api/v1/wants/{want_id}", json={"status": "whatever"})
check("非法状态 -> 400", r.status_code == 400, (r.status_code, r.text))

# 新请求被接受时若商品已 exchanged/removed 则拒绝（先创建请求、商品随后下架）
r2 = client.post("/api/v1/goods", json={
    "user_id": user_a, "name": "已下架商品", "category": "life_goods",
    "condition": "fair", "original_price": 20, "trade_type": "sell"})
g2_id = r2.json().get("goods", {}).get("id")
w2 = client.post(f"/api/v1/goods/{g2_id}/want",
                 json={"user_id": user_b}).json().get("want", {})
client.patch(f"/api/v1/goods/{g2_id}", json={"status": "removed"})
r = client.patch(f"/api/v1/wants/{w2.get('id')}", json={"status": "accepted"})
check("商品已下架无法接受请求 -> 400", r.status_code == 400, (r.status_code, r.text))

print(f"\n===== Day7 想要请求 API 测试完成：PASS={PASS} FAIL={FAIL} =====")
sys.exit(1 if FAIL else 0)
