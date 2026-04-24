from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import Player, Room, User
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("/room/{room_id}")
def get_room_players(
    room_id: int,
    db: Session = Depends(get_db)
):
    """获取房间玩家状态"""
    # 检查房间是否存在
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # 获取房间内所有玩家
    players = db.query(Player).filter(Player.room_id == room_id).all()
    
    return [
        {
            "id": player.id,
            "user_id": player.user_id,
            "nickname": player.nickname,
            "seat": player.seat,
            "current_score": player.current_score,
            "status": player.status,
            "is_first_winner": player.is_first_winner,
            "joined_at": player.joined_at
        }
        for player in players
    ]


@router.put("/{player_id}/status")
def update_player_status(
    player_id: int,
    status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新玩家状态"""
    # 查找玩家
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    # 检查权限（只有房间创建者可以更新玩家状态）
    room = db.query(Room).filter(Room.id == player.room_id).first()
    if room.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # 验证状态值
    valid_statuses = ["active", "eliminated", "won"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    # 更新状态
    player.status = status
    
    # 如果设置为won，检查是否是第一个胜利者
    if status == "won" and not player.is_first_winner:
        first_winner = db.query(Player).filter(
            Player.room_id == player.room_id,
            Player.status == "won"
        ).first()
        if not first_winner:
            player.is_first_winner = True
    
    db.commit()
    db.refresh(player)
    
    return {
        "id": player.id,
        "status": player.status,
        "is_first_winner": player.is_first_winner
    }