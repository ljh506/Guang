# -*- coding: utf-8 -*-
"""Pydantic schemas for School / User APIs (Day 3)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- School ----------

class SchoolBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="学校名称")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")


class SchoolCreate(SchoolBase):
    pass


class SchoolUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SchoolOut(SchoolBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- User ----------

class UserBase(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像路径")


class UserCreate(UserBase):
    school_id: int = Field(..., description="所属学校ID")


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(None, min_length=1, max_length=50)
    avatar: Optional[str] = Field(None, max_length=255)
    school_id: Optional[int] = None


class UserOut(UserBase):
    id: int
    school_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SelectSchoolRequest(BaseModel):
    """选校请求：Day3 核心流程「选择学校→进入首页」"""
    school_id: int = Field(..., description="目标学校ID")


class SelectSchoolResponse(BaseModel):
    user: UserOut
    school: SchoolOut


# ---------- Goods（Day 4） ----------

class GoodsCreate(BaseModel):
    """发布商品请求。category 使用 Day4 统一类别 ID（10 类）。"""
    user_id: int = Field(..., description="发布者用户ID")
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., description="Day4 统一类别ID")
    condition: str = Field(..., description="品相 new_like/good/fair")
    original_price: float = Field(..., gt=0, description="参考原价")
    asking_price: Optional[float] = Field(None, ge=0, description="用户手填真实标价")
    description: Optional[str] = Field(None, max_length=1000)
    image: Optional[str] = Field(None, max_length=500)
    trade_type: str = Field("sell", description="sell 出售 / free 免费赠送 / exchange 以物换物")
    school_id: Optional[int] = Field(None, description="覆盖学校ID（默认取用户学校）")
    months_used: Optional[int] = Field(None, ge=0, description="使用年限（月），电子产品用")


class GoodsUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = None
    condition: Optional[str] = None
    original_price: Optional[float] = Field(None, gt=0)
    asking_price: Optional[float] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=1000)
    image: Optional[str] = Field(None, max_length=500)
    trade_type: Optional[str] = None
    status: Optional[str] = None


class GoodsOut(BaseModel):
    id: int
    user_id: int
    school_id: int
    name: str
    category: str
    category_name: str
    description: Optional[str]
    image: Optional[str]
    original_price: float
    estimated_min: Optional[int]
    estimated_max: Optional[int]
    reason_text: Optional[str]
    asking_price: Optional[float]
    condition: str
    trade_type: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoodsListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[GoodsOut]
