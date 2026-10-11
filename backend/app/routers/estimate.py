# -*- coding: utf-8 -*-
"""
估价接口（Day 6 成员A）：POST /api/v1/estimate
================================================
调用成员B Day6 价格规则引擎（price_engine.estimate_price），
对「类别 + 品相 + 参考原价（+使用年限/免费赠送/用户标价）」返回建议估价区间。

字段契约严格遵循成员B《交接文档_成员B_Day6.md §五》（前端按此联调）：
- 请求：category / condition / original_price / months_used / is_free / asking_price
- 成功：{success: true, data: {estimated_min, estimated_max, reason_text, rule_ref, price_tip}}
- 失败：{success: false, error: {error_code, message}}
错误码沿用 Day2/Day4 统一错误码（CATEGORY_INVALID / CONDITION_REQUIRED /
CONDITION_INVALID / PRICE_ORIGINAL_REQUIRED / PRICE_INVALID_FORMAT / PRICE_OUT_OF_RANGE）。

本接口为纯计算接口（不写库）；发布商品时的价格落库在 POST /api/v1/goods 完成。
"""
from typing import Optional, Union

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..services.price_engine import estimate_price

router = APIRouter()


class EstimateRequest(BaseModel):
    """估价请求（字段命名与成员B契约一致）。"""
    category: str = Field(..., description="Day4 统一类别 ID（10 类）")
    condition: str = Field(..., description="品相 new_like / good / fair")
    original_price: Optional[Union[int, float, str]] = Field(
        None, description="参考原价（元）；免费赠送可传 0 或省略")
    months_used: Optional[int] = Field(None, ge=0, description="使用年限（月），电子产品用")
    is_free: bool = Field(False, description="是否免费赠送")
    asking_price: Optional[Union[int, float, str]] = Field(
        None, ge=0, description="用户手填真实标价（选填，用于生成 price_tip）")


@router.post("/estimate")
def estimate(payload: EstimateRequest):
    """
    估价：按类别/品相/原价查折扣表，返回建议估价区间与依据文本。

    失败时业务包裹返回 {success: false, error: {...}}（HTTP 200），
    前端按 success 字段分流即可；错误码见模块 docstring。
    """
    est = estimate_price(
        payload.category,
        payload.condition,
        payload.original_price,
        months_used=payload.months_used,
        is_free=payload.is_free,
        asking_price=payload.asking_price,
    )
    if "error" in est:
        return {"success": False, "error": est["error"]}
    return {"success": True, "data": est}
