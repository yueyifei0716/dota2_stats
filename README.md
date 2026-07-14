# DotaSense

面向普通天梯玩家的 Dota 2 个人教练 Dashboard。当前 MVP 支持输入任意 OpenDota `account_id` 或玩家名搜索，查看最近表现，并把数据转成可执行的训练建议。

## 功能

- 任意玩家 Dashboard：OpenDota 提供公开战绩、出装与 Replay 事件，STRATZ 提供可验证的 Ranked Roles 位置与 IMP 表现，不依赖 Notion。
- Overview 个人总览：用近期胜率、趋势、KDA、死亡、主力英雄和段位组成一条决策摘要，紧接三局任务与比赛历史。
- 个人数据工作台：默认只展示英雄、真实 1–5 号位、胜负和日期；阵营、模式、匹配类型、组队状态收进“更多筛选”。
- Matches 比赛复盘：单局结算数据、STRATZ IMP/奖项、6 个主装备槽、中立物品、同英雄百分位和证据覆盖清单；不展示背包槽。
- 五标签工作区：Overview、Matches、Heroes、Meta、Progress，移动端支持横向切换。
- 五位置 Meta：基于 STRATZ GraphQL `heroStats` 的 Ranked Roles，分别展示 1–5 号位的胜率、校准胜率、样本量和位置选取率；实时接口不可用时回退到随版本发布的上一完整周验证快照，不会用分路、经济或补刀数据猜测位置。
- 最近表现：最近 30/50/80 场胜率、KDA、状态评分、连胜/连败、平均时长。
- 英雄分析：近期英雄池、生涯常用英雄、胜率和 KDA。
- 趋势图表：滚动胜率、段位轨迹、时段表现、星期表现。
- 个人位置表现：只统计 STRATZ 明确返回的 `POSITION_1`–`POSITION_5`；缺失位置不推断，也不进入五位置表现比较。
- 眼位热图：基于 OpenDota wardmap 展示侦查守卫/岗哨守卫点位。
- 证据化 AI 复盘：免费预览 + Pro 完整报告；没有 Replay 事件时禁止推断具体团战、死亡位置或装备时间。
- 商业化入口：Founder Pro、单次复盘、战队空间三档付费入口，支持支付链接、访问码解锁和 webhook 线索投递。
- 保留旧数据能力：Notion 数据抓取、MMR 记录、比赛笔记和旧接口仍在项目中。

## 技术栈

- 后端：FastAPI + OpenDota API + STRATZ GraphQL + Notion API
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

`OPENDOTA_API_KEY` 是可选项；不填也能用公共 OpenDota API，但限流更低。`STRATZ_API_TOKEN` 用于五位置 Meta、个人真实位置、IMP 与比赛奖项；STRATZ Token 限制为单一出口 IP，因此 Serverless 生产环境必须配置固定出口，或设置 `STRATZ_RUNTIME_MODE=snapshot` 使用验证周快照。快照模式下个人位置字段明确不可用且不回退到推断。Notion 变量只影响旧的数据抓取、MMR 和比赛笔记能力。

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
- `GET /api/players/{account_id}/dashboard?limit=50`：聚合玩家 Dashboard、STRATZ 真实位置/IMP 和 Coach 数据。
- `GET /api/players/{account_id}/dashboard/quick?limit=20`：快速返回 Overview 首屏，深度数据可随后补全。
- `GET /api/meta/overview`：返回 Divine/Immortal 上一完整周的 1–5 号位英雄 Meta；需要免费的 `STRATZ_API_TOKEN`，未配置时返回明确的不可用状态，不回退到位置推断。
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
