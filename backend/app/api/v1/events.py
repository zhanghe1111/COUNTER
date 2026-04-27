from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.database import get_db
from app.db.models import EventRecord, Room

router = APIRouter()


@router.get("/room/{room_id}")
def get_room_events(
    room_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    events = db.query(EventRecord).filter(
        EventRecord.room_id == room_id
    ).order_by(desc(EventRecord.created_at)).limit(limit).all()

    result = []
    for e in reversed(events):
        result.append({
            "id": e.id,
            "type": e.type,
            "content": e.content,
            "created_at": e.created_at.isoformat() if e.created_at else None
        })

    return result
