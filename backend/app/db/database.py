from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
    pool_size=10 if not settings.DATABASE_URL.startswith("sqlite") else 5,
    max_overflow=20 if not settings.DATABASE_URL.startswith("sqlite") else 10
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


# 依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()