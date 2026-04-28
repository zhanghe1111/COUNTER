from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json

from app.db.database import get_db
from app.db.models import Player, Room, User, EventRecord
from app.api.v1.auth import get_current_user
from app.schemas.confirmation import ConfirmationRequest, RoomConfirmationStatus, ConfirmationStatus
from app.api.v1.websocket import manager
from datetime import datetime, timezone

router = APIRouter()


@router.get("/room/{room_id}/status", response_model=RoomConfirmationStatus)
def get_room_confirmation_status(
    room_id: int,
    db: Session = Depends(get_db)
):
    """获取房间确认状态"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    players = db.query(Player).filter(Player.room_id == room_id).all()

    player_statuses = [
        ConfirmationStatus(
            player_id=p.id,
            nickname=p.nickname,
            is_confirmed=p.is_confirmed and p.confirmed_round >= room.current_round,
            confirmed_round=p.confirmed_round
        )
        for p in players
    ]

    all_confirmed = all(
        p.is_confirmed and p.confirmed_round >= room.current_round
        for p in players
    )

    return RoomConfirmationStatus(
        room_id=room_id,
        current_round=room.current_round,
        players=player_statuses,
        all_confirmed=all_confirmed
    )


@router.post("/room/{room_id}/confirm")
def submit_confirmation(
    room_id: int,
    confirmation: ConfirmationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """提交确认状态"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    player = db.query(Player).filter(
        Player.room_id == room_id,
        Player.user_id == current_user.id
    ).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found in this room"
        )

    if player.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active players can confirm"
        )

    player.is_confirmed = confirmation.confirmed
    if confirmation.confirmed:
        player.confirmed_round = room.current_round

    db.commit()

    db.query(Room).filter(Room.id == room_id).update({"last_activity": datetime.now(timezone.utc)})
    db.commit()

    if confirmation.confirmed:
        event_data = {
            "player_id": player.id,
            "player_nickname": player.nickname,
            "round": room.current_round
        }
        event_record = EventRecord(room_id=room_id, type="round_confirmed", content=event_data)
        db.add(event_record)
        db.commit()

        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(manager.broadcast(
                    json.dumps({
                        "type": "room_event",
                        "event_type": "round_confirmed",
                        "data": event_data
                    }),
                    room_id
                ))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(manager.broadcast(
                json.dumps({
                    "type": "room_event",
                    "event_type": "round_confirmed",
                    "data": event_data
                }),
                room_id
            ))
            loop.close()

    players = db.query(Player).filter(Player.room_id == room_id).all()
    all_confirmed = all(
        p.is_confirmed and p.confirmed_round >= room.current_round
        for p in players if p.status == "active"
    )

    active_players = [p for p in players if p.status == "active"]
    all_active_confirmed = all(
        p.is_confirmed and p.confirmed_round >= room.current_round
        for p in active_players
    )

    return {
        "player_id": player.id,
        "is_confirmed": player.is_confirmed,
        "confirmed_round": player.confirmed_round,
        "all_confirmed": all_active_confirmed,
        "can_advance_round": all_active_confirmed
    }


@router.post("/room/{room_id}/next-round")
def advance_to_next_round(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """进入下一轮（所有玩家确认后才能调用）"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    if room.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only room creator can advance to next round"
        )

    players = db.query(Player).filter(Player.room_id == room_id).all()
    active_players = [p for p in players if p.status == "active"]

    all_active_confirmed = all(
        p.is_confirmed and p.confirmed_round >= room.current_round
        for p in active_players
    )

    if not all_active_confirmed:
        unconfirmed = [
            p.nickname for p in active_players
            if not (p.is_confirmed and p.confirmed_round >= room.current_round)
        ]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not all players have confirmed. Unconfirmed: {', '.join(unconfirmed)}"
        )

    room.current_round += 1

    for player in players:
        player.is_confirmed = False

    db.commit()
    db.refresh(room)

    db.query(Room).filter(Room.id == room_id).update({"last_activity": datetime.now(timezone.utc)})
    db.commit()

    event_data = {
        "new_round": room.current_round,
        "previous_round": room.current_round - 1
    }
    event_record = EventRecord(room_id=room_id, type="round_advanced", content=event_data)
    db.add(event_record)
    db.commit()

    import asyncio
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.ensure_future(manager.broadcast(
                json.dumps({
                    "type": "room_event",
                    "event_type": "round_advanced",
                    "data": event_data
                }),
                room_id
            ))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(manager.broadcast(
            json.dumps({
                "type": "room_event",
                "event_type": "round_advanced",
                "data": event_data
            }),
            room_id
        ))
        loop.close()

    return {
        "message": "Advanced to next round",
        "new_round": room.current_round
    }


@router.post("/room/{room_id}/reset-confirmations")
def reset_confirmations(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重置所有玩家的确认状态"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    if room.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only room creator can reset confirmations"
        )

    players = db.query(Player).filter(Player.room_id == room_id).all()
    for player in players:
        player.is_confirmed = False

    db.commit()

    return {"message": "All confirmations reset"}