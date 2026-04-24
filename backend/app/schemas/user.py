from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(None, min_length=1, max_length=100)


class UserResponse(BaseModel):
    id: int
    username: str
    nickname: str
    created_at: datetime
    
    class Config:
        from_attributes = True