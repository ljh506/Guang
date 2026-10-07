# -*- coding: utf-8 -*-
"""
拾光Agent · 价格规则引擎初版（成员B Day 2 交付）
====================================================
基于 Day 1《2_价格规则初稿.md》落地。

机制要点：
- 规则引擎输出的 estimated_min / estimated_max 为「建议估价区间（参考价）」，
  仅供展示与参考；真实成交标价 asking_price 由用户在发布页手动输入，
  引擎不强制约束，仅在校验时给出提示（price_tip，不阻断发布）。
- 输出字段：estimated_min / estimated_max / reason_text / rule_ref，
  供估价接口（POST /estimate）复用。

模块化设计：
- DISCOUNT_TABLE      ：类别 × 品相 折扣表（与 Day1 文档 / 计划书数字一致）
- estimate_price()    ：核心估价函数（Day 6 前可扩展电子产品年限微调）
- validate_asking_price()：用户手填标价的提示校验（仅提示不阻断）
"""

import re

# ---------------------------------------------------------------------------
# 常量定义（与 Day1 文档 / 计划书 §四 保持一致）
# ---------------------------------------------------------------------------

# 类别ID -> 类别名（与《1_AI识别类别清单.md》的 10 个一级类别对齐）
CATEGORY_NAMES = {
    "textbook": "教材",
    "electronics": "电子产品",
    "life_goods": "生活用品",
    "clothing": "衣物",
    "school_supplies": "文具用品",
    "digital_accessory": "数码配件",
    "sports": "运动器材",
    "furniture": "家具与宿舍用品",
    "books_other": "其他书籍/资料",
    "other": "其他",
}

# 品相取值 -> 中文名
CONDITION_NAMES = {
    "new_like": "全新/较新",
    "good": "良好",
    "fair": "一般",
}

# 折扣表：category_id -> condition -> (low, high)
# 数值与计划书 §四 / Day1 文档完全一致（计划书四类 + 扩展六类）
DISCOUNT_TABLE = {
    "textbook":          {"new_like": (0.60, 0.80), "good": (0.40, 0.60), "fair": (0.20, 0.40)},
    "electronics":       {"new_like": (0.70, 0.85), "good": (0.50, 0.70), "fair": (0.10, 0.50)},
    "life_goods":        {"new_like": (0.50, 0.70), "good": (0.40, 0.50), "fair": (0.10, 0.40)},
    "clothing":          {"new_like": (0.40, 0.60), "good": (0.30, 0.40), "fair": (0.15, 0.30)},
    "school_supplies":   {"new_like": (0.50, 0.70), "good": (0.40, 0.50), "fair": (0.15, 0.35)},
    "digital_accessory": {"new_like": (0.50, 0.70), "good": (0.30, 0.50), "fair": (0.10, 0.30)},
    "sports":            {"new_like": (0.50, 0.70), "good": (0.35, 0.50), "fair": (0.15, 0.30)},
    "furniture":         {"new_like": (0.50, 0.70), "good": (0.35, 0.50), "fair": (0.15, 0.35)},
    "books_other":       {"new_like": (0.40, 0.60), "good": (0.30, 0.40), "fair": (0.15, 0.30)},
    "other":             {"new_like": (0.40, 0.60), "good": (0.30, 0.50), "fair": (0.10, 0.30)},
}

# 原价合理上限（边界情况：异常大视为非法输入）
MAX_ORIGINAL_PRICE = 100000

# 错误码（与 Day1 文档 §6 对应）
ERROR_CODES = {
    "PRICE_ORIGINAL_REQUIRED": "请填写参考原价",
    "PRICE_INVALID_FORMAT": "原价格式不正确，请输入数字",
    "PRICE_OUT_OF_RANGE": "原价超出合理范围",
    "CONDITION_REQUIRED": "请选择品相",
    "CONDITION_INVALID": "品相取值非法",
    "CATEGORY_INVALID": "类别非法，未在折扣表中",
}


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _parse_original_price(original_price):
    """
    解析并校验原价。

    返回 (price, error_code)，error_code 为 None 表示通过。
    - None / 空串 / 缺失        -> PRICE_ORIGINAL_REQUIRED
    - 非数字（字符串无法转换）   -> PRICE_INVALID_FORMAT
    - 负值                      -> PRICE_INVALID_FORMAT（≤0 由调用方按免费赠送分支处理）
    - 超过 MAX_ORIGINAL_PRICE   -> PRICE_OUT_OF_RANGE
    """
    if original_price is None:
        return None, "PRICE_ORIGINAL_REQUIRED"
    if isinstance(original_price, str):
        # 兼容前端可能传来的字符串（含 "元" 等字符视为非法）
        cleaned = original_price.strip()
        if cleaned == "":
            return None, "PRICE_ORIGINAL_REQUIRED"
        # 允许数字字符串
        if not re.fullmatch(r"\d+(\.\d+)?", cleaned):
            return None, "PRICE_INVALID_FORMAT"
        original_price = float(cleaned)
    if not isinstance(original_price, (int, float)):
        return None, "PRICE_INVALID_FORMAT"
    if original_price < 0:
        return None, "PRICE_INVALID_FORMAT"
    if original_price > MAX_ORIGINAL_PRICE:
        return None, "PRICE_OUT_OF_RANGE"
    return float(original_price), None


def _round_price(value):
    """四舍五入到整数元；结果为 0 但非赠送场景由调用方保证原价>0，此处仅做基础 round。"""
    return int(round(value))


# ---------------------------------------------------------------------------
# 核心估价函数
# ---------------------------------------------------------------------------

def estimate_price(category_id, condition, original_price, is_free=False,
                   device_age_months=None):
    """
    按类别 + 品相查折扣表，计算建议估价区间。

    参数：
        category_id        : str，类别ID（见 CATEGORY_NAMES）
        condition          : str，品相（new_like / good / fair）
        original_price     : 数字或数字字符串，参考原价（元）
        is_free            : bool，免费赠送标记
        device_age_months  : int/None，电子产品使用年限（月），仅 electronics 生效

    返回：
        dict 成功：
            {
                "estimated_min": int,
                "estimated_max": int,
                "reason_text": str,
                "rule_ref": {"category": str, "condition": str, "low": float, "high": float},
            }
        dict 失败：
            {"error": {"error_code": str, "message": str}}
    """
    # 1) 类别校验
    if category_id not in DISCOUNT_TABLE:
        return {"error": {"error_code": "CATEGORY_INVALID",
                          "message": ERROR_CODES["CATEGORY_INVALID"]}}

    # 2) 品相校验（禁止默认猜测品相）
    if condition is None or (isinstance(condition, str) and condition.strip() == ""):
        return {"error": {"error_code": "CONDITION_REQUIRED",
                          "message": ERROR_CODES["CONDITION_REQUIRED"]}}
    if condition not in CONDITION_NAMES:
        return {"error": {"error_code": "CONDITION_INVALID",
                          "message": ERROR_CODES["CONDITION_INVALID"]}}

    # 3) 原价校验
    price, err_code = _parse_original_price(original_price)
    if err_code is not None:
        # 免费赠送时允许原价为 0 或缺失（缺省视为 0）
        if is_free:
            price = 0.0
        else:
            return {"error": {"error_code": err_code, "message": ERROR_CODES[err_code]}}

    if price == 0:
        # 免费赠送：估价恒为 [0, 0]
        if not is_free:
            # 原价 0 且非赠送：按 Day1 文档，原价 ≤ 0 非赠送按无效处理
            return {"error": {"error_code": "PRICE_INVALID_FORMAT",
                              "message": "非免费赠送物品原价必须大于 0"}}
        low, high = 0.0, 0.0
    else:
        # 查折扣表
        low, high = DISCOUNT_TABLE[category_id][condition]

        # 电子产品 + 全新/较新：使用年限微调（Day1 文档 §3 框架，Day 6 细化）
        if category_id == "electronics" and condition == "new_like" \
                and device_age_months is not None:
            try:
                months = int(device_age_months)
            except (TypeError, ValueError):
                months = 0
            if months <= 6:
                low, high = 0.70, 0.78
            elif months <= 18:
                low, high = 0.75, 0.82
            else:
                low, high = 0.80, 0.85

    estimated_min = _round_price(price * low)
    estimated_max = _round_price(price * high)
    # 非赠送场景：结果 0 元但原价 > 0 时，min 至少取 1
    if not is_free and price > 0 and estimated_min == 0:
        estimated_min = 1

    rule_ref = {"category": category_id, "condition": condition,
                "low": low, "high": high}
    reason_text = build_reason_text(category_id, condition, price,
                                    estimated_min, estimated_max,
                                    is_free=is_free,
                                    device_age_months=device_age_months)

    return {
        "estimated_min": estimated_min,
        "estimated_max": estimated_max,
        "reason_text": reason_text,
        "rule_ref": rule_ref,
    }


# ---------------------------------------------------------------------------
# 估价依据文本生成（可解释性，Day1 文档 §5）
# ---------------------------------------------------------------------------

def build_reason_text(category_id, condition, original_price,
                      estimated_min, estimated_max,
                      is_free=False, device_age_months=None):
    """生成 reason_text 可解释文本。"""
    if is_free or original_price == 0:
        return "该物品选择免费赠送，估价为 0 元。"

    category_name = CATEGORY_NAMES.get(category_id, category_id)
    condition_name = CONDITION_NAMES.get(condition, condition)
    low, high = DISCOUNT_TABLE[category_id][condition]

    text = ("「{category}」{condition}，参考原价 {price} 元，"
            "按{category}类{condition}折扣 {low}~{high} 计算，"
            "建议估价 {min}~{max} 元。").format(
                category=category_name,
                condition=condition_name,
                price=_format_price(original_price),
                low=low, high=high,
                min=estimated_min, max=estimated_max)

    if category_id == "electronics" and device_age_months is not None \
            and not is_free:
        try:
            months = int(device_age_months)
            text += "已按使用年限 {n} 个月微调折扣区间。".format(n=months)
        except (TypeError, ValueError):
            pass
    return text


def _format_price(value):
    """原价展示：整数不带小数，否则保留两位。"""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return "{:.2f}".format(value)


# ---------------------------------------------------------------------------
# 用户手填标价校验（仅提示、不阻断，Day1 文档 §4.5）
# ---------------------------------------------------------------------------

def validate_asking_price(asking_price, estimated_min, estimated_max):
    """
    校验用户手动填写的真实标价，返回 price_tip 提示文案；无需提示返回 None。

    - asking_price < estimated_min : 提示可参考建议价
    - 区间内                          : None（无需提示）
    - asking_price > estimated_max : 提示可能影响交换成功率
    """
    if asking_price is None or asking_price == "":
        return None  # 发布表单层面必填，此处仅做区间校验
    try:
        asking = float(asking_price)
    except (TypeError, ValueError):
        return None  # 非法格式由表单校验处理，引擎不重复拦截
    if asking < estimated_min:
        return ("您的标价低于建议区间（{min}~{max} 元），可适当参考建议价"
                .format(min=estimated_min, max=estimated_max))
    if asking > estimated_max:
        return ("您的标价高于建议区间（{min}~{max} 元），可能影响交换成功率"
                .format(min=estimated_min, max=estimated_max))
    return None


# ---------------------------------------------------------------------------
# 简易命令行自测入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("price_engine.py 自测：")
    r = estimate_price("textbook", "good", 68)
    print(r)
    assert r["estimated_min"] == 27 and r["estimated_max"] == 41, "计划书示例校验失败"
    print("计划书示例 68元/良好/教材 -> 27~41 校验通过")
