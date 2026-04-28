from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import random
import string
import json
from datetime import datetime, timezone

from app.db.database import get_db
from app.db.models import Room, Player, User, EventRecord, EndGameVote, LeaveRequest, Score, PendingScore
from app.api.v1.auth import get_current_user, get_password_hash, verify_password
from app.schemas.room import RoomCreate, RoomResponse, RoomJoin
from app.api.v1.websocket import manager

router = APIRouter()


def generate_room_code(length=6):
    return ''.join(random.choice(string.digits) for i in range(length))


def _create_event(room_id: int, event_type: str, content: dict, db: Session):
    event = EventRecord(room_id=room_id, type=event_type, content=content)
    db.add(event)
    return event


def _reset_game_state(room_id: int, db: Session):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        return

    db.query(EndGameVote).filter(EndGameVote.room_id == room_id).delete()
    db.query(LeaveRequest).filter(LeaveRequest.room_id == room_id).delete()
    db.query(PendingScore).filter(PendingScore.room_id == room_id).delete()
    db.query(Score).filter(Score.room_id == room_id).delete()
    db.query(EventRecord).filter(EventRecord.room_id == room_id).delete()

    players = db.query(Player).filter(Player.room_id == room_id).all()
    for p in players:
        p.current_score = 0
        p.status = "active"
        p.is_first_winner = False
        p.is_confirmed = False
        p.confirmed_round = 0
        p.is_ready = False

    room.current_round = 1
    room.status = "open"


def _finish_game_state(room_id: int, db: Session):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        return

    db.query(EndGameVote).filter(EndGameVote.room_id == room_id).delete()
    db.query(LeaveRequest).filter(LeaveRequest.room_id == room_id).delete()
    db.query(PendingScore).filter(PendingScore.room_id == room_id).delete()

    players = db.query(Player).filter(Player.room_id == room_id).all()
    for p in players:
        p.status = "finished"
        p.is_confirmed = False
        p.is_ready = False

    room.status = "finished"


def _broadcast(room_id: int, event_type: str, data: dict):
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.ensure_future(manager.broadcast(
                json.dumps({"type": "room_event", "event_type": event_type, "data": data}),
                room_id
            ))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(manager.broadcast(
            json.dumps({"type": "room_event", "event_type": event_type, "data": data}),
            room_id
        ))
        loop.close()


def _touch_room(room_id: int, db: Session):
    db.query(Room).filter(Room.id == room_id).update({"last_activity": datetime.now(timezone.utc)})


@router.post("", response_model=RoomResponse)
def create_room(
    room: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room_code = generate_room_code()
    while db.query(Room).filter(Room.room_code == room_code).first():
        room_code = generate_room_code()

    password_hash = None
    if room.password:
        password_hash = get_password_hash(room.password)

    db_room = Room(
        room_code=room_code,
        name=room.name,
        password_hash=password_hash,
        game_type=room.game_type,
        created_by=current_user.id,
        status="open"
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)

    db_player = Player(
        room_id=db_room.id,
        user_id=current_user.id,
        nickname=current_user.nickname,
        current_score=0,
        status="active"
    )
    db.add(db_player)
    db.commit()

    return RoomResponse(
        id=db_room.id,
        room_code=db_room.room_code,
        name=db_room.name,
        game_type=db_room.game_type,
        created_by=db_room.created_by,
        status=db_room.status,
        current_round=db_room.current_round,
        created_at=db_room.created_at
    )


@router.get("", response_model=list[RoomResponse])
def get_rooms(db: Session = Depends(get_db)):
    rooms = db.query(Room).filter(Room.status.in_(["open", "playing"])).all()
    return [
        RoomResponse(
            id=room.id,
            room_code=room.room_code,
            name=room.name,
            game_type=room.game_type,
            created_by=room.created_by,
            status=room.status,
            current_round=room.current_round,
            has_password=bool(room.password_hash),
            created_at=room.created_at
        )
        for room in rooms
    ]


@router.get("/{room_code}", response_model=RoomResponse)
def get_room(room_code: str, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    return RoomResponse(
        id=room.id,
        room_code=room.room_code,
        name=room.name,
        game_type=room.game_type,
        created_by=room.created_by,
        status=room.status,
        current_round=room.current_round,
        has_password=bool(room.password_hash),
        created_at=room.created_at
    )


@router.get("/{room_code}/status")
def get_room_full_status(room_code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    players = db.query(Player).filter(Player.room_id == room.id).all()

    end_game_votes = db.query(EndGameVote).filter(EndGameVote.room_id == room.id).all()
    end_vote_map = {v.player_id: v.is_approved for v in end_game_votes}

    leave_requests = db.query(LeaveRequest).filter(
        LeaveRequest.room_id == room.id,
        LeaveRequest.status == "pending"
    ).all()

    return {
        "room_status": room.status,
        "is_playing": room.status == "playing",
        "players": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "nickname": p.nickname,
                "status": p.status,
                "is_ready": p.is_ready,
                "current_score": p.current_score,
                "is_confirmed": p.is_confirmed
            }
            for p in players
        ],
        "end_game_proposal": {
            "is_active": len(end_game_votes) > 0 if room.status == "playing" else False,
            "votes": [{"player_id": pid, "is_approved": approved} for pid, approved in end_vote_map.items()]
        } if room.status == "playing" else {"is_active": False},
        "leave_requests": [
            {
                "id": lr.id,
                "player_id": lr.player_id,
                "player_nickname": next((p.nickname for p in players if p.id == lr.player_id), "Unknown"),
                "status": lr.status
            }
            for lr in leave_requests
        ]
    }


@router.post("/{room_code}/join")
async def join_room(
    room_code: str,
    room_join: RoomJoin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    if room.status == "playing":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game already in progress, cannot join")

    if room.status == "closed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is closed")

    if room.password_hash and not verify_password(room_join.password, room.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incorrect room password")

    existing_player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    if existing_player:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are already in this room")

    db_player = Player(
        room_id=room.id,
        user_id=current_user.id,
        nickname=current_user.nickname,
        current_score=0,
        status="active"
    )
    db.add(db_player)
    db.commit()
    db.refresh(db_player)

    _touch_room(room.id, db)

    join_event_data = {"player_id": db_player.id, "player_nickname": db_player.nickname}
    _create_event(room.id, "player_joined", join_event_data, db)
    db.commit()

    _broadcast(room.id, "player_joined", join_event_data)

    return {"message": "Successfully joined room", "player_id": db_player.id}


@router.post("/{room_code}/ready")
def toggle_ready(
    room_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot ready up after game started")

    player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    if not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You are not in this room")

    player.is_ready = not player.is_ready
    db.commit()

    _touch_room(room.id, db)

    _broadcast(room.id, "ready_update", {
        "player_id": player.id,
        "player_nickname": player.nickname,
        "is_ready": player.is_ready
    })

    return {"player_id": player.id, "is_ready": player.is_ready}


@router.post("/{room_code}/start")
def start_game(
    room_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only room creator can start the game")
    if room.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game already started")

    players = db.query(Player).filter(Player.room_id == room.id).all()
    active_players = [p for p in players if p.status == "active"]

    if len(active_players) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Need at least 2 players to start")

    not_ready = [p.nickname for p in active_players if not p.is_ready]
    if not_ready:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not all players ready: {', '.join(not_ready)}"
        )

    room.status = "playing"
    room.current_round = 1
    db.commit()

    _touch_room(room.id, db)

    _broadcast(room.id, "game_started", {"round": 1})

    return {"message": "Game started", "round": 1}


@router.post("/{room_code}/propose-end")
def propose_end_game(
    room_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only room creator can propose ending")
    if room.status != "playing":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game is not in progress")

    existing = db.query(EndGameVote).filter(EndGameVote.room_id == room.id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End game already proposed")

    players = db.query(Player).filter(Player.room_id == room.id).all()
    for p in players:
        vote = EndGameVote(room_id=room.id, player_id=p.id, is_approved=(p.user_id == current_user.id))
        db.add(vote)

    db.commit()

    _touch_room(room.id, db)

    _broadcast(room.id, "end_proposed", {
        "owner_player_id": next((p.id for p in players if p.user_id == current_user.id), None),
        "owner_nickname": current_user.nickname
    })

    return {"message": "End game proposed"}


@router.post("/{room_code}/vote-end")
def vote_end_game(
    room_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status != "playing":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game is not in progress")

    player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    if not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You are not in this room")

    vote = db.query(EndGameVote).filter(
        EndGameVote.room_id == room.id,
        EndGameVote.player_id == player.id
    ).first()
    if not vote:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No end game proposal exists")

    vote.is_approved = True
    db.commit()

    _touch_room(room.id, db)

    _broadcast(room.id, "end_voted", {
        "player_id": player.id,
        "player_nickname": player.nickname,
        "is_approved": True
    })

    all_votes = db.query(EndGameVote).filter(EndGameVote.room_id == room.id).all()
    all_approved = all(v.is_approved for v in all_votes)
    total_players = db.query(Player).filter(Player.room_id == room.id).count()

    if all_approved:
        _finish_game_state(room.id, db)
        db.commit()

        _broadcast(room.id, "game_reset", {
            "reason": "all_agreed_end",
            "message": "All players agreed to end the game."
        })

        return {"message": "Game finished.", "game_reset": True, "all_approved": True}

    return {"message": "Vote recorded", "game_reset": False, "all_approved": False}


@router.get("/{room_code}/end-status")
def get_end_status(
    room_code: str,
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    votes = db.query(EndGameVote).filter(EndGameVote.room_id == room.id).all()
    players = db.query(Player).filter(Player.room_id == room.id).all()
    player_map = {p.id: p.nickname for p in players}

    return {
        "is_active": len(votes) > 0,
        "votes": [
            {
                "player_id": v.player_id,
                "player_nickname": player_map.get(v.player_id, "Unknown"),
                "is_approved": v.is_approved
            }
            for v in votes
        ],
        "all_approved": all(v.is_approved for v in votes) if votes else False
    }


@router.post("/{room_code}/request-leave")
def request_leave_game(
    room_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    if not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You are not in this room")

    existing = db.query(LeaveRequest).filter(
        LeaveRequest.room_id == room.id,
        LeaveRequest.player_id == player.id,
        LeaveRequest.status == "pending"
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Leave request already pending")

    if room.status == "playing":
        lr = LeaveRequest(room_id=room.id, player_id=player.id, status="pending")
        db.add(lr)
        db.commit()

        _touch_room(room.id, db)

        _broadcast(room.id, "leave_requested", {
            "player_id": player.id,
            "player_nickname": player.nickname,
            "request_id": lr.id
        })

        return {"message": "Leave request submitted. Waiting for room owner approval.", "request_id": lr.id}
    else:
        event_data = {"player_id": player.id, "player_nickname": player.nickname}
        _create_event(room.id, "player_left", event_data, db)
        db.delete(player)
        db.commit()

        _touch_room(room.id, db)

        _broadcast(room.id, "player_left", event_data)

        return {"message": "Left room"}


@router.post("/{room_code}/approve-leave/{request_id}")
def approve_leave_request(
    room_code: str,
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only room creator can approve leave requests")

    lr = db.query(LeaveRequest).filter(LeaveRequest.id == request_id, LeaveRequest.room_id == room.id).first()
    if not lr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")
    if lr.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request already processed")

    leaving_player = db.query(Player).filter(Player.id == lr.player_id).first()
    if not leaving_player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    leaving_nickname = leaving_player.nickname

    lr.status = "approved"

    if room.status == "playing":
        db.query(EndGameVote).filter(EndGameVote.room_id == room.id).delete()
        db.query(PendingScore).filter(PendingScore.room_id == room.id).delete()
        db.query(Score).filter(Score.room_id == room.id).delete()
        db.query(EventRecord).filter(EventRecord.room_id == room.id).delete()

        remaining_players = db.query(Player).filter(Player.room_id == room.id).all()
        for p in remaining_players:
            p.current_score = 0
            p.status = "active"
            p.is_first_winner = False
            p.is_confirmed = False
            p.confirmed_round = 0
            p.is_ready = False

        db.delete(leaving_player)

        room.current_round = 1
        room.status = "open"
    else:
        db.delete(leaving_player)

    db.query(LeaveRequest).filter(LeaveRequest.room_id == room.id).delete()

    db.commit()

    _touch_room(room.id, db)

    _broadcast(room.id, "leave_approved", {
        "player_id": lr.player_id,
        "player_nickname": leaving_nickname,
        "game_reset": room.status == "open"
    })

    return {"message": f"{leaving_nickname} has left. Game has been reset."}


@router.post("/{room_code}/reject-leave/{request_id}")
def reject_leave_request(
    room_code: str,
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only room creator can reject leave requests")

    lr = db.query(LeaveRequest).filter(LeaveRequest.id == request_id, LeaveRequest.room_id == room.id).first()
    if not lr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    lr.status = "rejected"
    db.commit()

    _touch_room(room.id, db)

    _broadcast(room.id, "leave_rejected", {
        "player_id": lr.player_id,
        "player_nickname": (db.query(Player).filter(Player.id == lr.player_id).first()).nickname if db.query(Player).filter(Player.id == lr.player_id).first() else "Unknown"
    })

    return {"message": "Leave request rejected"}


@router.delete("/{room_code}/leave")
def leave_room(
    room_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    if not player:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in this room")

    if room.status == "playing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game in progress. Use /request-leave to ask the owner for permission."
        )

    event_data = {"player_id": player.id, "player_nickname": player.nickname}
    _create_event(room.id, "player_left", event_data, db)
    db.delete(player)
    db.commit()

    _touch_room(room.id, db)

    _broadcast(room.id, "player_left", event_data)

    return {"message": "Successfully left room"}
