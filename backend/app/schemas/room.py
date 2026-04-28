from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class RoomBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    game_type: str = Field(..., pattern="^(add_subtract|add_only)$")
    password: Optional[str] = None


class RoomCreate(RoomBase):
    pass


class RoomResponse(RoomBase):
    id: int
    room_code: str
    created_by: int
    status: str
    current_round: int = 1
    has_password: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class RoomJoin(BaseModel):
    password: Optional[str] = None