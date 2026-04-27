from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
import uuid

from app.db.database import get_db
from app.db.models import Score, Room, Player, User, PendingScore, EventRecord
from app.api.v1.auth import get_current_user
from app.schemas.score import ScoreCreate, ScoreResponse, ScoreUpdate
from app.api.v1.websocket import manager

router = APIRouter()


def _check_player_status(player: Player, room: Room, db: Session):
    if room.elimination_score is not None and player.current_score <= room.elimination_score:
        player.status = "eliminated"
    elif room.winning_score is not None and player.current_score >= room.winning_score:
        first_winner = db.query(Player).filter(
            Player.room_id == room.id,
            Player.status == "won"
        ).first()
        if not first_winner:
            player.is_first_winner = True
        player.status = "won"


def _create_event(room_id: int, event_type: str, content: dict, db: Session):
    event = EventRecord(
        room_id=room_id,
        type=event_type,
        content=content
    )
    db.add(event)
    return event


@router.post("")
async def create_score(
    score: ScoreCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.id == score.room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    submitter = db.query(Player).filter(
        Player.id == score.player_id,
        Player.room_id == score.room_id
    ).first()
    if not submitter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found in this room")
    if submitter.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Player is not active")

    targets = []
    if score.details and score.details.get("type") == "add_subtract" and score.details.get("targets"):
        targets = score.details["targets"]

    batch_id = str(uuid.uuid4())
    all_scores = []
    winner_score_value = score.score * len(targets) if targets else score.score

    db_score = Score(
        room_id=score.room_id,
        player_id=score.player_id,
        round=score.round,
        score=winner_score_value,
        details={**(score.details or {}), "batch_id": batch_id}
    )
    db.add(db_score)
    all_scores.append(db_score)
    submitter.current_score += winner_score_value
    _check_player_status(submitter, room, db)

    pending_records = []
    for target_id in targets:
        target_player = db.query(Player).filter(
            Player.id == target_id,
            Player.room_id == score.room_id
        ).first()
        if not target_player:
            continue
        if target_player.status != "active":
            continue

        db_target_score = Score(
            room_id=score.room_id,
            player_id=target_id,
            round=score.round,
            score=-score.score,
            details={**(score.details or {}), "source_player_id": score.player_id, "batch_id": batch_id}
        )
        db.add(db_target_score)
        all_scores.append(db_target_score)
        target_player.current_score -= score.score
        _check_player_status(target_player, room, db)

        pending = PendingScore(
            room_id=score.room_id,
            source_player_id=score.player_id,
            target_player_id=target_id,
            batch_id=batch_id,
            round=score.round,
            score=score.score,
            status="pending"
        )
        db.add(pending)
        pending_records.append(pending)

    for pr in pending_records:
        pr.target_player = db.query(Player).filter(Player.id == pr.target_player_id).first()

    event_data = {
        "source_player_id": score.player_id,
        "source_nickname": submitter.nickname,
        "targets": [{"player_id": pr.target_player_id, "nickname": pr.target_player.nickname} for pr in pending_records],
        "score": score.score,
        "round": score.round,
        "batch_id": batch_id
    }
    _create_event(score.room_id, "score_collected", event_data, db)

    db.commit()

    for ps in all_scores:
        db.refresh(ps)
    for pr in pending_records:
        db.refresh(pr)

    await manager.broadcast(
        json.dumps({
            "type": "room_event",
            "event_type": "score_collected",
            "data": event_data
        }),
        score.room_id
    )

    return {
        "message": "Score submitted",
        "batch_id": batch_id,
        "winner_score": winner_score_value,
        "targets": [{"target_player_id": pr.target_player_id, "target_nickname": pr.target_player.nickname, "pending_id": pr.id} for pr in pending_records]
    }


@router.get("/room/{room_id}", response_model=List[ScoreResponse])
def get_room_scores(
    room_id: int,
    db: Session = Depends(get_db)
):
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
    db_score = db.query(Score).filter(Score.id == score_id).first()
    if not db_score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Score not found")

    room = db.query(Room).filter(Room.id == db_score.room_id).first()
    player = db.query(Player).filter(
        Player.id == db_score.player_id,
        Player.room_id == db_score.room_id
    ).first()

    if room.created_by != current_user.id and player.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    if score_update.score is not None:
        score_diff = score_update.score - db_score.score
        db_score.score = score_update.score
        player.current_score += score_diff

        if room.elimination_score is not None and player.current_score <= room.elimination_score:
            player.status = "eliminated"
        elif room.winning_score is not None and player.current_score >= room.winning_score:
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
    db_score = db.query(Score).filter(Score.id == score_id).first()
    if not db_score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Score not found")

    room = db.query(Room).filter(Room.id == db_score.room_id).first()
    player = db.query(Player).filter(
        Player.id == db_score.player_id,
        Player.room_id == db_score.room_id
    ).first()

    if room.created_by != current_user.id and player.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    player.current_score -= db_score.score

    if room.elimination_score is not None and player.current_score > room.elimination_score:
        player.status = "active"

    db.delete(db_score)
    db.commit()

    return {"message": "Score deleted successfully"}
