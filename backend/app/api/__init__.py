from fastapi import APIRouter

from app.api.v1 import auth, users, rooms, scores, charts, players, websocket, confirmations

api_router = APIRouter()

# 注册各个模块的路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/user", tags=["用户"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["房间"])
api_router.include_router(scores.router, prefix="/scores", tags=["分数"])
api_router.include_router(charts.router, prefix="/charts", tags=["图表"])
api_router.include_router(players.router, prefix="/players", tags=["玩家"])
api_router.include_router(websocket.router, tags=["WebSocket"])
api_router.include_router(confirmations.router, prefix="/confirmations", tags=["确认状态"])
