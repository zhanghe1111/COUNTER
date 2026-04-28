from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.db.database import engine, Base, SessionLocal
from app.db.models import Room
from app.api import api_router


async def cleanup_stale_rooms():
    while True:
        try:
            db = SessionLocal()
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
                stale = db.query(Room).filter(
                    Room.status.in_(["open", "playing", "finished"]),
                    Room.last_activity < cutoff
                ).all()
                for room in stale:
                    old_status = room.status
                    room.status = "closed"
                    print(f"[cleanup] Room {room.room_code} (id={room.id}) closed after 2h inactivity (was {old_status})")
                if stale:
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"[cleanup] Error: {e}")
        await asyncio.sleep(600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(cleanup_stale_rooms())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="麻将/桌游算分器 API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "Welcome to 麻将/桌游算分器 API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
