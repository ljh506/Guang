# -*- coding: utf-8 -*-
"""
拾光Agent · 价格规则引擎 Day7 边界加固版（成员B Day 7 交付）
============================================================
来源：Day6 完整版（price_engine.py，Day6 交付）基础上做「边界与异常价格处理」专项
检查与最小加固。Day7 任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 7 行，
成员B 当日任务为「检查价格规则边界和异常价格处理」（当天目标：商品详情与我想要）。

Day7 加固点（相对 Day6 完整版，向后兼容，错误码语义不变）：
  ① 原价解析：拦截 NaN（此前会触发 round() 崩溃 ValueError），归入
     PRICE_INVALID_FORMAT；inf 由原范围检查归入 PRICE_OUT_OF_RANGE（行为不变）。
  ② asking_price 标价提示：拦截 bool 输入（此前 float(True)=1.0 会产生误导性提示），
     统一视为无效格式返回 price_tip=None（不阻断）。
  ③ months_used 使用年限：对负数 / 非数字 / 非有限值明确「忽略微调、走原始折扣」的
     语义并文档化（行为与 Day6 一致，不崩溃）；Day4 EstimateParams.validate 仍负责
     前置严格校验，两层分工明确。
  ④ 全部输出仍满足：min≤max、非赠送且原价>0 保底 1 元、整数元、reason_text 可解释。

输出字段 / 错误码 / 调用签名与 Day6 完全一致：
    estimated_min / estimated_max / reason_text / rule_ref / price_tip
    PRICE_ORIGINAL_REQUIRED / PRICE_INVALID_FORMAT / PRICE_OUT_OF_RANGE /
    CONDITION_REQUIRED / CONDITION_INVALID / CATEGORY_INVALID

依赖：仅标准库。
"""

import math
import re

# ---------------------------------------------------------------------------
# 常量定义（Day4 统一类别体系，与 Day6 一致）
# ---------------------------------------------------------------------------

# 类别ID -> 类别名（Day4 统一 10 个一级类别）
CATEGORY_NAMES = {
    "textbook": "教材",
    "electronics": "电子产品",
    "life_goods": "生活用品",
    "clothing": "衣物",
    "stationery": "文具用品",
    "digital_accessories": "数码配件",
    "sports_equipment": "运动器材",
    "furniture": "家具与宿舍用品",
    "other_books": "其他书籍/资料",
    "other": "其他",
}

# Day2 旧类别ID -> Day6 统一类别ID（向后兼容，避免联调破坏）
LEGACY_CATEGORY_MAP = {
    "school_supplies": "stationery",
    "digital_accessory": "digital_accessories",
    "sports": "sports_equipment",
    "books_other": "other_books",
}

# 品相取值 -> 中文名
CONDITION_NAMES = {
    "new_like": "全新/较新",
    "good": "良好",
    "fair": "一般",
}

CONDITIONS = ("new_like", "good", "fair")

# 折扣表：category_id -> condition -> (low, high)
# 数值与计划书 §四 / Day1 文档完全一致（教材/电子产品/生活用品/衣物），
# 扩展六类沿用 Day2 初版自拟合理值。
DISCOUNT_TABLE = {
    "textbook":            {"new_like": (0.60, 0.80), "good": (0.40, 0.60), "fair": (0.20, 0.40)},
    "electronics":         {"new_like": (0.70, 0.85), "good": (0.50, 0.70), "fair": (0.10, 0.50)},
    "life_goods":          {"new_like": (0.50, 0.70), "good": (0.40, 0.50), "fair": (0.10, 0.40)},
    "clothing":            {"new_like": (0.40, 0.60), "good": (0.30, 0.40), "fair": (0.15, 0.30)},
    "stationery":          {"new_like": (0.50, 0.70), "good": (0.40, 0.50), "fair": (0.15, 0.35)},
    "digital_accessories": {"new_like": (0.50, 0.70), "good": (0.30, 0.50), "fair": (0.10, 0.30)},
    "sports_equipment":    {"new_like": (0.50, 0.70), "good": (0.35, 0.50), "fair": (0.15, 0.30)},
    "furniture":           {"new_like": (0.50, 0.70), "good": (0.35, 0.50), "fair": (0.15, 0.35)},
    "other_books":         {"new_like": (0.40, 0.60), "good": (0.30, 0.40), "fair": (0.15, 0.30)},
    "other":               {"new_like": (0.40, 0.60), "good": (0.30, 0.50), "fair": (0.10, 0.30)},
}

# 原价合理上限（边界情况：异常大视为非法输入）
MAX_ORIGINAL_PRICE = 100000

# 错误码（与 Day1 文档 §6 / Day2 初版 / Day4 EstimateParams 保持一致）
ERROR_CODES = {
    "PRICE_ORIGINAL_REQUIRED": "请填写参考原价",
    "PRICE_INVALID_FORMAT": "原价格式不正确，请输入数字",
    "PRICE_OUT_OF_RANGE": "原价超出合理范围",
    "CONDITION_REQUIRED": "请选择品相",
    "CONDITION_INVALID": "品相取值非法",
    "CATEGORY_INVALID": "类别非法，未在折扣表中",
}

# 电子产品使用年限微调阈值（月）与降档阈值
ELECTRONICS_AGE_BREAKPOINTS = (
    (6, (0.70, 0.80)),   # 0 < 月 <= 6    : 全新档轻微递减
    (12, (0.65, 0.75)),  # 6 < 月 <= 12   : 明显递减
    (24, (0.55, 0.70)),  # 12 < 月 <= 24  : 进一步递减
)
ELECTRONICS_DOWNGRADE_AFTER_MONTHS = 24  # 超过则降档至良好档
ELECTRONICS_DOWNGRADE_CONDITION = "good"


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def normalize_category(category_id):
    """类别ID 规范化：Day2 旧 ID 映射为 Day6 统一 ID；未知返回 None。"""
    if category_id is None:
        return None
    cid = str(category_id).strip()
    if cid in CATEGORY_NAMES:
        return cid
    if cid in LEGACY_CATEGORY_MAP:
        return LEGACY_CATEGORY_MAP[cid]
    return None


def _parse_original_price(original_price):
    """
    解析并校验原价。

    返回 (price, error_code)，error_code 为 None 表示通过。
    - None / 空串 / 缺失        -> PRICE_ORIGINAL_REQUIRED
    - 非数字（字符串无法转换）   -> PRICE_INVALID_FORMAT
    - 负值                      -> PRICE_INVALID_FORMAT（≤0 由调用方按免费赠送分支处理）
    - 非有限数值（NaN/inf）      -> NaN: PRICE_INVALID_FORMAT；inf: PRICE_OUT_OF_RANGE
                                    （Day7 加固：NaN 此前会触发 round() 崩溃）
    - 超过 MAX_ORIGINAL_PRICE   -> PRICE_OUT_OF_RANGE
    """
    if original_price is None:
        return None, "PRICE_ORIGINAL_REQUIRED"
    if isinstance(original_price, str):
        cleaned = original_price.strip()
        if cleaned == "":
            return None, "PRICE_ORIGINAL_REQUIRED"
        # 允许数字字符串（含一位小数）
        if not re.fullmatch(r"\d+(\.\d+)?", cleaned):
            return None, "PRICE_INVALID_FORMAT"
        original_price = float(cleaned)
    if not isinstance(original_price, (int, float)) or isinstance(original_price, bool):
        return None, "PRICE_INVALID_FORMAT"
    # Day7 加固①：拦截 NaN（isnan 判断需在范围判断之前，否则 NaN 会穿透范围检查）
    if isinstance(original_price, float) and math.isnan(original_price):
        return None, "PRICE_INVALID_FORMAT"
    if original_price < 0:
        return None, "PRICE_INVALID_FORMAT"
    if original_price > MAX_ORIGINAL_PRICE:
        return None, "PRICE_OUT_OF_RANGE"
    return float(original_price), None


def _round_price(value):
    """四舍五入到整数元（Python round 为银行家舍入，对 .5 场景影响极小）。"""
    return int(round(value))


def _clamp_min_positive(price, estimated_min, estimated_max, is_free):
    """非赠送且原价>0 时，保底 1 元，避免展示 0 元估价。"""
    if not is_free and price > 0:
        if estimated_min < 1:
            estimated_min = 1
        if estimated_max < 1:
            estimated_max = 1
    return estimated_min, estimated_max


def _resolve_discount(category_id, condition, months_used):
    """
    解析最终折扣区间 (low, high)，含电子产品年限微调与降档。

    返回 (low, high, downgraded, months_text)

    Day7 文档化：months_used 仅对 electronics + new_like 生效。
    负数 / 非数字 / 非有限值 / None：一律视为无年限，走原始折扣（不崩溃、不报错，
    由 Day4 EstimateParams.validate 前置严格校验；引擎层保持宽容以兼容各调用方）。
    """
    low, high = DISCOUNT_TABLE[category_id][condition]
    downgraded = False
    months_text = None

    # 电子产品使用年限微调（Day6 精细版：全新档按年限递减，超阈值降档）
    if category_id == "electronics" and condition == "new_like" \
            and months_used is not None:
        try:
            months = int(months_used)
        except (TypeError, ValueError, OverflowError):
            months = 0
        if months > 0:
            months_text = "{n} 个月".format(n=months)
            if months <= ELECTRONICS_DOWNGRADE_AFTER_MONTHS:
                for limit, band in ELECTRONICS_AGE_BREAKPOINTS:
                    if months <= limit:
                        low, high = band
                        break
            else:
                # 超过阈值：降档至良好档
                low, high = DISCOUNT_TABLE[category_id][ELECTRONICS_DOWNGRADE_CONDITION]
                downgraded = True
                months_text += "（超过 {n} 个月，按良好档计算）".format(
                    n=ELECTRONICS_DOWNGRADE_AFTER_MONTHS)

    return low, high, downgraded, months_text


# ---------------------------------------------------------------------------
# 核心估价函数（Day7 边界加固版，签名与 Day6 完全一致）
# ---------------------------------------------------------------------------

def estimate_price(category_id, condition, original_price,
                   months_used=None, is_free=False, asking_price=None, **kwargs):
    """
    按类别 + 品相查折扣表，计算建议估价区间（Day7 边界加固版）。

    参数（与 Day4 EstimateParams 对齐）：
        category_id     : str，类别ID（Day4 统一体系 10 类；兼容 Day2 旧 ID）
        condition       : str，品相（new_like / good / fair）
        original_price  : 数字或数字字符串，参考原价（元，必填 >0，免费赠送除外）
        months_used     : int/None，电子产品使用年限（月），仅 electronics 生效
        is_free         : bool，免费赠送标记
        asking_price    : 数字/None，用户手填真实标价（可选，用于生成 price_tip）
        **kwargs        : 兼容 Day2 旧参数名 device_age_months

    返回：
        dict 成功：
            {
                "estimated_min": int,
                "estimated_max": int,
                "reason_text": str,
                "rule_ref": {"category": str, "condition": str, "low": float, "high": float},
                "price_tip": str|None,
            }
        dict 失败：
            {"error": {"error_code": str, "message": str}}
    """
    # 兼容 Day2 旧参数名 device_age_months
    if months_used is None:
        months_used = kwargs.get("device_age_months")

    # 1) 类别校验（含 Day2 旧 ID 映射）
    cid = normalize_category(category_id)
    if cid is None:
        return {"error": {"error_code": "CATEGORY_INVALID",
                          "message": ERROR_CODES["CATEGORY_INVALID"]}}

    # 2) 品相校验（禁止默认猜测品相）
    if condition is None or (isinstance(condition, str) and condition.strip() == ""):
        return {"error": {"error_code": "CONDITION_REQUIRED",
                          "message": ERROR_CODES["CONDITION_REQUIRED"]}}
    if condition not in CONDITION_NAMES:
        return {"error": {"error_code": "CONDITION_INVALID",
                          "message": ERROR_CODES["CONDITION_INVALID"]}}

    # 3) 原价校验（Day7 加固①：NaN 不再崩溃，返回 PRICE_INVALID_FORMAT）
    price, err_code = _parse_original_price(original_price)
    if err_code is not None:
        if is_free:
            price = 0.0
        else:
            return {"error": {"error_code": err_code, "message": ERROR_CODES[err_code]}}

    if price == 0:
        if not is_free:
            return {"error": {"error_code": "PRICE_INVALID_FORMAT",
                              "message": "非免费赠送物品原价必须大于 0"}}
        low, high = 0.0, 0.0
        estimated_min = estimated_max = 0
        downgraded = False
        months_text = None
    else:
        low, high, downgraded, months_text = _resolve_discount(
            cid, condition, months_used)
        estimated_min = _round_price(price * low)
        estimated_max = _round_price(price * high)
        estimated_min, estimated_max = _clamp_min_positive(
            price, estimated_min, estimated_max, is_free)

    rule_ref = {"category": cid, "condition": condition,
                "low": low, "high": high}
    reason_text = build_reason_text(
        cid, condition, price, estimated_min, estimated_max,
        is_free=is_free, months_used=months_used,
        low=low, high=high, downgraded=downgraded, months_text=months_text)
    price_tip = validate_asking_price(asking_price, estimated_min, estimated_max)

    return {
        "estimated_min": estimated_min,
        "estimated_max": estimated_max,
        "reason_text": reason_text,
        "rule_ref": rule_ref,
        "price_tip": price_tip,
    }


# ---------------------------------------------------------------------------
# 估价依据文本生成（可解释性，Day1 文档 §5 / Day6 增强含计算过程）
# ---------------------------------------------------------------------------

def build_reason_text(category_id, condition, original_price,
                      estimated_min, estimated_max,
                      is_free=False, months_used=None,
                      low=None, high=None, downgraded=False, months_text=None):
    """生成 reason_text 可解释文本（含类别名、品相描述、折扣区间、计算过程）。"""
    if is_free or original_price == 0:
        return "该物品选择免费赠送，估价为 0 元。"

    category_name = CATEGORY_NAMES.get(category_id, category_id)
    condition_name = CONDITION_NAMES.get(condition, condition)
    if low is None or high is None:
        low, high = DISCOUNT_TABLE[category_id][condition]
    price_text = _format_price(original_price)

    text = ("原价 {price} 元 × 「{category}」{condition}折扣 {low}~{high}"
            " = {min}~{max} 元。").format(
                price=price_text,
                category=category_name,
                condition=condition_name,
                low=low, high=high,
                min=estimated_min, max=estimated_max)

    if category_id == "electronics" and months_text:
        text += "电子产品使用年限 {n}，已按年限微调折扣区间。".format(n=months_text)
    if downgraded:
        text += "使用年限超过阈值，按良好档计算。"
    return text


def _format_price(value):
    """原价展示：整数不带小数，否则保留两位。"""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return "{:.2f}".format(value)


# ---------------------------------------------------------------------------
# 用户手填标价校验（仅提示、不阻断，Day1 文档 §4.5 / Day2 保留 / Day7 加固②）
# ---------------------------------------------------------------------------

def validate_asking_price(asking_price, estimated_min, estimated_max):
    """
    校验用户手动填写的真实标价，返回 price_tip 提示文案；无需提示返回 None。

    - asking_price < estimated_min : 提示可参考建议价
    - 区间内                          : None（无需提示）
    - asking_price > estimated_max : 提示可能影响交换成功率
    - bool / NaN / 非数字            : None（Day7 加固②：bool 此前被 float() 转成 1.0
                                       会产出误导提示；NaN 比较恒 False 无提示）
    """
    if asking_price is None or asking_price == "":
        return None  # 发布表单层面必填，此处仅做区间校验
    if isinstance(asking_price, bool):
        return None  # Day7 加固②：布尔值不参与标价提示
    try:
        asking = float(asking_price)
    except (TypeError, ValueError):
        return None  # 非法格式由表单校验处理，引擎不重复拦截
    if not math.isfinite(asking):
        return None  # NaN / inf 不产出提示
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
    print("price_engine_day7.py（Day7 边界加固版）自测：")
    r = estimate_price("textbook", "good", 68)
    print(r)
    assert r["estimated_min"] == 27 and r["estimated_max"] == 41, "计划书示例校验失败"
    assert "0.4~0.6" in r["reason_text"], "reason_text 缺少折扣区间"
    print("计划书示例 68元/良好/教材 -> 27~41 校验通过")
