from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class ConfirmationStatus(BaseModel):
    player_id: int
    nickname: str
    is_confirmed: bool
    confirmed_round: int


class RoomConfirmationStatus(BaseModel):
    room_id: int
    current_round: int
    players: List[ConfirmationStatus]
    all_confirmed: bool


class ConfirmationRequest(BaseModel):
    confirmed: bool