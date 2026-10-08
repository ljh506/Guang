# -*- coding: utf-8 -*-
"""School CRUD router (Day 3)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import School
from ..schemas import SchoolCreate, SchoolOut, SchoolUpdate

router = APIRouter()


@router.get("/schools", response_model=list[SchoolOut])
def list_schools(db: Session = Depends(get_db)):
    """列出全部学校（供前端选校下拉/搜索）。"""
    return db.query(School).order_by(School.id).all()


@router.get("/schools/{school_id}", response_model=SchoolOut)
def get_school(school_id: int, db: Session = Depends(get_db)):
    """获取学校详情。"""
    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")
    return school


@router.post("/schools", response_model=SchoolOut, status_code=status.HTTP_201_CREATED)
def create_school(payload: SchoolCreate, db: Session = Depends(get_db)):
    """新增学校。"""
    school = School(name=payload.name,
                    latitude=payload.latitude,
                    longitude=payload.longitude)
    db.add(school)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="学校名称已存在")
    db.refresh(school)
    return school


@router.patch("/schools/{school_id}", response_model=SchoolOut)
def update_school(school_id: int, payload: SchoolUpdate,
                  db: Session = Depends(get_db)):
    """更新学校信息（部分字段）。"""
    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(school, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="学校名称已存在")
    db.refresh(school)
    return school


@router.delete("/schools/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_school(school_id: int, db: Session = Depends(get_db)):
    """删除学校。"""
    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")
    db.delete(school)
    db.commit()
