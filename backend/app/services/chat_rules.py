# -*- coding: utf-8 -*-
"""
拾光Agent · 快捷消息与交易状态逻辑（成员B Day 8 交付）
========================================================
任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 8 行，成员B 当日任务
「定义快捷消息和交易状态逻辑」（当天目标：轻量聊天）。

本模块交付两部分业务规则定义（仅标准库，供后端成员A 直接落地 API，前端取文案渲染）：

1) 快捷消息模板 QUICK_MESSAGES
   聊天页一键发送的模板文案，按场景分组，避免 15 天内开发复杂实时 IM
   （计划书三-5「轻量聊天」）。含用户侧模板与发送方约束。

2) 交易状态机 TRADE_STATES / TRANSITIONS / validate_transition()
   围绕「我想要 → 聊天 → 匹配 → 交换 → 确认」整条链路的交易状态流转规则，
   Day7（商品详情/我想要）与 Day9（匹配算法）为相邻状态来源，Day10 为下游确认态。
   状态字段建议由后端写入 Transaction / Goods.status 侧，本模块只定义规则。

依赖：仅标准库。
"""

# ---------------------------------------------------------------------------
# 一、快捷消息模板
# ---------------------------------------------------------------------------

# 场景分组：每个场景下含若干模板
QUICK_MESSAGE_SCENES = {
    "greeting": "打招呼",
    "request": "想要/交易请求",
    "price": "价格沟通",
    "swap": "以物换物",
    "meet": "见面/取件",
    "deal": "确认/完成",
}

# 模板字段：key（唯一标识）/ text（文案，{占位符} 由前端替换）/ scene / sender（建议发送方）
# sender 取值：buyer=想要方 / seller=发布方 / any=双方可用
QUICK_MESSAGES = [
    {"key": "hi", "text": "你好，我看到你发布的物品，想了解一下～",
     "scene": "greeting", "sender": "any"},
    {"key": "thanks", "text": "好的，谢谢！",
     "scene": "greeting", "sender": "any"},

    {"key": "want", "text": "你好，我想要这个，还在吗？",
     "scene": "request", "sender": "buyer"},
    {"key": "want_available", "text": "还在的，可以拍给你看～",
     "scene": "request", "sender": "seller"},
    {"key": "want_sold", "text": "不好意思，这个已经被预定了。",
     "scene": "request", "sender": "seller"},

    {"key": "price_negotiate", "text": "价格可以再商量一下吗？",
     "scene": "price", "sender": "buyer"},
    {"key": "price_offer", "text": "我出 {amount} 元，你看可以吗？",
     "scene": "price", "sender": "buyer"},
    {"key": "price_accept", "text": "可以的，按这个价格成交。",
     "scene": "price", "sender": "seller"},
    {"key": "price_decline", "text": "这个价格稍微低了点，再考虑考虑？",
     "scene": "price", "sender": "seller"},

    {"key": "swap_suggest", "text": "我有一件物品想和你交换，可以看看吗？",
     "scene": "swap", "sender": "buyer"},
    {"key": "swap_show", "text": "可以，我把我的物品发给你看看～",
     "scene": "swap", "sender": "any"},
    {"key": "swap_confirm", "text": "可以，交换吧～",
     "scene": "swap", "sender": "any"},

    {"key": "meet_place", "text": "校内哪里见面交易？",
     "scene": "meet", "sender": "any"},
    {"key": "meet_time", "text": "好的，约个时间：{time}，可以吗？",
     "scene": "meet", "sender": "any"},

    {"key": "confirm_deal", "text": "确认交易，谢谢！",
     "scene": "deal", "sender": "any"},
    {"key": "free_thanks", "text": "谢谢免费赠送，我会好好用的～",
     "scene": "deal", "sender": "buyer"},
    {"key": "complete_feedback", "text": "交易完成，祝你使用愉快！",
     "scene": "deal", "sender": "any"},
]

# 快捷消息 key -> 模板 dict（去重校验用）
QUICK_MESSAGES_INDEX = {m["key"]: m for m in QUICK_MESSAGES}


def get_quick_messages(scene=None, sender=None):
    """
    按场景/发送方过滤快捷消息模板列表。

    参数：
        scene : None 或 QUICK_MESSAGE_SCENES 中的 key（如 "price"）
        sender: None 或 "buyer"/"seller"/"any"
    返回：过滤后的模板列表（原 dict 副本）。
    """
    result = []
    for m in QUICK_MESSAGES:
        if scene is not None and m["scene"] != scene:
            continue
        if sender is not None and m["sender"] != "any" and m["sender"] != sender:
            continue
        result.append(dict(m))
    return result


def render_quick_message(key, **placeholders):
    """
    渲染快捷消息文案：将 {占位符} 替换为传入值；未知 key 返回 None。

    示例：render_quick_message("price_offer", amount=25)
          -> "我出 25 元，你看可以吗？"
    """
    tpl = QUICK_MESSAGES_INDEX.get(key)
    if tpl is None:
        return None
    text = tpl["text"]
    for name, value in placeholders.items():
        text = text.replace("{" + name + "}", str(value))
    return text


# ---------------------------------------------------------------------------
# 二、交易状态机
# ---------------------------------------------------------------------------

# 交易状态常量（整条链路：我想要 → 聊天 → 匹配 → 交换 → 确认）
TRADE_STATES = {
    # 初始：用户B 点击「我想要」（Day7 验收产生请求）
    "requested": "已发起想要请求",
    # 进入聊天（Day8 轻量聊天；请求被接受或直接建立会话）
    "chatting": "聊天中",
    # Day9 匹配算法触发：双方物品/意愿互相匹配
    "matched": "已匹配",
    # Day10 前置：匹配后发起交换、待双方确认
    "negotiating": "交换待确认",
    # Day10：双方确认，生成交换协议
    "confirmed": "已确认",
    # 任一方取消 / 关闭交易
    "cancelled": "已取消",
}

# 状态流转规则表：(from, to) -> 触发说明
# 每条流转必须显式声明；未声明即为非法流转，拒绝更新。
TRANSITIONS = [
    # 请求 → 聊天
    ("requested", "chatting", "卖家接受请求，进入聊天（或系统自动建立会话）"),
    ("requested", "cancelled", "买家取消请求"),
    # 聊天 → 匹配 / 取消
    ("chatting", "matched", "Day9 匹配算法判定双方物品与意愿互相匹配"),
    ("chatting", "cancelled", "任一方取消交易"),
    # 匹配 → 交换协商 / 取消
    ("matched", "negotiating", "任一方发起交换，等待双方确认"),
    ("matched", "cancelled", "匹配后任一方放弃"),
    # 协商 → 确认 / 取消
    ("negotiating", "confirmed", "双方均确认，生成交换协议"),
    ("negotiating", "cancelled", "任一方取消或协商失败"),
    # 已确认后不再流转（协议生效，交易闭环）
]

# 便捷查询：from -> [(to, 说明), ...]
TRANSITION_MAP = {}
for _from, _to, _desc in TRANSITIONS:
    TRANSITION_MAP.setdefault(_from, []).append((_to, _desc))

# 终态：不可再流转的状态
TERMINAL_STATES = {"confirmed", "cancelled"}

# 允许从任意非终态直接取消
ALLOW_CANCEL_FROM = set(TRADE_STATES) - TERMINAL_STATES


def validate_transition(from_state, to_state):
    """
    校验交易状态流转是否合法。

    返回：
        {"valid": True, "reason": "..."}
        或 {"valid": False, "reason": "非法流转：..."}
    """
    if from_state not in TRADE_STATES:
        return {"valid": False, "reason": "未知状态：%s" % (from_state,)}
    if to_state not in TRADE_STATES:
        return {"valid": False, "reason": "未知状态：%s" % (to_state,)}
    if from_state == to_state:
        return {"valid": True, "reason": "状态未变化"}
    if to_state == "cancelled":
        if from_state in ALLOW_CANCEL_FROM:
            return {"valid": True, "reason": "任一方取消交易"}
        return {"valid": False, "reason": "终态不可取消"}
    for f, t, desc in TRANSITIONS:
        if f == from_state and t == to_state:
            return {"valid": True, "reason": desc}
    return {"valid": False, "reason": "非法流转：%s -> %s" % (from_state, to_state)}


def next_allowed_states(from_state):
    """
    返回某状态可到达的下一状态列表 [(to, 说明), ...]；未知状态返回 []。
    """
    return list(TRANSITION_MAP.get(from_state, []))


# ---------------------------------------------------------------------------
# 简易命令行自测入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("chat_rules.py（Day8 快捷消息与交易状态逻辑）自测：")
    assert get_quick_messages(scene="price", sender="buyer"), "price 场景 buyer 模板为空"
    text = render_quick_message("price_offer", amount=25)
    print("price_offer 渲染 ->", text)
    assert text == "我出 25 元，你看可以吗？", "占位符渲染失败"
    r = validate_transition("chatting", "matched")
    print("chatting -> matched:", r)
    assert r["valid"], "chatting -> matched 应为合法流转"
    print("快捷消息与状态机自测通过")
