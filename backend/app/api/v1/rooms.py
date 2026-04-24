from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import random
import string

from app.db.database import get_db
from app.db.models import Room, Player, User
from app.api.v1.auth import get_current_user, get_password_hash, verify_password
from app.schemas.room import RoomCreate, RoomResponse, RoomJoin

router = APIRouter()


def generate_room_code(length=6):
    """生成房间码"""
    letters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letters) for i in range(length))


@router.post("", response_model=RoomResponse)
def create_room(
    room: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建房间"""
    # 生成唯一的房间码
    room_code = generate_room_code()
    while db.query(Room).filter(Room.room_code == room_code).first():
        room_code = generate_room_code()
    
    # 处理密码
    password_hash = None
    if room.password:
        password_hash = get_password_hash(room.password)
    
    # 创建房间
    db_room = Room(
        room_code=room_code,
        name=room.name,
        password_hash=password_hash,
        game_type=room.game_type,
        base_score=room.base_score or 0.0,
        elimination_score=room.elimination_score,
        winning_score=room.winning_score,
        created_by=current_user.id,
        status="open"
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    
    # 创建者自动加入房间
    db_player = Player(
        room_id=db_room.id,
        user_id=current_user.id,
        nickname=current_user.nickname,
        current_score=db_room.base_score,
        status="active"
    )
    db.add(db_player)
    db.commit()
    
    return RoomResponse(
        id=db_room.id,
        room_code=db_room.room_code,
        name=db_room.name,
        game_type=db_room.game_type,
        base_score=db_room.base_score,
        elimination_score=db_room.elimination_score,
        winning_score=db_room.winning_score,
        created_by=db_room.created_by,
        status=db_room.status,
        current_round=db_room.current_round,
        created_at=db_room.created_at
    )


@router.get("", response_model=list[RoomResponse])
def get_rooms(db: Session = Depends(get_db)):
    """获取房间列表"""
    rooms = db.query(Room).filter(Room.status != "closed").all()
    return [
        RoomResponse(
            id=room.id,
            room_code=room.room_code,
            name=room.name,
            game_type=room.game_type,
            base_score=room.base_score,
            elimination_score=room.elimination_score,
            winning_score=room.winning_score,
            created_by=room.created_by,
            status=room.status,
            current_round=room.current_round,
            created_at=room.created_at
        )
        for room in rooms
    ]


@router.get("/{room_code}", response_model=RoomResponse)
def get_room(room_code: str, db: Session = Depends(get_db)):
    """获取房间详情"""
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    return RoomResponse(
        id=room.id,
        room_code=room.room_code,
        name=room.name,
        game_type=room.game_type,
        base_score=room.base_score,
        elimination_score=room.elimination_score,
        winning_score=room.winning_score,
        created_by=room.created_by,
        status=room.status,
        current_round=room.current_round,
        created_at=room.created_at
    )


@router.post("/{room_code}/join")
def join_room(
    room_code: str,
    room_join: RoomJoin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """加入房间"""
    # 查找房间
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # 检查房间状态
    if room.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room is closed"
        )
    
    # 验证密码
    if room.password_hash and not verify_password(room_join.password, room.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect room password"
        )
    
    # 检查用户是否已在房间中
    existing_player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    if existing_player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already in this room"
        )
    
    # 加入房间
    db_player = Player(
        room_id=room.id,
        user_id=current_user.id,
        nickname=current_user.nickname,
        current_score=room.base_score,
        status="active"
    )
    db.add(db_player)
    db.commit()
    
    return {"message": "Successfully joined room"}


@router.delete("/{room_code}/leave")
def leave_room(
    room_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """离开房间"""
    # 查找房间
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # 查找玩家
    player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not in this room"
        )
    
    # 离开房间
    db.delete(player)
    db.commit()
    
    return {"message": "Successfully left room"}