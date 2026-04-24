from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    rooms = relationship("Room", back_populates="creator")
    players = relationship("Player", back_populates="user")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=True)
    game_type = Column(String(20), nullable=False)  # 'add_subtract' 或 'add_only'
    base_score = Column(Float, default=0.0, nullable=False)
    elimination_score = Column(Float, nullable=True)  # 可为NULL表示无下限
    winning_score = Column(Float, nullable=True)  # 可为NULL表示无上限
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default="open", nullable=False)  # open, closed, playing
    current_round = Column(Integer, default=1, nullable=False)  # 当前轮次
    
    # 关系
    creator = relationship("User", back_populates="rooms")
    players = relationship("Player", back_populates="room", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="room", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    nickname = Column(String(100), nullable=False)
    seat = Column(Integer, nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    current_score = Column(Float, default=0.0, nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active, eliminated, won
    is_first_winner = Column(Boolean, default=False, nullable=False)
    is_confirmed = Column(Boolean, default=False, nullable=False)  # 是否已确认当前轮次
    confirmed_round = Column(Integer, default=0, nullable=False)  # 已确认的轮次
    
    # 关系
    room = relationship("Room", back_populates="players")
    user = relationship("User", back_populates="players")
    scores = relationship("Score", back_populates="player", cascade="all, delete-orphan")


class Score(Base):
    __tablename__ = "scores"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    round = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    details = Column(JSON, nullable=True)  # 分数详情，包含来源信息等
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    room = relationship("Room", back_populates="scores")
    player = relationship("Player", back_populates="scores")