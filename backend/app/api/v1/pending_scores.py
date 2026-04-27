from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from app.db.database import get_db
from app.db.models import PendingScore, Score, Player, Room, User, EventRecord
from app.api.v1.auth import get_current_user
from app.api.v1.websocket import manager

router = APIRouter()


def _create_event(room_id: int, event_type: str, content: dict, db: Session):
    event = EventRecord(room_id=room_id, type=event_type, content=content)
    db.add(event)
    return event


@router.get("/room/{room_id}/player/{player_id}")
def get_player_pending_scores(
    room_id: int,
    player_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    player = db.query(Player).filter(
        Player.id == player_id,
        Player.room_id == room_id,
        Player.user_id == current_user.id
    ).first()
    if not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    pendings = db.query(PendingScore).filter(
        PendingScore.room_id == room_id,
        PendingScore.target_player_id == player_id,
        PendingScore.status == "pending"
    ).order_by(PendingScore.created_at.desc()).all()

    result = []
    for p in pendings:
        source = db.query(Player).filter(Player.id == p.source_player_id).first()
        result.append({
            "id": p.id,
            "batch_id": p.batch_id,
            "source_player_id": p.source_player_id,
            "source_nickname": source.nickname if source else "Unknown",
            "score": p.score,
            "round": p.round,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None
        })

    return result


@router.post("/{pending_id}/accept")
async def accept_pending_score(
    pending_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pending = db.query(PendingScore).filter(PendingScore.id == pending_id).first()
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending score not found")

    target_player = db.query(Player).filter(Player.id == pending.target_player_id).first()
    if not target_player or target_player.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    if pending.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This request is no longer pending")

    pending.status = "accepted"
    pending.confirmed_at = datetime.now(timezone.utc)

    source = db.query(Player).filter(Player.id == pending.source_player_id).first()
    event_data = {
        "target_player_id": pending.target_player_id,
        "target_nickname": target_player.nickname,
        "source_player_id": pending.source_player_id,
        "source_nickname": source.nickname if source else "Unknown",
        "score": pending.score,
        "round": pending.round,
        "batch_id": pending.batch_id
    }
    _create_event(pending.room_id, "score_accepted", event_data, db)
    db.commit()

    await manager.broadcast(
        json.dumps({"type": "room_event", "event_type": "score_accepted", "data": event_data}),
        pending.room_id
    )

    return {"message": "Accepted", "pending_id": pending.id}


@router.post("/{pending_id}/reject")
async def reject_pending_score(
    pending_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pending = db.query(PendingScore).filter(PendingScore.id == pending_id).first()
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending score not found")

    target_player = db.query(Player).filter(Player.id == pending.target_player_id).first()
    if not target_player or target_player.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    if pending.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This request is no longer pending")

    batch_id = pending.batch_id
    room_id = pending.room_id
    source_player_id = pending.source_player_id
    score_value = pending.score
    round_num = pending.round

    source_player = db.query(Player).filter(Player.id == source_player_id).first()
    source_nickname = source_player.nickname if source_player else "Unknown"
    rejector_nickname = target_player.nickname

    batch_pendings = db.query(PendingScore).filter(
        PendingScore.batch_id == batch_id,
        PendingScore.room_id == room_id
    ).all()

    batch_scores = db.query(Score).filter(
        Score.room_id == room_id,
        Score.round == round_num
    ).all()

    matched_score_ids = []
    for bs in batch_scores:
        if bs.details and bs.details.get("batch_id") == batch_id:
            matched_score_ids.append(bs.id)

    batch_scores_to_revert = db.query(Score).filter(Score.id.in_(matched_score_ids)).all() if matched_score_ids else []
    for bs in batch_scores_to_revert:
        player_to_revert = db.query(Player).filter(Player.id == bs.player_id).first()
        if player_to_revert:
            player_to_revert.current_score -= bs.score
        db.delete(bs)

    for bp in batch_pendings:
        bp.status = "rejected"
        bp.confirmed_at = datetime.now(timezone.utc)

    target_names_list = []
    for bp in batch_pendings:
        tp = db.query(Player).filter(Player.id == bp.target_player_id).first()
        target_names_list.append(tp.nickname if tp else "Unknown")

    target_players_for_event = [
        {"player_id": bp.target_player_id, "nickname": tname}
        for bp, tname in zip(batch_pendings, target_names_list)
    ]

    event_data = {
        "source_player_id": source_player_id,
        "source_nickname": source_nickname,
        "rejector_player_id": pending.target_player_id,
        "rejector_nickname": rejector_nickname,
        "targets": target_players_for_event,
        "score": score_value,
        "round": round_num,
        "batch_id": batch_id
    }
    _create_event(room_id, "score_rejected", event_data, db)
    db.commit()

    await manager.broadcast(
        json.dumps({"type": "room_event", "event_type": "score_rejected", "data": event_data}),
        room_id
    )

    return {
        "message": "Rejected. All scores in this batch have been rolled back.",
        "batch_id": batch_id,
        "reverted_player_ids": [bs.player_id for bs in batch_scores_to_revert]
    }
