from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import json
from typing import Dict

from app.db.database import get_db
from app.db.models import Room, Player, EventRecord

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: int, player_id: int):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][player_id] = websocket

    def disconnect(self, room_id: int, player_id: int):
        if room_id in self.active_connections:
            if player_id in self.active_connections[room_id]:
                del self.active_connections[room_id][player_id]
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def send_personal_message(self, message: str, room_id: int, player_id: int):
        if room_id in self.active_connections and player_id in self.active_connections[room_id]:
            await self.active_connections[room_id][player_id].send_text(message)

    async def broadcast(self, message: str, room_id: int):
        if room_id in self.active_connections:
            disconnected = []
            for player_id, connection in self.active_connections[room_id].items():
                try:
                    await connection.send_text(message)
                except Exception:
                    disconnected.append(player_id)
            for player_id in disconnected:
                self.disconnect(room_id, player_id)


manager = ConnectionManager()


@router.websocket("/ws/{room_id}/{player_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    player_id: int,
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        await websocket.close(code=1000, reason="Room not found")
        return

    player = db.query(Player).filter(
        Player.id == player_id,
        Player.room_id == room_id
    ).first()
    if not player:
        await websocket.close(code=1000, reason="Player not found in this room")
        return

    await manager.connect(websocket, room_id, player_id)

    try:
        await manager.send_personal_message(
            json.dumps({
                "type": "welcome",
                "message": f"Welcome to room {room.name}, {player.nickname}!",
                "room_id": room_id,
                "player_id": player_id,
                "current_round": room.current_round
            }),
            room_id,
            player_id
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "confirmation_update":
                await manager.broadcast(
                    json.dumps({
                        "type": "confirmation_update",
                        "player_id": player_id,
                        "is_confirmed": message["is_confirmed"],
                        "all_confirmed": message.get("all_confirmed", False),
                        "can_advance_round": message.get("can_advance_round", False)
                    }),
                    room_id
                )
            elif message["type"] == "round_advanced":
                await manager.broadcast(
                    json.dumps({
                        "type": "round_advanced",
                        "new_round": message["new_round"]
                    }),
                    room_id
                )
    except WebSocketDisconnect:
        manager.disconnect(room_id, player_id)

        leave_event_data = {
            "player_id": player_id,
            "player_nickname": player.nickname
        }
        event_record = EventRecord(room_id=room_id, type="player_left", content=leave_event_data)
        db.add(event_record)
        db.commit()

        await manager.broadcast(
            json.dumps({
                "type": "room_event",
                "event_type": "player_left",
                "data": leave_event_data
            }),
            room_id
        )
