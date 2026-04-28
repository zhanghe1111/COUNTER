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

    rooms = relationship("Room", back_populates="creator")
    players = relationship("Player", back_populates="user")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=True)
    game_type = Column(String(20), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default="open", nullable=False)
    current_round = Column(Integer, default=1, nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    creator = relationship("User", back_populates="rooms")
    players = relationship("Player", back_populates="room", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="room", cascade="all, delete-orphan")
    pending_scores = relationship("PendingScore", back_populates="room", cascade="all, delete-orphan")
    events = relationship("EventRecord", back_populates="room", cascade="all, delete-orphan")
    end_game_votes = relationship("EndGameVote", back_populates="room", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequest", back_populates="room", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    nickname = Column(String(100), nullable=False)
    seat = Column(Integer, nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    current_score = Column(Float, default=0.0, nullable=False)
    status = Column(String(20), default="active", nullable=False)
    is_first_winner = Column(Boolean, default=False, nullable=False)
    is_confirmed = Column(Boolean, default=False, nullable=False)
    confirmed_round = Column(Integer, default=0, nullable=False)
    is_ready = Column(Boolean, default=False, nullable=False)

    room = relationship("Room", back_populates="players")
    user = relationship("User", back_populates="players")
    scores = relationship("Score", back_populates="player", cascade="all, delete-orphan")
    pending_as_source = relationship("PendingScore", back_populates="source_player", foreign_keys="PendingScore.source_player_id", cascade="all, delete-orphan")
    pending_as_target = relationship("PendingScore", back_populates="target_player", foreign_keys="PendingScore.target_player_id", cascade="all, delete-orphan")
    end_game_votes = relationship("EndGameVote", back_populates="player", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequest", back_populates="player", cascade="all, delete-orphan")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    round = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room", back_populates="scores")
    player = relationship("Player", back_populates="scores")


class PendingScore(Base):
    __tablename__ = "pending_scores"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    source_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    target_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    batch_id = Column(String(36), nullable=False, index=True)
    round = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    room = relationship("Room", back_populates="pending_scores")
    source_player = relationship("Player", back_populates="pending_as_source", foreign_keys=[source_player_id])
    target_player = relationship("Player", back_populates="pending_as_target", foreign_keys=[target_player_id])


class EventRecord(Base):
    __tablename__ = "event_records"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    type = Column(String(50), nullable=False)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room", back_populates="events")


class EndGameVote(Base):
    __tablename__ = "end_game_votes"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room")
    player = relationship("Player", back_populates="end_game_votes")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room")
    player = relationship("Player", back_populates="leave_requests")
