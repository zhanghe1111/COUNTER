import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.db.database import SessionLocal, engine, Base
from app.db.models import User
from sqlalchemy import text


def reset():
    print("=" * 50)
    print("  重置数据库 - 保留用户数据")
    print("=" * 50)

    with SessionLocal() as db:
        user_count = db.query(User).count()
        print(f"\n当前注册用户数: {user_count}")

    confirm = input(f"\n确认要清空并重建表结构吗？(yes/no): ")
    if confirm.lower() not in ('yes', 'y'):
        print("已取消")
        return

    print("\n  删除旧表并重建...")

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS end_game_votes CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS leave_requests CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS pending_scores CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS scores CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS event_records CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS players CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS rooms CASCADE"))
        conn.commit()

    Base.metadata.create_all(bind=engine)
    print("  所有表已重建完成")

    print(f"\n  已重建:")
    print(f"    - 结束投票 (end_game_votes)")
    print(f"    - 退出申请 (leave_requests)")
    print(f"    - 待确认通知 (pending_scores)")
    print(f"    - 事件日志 (event_records)")
    print(f"    - 历史分数 (scores)")
    print(f"    - 玩家记录 (players)")
    print(f"    - 房间记录 (rooms)")

    with SessionLocal() as db:
        remaining = db.query(User).count()
        print(f"\n  用户表: 保留 {remaining} 位注册用户 (未受影响)")

    print("\n" + "=" * 50)
    print("  重置完成！请重新启动服务。")
    print("=" * 50)


if __name__ == "__main__":
    reset()
