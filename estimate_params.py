# -*- coding: utf-8 -*-
"""
拾光Agent · 估价输入参数定义（成员B Day 4 交付）
====================================================
定义估价接口 / 函数的输入数据模型（dataclass 实现，仅标准库）。

字段：
    category        : 标准化后的 category_id（Day4 统一类别体系，必填）
    condition       : 品相 new_like / good / fair（必填）
    original_price  : 参考原价（数字，必填，>0）
    asking_price    : 用户手填真实标价（选填）
    months_used     : 使用年限（月，选填，电子产品用）
    image_path      : 识别图片路径（选填，Day5 识别链路预留）
    image_bytes     : 识别图片字节（选填，Day5 识别链路预留）

validate() 返回错误码与错误信息，错误码与 Day2 price_engine 保持一致：
    CATEGORY_INVALID / CONDITION_REQUIRED / CONDITION_INVALID /
    PRICE_ORIGINAL_REQUIRED / PRICE_INVALID_FORMAT / PRICE_OUT_OF_RANGE

依赖：仅标准库（dataclasses / typing）。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union

# 与 Day4 类别标准化模块共用类别体系
CATEGORY_IDS = {
    "textbook", "electronics", "life_goods", "clothing", "stationery",
    "digital_accessories", "sports_equipment", "furniture", "other_books", "other",
}

CONDITIONS = {"new_like", "good", "fair"}

# 原价合理上限（与 Day2 price_engine.MAX_ORIGINAL_PRICE 一致）
MAX_ORIGINAL_PRICE = 100000

ERROR_MESSAGES = {
    "PRICE_ORIGINAL_REQUIRED": "请填写参考原价",
    "PRICE_INVALID_FORMAT": "原价格式不正确，请输入数字",
    "PRICE_OUT_OF_RANGE": "原价超出合理范围",
    "CONDITION_REQUIRED": "请选择品相",
    "CONDITION_INVALID": "品相取值非法",
    "CATEGORY_INVALID": "类别非法，未在折扣表中",
}


@dataclass
class EstimateParams:
    """估价输入数据模型。"""
    category: str = ""
    condition: str = ""
    original_price: Union[int, float, str, None] = None
    asking_price: Union[int, float, str, None] = None       # 选填，用户手填真实标价
    months_used: Optional[int] = None                       # 选填，使用年限（月，电子产品用）
    image_path: Optional[str] = None                        # Day5 预留：识别图片路径
    image_bytes: Optional[bytes] = None                     # Day5 预留：识别图片字节

    def validate(self) -> dict:
        """
        校验输入参数。

        返回：
            {"valid": True, "errors": []}
            或 {"valid": False, "errors": [{"error_code": ..., "message": ...}, ...]}
        """
        errors: List[dict] = []

        # 1) 类别（必填）
        if not self.category or (isinstance(self.category, str) and self.category.strip() == ""):
            errors.append({"error_code": "CATEGORY_INVALID",
                           "message": ERROR_MESSAGES["CATEGORY_INVALID"]})
        elif self.category not in CATEGORY_IDS:
            errors.append({"error_code": "CATEGORY_INVALID",
                           "message": ERROR_MESSAGES["CATEGORY_INVALID"]})

        # 2) 品相（必填）
        if self.condition is None or (isinstance(self.condition, str) and self.condition.strip() == ""):
            errors.append({"error_code": "CONDITION_REQUIRED",
                           "message": ERROR_MESSAGES["CONDITION_REQUIRED"]})
        elif self.condition not in CONDITIONS:
            errors.append({"error_code": "CONDITION_INVALID",
                           "message": ERROR_MESSAGES["CONDITION_INVALID"]})

        # 3) 原价（必填，>0）
        price_err = _validate_original_price(self.original_price)
        if price_err:
            errors.append(price_err)

        # 4) 选填：asking_price（若提供则校验数字格式）
        if self.asking_price is not None and self.asking_price != "":
            if not _is_number(self.asking_price):
                errors.append({"error_code": "PRICE_INVALID_FORMAT",
                               "message": "标价格式不正确，请输入数字"})

        # 5) 选填：months_used（若提供则校验非负整数）
        if self.months_used is not None:
            try:
                months = int(self.months_used)
                if months < 0:
                    errors.append({"error_code": "PRICE_INVALID_FORMAT",
                                   "message": "使用年限不能为负数"})
            except (TypeError, ValueError):
                errors.append({"error_code": "PRICE_INVALID_FORMAT",
                               "message": "使用年限必须为整数"})

        return {"valid": not errors, "errors": errors}


def _is_number(value) -> bool:
    """判断是否为可转换的非负数字。"""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return False
        try:
            float(s)
            return True
        except ValueError:
            return False
    return False


def _validate_original_price(value) -> Optional[dict]:
    """原价校验：缺失 / 非数字 / ≤0 / 超范围。"""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return {"error_code": "PRICE_ORIGINAL_REQUIRED",
                "message": ERROR_MESSAGES["PRICE_ORIGINAL_REQUIRED"]}
    if not _is_number(value):
        return {"error_code": "PRICE_INVALID_FORMAT",
                "message": ERROR_MESSAGES["PRICE_INVALID_FORMAT"]}
    price = float(value)
    if price <= 0:
        return {"error_code": "PRICE_INVALID_FORMAT",
                "message": "非免费赠送物品原价必须大于 0"}
    if price > MAX_ORIGINAL_PRICE:
        return {"error_code": "PRICE_OUT_OF_RANGE",
                "message": ERROR_MESSAGES["PRICE_OUT_OF_RANGE"]}
    return None


# ---------------------------------------------------------------------------
# 简易命令行自测入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    p = EstimateParams(category="textbook", condition="good", original_price=68,
                       asking_price=30, months_used=None, image_path="demo.jpg")
    print(p.validate())
