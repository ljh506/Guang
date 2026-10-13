# -*- coding: utf-8 -*-
"""轻量聊天 API（Day 8 成员A）。

计划书 Day8 成员A 任务：「完成 Message 模型和消息接口」（当天目标：轻量聊天）。
当天验收：想要请求 → 消息列表 → 聊天 → 发送/接收演示消息。

接口：
  GET   /api/v1/quick-messages                  快捷消息模板（集成成员B chat_rules）
  POST  /api/v1/conversations                   创建会话（买卖双方 + 商品）
  GET   /api/v1/conversations?user_id=          消息列表（我的会话：最后一条消息/未读数/交易状态）
  GET   /api/v1/conversations/{id}/messages     聊天记录（分页，页内按时间正序）
  POST  /api/v1/conversations/{id}/messages     发送消息（首条消息自动 requested -> chatting）
  POST  /api/v1/conversations/{id}/read         标记会话已读
  PATCH /api/v1/conversations/{id}/state        交易状态流转（成员B 状态机校验）

交易状态（成员B Day8 chat_rules）：
  requested -> chatting -> matched -> negotiating -> confirmed / cancelled
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Conversation, Goods, Message, User, Want
from ..schemas import (ConversationCreate, ConversationListOut,
                       ConversationOut, MarkReadRequest, MessageCreate,
                       MessageListOut, MessageOut, TradeStateUpdate)
from ..services.chat_rules import (QUICK_MESSAGE_SCENES, TRADE_STATES,
                                   get_quick_messages, validate_transition)

router = APIRouter()

ACTIVE_TRADE_STATES = ("requested", "chatting", "matched", "negotiating")


def _nickname(db: Session, user_id: int) -> str | None:
    u = db.get(User, user_id)
    return u.nickname if u else None


def _conversation_to_out(c: Conversation, db: Session,
                         viewer_id: int | None = None) -> ConversationOut:
    g = db.get(Goods, c.goods_id)
    last = (db.query(Message)
            .filter(Message.conversation_id == c.id)
            .order_by(Message.id.desc()).first())
    unread = 0
    if viewer_id is not None:
        unread = (db.query(Message)
                  .filter(Message.conversation_id == c.id,
                          Message.sender_id != viewer_id,
                          Message.is_read.is_(False))
                  .count())
    return ConversationOut(
        id=c.id, goods_id=c.goods_id,
        goods_name=g.name if g else None,
        want_id=c.want_id,
        buyer_id=c.buyer_id, buyer_nickname=_nickname(db, c.buyer_id),
        seller_id=c.seller_id, seller_nickname=_nickname(db, c.seller_id),
        trade_state=c.trade_state,
        trade_state_name=TRADE_STATES.get(c.trade_state, c.trade_state),
        last_message=last.content if last else None,
        last_message_time=last.created_at if last else None,
        unread_count=unread,
        created_at=c.created_at, updated_at=c.updated_at,
    )


def _message_to_out(m: Message, db: Session) -> MessageOut:
    return MessageOut(
        id=m.id, conversation_id=m.conversation_id,
        sender_id=m.sender_id, sender_nickname=_nickname(db, m.sender_id),
        content=m.content, is_read=bool(m.is_read), created_at=m.created_at,
    )


# ---------------------------------------------------------------------------
# 快捷消息模板（成员B chat_rules 集成）
# ---------------------------------------------------------------------------

@router.get("/quick-messages")
def list_quick_messages(scene: str | None = Query(None),
                        sender: str | None = Query(None)):
    """快捷消息模板列表：?scene=price&sender=buyer 过滤；前端渲染快捷回复按钮。"""
    if scene is not None and scene not in QUICK_MESSAGE_SCENES:
        raise HTTPException(
            status_code=400,
            detail=f"scene 非法，可选：{sorted(QUICK_MESSAGE_SCENES.keys())}")
    if sender is not None and sender not in ("buyer", "seller", "any"):
        raise HTTPException(status_code=400,
                            detail="sender 非法（buyer/seller/any）")
    return {"scenes": QUICK_MESSAGE_SCENES,
            "templates": get_quick_messages(scene=scene, sender=sender)}


# ---------------------------------------------------------------------------
# 会话（消息列表）
# ---------------------------------------------------------------------------

@router.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate,
                        db: Session = Depends(get_db)):
    """创建会话：交易发起（想要方 buyer 与发布方 seller 围绕 goods 建立会话）。"""
    g = db.get(Goods, payload.goods_id)
    if not g:
        raise HTTPException(status_code=404, detail="商品不存在")
    if not db.get(User, payload.buyer_id):
        raise HTTPException(status_code=404, detail="buyer_id 用户不存在")
    if not db.get(User, payload.seller_id):
        raise HTTPException(status_code=404, detail="seller_id 用户不存在")
    if payload.buyer_id == payload.seller_id:
        raise HTTPException(status_code=400, detail="买卖双方不能是同一用户")

    if payload.want_id is not None:
        want = db.get(Want, payload.want_id)
        if not want:
            raise HTTPException(status_code=404, detail="want_id 不存在")
        if want.goods_id != payload.goods_id or want.requester_id != payload.buyer_id:
            raise HTTPException(status_code=400,
                                detail="want 与商品/买家不匹配")

    # 已有进行中的会话则复用，避免重复会话
    dup = (db.query(Conversation)
           .filter(Conversation.goods_id == payload.goods_id,
                   Conversation.buyer_id == payload.buyer_id,
                   Conversation.seller_id == payload.seller_id,
                   Conversation.trade_state.in_(ACTIVE_TRADE_STATES))
           .first())
    if dup:
        return {"conversation": _conversation_to_out(dup, db), "created": False}

    conv = Conversation(goods_id=payload.goods_id,
                        want_id=payload.want_id,
                        buyer_id=payload.buyer_id,
                        seller_id=payload.seller_id,
                        trade_state="requested")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"conversation": _conversation_to_out(conv, db), "created": True}


@router.get("/conversations", response_model=ConversationListOut)
def list_conversations(user_id: int = Query(...,
                                            description="当前用户ID（消息列表页）"),
                       db: Session = Depends(get_db)):
    """我的会话列表（消息列表页）：含最后一条消息、未读数、交易状态。"""
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="用户不存在")
    items = (db.query(Conversation)
             .filter(or_(Conversation.buyer_id == user_id,
                         Conversation.seller_id == user_id))
             .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
             .all())
    return ConversationListOut(
        total=len(items), page=1, page_size=100,
        items=[_conversation_to_out(c, db, viewer_id=user_id) for c in items])


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    return _conversation_to_out(conv, db)


# ---------------------------------------------------------------------------
# 消息（聊天页）
# ---------------------------------------------------------------------------

@router.get("/conversations/{conversation_id}/messages",
            response_model=MessageListOut)
def list_messages(conversation_id: int,
                  page: int = Query(1, ge=1),
                  page_size: int = Query(50, ge=1, le=200),
                  db: Session = Depends(get_db)):
    """聊天记录：按时间倒序分页，页内返回正序（最新在下）。"""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    q = (db.query(Message).filter(Message.conversation_id == conversation_id))
    total = q.count()
    rows = (q.order_by(Message.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    rows.reverse()  # 页内按时间正序
    return MessageListOut(total=total, page=page, page_size=page_size,
                          items=[_message_to_out(m, db) for m in rows])


@router.post("/conversations/{conversation_id}/messages",
             status_code=status.HTTP_201_CREATED)
def send_message(conversation_id: int, payload: MessageCreate,
                 db: Session = Depends(get_db)):
    """发送消息：仅会话参与者可发；首条消息使交易状态 requested -> chatting。"""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    if payload.sender_id not in (conv.buyer_id, conv.seller_id):
        raise HTTPException(status_code=400, detail="仅会话参与者可发送消息")
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    msg = Message(conversation_id=conv.id, sender_id=payload.sender_id,
                  content=content)
    db.add(msg)
    if conv.trade_state == "requested":
        conv.trade_state = "chatting"   # 聊天建立（状态机 requested -> chatting）
    db.commit()
    db.refresh(msg)
    return {"message": _message_to_out(msg, db),
            "trade_state": conv.trade_state}


@router.post("/conversations/{conversation_id}/read")
def mark_read(conversation_id: int, payload: MarkReadRequest,
              db: Session = Depends(get_db)):
    """标记会话已读：把非当前用户的未读消息置为已读。"""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    if payload.user_id not in (conv.buyer_id, conv.seller_id):
        raise HTTPException(status_code=400, detail="仅会话参与者可操作")
    (db.query(Message)
     .filter(Message.conversation_id == conv.id,
             Message.sender_id != payload.user_id,
             Message.is_read.is_(False))
     .update({"is_read": True}, synchronize_session=False))
    db.commit()
    return {"ok": True, "unread_count": 0}


# ---------------------------------------------------------------------------
# 交易状态流转（成员B Day8 状态机）
# ---------------------------------------------------------------------------

@router.patch("/conversations/{conversation_id}/state")
def update_trade_state(conversation_id: int, payload: TradeStateUpdate,
                       db: Session = Depends(get_db)):
    """交易状态流转：使用成员B validate_transition 白名单校验，非法流转拒绝。"""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    result = validate_transition(conv.trade_state, payload.trade_state)
    if not result["valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"非法状态流转：{conv.trade_state} -> {payload.trade_state}"
                   f"（{result['reason']}）")
    conv.trade_state = payload.trade_state
    db.commit()
    db.refresh(conv)
    return {"conversation": _conversation_to_out(conv, db)}
