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
    wish_category_id: Optional[str] = Field(None, description="想换的类别（Day9 意愿匹配用，Day4 十类之一）")
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
    wish_category_id: Optional[str] = None
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
    wish_category_id: Optional[str] = Field(None, description="想换的类别（Day9）")
    condition: str
    trade_type: str
    status: str
    wants_count: Optional[int] = Field(None, description="想要人数（详情接口返回）")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoodsListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[GoodsOut]


# ---------- Want（Day 7：收藏/想要请求） ----------

class WantCreate(BaseModel):
    """发起「我想要」请求。"""
    user_id: int = Field(..., description="发起用户ID（想要的人）")
    message: Optional[str] = Field(None, max_length=500, description="想说的话（选填）")


class WantStatusUpdate(BaseModel):
    """更新想要请求状态。"""
    status: str = Field(..., description="目标状态：pending/accepted/rejected/cancelled")


class WantOut(BaseModel):
    id: int
    goods_id: int
    requester_id: int
    status: str
    message: Optional[str]
    goods_name: Optional[str]
    requester_nickname: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WantListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[WantOut]


# ---------- 轻量聊天（Day 8：Message 模型与消息接口） ----------

class ConversationCreate(BaseModel):
    """创建会话（买卖双方 + 商品）。want_id 可选，关联 Day7 想要请求。"""
    goods_id: int = Field(..., description="商品ID")
    buyer_id: int = Field(..., description="想要方用户ID")
    seller_id: int = Field(..., description="发布方用户ID")
    want_id: Optional[int] = Field(None, description="关联的想要请求ID（选填）")


class MessageCreate(BaseModel):
    """发送消息。"""
    sender_id: int = Field(..., description="发送方用户ID（必须是会话参与者）")
    content: str = Field(..., min_length=1, max_length=1000, description="消息内容")


class MarkReadRequest(BaseModel):
    """标记会话已读。"""
    user_id: int = Field(..., description="当前浏览用户ID")


class TradeStateUpdate(BaseModel):
    """交易状态流转（成员B Day8 状态机校验）。"""
    trade_state: str = Field(..., description="目标状态：requested/chatting/matched/negotiating/confirmed/cancelled")


class ConversationOut(BaseModel):
    id: int
    goods_id: int
    goods_name: Optional[str]
    want_id: Optional[int]
    buyer_id: int
    buyer_nickname: Optional[str]
    seller_id: int
    seller_nickname: Optional[str]
    trade_state: str
    trade_state_name: Optional[str]
    last_message: Optional[str]
    last_message_time: Optional[datetime]
    unread_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ConversationOut]


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    sender_nickname: Optional[str]
    content: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[MessageOut]


# ---------- 交换匹配（Day 9：Exchange 模型与匹配接口） ----------

class ExchangeMatchRequest(BaseModel):
    """发起匹配推荐：基于用户某商品的意愿/价格/同校计算推荐列表。"""
    user_id: int = Field(..., description="发起匹配的用户ID")
    goods_id: int = Field(..., description="发起匹配的商品ID（asking_price 由 Goods 表提供）")


class ExchangeWishRequest(BaseModel):
    """意愿表达：设置某商品「想换什么」类别（只能设置自己的商品）。"""
    user_id: int = Field(..., description="设置意愿的用户ID（必须是商品发布者）")
    goods_id: int = Field(..., description="商品ID")
    wish_category_id: str = Field(..., description="想换的类别（Day4 十类之一）")


class ExchangeAcceptRequest(BaseModel):
    """确认匹配：把一条高/普通匹配推荐落为 Exchange 记录（status=open），用于去重。"""
    user_id: int = Field(..., description="发起匹配的用户ID")
    goods_id: int = Field(..., description="发起方商品ID")
    target_goods_id: int = Field(..., description="目标商品ID（匹配推荐中的一方）")


class MatchItemOut(BaseModel):
    """单条匹配推荐（含展示字段，供前端直接渲染）。"""
    target_goods_id: int
    target_user_id: int
    match_score: float
    score_detail: dict
    weights: dict
    level: str
    match_reason: str
    target_goods_name: Optional[str] = None
    target_category_name: Optional[str] = None
    target_asking_price: Optional[float] = None
    target_user_nickname: Optional[str] = None


class ExchangeOut(BaseModel):
    """交换匹配记录（Exchange 模型对外视图）。"""
    id: int
    goods_id: int
    user_id: int
    target_goods_id: int
    target_user_id: int
    match_score: float
    level: str
    status: str
    confirm_a: bool = False
    confirm_b: bool = False
    goods_name: Optional[str] = None
    target_goods_name: Optional[str] = None
    target_user_nickname: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExchangeListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ExchangeOut]


class ExchangeConfirmRequest(BaseModel):
    """交换确认：交换参与者对本次交换确认（待确认 open -> 双方确认 -> confirmed）。"""
    user_id: int = Field(..., description="确认方用户ID（必须是交换参与者）")


class ExchangeCancelRequest(BaseModel):
    """交换取消：交换参与者取消本次交换（open/negotiating -> cancelled）。"""
    user_id: int = Field(..., description="取消方用户ID（必须是交换参与者）")


class ExchangeProtocolOut(BaseModel):
    """交换协议卡片（Day10 验收：匹配→发起交换→双方确认→生成协议卡片）。"""
    exchange_id: int
    status: str
    state_name: str
    confirm_a: bool
    confirm_b: bool
    protocol_text: str
    match_explanation: str
    validation: dict
