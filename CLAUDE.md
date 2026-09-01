# Dota 2 Stats Tracker

个人 Dota 2 战绩追踪系统。从 OpenDota API 抓取数据存入 Notion，通过 FastAPI + Next.js 展示。

## 技术栈

- **后端**: Python 3.10+ / FastAPI / Uvicorn
- **前端**: Next.js 16 / React 19 / Tailwind CSS / Recharts
- **数据**: Notion Databases (4 个: Matches, Hero Stats, MMR History, Profile)
- **外部 API**: OpenDota API
- **环境**: 项目根目录的 `.venv`（`./start.sh` 会自动创建并安装依赖）

## 目录结构

```
dota2_stats/
├── api/                    # FastAPI 后端
│   ├── main.py             # FastAPI 入口 (端口 8000)
│   ├── routers/            # 路由: dashboard, matches, heroes, mmr, actions, opendota
│   └── services/           # 业务逻辑: cache.py, stats.py
├── frontend/               # Next.js 前端
│   ├── app/                # Next.js App Router (端口 3000)
│   ├── components/         # React 组件 (MatchTable, MmrChart, HeroStats 等)
│   ├── hooks/              # useApi.ts
│   └── lib/                # api.ts, types.ts, constants.ts
├── fetch_dota_stats.py     # OpenDota 数据抓取 + 高级指标计算
├── notion_db.py            # Notion CRUD 封装 (限流 3req/s)
├── notion_cache.py         # 双层缓存 (内存 + 文件, 5min TTL)
├── daily_report.py         # 每日战报生成 (UTC+8)
├── obsidian_sync.py        # Obsidian 同步
├── cache/                  # JSON 缓存文件
├── start.sh / stop.sh      # 启动/停止 FastAPI + Next.js
└── .env                    # 环境变量 (Notion API 凭证)
```

## 常用命令

```bash
# 启动/停止服务（自动补齐依赖 + 同时启动 FastAPI + Next.js）
./start.sh
./stop.sh

# 单独启动
cd api && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev

# 数据抓取
python fetch_dota_stats.py                # 抓取最近 200 场比赛
python fetch_dota_stats.py --items        # 抓取物品数据 (慢，仅 20 场)
python fetch_dota_stats.py --advanced     # 回填高级数据 (金钱优势、Benchmark)
python fetch_dota_stats.py --fix-roles    # 修复历史位置检测
python fetch_dota_stats.py --backfill     # 回填历史物品数据

# 每日战报
python daily_report.py

# 前端
cd frontend && npm run lint               # ESLint 检查
cd frontend && npm run build              # 生产构建
```

## 验证变更

- **后端修改**: 重启 FastAPI — `./stop.sh && ./start.sh`
- **前端修改**: Next.js 支持热重载，无需重启
- **前端 lint**: `cd frontend && npm run lint`

## 重要约定

### OpenDota API

- **Steam ID**: 894447460
- **Base URL**: https://api.opendota.com/api
- **限流**: 比赛详情请求间隔 0.5 秒
- **刷新机制**: 更新前先调用 `/players/{STEAM_ID}/refresh`，等待 3 秒
- **延迟**: 最新比赛需 1-2 分钟才能出现

### API 路由 (FastAPI, 所有以 /api 为前缀)

- `GET /api/health` — 健康检查
- `GET /api/dashboard` — 聚合仪表盘数据
- `GET /api/matches` — 比赛列表 (支持筛选)
- `GET /api/heroes` — 英雄统计
- `GET /api/mmr_history` — MMR 历史
- `POST /api/update_data` — 触发后台数据更新
- `POST /api/update_mmr` — 手动更新 MMR
- `POST /api/calibrate_mmr` — 校准 MMR
- `GET/POST /api/match_notes` — 比赛笔记 CRUD
- `GET /api/all_heroes` — 全部 127 个英雄列表
- `GET /api/wardmap` — 眼位热力图 (代理 OpenDota)
- `GET /api/histograms/{field}` — 数据分布直方图 (GPM/XPM/击杀等)
- `GET /api/counts` — 游戏统计分布 (模式/大厅/阵营/路线)
- `GET /api/hero_items/{hero_id}` — 英雄出装推荐 (全局数据)
- `GET /api/hero_durations/{hero_id}` — 英雄胜率vs时长
- `GET /api/pro_encounters` — 职业选手对局记录

### 前后端通信

- Next.js 通过 `frontend/lib/api.ts` 调用 FastAPI
- CORS 已配置允许 `localhost:3000`

### Git 提交规则

不要在 commit message 中添加 "Co-Authored-By: Claude"。所有提交仅显示仓库所有者 (yueyifei0716) 为作者。

### 已知限制

1. 最新比赛需 1-2 分钟才能出现（OpenDota 解析延迟）
2. 物品抓取为慢操作，默认仅抓 20 场
3. 翻盘/送分检测仅适用于有 `radiant_gold_adv` 数据的比赛
4. 影响力评分需要高级数据（`hero_damage`, `tower_damage`）

### 环境配置

`./start.sh` 会自动完成全部准备：缺 `.venv` 就创建、缺 Python 依赖就装、缺
`frontend/node_modules` 就 `npm install`，然后才启动服务。**不需要手动激活环境或
预装依赖。**

单独跑脚本（抓数据、日报）时用 `.venv` 里的解释器：

```bash
./.venv/bin/python fetch_dota_stats.py
```

`.env` 中需配置: NOTION_TOKEN, NOTION_MATCHES_DB_ID, NOTION_HERO_STATS_DB_ID,
NOTION_MMR_HISTORY_DB_ID, NOTION_PROFILE_DB_ID。不配也能用 —— 只影响 Notion
抓取、MMR 记录和比赛笔记，OpenDota 部分正常。
