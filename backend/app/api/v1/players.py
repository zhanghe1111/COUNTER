from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Player, Room

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
            "joined_at": player.joined_at
        }
        for player in players
    ]


