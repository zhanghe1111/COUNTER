from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Any

from app.db.database import get_db
from app.db.models import Score, Player, Room

router = APIRouter()


@router.get("/room/{room_id}")
def get_room_chart_data(
    room_id: int,
    db: Session = Depends(get_db)
):
    """获取房间分数曲线数据"""
    # 检查房间是否存在
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # 获取所有玩家
    players = db.query(Player).filter(Player.room_id == room_id).all()
    player_ids = [player.id for player in players]
    player_names = {player.id: player.nickname for player in players}
    
    # 获取所有轮次
    rounds = db.query(func.distinct(Score.round)).filter(
        Score.room_id == room_id
    ).order_by(Score.round).all()
    round_numbers = [r[0] for r in rounds]
    
    # 计算每个玩家在每轮的累计分数
    chart_data = {
        "rounds": round_numbers,
        "players": []
    }
    
    for player_id, player_name in player_names.items():
        # 获取该玩家的所有分数记录
        player_scores = db.query(Score).filter(
            Score.room_id == room_id,
            Score.player_id == player_id
        ).order_by(Score.round).all()
        
        # 计算每轮的累计分数
        cumulative_score = room.base_score
        scores_by_round = {}
        
        for score in player_scores:
            cumulative_score += score.score
            scores_by_round[score.round] = cumulative_score
        
        # 填充所有轮次的分数
        player_data = {
            "id": player_id,
            "name": player_name,
            "scores": []
        }
        
        for round_num in round_numbers:
            player_data["scores"].append(scores_by_round.get(round_num, cumulative_score))
        
        chart_data["players"].append(player_data)
    
    return chart_data


@router.get("/room/{room_id}/round/{round}")
def get_round_chart_data(
    room_id: int,
    round: int,
    db: Session = Depends(get_db)
):
    """获取某轮的分数曲线数据"""
    # 检查房间是否存在
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # 获取所有玩家
    players = db.query(Player).filter(Player.room_id == room_id).all()
    player_ids = [player.id for player in players]
    player_names = {player.id: player.nickname for player in players}
    
    # 获取该轮的所有分数记录
    round_scores = db.query(Score).filter(
        Score.room_id == room_id,
        Score.round == round
    ).order_by(Score.created_at).all()
    
    # 计算每个玩家在该轮的分数变化
    chart_data = {
        "round": round,
        "players": []
    }
    
    for player_id, player_name in player_names.items():
        # 获取该玩家在该轮的分数记录
        player_round_scores = [s for s in round_scores if s.player_id == player_id]
        
        # 计算分数变化
        score_changes = [s.score for s in player_round_scores]
        cumulative_changes = []
        total = 0
        
        for change in score_changes:
            total += change
            cumulative_changes.append(total)
        
        player_data = {
            "id": player_id,
            "name": player_name,
            "score_changes": score_changes,
            "cumulative_changes": cumulative_changes
        }
        
        chart_data["players"].append(player_data)
    
    return chart_data