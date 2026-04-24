from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import Score, Room, Player, User
from app.api.v1.auth import get_current_user
from app.schemas.score import ScoreCreate, ScoreResponse, ScoreUpdate

router = APIRouter()


@router.post("", response_model=ScoreResponse)
def create_score(
    score: ScoreCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加分数记录"""
    # 检查房间是否存在
    room = db.query(Room).filter(Room.id == score.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # 检查玩家是否存在且在该房间
    player = db.query(Player).filter(
        Player.id == score.player_id,
        Player.room_id == score.room_id
    ).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found in this room"
        )
    
    # 检查玩家是否有权限操作（只有活跃状态的玩家可以计分）
    if player.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is not active"
        )
    
    # 创建分数记录
    db_score = Score(
        room_id=score.room_id,
        player_id=score.player_id,
        round=score.round,
        score=score.score,
        details=score.details
    )
    db.add(db_score)
    
    # 更新玩家的当前分数
    player.current_score += score.score
    
    # 检查玩家状态变化
    if room.elimination_score is not None and player.current_score <= room.elimination_score:
        player.status = "eliminated"
    elif room.winning_score is not None and player.current_score >= room.winning_score:
        # 检查是否是第一个胜利者
        first_winner = db.query(Player).filter(
            Player.room_id == room.id,
            Player.status == "won"
        ).first()
        if not first_winner:
            player.is_first_winner = True
        player.status = "won"
    
    db.commit()
    db.refresh(db_score)
    
    return ScoreResponse(
        id=db_score.id,
        room_id=db_score.room_id,
        player_id=db_score.player_id,
        round=db_score.round,
        score=db_score.score,
        details=db_score.details,
        created_at=db_score.created_at
    )


@router.get("/room/{room_id}", response_model=List[ScoreResponse])
def get_room_scores(
    room_id: int,
    db: Session = Depends(get_db)
):
    """获取房间分数"""
    scores = db.query(Score).filter(Score.room_id == room_id).order_by(Score.round, Score.created_at).all()
    return [
        ScoreResponse(
            id=score.id,
            room_id=score.room_id,
            player_id=score.player_id,
            round=score.round,
            score=score.score,
            details=score.details,
            created_at=score.created_at
        )
        for score in scores
    ]


@router.get("/room/{room_id}/player/{player_id}", response_model=List[ScoreResponse])
def get_player_scores(
    room_id: int,
    player_id: int,
    db: Session = Depends(get_db)
):
    """获取玩家分数历史"""
    scores = db.query(Score).filter(
        Score.room_id == room_id,
        Score.player_id == player_id
    ).order_by(Score.round, Score.created_at).all()
    return [
        ScoreResponse(
            id=score.id,
            room_id=score.room_id,
            player_id=score.player_id,
            round=score.round,
            score=score.score,
            details=score.details,
            created_at=score.created_at
        )
        for score in scores
    ]


@router.put("/{score_id}", response_model=ScoreResponse)
def update_score(
    score_id: int,
    score_update: ScoreUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新分数"""
    # 查找分数记录
    db_score = db.query(Score).filter(Score.id == score_id).first()
    if not db_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Score not found"
        )
    
    # 检查权限（只有房间创建者或分数所属玩家可以更新）
    room = db.query(Room).filter(Room.id == db_score.room_id).first()
    player = db.query(Player).filter(
        Player.id == db_score.player_id,
        Player.room_id == db_score.room_id
    ).first()
    
    if room.created_by != current_user.id and player.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # 更新分数
    if score_update.score is not None:
        # 计算分数变化
        score_diff = score_update.score - db_score.score
        db_score.score = score_update.score
        # 更新玩家的当前分数
        player.current_score += score_diff
        
        # 重新检查玩家状态
        if room.elimination_score is not None and player.current_score <= room.elimination_score:
            player.status = "eliminated"
        elif room.winning_score is not None and player.current_score >= room.winning_score:
            # 检查是否是第一个胜利者
            first_winner = db.query(Player).filter(
                Player.room_id == room.id,
                Player.status == "won"
            ).first()
            if not first_winner:
                player.is_first_winner = True
            player.status = "won"
    
    if score_update.details is not None:
        db_score.details = score_update.details
    
    db.commit()
    db.refresh(db_score)
    
    return ScoreResponse(
        id=db_score.id,
        room_id=db_score.room_id,
        player_id=db_score.player_id,
        round=db_score.round,
        score=db_score.score,
        details=db_score.details,
        created_at=db_score.created_at
    )


@router.delete("/{score_id}")
def delete_score(
    score_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除分数"""
    # 查找分数记录
    db_score = db.query(Score).filter(Score.id == score_id).first()
    if not db_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Score not found"
        )
    
    # 检查权限（只有房间创建者或分数所属玩家可以删除）
    room = db.query(Room).filter(Room.id == db_score.room_id).first()
    player = db.query(Player).filter(
        Player.id == db_score.player_id,
        Player.room_id == db_score.room_id
    ).first()
    
    if room.created_by != current_user.id and player.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # 从玩家当前分数中扣除该分数
    player.current_score -= db_score.score
    
    # 重新检查玩家状态
    if player.current_score > room.elimination_score:
        player.status = "active"
    
    # 删除分数记录
    db.delete(db_score)
    db.commit()
    
    return {"message": "Score deleted successfully"}