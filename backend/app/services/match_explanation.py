# -*- coding: utf-8 -*-
"""
拾光Agent · 匹配解释文本与交换协议文本模块 match_explanation.py（成员B Day 10 交付）
============================================================================
任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 10 行，成员B 当日任务
「完成匹配解释文本」（当天目标：交换协议；验收：匹配→发起交换→双方确认→生成协议卡片）。

本模块在 Day9 match_engine 输出的 match_reason（一句话解释）之上，为「交换详情页 /
交换协议卡片」场景提供三层产出：

1) build_match_explanation()
   完整匹配解释文本：逐条列出各维度（类别/意愿、价格接近、同校）的得分与权重、
   匹配分级原因，供前端展示「为什么推荐这次交换」。

2) build_exchange_protocol_text()
   交换协议卡片文本：双方用户/物品/真实标价/学校/匹配结论/状态/确认信息，
   供成员C/D 渲染协议卡片（计划书 §三.7 交换协议、§七 Exchange 表）。

3) validate_protocol()
   协议生成前置校验：状态机合法性（衔接 Day8 chat_rules：negotiating -> confirmed）、
   双方确认标记齐全、基础条件（双方物品可交换）。

与前后模块衔接：
- 上游：Day9 match_engine.match_score / recommend / build_match_reason（本模块可导入复用）
- 下游：Day8 chat_rules.validate_transition（状态机合法性校验；导入失败自动降级）
- 数据来源：Goods 表字段（category_id / asking_price / school_id / status / name）
依赖：仅标准库。
"""

import sys

# ---------------------------------------------------------------------------
# Day9 / Day8 模块衔接（可选导入，失败自动降级；本模块仍可独立运行）
# ---------------------------------------------------------------------------
from .match_engine import (
    match_score, recommend_level, build_match_reason,
    THRESHOLD_HIGH, THRESHOLD_NORMAL,
)

try:
    from .chat_rules import validate_transition
except ModuleNotFoundError:
    validate_transition = None

# Day7 类别/品相名称（用于解释文本更友好；导入失败回退内置精简表）
try:
    from .price_engine import CATEGORY_NAMES, CONDITION_NAMES
except ModuleNotFoundError:
    CATEGORY_NAMES = {}
    CONDITION_NAMES = {}

# 状态中文名（Day8 已定义；此处内置一份便于独立渲染，避免跨目录强依赖）
STATE_NAMES = {
    "requested": "已发起想要请求",
    "chatting": "聊天中",
    "matched": "已匹配",
    "negotiating": "交换待确认",
    "confirmed": "已确认",
    "cancelled": "已取消",
}

LEVEL_NAMES = {"high": "高匹配", "normal": "普通匹配", "low": "低匹配"}


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------
def _cat_name(category_id):
    """类别中文名；无则回退原始 id。"""
    if category_id is None:
        return "未知"
    return CATEGORY_NAMES.get(str(category_id), str(category_id))


def _fmt_price(value):
    """标价展示：None/非法显示 '未填写'，整数不带小数。"""
    if value is None or value == "":
        return "未填写"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if num != num or num < 0:
        return str(value)
    if num == int(num):
        return str(int(num))
    return "{:.2f}".format(num)


def _school_text(school_id_a, school_id_b):
    """同校/跨校文本。"""
    if school_id_a is None or school_id_b is None:
        return "学校信息缺失"
    return "同校" if str(school_id_a) == str(school_id_b) else "跨校"


def _fmt_score(value):
    """得分展示为百分比整数（0.9375 -> 94%）。"""
    if value is None:
        return "未计"
    try:
        return str(int(round(float(value) * 100))) + "%"
    except (TypeError, ValueError):
        return str(value)


# ---------------------------------------------------------------------------
# 一、完整匹配解释文本
# ---------------------------------------------------------------------------
def build_match_explanation(goods_a, goods_b, match_result=None, include_detail=True):
    """
    生成完整匹配解释文本（含维度明细与分级原因）。

    参数：
        goods_a / goods_b : 双方商品 dict（同 Day9 match_engine 输入约定）
        match_result      : 可选，Day9 match_score() 返回结果；缺省时内部重新计算
        include_detail    : 是否包含逐维度明细行
    返回：
        str 解释文本；无法匹配（None 结果）时返回以「暂不推荐」开头的说明文本。
    """
    result = match_result
    if result is None and match_score is not None:
        result = match_score(goods_a, goods_b)

    a_name = _cat_name(goods_a.get("category_id"))
    b_name = _cat_name(goods_b.get("category_id"))

    if result is None:
        return ("暂不推荐本次交换：双方物品类别/意愿未形成匹配，"
                "或任一方物品当前不可交换。（%s ↔ %s）"
                % (a_name, b_name))

    score = result["match_score"]
    detail = result["score_detail"]
    level_name = LEVEL_NAMES.get(result["level"], result["level"])
    reason = result.get("match_reason", "")

    if not include_detail:
        return "匹配度 %s，%s。%s" % (_fmt_score(score), level_name, reason)

    school_txt = _school_text(goods_a.get("school_id"), goods_b.get("school_id"))
    lines = [
        "匹配说明（%s ↔ %s）：" % (a_name, b_name),
        "- 类别/意愿（权重50%%）：%s，得分 %s" % (
            _wish_desc(goods_a, goods_b, detail["category_wish"]),
            _fmt_score(detail["category_wish"])),
        "- 价格接近（权重30%%）：%s，得分 %s" % (
            _price_desc(goods_a, goods_b, detail["price"]),
            _fmt_score(detail["price"])),
        "- 同校优先（权重20%%）：%s，得分 %s" % (
            school_txt, _fmt_score(detail["school"])),
        "综合匹配度 %s，属「%s」，%s。"
        % (_fmt_score(score), level_name, _level_tip(result["level"])),
    ]
    return "\n".join(lines)


def _wish_desc(goods_a, goods_b, cw):
    """类别/意愿维度描述文本。"""
    if cw >= 1.0:
        return "双方意愿双向命中（你想要的正是对方物品）"
    if cw >= 0.9:
        return "双方在售物品类别一致（未表达显式意愿）"
    if cw >= 0.5:
        return "单向意愿命中（仅一方想要对方物品）"
    return "类别/意愿未命中"


def _price_desc(goods_a, goods_b, pc):
    """价格维度描述文本（含免费赠送中性说明）。"""
    a = goods_a.get("asking_price")
    b = goods_b.get("asking_price")
    if a in (0, "0") and b in (0, "0"):
        return "双方均免费赠送，视为价格完全接近"
    if a in (0, "0") or b in (0, "0"):
        return "一方为免费赠送，价格维度按中性处理"
    if pc >= 1.0:
        return "双方标价相同（%s 元）" % _fmt_price(a)
    return "双方标价 %s 元与 %s 元接近度 %s" % (_fmt_price(a), _fmt_price(b), _fmt_score(pc))


def _level_tip(level):
    """分级原因提示。"""
    if level == "high":
        return "推荐优先交换"
    if level == "normal":
        return "可作为候选，建议继续沟通"
    return "匹配度较低，暂不推荐"


# ---------------------------------------------------------------------------
# 二、交换协议卡片文本
# ---------------------------------------------------------------------------
def build_exchange_protocol_text(goods_a, user_a, goods_b, user_b,
                                 exchange_id=None, state="negotiating",
                                 confirm_a=False, confirm_b=False,
                                 match_result=None):
    """
    生成交换协议卡片文本（供成员C/D 渲染协议卡片）。

    参数：
        goods_a / user_a  : 甲方商品 dict / 用户 dict（含 nickname / school_name 可选）
        goods_b / user_b  : 乙方商品 dict / 用户 dict
        exchange_id       : 可选，Exchange 表 id（无则显示占位）
        state             : 交易状态（negotiating / confirmed / cancelled 等）
        confirm_a / confirm_b : 双方是否已确认
        match_result      : 可选，Day9 match_score() 结果（缺省自动计算）
    返回：
        多行协议文本 str。
    """
    a_name = _cat_name(goods_a.get("category_id"))
    b_name = _cat_name(goods_b.get("category_id"))
    a_goods_name = goods_a.get("name") or ("物品%s" % goods_a.get("goods_id", ""))
    b_goods_name = goods_b.get("name") or ("物品%s" % goods_b.get("goods_id", ""))
    a_user_name = (user_a or {}).get("nickname") or ("用户%s" % (user_a or {}).get("user_id", "A"))
    b_user_name = (user_b or {}).get("nickname") or ("用户%s" % (user_b or {}).get("user_id", "B"))
    a_school = (user_a or {}).get("school_name") or goods_a.get("school_id") or "未知"
    b_school = (user_b or {}).get("school_name") or goods_b.get("school_id") or "未知"

    reason = ""
    if match_result is None and match_score is not None:
        match_result = match_score(goods_a, goods_b)
    if match_result is not None:
        reason = match_result.get("match_reason", "")

    state_name = STATE_NAMES.get(state, state)
    confirm_a_txt = "已确认" if confirm_a else "待确认"
    confirm_b_txt = "已确认" if confirm_b else "待确认"

    lines = [
        "拾光Agent · 物品交换协议",
        "协议编号：%s" % ("EX-%s" % exchange_id if exchange_id is not None else "待生成"),
        "甲方：%s（用户%s）｜物品：%s（%s）｜标价：%s 元｜学校：%s" % (
            a_user_name, (user_a or {}).get("user_id", "A"), a_goods_name, a_name,
            _fmt_price(goods_a.get("asking_price")), a_school),
        "乙方：%s（用户%s）｜物品：%s（%s）｜标价：%s 元｜学校：%s" % (
            b_user_name, (user_b or {}).get("user_id", "B"), b_goods_name, b_name,
            _fmt_price(goods_b.get("asking_price")), b_school),
    ]
    if reason:
        lines.append("匹配结论：%s" % reason)
    lines.append("交易状态：%s" % state_name)
    lines.append("确认状态：甲方%s，乙方%s" % (confirm_a_txt, confirm_b_txt))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 三、协议生成前置校验
# ---------------------------------------------------------------------------
def validate_protocol(goods_a, goods_b, state="negotiating",
                      confirm_a=False, confirm_b=False):
    """
    协议生成前置校验。

    返回：
        {"valid": True/False, "reason": str, "state_valid": bool, ...}
    校验项：
        1) 双方物品可交换（status 允许；缺失视为可交换）
        2) 状态机合法：默认要求 state 为 negotiating，且 negotiating -> confirmed 为合法流转
           （衔接 Day8 chat_rules；导入失败时使用内置规则表）
        3) 双方确认标记齐全（确认后需双方均为 True）
        4) 类别/意愿匹配存在（match_score 不为 None，避免对不可匹配对象生成协议）
    """
    from_match = state
    to_match = "confirmed"

    # 1) 物品可交换
    status_a = str(goods_a.get("status") or "on_sale")
    status_b = str(goods_b.get("status") or "on_sale")
    exchangeable = {"on_sale", "active", "available", "可交换"}
    if status_a not in exchangeable or status_b not in exchangeable:
        return {"valid": False, "reason": "任一方物品当前不可交换",
                "state_valid": False}

    # 2) 状态机合法性：非终态需校验 negotiating -> confirmed 合法流转；
    #    终态（confirmed / cancelled）为已完成的协议状态，豁免流转校验
    FINAL_STATES = {"confirmed", "cancelled"}
    state_valid = True
    state_reason = ""
    if state in FINAL_STATES:
        state_valid = True
        state_reason = "终态协议（%s），无需流转校验" % state
    elif validate_transition is not None:
        r = validate_transition(from_match, to_match)
        state_valid = r["valid"]
        state_reason = r["reason"]
    else:
        # 内置规则（与 Day8 一致）：negotiating -> confirmed 合法
        state_valid = (from_match == "negotiating" and to_match == "confirmed")
        state_reason = "negotiating -> confirmed 为合法流转" if state_valid else "非法流转"

    if not state_valid:
        return {"valid": False, "reason": "状态流转非法：%s -> %s（%s）"
                % (from_match, to_match, state_reason), "state_valid": False}

    # 3) 匹配存在（不可匹配不生成协议）
    m = None
    if match_score is not None:
        m = match_score(goods_a, goods_b)
    if m is None:
        return {"valid": False, "reason": "双方类别/意愿未形成匹配，无法生成交换协议",
                "state_valid": True}

    # 4) 确认标记：双方确认后协议生成
    if state == "confirmed" and not (confirm_a and confirm_b):
        return {"valid": False, "reason": "状态为已确认但双方确认标记未齐全",
                "state_valid": True}

    return {"valid": True, "reason": "协议生成校验通过（%s）" % state_reason,
            "state_valid": True, "match_score": m["match_score"]}


# ---------------------------------------------------------------------------
# 简易命令行自测入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("match_explanation.py（Day10 匹配解释文本与交换协议）自测：")
    A = {"category_id": "textbook", "wish_category_id": "physics",
         "asking_price": 30, "school_id": 1, "status": "on_sale",
         "goods_id": 12, "user_id": 1, "name": "高等数学"}
    B = {"category_id": "physics", "wish_category_id": "textbook",
         "asking_price": 32, "school_id": 1, "status": "on_sale",
         "goods_id": 20, "user_id": 2, "name": "大学物理"}
    print(build_match_explanation(A, B))
    print("---")
    print(build_exchange_protocol_text(A, {"user_id": 1, "nickname": "小明", "school_name": "同校大学"},
                                       B, {"user_id": 2, "nickname": "小红", "school_name": "同校大学"},
                                       exchange_id=1, state="negotiating",
                                       confirm_a=True, confirm_b=True))
    v = validate_protocol(A, B, state="negotiating", confirm_a=True, confirm_b=True)
    print("validate_protocol ->", v)
    assert v["valid"], "协议校验应通过"
    print("match_explanation 自测通过")
