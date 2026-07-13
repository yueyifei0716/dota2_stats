# DotaSense

面向普通天梯玩家的 Dota 2 个人教练 Dashboard。当前 MVP 支持输入任意 OpenDota `account_id` 或玩家名搜索，查看最近表现，并把数据转成可执行的训练建议。

## 功能

- 任意玩家 Dashboard：基于 OpenDota 公共 API，不依赖 Notion。
- Today 训练驾驶舱：快速首屏、当前训练目标、三局挑战和自动进度记录。
- Match Lab：单局结算数据、同英雄百分位、下一组三局动作和证据覆盖清单。
- 五标签工作区：Today、Match Lab、Hero Pool、Meta、Progress，移动端支持横向切换。
- 最近表现：最近 30/50/80 场胜率、KDA、状态评分、连胜/连败、平均时长。
- 英雄分析：近期英雄池、生涯常用英雄、胜率和 KDA。
- 趋势图表：滚动胜率、段位轨迹、时段表现、星期表现。
- 长期分布：OpenDota 分路样本、常见游戏模式。
- 眼位热图：基于 OpenDota wardmap 展示侦查守卫/岗哨守卫点位。
- 证据化 AI 复盘：免费预览 + Pro 完整报告；没有 Replay 事件时禁止推断具体团战、死亡位置或装备时间。
- 商业化入口：Founder Pro、单次复盘、战队空间三档付费入口，支持支付链接、访问码解锁和 webhook 线索投递。
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

### 商业化配置

生产环境可以先只配置 `DOTASENSE_LEADS_WEBHOOK_URL`，把购买意向发送到飞书、Discord、Slack、Make/Zapier 等 webhook。配置支付链接后，Pro 表单提交成功会直接跳转付款。

```bash
DOTASENSE_CHECKOUT_FOUNDER_URL="https://..."
DOTASENSE_CHECKOUT_REVIEW_URL="https://..."
DOTASENSE_CHECKOUT_TEAM_URL="https://..."
DOTASENSE_LEADS_WEBHOOK_URL="https://..."
DOTASENSE_SALES_CONTACT="微信或邮箱"
DOTASENSE_SALES_URL="https://..."
DOTASENSE_DISCORD_URL="https://..."
DOTASENSE_PRO_ACCESS_CODE="发给付费用户的访问码"
DOTASENSE_ACCESS_SECRET="用于签名 Pro token 的长随机字符串"
DEEPSEEK_API_KEY="填入 DeepSeek API key"
```

没有配置支付链接时，购买表单仍可提交，后端会把线索写入日志，日志前缀为 `DOTASENSE_LEAD`。没有配置 `DEEPSEEK_API_KEY` 时，完整复盘仍会返回本地规则报告，但不会调用外部 AI 模型。

`DOTASENSE_PRO_ACCESS_CODE` 是当前 MVP 的付费解锁凭证：用户付款后获得访问码，前端换取 30 天签名 token。后续接入 Stripe、微信支付或 Lemon Squeezy webhook 时，可以复用同一套 token 签发逻辑。

## 主要 API

- `GET /api/players/search?q=<name>`：搜索玩家。
- `GET /api/players/{account_id}/dashboard?limit=50`：聚合玩家 Dashboard 和 Coach 数据。
- `GET /api/players/{account_id}/dashboard/quick?limit=20`：快速返回 Today 首屏，深度数据可随后补全。
- `GET /api/players/{account_id}/matches/{match_id}/scorecard`：返回单局英雄百分位、训练动作和证据状态。
- `GET /api/players/{account_id}/review/preview`：免费复盘预览。
- `POST /api/players/{account_id}/review`：Pro 完整 AI 复盘，需要访问 token。
- `GET /api/wardmap?account_id=<id>`：获取玩家眼位热图数据。
- `GET /api/commercial/config`：获取 Pro 定价和支付链接配置状态。
- `POST /api/commercial/leads`：提交购买意向，配置支付链接后返回 checkout URL。
- `POST /api/commercial/access`：用付费访问码换取 Pro token。
- `GET /api/commercial/access/verify`：校验 Pro token 是否仍有效。
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
