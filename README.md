# DotaSense

面向普通天梯玩家的 Dota 2 个人教练 Dashboard。当前 MVP 支持输入任意 OpenDota `account_id` 或玩家名搜索，查看最近表现，并把数据转成可执行的训练建议。

## 功能

- 任意玩家 Dashboard：基于 OpenDota 公共 API，不依赖 Notion。
- Coach 指挥台：状态评分、近期洞察、三步训练计划。
- 最近表现：最近 30/50/80 场胜率、KDA、状态评分、连胜/连败、平均时长。
- 英雄分析：近期英雄池、生涯常用英雄、胜率和 KDA。
- 趋势图表：滚动胜率、段位轨迹、时段表现、星期表现。
- 长期分布：OpenDota 分路样本、常见游戏模式。
- 眼位热图：基于 OpenDota wardmap 展示侦查守卫/岗哨守卫点位。
- 全局 Meta：基于 OpenDota heroStats 展示英雄热度、胜率、职业样本和个人英雄池对照。
- 保留旧数据能力：Notion 数据抓取、MMR 记录、比赛笔记和旧接口仍在项目中。

## 技术栈

- 后端：FastAPI + OpenDota API + Notion API
- 前端：Next.js 16 + React 19 + TypeScript + Tailwind CSS + Recharts
- 缓存：后端内存缓存，OpenDota 聚合接口默认 180 秒 TTL

## 快速启动

```bash
# 后端依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt

# 前端依赖
cd frontend
npm ci
cd ..

# 同时启动 FastAPI 和 Next.js
./start.sh
```

访问：

- Dashboard: http://localhost:3000
- Public profile: http://localhost:3000/p/894447460
- API health: http://localhost:8000/api/health

## 环境变量

复制 `.env.example` 到 `.env` 后按需填写。

```bash
cp .env.example .env
```

`OPENDOTA_API_KEY` 是可选项；不填也能用公共 OpenDota API，但限流更低。Notion 变量只影响旧的数据抓取、MMR 和比赛笔记能力。

## 主要 API

- `GET /api/players/search?q=<name>`：搜索玩家。
- `GET /api/players/{account_id}/dashboard?limit=50`：聚合玩家 Dashboard 和 Coach 数据。
- `GET /api/meta/overview`：获取全局英雄 Meta 样本。
- `GET /api/wardmap?account_id=<id>`：获取玩家眼位热图数据。
- `GET /api/health`：健康检查。
- 旧接口仍保留：`/api/dashboard`、`/api/matches`、`/api/update_data`、`/api/match_notes` 等。

## 常用命令

```bash
# 前端检查
cd frontend && npm run lint
cd frontend && npm run build
cd frontend && npx tsc --noEmit

# 后端语法检查
PYTHONPYCACHEPREFIX=/private/tmp/dota2_stats_pycache python3 -m compileall -q api

# 单独启动
cd api && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

## 数据来源

OpenDota API 文档：https://docs.opendota.com/

默认账号：`894447460`
