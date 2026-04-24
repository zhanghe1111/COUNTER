from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List


class ScoreBase(BaseModel):
    room_id: int
    player_id: int
    round: int
    score: float
    details: Optional[Dict[str, Any]] = None


class ScoreCreate(ScoreBase):
    pass


class ScoreResponse(ScoreBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ScoreUpdate(BaseModel):
    score: Optional[float] = None
    details: Optional[Dict[str, Any]] = None