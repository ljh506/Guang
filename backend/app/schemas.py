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
