# -*- coding: utf-8 -*-
"""
拾光Agent · Day8 快捷消息与交易状态逻辑自测（成员B 交付）
====================================================
任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 8 行，成员B 当日任务
「定义快捷消息和交易状态逻辑」（当天目标：轻量聊天）。

覆盖：
1. 快捷消息：模板齐全、key 唯一、字段完整、场景过滤、发送方过滤、占位符渲染、未知 key
2. 交易状态机：全状态覆盖、合法流转、非法流转拒绝、终态保护、取消规则、与 Day9/Day10 衔接

运行方式：python test_day8.py
依赖：仅标准库。
"""

import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.services.chat_rules import (QUICK_MESSAGES, QUICK_MESSAGES_INDEX, QUICK_MESSAGE_SCENES,
                        TRADE_STATES, TRANSITIONS, TRANSITION_MAP, TERMINAL_STATES,
                        ALLOW_CANCEL_FROM, get_quick_messages, render_quick_message,
                        validate_transition, next_allowed_states)

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print("[PASS]", name)
    else:
        FAIL += 1
        print("[FAIL]", name, "->", detail)


# ---------------------------------------------------------------------------
# 1) 快捷消息
# ---------------------------------------------------------------------------

def test_quick_messages():
    print("\n===== 1) 快捷消息模板 =====")
    check("模板数量 >= 15", len(QUICK_MESSAGES) >= 15, len(QUICK_MESSAGES))
    check("key 唯一", len({m["key"] for m in QUICK_MESSAGES}) == len(QUICK_MESSAGES))
    check("索引与列表一致", len(QUICK_MESSAGES_INDEX) == len(QUICK_MESSAGES))

    field_ok = all(
        set(m.keys()) == {"key", "text", "scene", "sender"}
        and m["scene"] in QUICK_MESSAGE_SCENES
        and m["sender"] in ("buyer", "seller", "any")
        for m in QUICK_MESSAGES
    )
    check("字段完整且取值合法", field_ok)

    # 场景全覆盖
    scenes_used = {m["scene"] for m in QUICK_MESSAGES}
    check("6 个场景均有模板", set(QUICK_MESSAGE_SCENES) == scenes_used, scenes_used)

    # 场景过滤
    only_price = get_quick_messages(scene="price")
    check("场景过滤 price 仅含 price", all(m["scene"] == "price" for m in only_price)
          and len(only_price) >= 3, len(only_price))

    # 发送方过滤：buyer 看到模板不应含 seller-only
    buyer_msgs = get_quick_messages(sender="buyer")
    check("buyer 过滤不含 seller 专属", all(m["sender"] in ("any", "buyer") for m in buyer_msgs))

    # 占位符渲染
    text = render_quick_message("price_offer", amount=25)
    check("price_offer 渲染占位符", text == "我出 25 元，你看可以吗？", text)
    text2 = render_quick_message("meet_time", time="明天下午 3 点")
    check("meet_time 渲染占位符", text2 == "好的，约个时间：明天下午 3 点，可以吗？", text2)

    # 未知 key / 空渲染
    check("未知 key -> None", render_quick_message("no_such_key") is None)
    check("无占位符 key 渲染不变",
          render_quick_message("want") == "你好，我想要这个，还在吗？")

    # 返回副本不污染原表
    msgs = get_quick_messages(scene="greeting")
    if msgs:
        msgs[0]["text"] = "HACKED"
        check("get_quick_messages 返回副本", QUICK_MESSAGES_INDEX[msgs[0]["key"]]["text"] != "HACKED")


# ---------------------------------------------------------------------------
# 2) 交易状态机
# ---------------------------------------------------------------------------

def test_state_machine():
    print("\n===== 2) 交易状态机 =====")
    check("状态覆盖 6 个", len(TRADE_STATES) == 6, len(TRADE_STATES))
    expect_states = {"requested", "chatting", "matched", "negotiating",
                     "confirmed", "cancelled"}
    check("核心链路状态齐全", expect_states <= set(TRADE_STATES))

    # 全部 TRANSITIONS 引用的状态必须已定义
    state_ok = all(f in TRADE_STATES and t in TRADE_STATES for f, t, _ in TRANSITIONS)
    check("流转表状态均已定义", state_ok)

    # 合法流转：全链路
    full_chain = [("requested", "chatting"), ("chatting", "matched"),
                  ("matched", "negotiating"), ("negotiating", "confirmed")]
    chain_ok = all(validate_transition(f, t)["valid"] for f, t in full_chain)
    check("全链路 4 步均合法（想要→聊天→匹配→协商→确认）", chain_ok)

    # 非法流转拒绝
    bad_cases = [
        ("requested", "confirmed"),   # 跳过中间态
        ("matched", "chatting"),      # 回退
        ("confirmed", "cancelled"),   # 终态不可取消
        ("cancelled", "requested"),   # 终态复活
        ("negotiating", "requested"),  # 回退
    ]
    for f, t in bad_cases:
        r = validate_transition(f, t)
        check("非法流转 %s -> %s 被拒" % (f, t), not r["valid"], r)

    # 终态保护
    check("confirmed 不可流转", next_allowed_states("confirmed") == [])
    check("cancelled 不可流转", next_allowed_states("cancelled") == [])

    # 取消规则
    for f in sorted(ALLOW_CANCEL_FROM):
        r = validate_transition(f, "cancelled")
        check("非终态 %s 可取消" % f, r["valid"], r)

    # 未知状态
    check("未知 from -> invalid", not validate_transition("ghost", "chatting")["valid"])
    check("未知 to -> invalid", not validate_transition("chatting", "ghost")["valid"])
    check("未知状态 next_allowed -> []", next_allowed_states("ghost") == [])

    # 自环视为合法（状态未变化）
    check("自环合法", validate_transition("chatting", "chatting")["valid"])

    # TRANSITION_MAP 一致性
    map_ok = all(len(TRANSITION_MAP.get(f, [])) >= 1 for f in ("requested", "chatting", "matched", "negotiating"))
    check("TRANSITION_MAP 覆盖 4 个非终态", map_ok, TRANSITION_MAP.keys())

    # Day9/Day10 衔接：matched 可由 chatting 到达，confirmed 为链路终点
    check("Day9 衔接：chatting -> matched 合法",
          validate_transition("chatting", "matched")["valid"])
    check("Day10 衔接：negotiating -> confirmed 合法",
          validate_transition("negotiating", "confirmed")["valid"])
    check("confirmed 为终态", "confirmed" in TERMINAL_STATES)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_quick_messages()
    test_state_machine()
    print("\n===== Day8 自测结果汇总：PASS=%d FAIL=%d =====" % (PASS, FAIL))
    sys.exit(0 if FAIL == 0 else 1)
