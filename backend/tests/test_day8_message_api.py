# -*- coding: utf-8 -*-
"""Day8 后端 API 验收测试：Message 模型 + 消息接口（轻量聊天）。

覆盖（对应计划书 Day8 成员A 任务「完成 Message 模型和消息接口」、
当天验收「想要请求 → 消息列表 → 聊天 → 发送/接收演示消息」）：
1. ★ 验收链路：卖家发布 → 买家想要（Day7）→ 卖家接受 → 创建会话
   → 买家发送消息（requested -> chatting）→ 卖家会话列表看到未读
   → 聊天记录读取 → 卖家回复（快捷消息文案）→ 双方收发成功
2. 快捷消息模板：数量/场景/发送方过滤（集成成员B chat_rules）
3. 消息列表页字段：last_message / unread_count / trade_state / 交易状态中文名
4. 已读标记：读后 unread_count = 0
5. 错误分支：非参与者发送 / 空内容 / 非法状态流转 / 未知 scene
6. 交易状态机流转：chatting -> matched 合法；跳过中间态/回退/终态被拒

运行：C:\\Users\\HUAWEI\\mini\\envs\\shiguang\\python.exe backend/tests/test_day8_message_api.py
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


# ---------- 前置：自建 school + 卖家A + 买家B + 无关用户C ----------
uniq = int(time.time() * 1000)
school_id = client.post("/api/v1/schools", json={
    "name": f"Day8测试大学-{uniq}", "latitude": 39.9, "longitude": 116.4}).json()["id"]
seller_a = client.post("/api/v1/users", json={
    "nickname": f"卖家A-{uniq}", "school_id": school_id}).json()["id"]
buyer_b = client.post("/api/v1/users", json={
    "nickname": f"买家B-{uniq}", "school_id": school_id}).json()["id"]
outsider_c = client.post("/api/v1/users", json={
    "nickname": f"路人C-{uniq}", "school_id": school_id}).json()["id"]
check("前置 school/用户 创建成功",
      school_id and seller_a and buyer_b and outsider_c,
      (school_id, seller_a, buyer_b, outsider_c))

# 卖家A 发布商品（68 元教材良好 -> 27~41，Day6 验收场景）
r = client.post("/api/v1/goods", json={
    "user_id": seller_a, "name": "高等数学（上册）", "category": "textbook",
    "condition": "good", "original_price": 68, "asking_price": 30,
    "description": "九成新", "trade_type": "sell"})
g = r.json().get("goods", {})
goods_id = g.get("id")
check("卖家A发布商品 201", r.status_code == 201 and goods_id, (r.status_code, r.text))

# ---------- 1) ★ 验收链路：想要 → 会话 → 消息列表 → 聊天 → 收发 ----------
want = client.post(f"/api/v1/goods/{goods_id}/want", json={
    "user_id": buyer_b, "message": "你好，我想要这个"}).json()["want"]
want_id = want["id"]
check("买家B发起想要 pending", want["status"] == "pending", want)

# 卖家A 接受想要 → 商品 available -> reserved
r = client.patch(f"/api/v1/wants/{want_id}", json={"status": "accepted"})
check("卖家A接受想要 accepted", r.status_code == 200 and r.json()["want"]["status"] == "accepted",
      (r.status_code, r.text))
goods_detail = client.get(f"/api/v1/goods/{goods_id}").json()
check("商品状态流转 reserved", goods_detail.get("status") == "reserved",
      goods_detail)

# 创建会话（关联 want）
r = client.post("/api/v1/conversations", json={
    "goods_id": goods_id, "buyer_id": buyer_b, "seller_id": seller_a, "want_id": want_id})
data = r.json()
conv = data["conversation"]
check("创建会话 201 / trade_state=requested",
      r.status_code == 201 and data["created"] is True and conv["trade_state"] == "requested",
      (r.status_code, data))

# 重复创建 → 复用已有会话
r2 = client.post("/api/v1/conversations", json={
    "goods_id": goods_id, "buyer_id": buyer_b, "seller_id": seller_a, "want_id": want_id})
check("重复创建复用会话", r2.json().get("created") is False and r2.json()["conversation"]["id"] == conv["id"],
      r2.json())

# 快捷消息模板（成员B chat_rules 集成）
r = client.get("/api/v1/quick-messages")
templates = r.json()["templates"]
check("快捷消息模板 >= 15 条", r.status_code == 200 and len(templates) >= 15, len(templates))
price_buyer = client.get("/api/v1/quick-messages", params={"scene": "price", "sender": "buyer"}).json()["templates"]
check("快捷消息 scene/sender 过滤",
      all(t["scene"] == "price" and t["sender"] in ("any", "buyer") for t in price_buyer),
      price_buyer)
r_bad_scene = client.get("/api/v1/quick-messages", params={"scene": "ghost"})
check("未知 scene 400", r_bad_scene.status_code == 400, (r_bad_scene.status_code, r_bad_scene.text))

# 买家B 发送消息（首条：requested -> chatting）
r = client.post(f"/api/v1/conversations/{conv['id']}/messages", json={
    "sender_id": buyer_b, "content": "你好，我想要这个，还在吗？"})
msg1 = r.json()["message"]
check("买家发送消息 201 / 状态流转 chatting",
      r.status_code == 201 and r.json()["trade_state"] == "chatting" and msg1["sender_nickname"],
      (r.status_code, r.json()))

# 卖家A 消息列表（未读 1 条 + 最后消息 + 交易状态名）
r = client.get("/api/v1/conversations", params={"user_id": seller_a})
lst = r.json()["items"]
check("卖家会话列表含该会话/未读=1/最后消息/状态名",
      r.status_code == 200 and len(lst) == 1 and lst[0]["unread_count"] == 1
      and lst[0]["last_message"] == msg1["content"]
      and lst[0]["trade_state_name"] == "聊天中" and lst[0]["goods_name"] == "高等数学（上册）",
      lst)

# 聊天记录（买家视角）
r = client.get(f"/api/v1/conversations/{conv['id']}/messages")
msgs = r.json()["items"]
check("聊天记录 1 条 / sender_nickname=买家B",
      r.status_code == 200 and len(msgs) == 1 and msgs[0]["sender_nickname"].startswith("买家B"),
      msgs)

# 卖家A 用快捷消息文案回复（渲染成员B price_accept 模板）
r = client.post(f"/api/v1/conversations/{conv['id']}/messages", json={
    "sender_id": seller_a, "content": "可以的，按这个价格成交。"})
check("卖家回复 201 / 共 2 条", r.status_code == 201, (r.status_code, r.text))
total = client.get(f"/api/v1/conversations/{conv['id']}/messages").json()["total"]
check("双方共收发 2 条消息", total == 2, total)

# 买家B 标记已读
r = client.post(f"/api/v1/conversations/{conv['id']}/read", json={"user_id": buyer_b})
check("标记已读 ok", r.status_code == 200 and r.json()["ok"] is True, (r.status_code, r.text))
lst_b = client.get("/api/v1/conversations", params={"user_id": buyer_b}).json()["items"]
check("买家未读清零", lst_b[0]["unread_count"] == 0, lst_b)

# ---------- 2) 错误分支 ----------
r = client.post(f"/api/v1/conversations/{conv['id']}/messages", json={
    "sender_id": outsider_c, "content": "乱入"})
check("非参与者发送 400", r.status_code == 400, (r.status_code, r.text))
r = client.post(f"/api/v1/conversations/{conv['id']}/messages", json={
    "sender_id": buyer_b, "content": "   "})
check("空内容发送 400", r.status_code == 400, (r.status_code, r.text))
r = client.get("/api/v1/conversations/999999")
check("会话不存在 404", r.status_code == 404, (r.status_code, r.text))
r = client.post("/api/v1/conversations", json={
    "goods_id": goods_id, "buyer_id": seller_a, "seller_id": seller_a})
check("买卖双方同一人 400", r.status_code == 400, (r.status_code, r.text))

# ---------- 3) 交易状态机（成员B chat_rules 校验） ----------
r = client.patch(f"/api/v1/conversations/{conv['id']}/state", json={"trade_state": "matched"})
check("chatting -> matched 合法（Day9 衔接）",
      r.status_code == 200 and r.json()["conversation"]["trade_state"] == "matched",
      (r.status_code, r.text))
r = client.patch(f"/api/v1/conversations/{conv['id']}/state", json={"trade_state": "confirmed"})
check("matched -> confirmed 非法（跳过 negotiating）400",
      r.status_code == 400, (r.status_code, r.text))
r = client.patch(f"/api/v1/conversations/{conv['id']}/state", json={"trade_state": "negotiating"})
check("matched -> negotiating 合法", r.status_code == 200, (r.status_code, r.text))
r = client.patch(f"/api/v1/conversations/{conv['id']}/state", json={"trade_state": "confirmed"})
check("negotiating -> confirmed 合法（Day10 衔接）",
      r.status_code == 200 and r.json()["conversation"]["trade_state"] == "confirmed",
      (r.status_code, r.text))
r = client.patch(f"/api/v1/conversations/{conv['id']}/state", json={"trade_state": "cancelled"})
check("终态 confirmed 不可取消 400", r.status_code == 400, (r.status_code, r.text))
r = client.patch(f"/api/v1/conversations/{conv['id']}/state", json={"trade_state": "ghost"})
check("未知状态 400", r.status_code == 400, (r.status_code, r.text))

print("\n===== Day8 消息接口测试汇总：PASS=%d FAIL=%d =====" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
