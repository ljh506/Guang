# -*- coding: utf-8 -*-
"""
拾光Agent · 匹配算法模块 match_engine.py（成员B Day 9 交付）
========================================================
任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 9 行，成员B 当日任务
「完成匹配算法：类别匹配 / 用户意愿匹配 / 价格区间接近 / 同校优先」。

本模块依据 Day1 交付《3_交换匹配规则初稿.md》细则实现可解释规则匹配：

    MatchScore = 0.50 × Score_category_wish + 0.30 × Score_price + 0.20 × Score_school

- 类别/意愿 50%（Score_category_wish）：
    双向完全匹配（A 物品 ∈ B 意愿 且 B 物品 ∈ A 意愿）        = 1.0
    双向类别匹配（无显式意愿，双方在售类别互相一致）            = 0.9
    单向匹配（仅一方物品在对方意愿中）                          = 0.5
    类别完全不匹配                                              = 0.0（不进入候选）
- 价格接近 30%（Score_price，基于 Goods.asking_price 用户手填真实标价）：
    ratio = |a - b| / max(a, b)；Score = 1.0 - ratio
    双方标价相同 -> 1.0；双方均免费（0 元）-> 1.0；仅一方免费 -> 0.3；标价缺失 -> 0.0
    （建议估价区间 estimated_min / estimated_max 仅作展示字段接收，不参与得分）
- 同校优先 20%（Score_school）：school_id 相同 -> 1.0；不同 -> 0.0
- 推荐阈值：>= 0.75 高匹配 high；>= 0.50 普通 normal；< 0.50 低 low（不进推荐列表）
- 排序：总分降序；总分相同（±0.001）按价格接近度降序，再按发布时间近者优先；单次最多 20 条。
- 去重：同一对 (user, goods) 已存在未完成 Exchange 记录时不重复生成推荐。

输入衔接：
- category_id 来自 Day5 recognition_pipeline 输出（Day4 统一 10 类体系）
- asking_price 为 Goods 表用户手填真实标价（Day1 明确价格维度唯一依据）
- estimated_min / estimated_max 由 Day7 price_engine 保障非负整数、异常不崩，仅透传展示
- 匹配成功触发 Day8 状态机 chatting -> matched（本模块提供 on_match() 衔接建议）

依赖：仅标准库；可选衔接 Day8 chat_rules（导入失败自动降级，不影响匹配计算）。
"""

import sys
import time

# ---------------------------------------------------------------------------
# 常量（与计划书 §五 / Day1 初稿严格一致）
# ---------------------------------------------------------------------------
WEIGHT_CATEGORY_WISH = 0.50
WEIGHT_PRICE = 0.30
WEIGHT_SCHOOL = 0.20
WEIGHT_SUM = WEIGHT_CATEGORY_WISH + WEIGHT_PRICE + WEIGHT_SCHOOL  # = 1.0

THRESHOLD_HIGH = 0.75
THRESHOLD_NORMAL = 0.50

REC_HIGH = "high"
REC_NORMAL = "normal"
REC_LOW = "low"

MAX_RECOMMEND_RESULTS = 20

# 基础条件：物品状态允许交换的状态集合（默认；调用方可覆盖）
EXCHANGEABLE_STATUS = {"on_sale", "active", "available", "可交换"}

# 免费赠送中性分（仅一方标价 0 元时，规则化中性偏低分）
PRICE_ONE_FREE_SCORE = 0.3


# ---------------------------------------------------------------------------
# Day8 状态机衔接（可选导入，失败自动降级）
# ---------------------------------------------------------------------------
try:
    from chat_rules import validate_transition, TRADE_STATES
except ModuleNotFoundError:
    sys.path.insert(0, r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day8_交付")
    try:
        from chat_rules import validate_transition, TRADE_STATES
    except ModuleNotFoundError:
        validate_transition = None
        TRADE_STATES = None


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------
def _to_nonneg_float(value, default=None):
    """把输入转成非负浮点数；布尔值、NaN、负数、非数字一律视为非法返回 default。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    if num != num:  # NaN
        return default
    if num < 0 or num == float("inf"):
        return default
    return num


def _wish_set(wish_category_id):
    """把 wish_category_id（str / int / list / set）规范为 set；缺失返回空集。"""
    if wish_category_id is None:
        return set()
    if isinstance(wish_category_id, (list, tuple, set)):
        return {str(x) for x in wish_category_id}
    return {str(wish_category_id)}


def _norm_category(category_id):
    """类别 id 规范为 str；缺失返回 None。"""
    if category_id is None:
        return None
    return str(category_id)


# ---------------------------------------------------------------------------
# 一、维度打分
# ---------------------------------------------------------------------------
def category_wish_score(goods_a, goods_b):
    """
    类别/意愿匹配分（0~1）。
    依据 Day1 细则 §3.1：双向完全匹配 1.0 / 双向类别匹配 0.9 / 单向匹配 0.5 / 完全不匹配 0.0。
    """
    a_cat = _norm_category(goods_a.get("category_id"))
    b_cat = _norm_category(goods_b.get("category_id"))
    a_want_b = b_cat in _wish_set(goods_a.get("wish_category_id")) if b_cat else False
    b_want_a = a_cat in _wish_set(goods_b.get("wish_category_id")) if a_cat else False

    # 双向完全匹配（双方显式意愿互中对方物品）
    if a_want_b and b_want_a:
        return 1.0
    # 双向类别匹配（无显式意愿：双方在售物品类别互相对上）
    if a_cat is not None and a_cat == b_cat:
        return 0.9
    # 单向匹配（仅一方意愿命中）
    if a_want_b or b_want_a:
        return 0.5
    # 类别完全不匹配
    return 0.0


def price_score(asking_price_a, asking_price_b):
    """
    价格接近分（0~1），基于双方真实标价 asking_price（Day1 细则 §3.2）。
    ratio = |a - b| / max(a, b)；Score = 1.0 - ratio。
    - 双方均免费（0 元）    -> 1.0
    - 仅一方免费            -> 0.3（中性偏低，reason 注明）
    - 任一方标价缺失/非法   -> 0.0
    """
    a = _to_nonneg_float(asking_price_a)
    b = _to_nonneg_float(asking_price_b)
    if a is None or b is None:
        return 0.0
    if a == 0 and b == 0:
        return 1.0
    if a == 0 or b == 0:
        return PRICE_ONE_FREE_SCORE
    denom = max(a, b)
    ratio = abs(a - b) / denom
    score = 1.0 - ratio
    return max(0.0, min(1.0, score))


def school_score(school_id_a, school_id_b):
    """同校优先分（0~1）：相同 1.0；不同或缺失 0.0（Day1 细则 §3.3）。"""
    if school_id_a is None or school_id_b is None:
        return 0.0
    return 1.0 if str(school_id_a) == str(school_id_b) else 0.0


# ---------------------------------------------------------------------------
# 二、匹配度计算
# ---------------------------------------------------------------------------
def _is_exchangeable(goods, exchangeable_status):
    """基础条件：物品状态允许交换。缺失状态视为可交换（宽松默认）。"""
    status = goods.get("status")
    if status is None:
        return True
    return str(status) in exchangeable_status


def match_score(goods_a, goods_b, exchangeable_status=None):
    """
    计算双方匹配度（可解释规则）。

    参数：goods_a / goods_b 为商品字典，至少含：
        category_id, wish_category_id(可缺省), asking_price, school_id,
        可选：status / estimated_min / estimated_max / publish_time / goods_id / user_id
    返回：
        dict：{score, category_wish, price, school, level, match_reason, ...}
        若基础条件不满足（任一方不可交换）或类别完全不匹配 -> 返回 None（不进入候选）。
    """
    exchangeable_status = exchangeable_status or EXCHANGEABLE_STATUS

    # 基础条件 1：双方物品状态均可交换
    if not _is_exchangeable(goods_a, exchangeable_status) or \
       not _is_exchangeable(goods_b, exchangeable_status):
        return None

    # 基础条件 2：类别/意愿必须命中（完全不匹配 -> 不进入候选）
    cw = category_wish_score(goods_a, goods_b)
    if cw <= 0:
        return None

    pc = price_score(goods_a.get("asking_price"), goods_b.get("asking_price"))
    sc = school_score(goods_a.get("school_id"), goods_b.get("school_id"))

    total = round(WEIGHT_CATEGORY_WISH * cw + WEIGHT_PRICE * pc + WEIGHT_SCHOOL * sc, 4)
    level = recommend_level(total)

    return {
        "match_score": total,
        "score_detail": {
            "category_wish": round(cw, 4),
            "price": round(pc, 4),
            "school": round(sc, 4),
        },
        "weights": {
            "category_wish": WEIGHT_CATEGORY_WISH,
            "price": WEIGHT_PRICE,
            "school": WEIGHT_SCHOOL,
        },
        "level": level,
        "match_reason": build_match_reason(goods_a, goods_b, cw, pc, sc, total),
    }


def recommend_level(score):
    """推荐分级：>=0.75 high；>=0.50 normal；<0.50 low。"""
    if score >= THRESHOLD_HIGH:
        return REC_HIGH
    if score >= THRESHOLD_NORMAL:
        return REC_NORMAL
    return REC_LOW


def build_match_reason(goods_a, goods_b, cw, pc, sc, total):
    """
    生成 match_reason 解释文本（Day1 细则 §5 模板）。

    模板：双方意愿匹配（{A类别}↔{B类别}），双方标价 {a} 元与 {b} 元接近度 {p}%，
          {同校/跨校}，综合匹配度 {s}%。
    """
    a_cat = _norm_category(goods_a.get("category_id")) or "未知"
    b_cat = _norm_category(goods_b.get("category_id")) or "未知"
    a_price = goods_a.get("asking_price")
    b_price = goods_b.get("asking_price")

    if a_price is None or b_price is None:
        price_part = "价格信息不完整"
    elif a_price == 0 and b_price == 0:
        price_part = "双方均免费赠送"
    elif a_price == 0 or b_price == 0:
        price_part = "一方为免费赠送，价格维度按中性处理"
    else:
        pct = int(round(pc * 100))
        price_part = "双方标价 %s 元与 %s 元接近度 %d%%" % (a_price, b_price, pct)

    same_school = "同校" if sc >= 1.0 else "跨校"
    score_pct = int(round(total * 100))
    return ("双方意愿匹配（%s↔%s），%s，%s，综合匹配度 %d%%。"
            % (a_cat, b_cat, price_part, same_school, score_pct))


# ---------------------------------------------------------------------------
# 三、候选排序 recommend()
# ---------------------------------------------------------------------------
def _publish_time_of(goods):
    """取发布时间用于排序；缺失视为最早（0），保证不报错。"""
    pt = goods.get("publish_time")
    if pt is None:
        return 0
    try:
        if isinstance(pt, (int, float)):
            return pt
        return float(pt)
    except (TypeError, ValueError):
        return 0


def _dedup_key(goods_a, goods_b):
    """去重键：同一对 (user, goods) 双向归一化排序，避免 (A,B) 与 (B,A) 重复。"""
    id_a = (goods_a.get("user_id"), goods_a.get("goods_id"))
    id_b = (goods_b.get("user_id"), goods_b.get("goods_id"))
    if id_a[1] is None or id_b[1] is None:
        return None
    pair = (id_a, id_b)
    return tuple(sorted(pair, key=lambda x: (str(x[0]), str(x[1]))))


def recommend(user_goods, candidates, max_results=MAX_RECOMMEND_RESULTS,
              exchangeable_status=None, existing_pairs=None):
    """
    对候选列表按匹配度降序返回推荐（Day1 细则 §4 排序策略）。

    参数：
        user_goods     : 发起匹配用户的商品 dict（含 category_id / wish_category_id /
                         asking_price / school_id / status / publish_time 等）
        candidates     : 候选商品 dict 列表
        max_results    : 推荐上限（默认 20）
        existing_pairs : 已存在未完成 Exchange 的 (user_id, goods_id) 对列表，
                         用于去重；每项可为 (user_id, goods_id) 或 dict
    返回：
        [ {match_score, score_detail, level, match_reason, ...} ]，按总分降序；
        同分按价格接近度降序，再按发布时间近者优先；<0.50 的候选不进入列表。
    """
    seen = set()
    results = []
    for cand in candidates:
        m = match_score(user_goods, cand, exchangeable_status=exchangeable_status)
        if m is None:
            continue
        if m["match_score"] < THRESHOLD_NORMAL:
            continue  # 低匹配度不进入推荐列表

        # 去重：同一对 (user, goods) 已有未完成 Exchange 记录时跳过
        if existing_pairs:
            u_goods = user_goods.get("goods_id")
            u_user = user_goods.get("user_id")
            skip = False
            for pair in existing_pairs:
                p_user = pair.get("user_id") if isinstance(pair, dict) else pair[0]
                p_goods = pair.get("goods_id") if isinstance(pair, dict) else pair[1]
                if u_user == p_user and u_goods == p_goods:
                    skip = True
                    break
            if skip:
                continue

        # 排序键：总分降序 -> 价格接近度降序 -> 发布时间近者优先
        key = (-m["match_score"], -m["score_detail"]["price"],
               -_publish_time_of(cand))
        results.append((key, cand, m))

    results.sort(key=lambda x: x[0])
    ranked = []
    for _key, cand, m in results[:max_results]:
        item = dict(m)
        item["target_goods_id"] = cand.get("goods_id")
        item["target_user_id"] = cand.get("user_id")
        ranked.append(item)
    return ranked


# ---------------------------------------------------------------------------
# 四、Day8 状态机衔接
# ---------------------------------------------------------------------------
def on_match(current_state, score, from_state="chatting", to_state="matched"):
    """
    匹配成功后建议交易状态流转（衔接 Day8 chat_rules 状态机）。

    规则：当前状态为 chatting（或允许进入 matched 的状态）且匹配度 >= 0.75
          （高匹配）时，返回合法流转建议 {'valid': True, 'to_state': 'matched', ...}；
          匹配度未达高匹配时返回不建议流转（仍可人工发起，但非算法推荐）。

    返回：
        {"valid": bool, "from_state": ..., "to_state": ...,
         "reason": str, "score": float, "level": str}
    """
    level = recommend_level(score)
    if validate_transition is None:
        return {
            "valid": True if level == REC_HIGH and current_state == from_state else False,
            "from_state": current_state,
            "to_state": to_state if (level == REC_HIGH and current_state == from_state) else current_state,
            "reason": ("Day9 匹配算法命中高匹配，建议流转 %s -> %s"
                       % (current_state, to_state)) if (level == REC_HIGH and current_state == from_state) \
                      else "匹配度未达高匹配或当前状态不允许自动流转",
            "score": score,
            "level": level,
        }
    r = validate_transition(current_state, to_state)
    if r["valid"] and level == REC_HIGH:
        return {"valid": True, "from_state": current_state, "to_state": to_state,
                "reason": r["reason"] + "；Day9 匹配命中", "score": score, "level": level}
    return {"valid": False, "from_state": current_state, "to_state": current_state,
            "reason": r["reason"] + "（或匹配度未达高匹配）", "score": score, "level": level}


# ---------------------------------------------------------------------------
# 简易命令行自测入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("match_engine.py（Day9 匹配算法）自测：")
    assert abs(WEIGHT_SUM - 1.0) < 1e-9, "权重合计应等于 1.0"
    a = {"category_id": "textbook", "wish_category_id": "physics",
         "asking_price": 30, "school_id": 1, "status": "on_sale",
         "goods_id": 12, "user_id": 1, "publish_time": 10}
    b = {"category_id": "physics", "wish_category_id": "textbook",
         "asking_price": 32, "school_id": 1, "status": "on_sale",
         "goods_id": 20, "user_id": 2, "publish_time": 20}
    m = match_score(a, b)
    assert m is not None, "高匹配示例不应返回 None"
    print("计划书示例 match_score ->", m["match_score"], m["level"])
    print("match_reason ->", m["match_reason"])
    assert m["match_score"] > 0.9, "示例应高匹配"
    recs = recommend(a, [b])
    print("recommend 命中条数 ->", len(recs))
    print("match_engine 自测通过")
