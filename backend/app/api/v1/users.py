from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.api.v1.auth import get_current_user
from app.schemas.user import UserUpdate, UserResponse

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
def get_user_profile(current_user: User = Depends(get_current_user)):
    """获取用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        nickname=current_user.nickname,
        created_at=current_user.created_at
    )


@router.put("/profile", response_model=UserResponse)
def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    # 更新用户信息
    if user_update.nickname:
        current_user.nickname = user_update.nickname
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        nickname=current_user.nickname,
        created_at=current_user.created_at
    )