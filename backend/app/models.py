from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base


class School(Base):
    """学校表（对齐计划书 §七：id、name、latitude、longitude）"""
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True, unique=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """用户表（对齐计划书 §七：id、nickname、avatar、school_id、created_at）"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String, nullable=False, index=True)
    avatar = Column(String, nullable=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Goods(Base):
    """商品表（对齐计划书 §七 + Day2/Day4 字段约定）"""
    __tablename__ = "goods"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)  # Day4 统一类别 ID（10 类）
    description = Column(String, nullable=True)
    image = Column(String, nullable=True)
    original_price = Column(Float, nullable=False)
    estimated_min = Column(Integer, nullable=True)   # 建议估价下限（price_engine 生成）
    estimated_max = Column(Integer, nullable=True)   # 建议估价上限
    reason_text = Column(String, nullable=True)      # 估价依据（可解释）
    asking_price = Column(Float, nullable=True)      # 用户手填真实标价（匹配用）
    condition = Column(String, nullable=False)      # new_like / good / fair
    trade_type = Column(String, nullable=False, default="sell")  # sell / free / exchange
    status = Column(String, nullable=False, default="available", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Want(Base):
    """想要请求表（Day7 成员A：用户B点击「我想要」产生的请求记录）。

    对齐计划书 Day7「商品详情与我想要」验收：用户A发布 → 用户B浏览 →
    点击我想要 → 产生请求。状态字段 status 支持：
        pending  已提交（默认）
        accepted 卖家接受（商品 available -> reserved）
        rejected 卖家拒绝（终态）
        cancelled 买家取消（终态）
    """
    __tablename__ = "wants"

    id = Column(Integer, primary_key=True, index=True)
    goods_id = Column(Integer, ForeignKey("goods.id"), nullable=False, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    message = Column(String, nullable=True)          # 想说的话（选填）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())


class Conversation(Base):
    """会话/交易表（Day8 成员A：轻量聊天的会话载体）。

    对齐计划书 §七 Message 之外引入的会话实体：一个「我想要 → 聊天 → 匹配 →
    交换 → 确认」的完整交易链路承载在一个 Conversation 上（Day9 匹配 /
    Day10 协议共用）。trade_state 使用成员B Day8 交易状态机：
        requested -> chatting -> matched -> negotiating -> confirmed / cancelled
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    goods_id = Column(Integer, ForeignKey("goods.id"), nullable=False, index=True)
    want_id = Column(Integer, ForeignKey("wants.id"), nullable=True)   # 关联 Day7 想要请求
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)   # 想要方
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 发布方
    trade_state = Column(String, nullable=False, default="requested", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())


class Message(Base):
    """消息表（对齐计划书 §七：id、sender_id、receiver_id、content、created_at）。

    Day8 轻量聊天消息：归属某个会话（conversation_id），receiver 由会话对端推导，
    存 sender_id + content + 已读标记，避免 15 天内开发复杂实时 IM。
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"),
                             nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(String, nullable=False)
    is_read = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())