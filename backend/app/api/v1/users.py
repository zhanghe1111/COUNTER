from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from app.db.database import get_db
from app.db.models import User, Player, Room, Score
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


@router.get("/history")
def get_user_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户游戏历史"""
    players = db.query(Player).filter(Player.user_id == current_user.id).all()
    
    result = []
    for player in players:
        room = db.query(Room).filter(Room.id == player.room_id).first()
        if not room:
            continue
        
        round_count = db.query(sa_func.count(sa_func.distinct(Score.round))).filter(
            Score.room_id == room.id
        ).scalar() or 0
        
        result.append({
            "room_id": room.id,
            "room_code": room.room_code,
            "room_name": room.name,
            "game_type": room.game_type,
            "status": room.status,
            "current_score": player.current_score,
            "round_count": round_count,
            "joined_at": player.joined_at.isoformat() if player.joined_at else None,
            "player_status": player.status,
            "seat": player.seat
        })
    
    result.sort(key=lambda x: x["joined_at"] or "", reverse=True)
    
    return result