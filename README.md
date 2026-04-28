# 桌游计分器 (Board Game Score Counter)

一个支持实时协作的麻将/桌游计分 Web 应用，支持多人实时同步计分、加减分/纯加分两种模式、分数确认流程，让桌游计分变得简单高效。

## 功能特性

- **房间系统** — 创建/加入游戏房间，支持密码保护，6 位房间号快速加入
- **双计分模式** — 支持「加减分」和「纯加分」两种计分规则
- **实时同步** — 基于 WebSocket 的实时分数更新和事件推送
- **分数确认** — 双向确认机制，确保每笔分数记录准确无误
- **游戏管理** — 准备/开始游戏、结束投票、中途离场请求
- **历史记录** — 完整的游戏记录和分数详情
- **数据可视化** — 使用 ECharts 展示分数趋势图表
- **自动清理** — 超过 2 小时无活动的房间自动关闭
- **用户系统** — 注册登录、昵称修改、个人游戏记录

## 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| Python 3.11+ | 运行环境 |
| FastAPI | Web 框架 |
| PostgreSQL | 数据库 |
| SQLAlchemy | ORM 框架 |
| Alembic | 数据库迁移 |
| python-jose | JWT 认证 |
| passlib / bcrypt | 密码加密 |
| WebSocket | 实时通信 |
| Uvicorn | ASGI 服务器 |

### 前端

| 技术 | 用途 |
|------|------|
| Vue 3 (Composition API) | 前端框架 |
| TypeScript | 类型安全 |
| Vite | 构建工具 |
| Pinia | 状态管理 |
| Vue Router | 路由管理 |
| Axios | HTTP 客户端 |
| ECharts / vue-echarts | 图表可视化 |
| Iconify | 图标库 |
| WebSocket | 实时通信 |

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### 1. 克隆项目

```bash
git clone <repository-url>
cd COUNTER
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

编辑 `.env` 文件配置数据库连接：

```env
DATABASE_URL=postgresql://counter_user:<password>@localhost:5432/counter_db
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
HOST=0.0.0.0
PORT=8000
```

### 3. 前端配置

```bash
cd frontend
npm install
```

### 4. 启动服务

**启动后端：**

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API 文档访问：http://localhost:8000/docs

**启动前端：**

```bash
cd frontend
npm run dev
```

前端访问：http://localhost:3001

## 项目结构

```
COUNTER/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py          # 路由注册
│   │   │   └── v1/
│   │   │       ├── auth.py          # 登录/注册
│   │   │       ├── users.py         # 用户信息
│   │   │       ├── rooms.py         # 房间管理
│   │   │       ├── players.py       # 玩家管理
│   │   │       ├── scores.py        # 分数记录
│   │   │       ├── pending_scores.py # 待确认分数
│   │   │       ├── confirmations.py  # 确认状态
│   │   │       ├── charts.py        # 图表数据
│   │   │       ├── events.py        # 事件日志
│   │   │       └── websocket.py     # WebSocket
│   │   ├── core/
│   │   │   └── config.py            # 配置管理
│   │   ├── db/
│   │   │   ├── database.py          # 数据库连接
│   │   │   └── models.py            # 数据模型
│   │   └── schemas/
│   │       ├── auth.py
│   │       ├── user.py
│   │       ├── room.py
│   │       ├── score.py
│   │       └── confirmation.py
│   ├── main.py                      # FastAPI 入口
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CollapsibleSection.vue
│   │   │   ├── SkeletonLoader.vue
│   │   │   └── ToastContainer.vue
│   │   ├── router/
│   │   │   └── index.ts
│   │   ├── stores/
│   │   │   ├── toast.ts
│   │   │   └── user.ts
│   │   ├── utils/
│   │   │   └── api.ts
│   │   ├── views/
│   │   │   ├── HomeView.vue          # 首页
│   │   │   ├── LoginView.vue         # 登录
│   │   │   ├── RegisterView.vue      # 注册
│   │   │   ├── CreateRoomView.vue    # 创建房间
│   │   │   ├── RoomView.vue          # 游戏房间
│   │   │   └── ProfileView.vue       # 个人中心
│   │   ├── App.vue
│   │   ├── main.ts
│   │   └── style.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
└── .gitignore
```

## 数据模型

### 核心实体关系

```
User (用户)
  └── 创建 Room (房间) ──── 包含 Player (玩家)
                              ├── Score (分数记录)
                              ├── PendingScore (待确认分数)
                              ├── EventRecord (事件记录)
                              ├── EndGameVote (结束投票)
                              └── LeaveRequest (离场请求)
```

### 房间生命周期

1. `open` — 开放加入，等待玩家
2. `playing` — 游戏中，开始计分
3. `finished` — 游戏结束
4. `closed` — 已关闭（超时自动或手动）

## API 概览

### 认证模块 (`/api/auth`)
- `POST /register` — 用户注册
- `POST /login` — 用户登录

### 用户模块 (`/api/user`)
- `GET /profile` — 获取个人信息
- `PUT /profile` — 修改昵称
- `GET /history` — 游戏历史记录

### 房间模块 (`/api/rooms`)
- `GET /` — 获取房间列表
- `POST /` — 创建房间
- `GET /{code}` — 获取房间详情
- `POST /{code}/join` — 加入房间
- `POST /{code}/ready` — 准备/取消准备
- `POST /{code}/start` — 开始游戏
- `POST /{code}/end-game` — 提议/投票结束游戏
- `POST /{code}/leave` — 请求离场
- `GET /{code}/status` — 获取房间状态

### 分数模块 (`/api/scores`)
- `POST /collect` — 收集分数（加减分模式）
- `POST /add` — 加分（纯加分模式）
- `GET /room/{room_id}` — 获取房间所有分数
- `GET /player/{player_id}` — 获取玩家分数

### 待确认分数 (`/api/pending-scores`)
- `POST /batch/confirm` — 批量确认分数
- `POST /batch/reject` — 批量拒绝分数

### WebSocket (`/ws/{room_code}?token={jwt}`)
- 实时推送房间事件
- 分数变动通知
- 玩家状态变更
- 确认状态更新

## 计分模式说明

### 加减分模式 (`add_subtract`)
- 玩家可向其他玩家添加正分或负分
- 需双向确认后生效
- 适合麻将等有输赢的桌游

### 纯加分模式 (`add_only`)
- 仅支持加分操作
- 无需确认，即时生效
- 适合积分制桌游

## 开发说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql://admin:password@localhost:5432/counter_db` |
| `SECRET_KEY` | JWT 密钥 | `your-secret-key-here` |
| `ALGORITHM` | JWT 加密算法 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间(分钟) | `30` |
| `HOST` | 服务监听地址 | `0.0.0.0` |
| `PORT` | 服务监听端口 | `8000` |

### 前端代理配置

`vite.config.ts` 中配置了开发代理，前端请求 `/api` 自动转发到后端 `8000` 端口，WebSocket 连接 `/ws` 也做了相应转发。
