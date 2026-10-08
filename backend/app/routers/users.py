# -*- coding: utf-8 -*-
"""User CRUD + select-school router (Day 3)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import School, User
from ..schemas import (SelectSchoolRequest, SelectSchoolResponse, UserCreate,
                       UserOut, UserUpdate)

router = APIRouter()


@router.get("/users", response_model=list[UserOut])
def list_users(school_id: int | None = None,
               db: Session = Depends(get_db)):
    """列出用户，可按 school_id 过滤（同校浏览）。"""
    q = db.query(User)
    if school_id is not None:
        q = q.filter(User.school_id == school_id)
    return q.order_by(User.id).all()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """创建用户（首次进入选择学校后保存用户信息）。"""
    if not db.get(School, payload.school_id):
        raise HTTPException(status_code=400, detail="school_id 不存在")
    user = User(nickname=payload.nickname,
                avatar=payload.avatar,
                school_id=payload.school_id)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="创建用户失败")
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate,
                db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    data = payload.model_dump(exclude_unset=True)
    if "school_id" in data and data["school_id"] is not None:
        if not db.get(School, data["school_id"]):
            raise HTTPException(status_code=400, detail="school_id 不存在")
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.delete(user)
    db.commit()


@router.post("/users/{user_id}/select-school",
             response_model=SelectSchoolResponse)
def select_school(user_id: int, payload: SelectSchoolRequest,
                  db: Session = Depends(get_db)):
    """Day3 选校主流程：选择（切换）当前学校并返回用户与学校信息。"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    school = db.get(School, payload.school_id)
    if not school:
        raise HTTPException(status_code=400, detail="学校不存在")
    user.school_id = payload.school_id
    db.commit()
    db.refresh(user)
    return SelectSchoolResponse(user=user, school=school)
