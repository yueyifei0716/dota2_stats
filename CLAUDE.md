# Dota 2 Stats Tracker

个人 Dota 2 战绩追踪系统，从 OpenDota API 抓取数据存入 Notion，通过 Flask Web 界面展示。

## 技术栈

- Python 3.10+ / Flask / Notion API / OpenDota API
- 数据存储: Notion Databases (4 个)
- 缓存: 内存 + 文件双层缓存（5 分钟 TTL）
- 环境: Miniconda (dota2 env)

## 目录结构

```
dota2_stats/
├── app.py                  # Flask 服务器 (端口 5001)
├── fetch_dota_stats.py     # OpenDota 数据抓取 + 高级指标计算
├── notion_db.py            # Notion CRUD 封装 (限流 3req/s)
├── notion_cache.py         # 双层缓存 (内存 + 文件)
├── daily_report.py         # 每日战报生成 (UTC+8)
├── obsidian_sync.py        # Obsidian 同步
├── migrate_to_notion.py    # CSV → Notion 迁移工具
├── templates/index.html    # Web UI
├── cache/                  # JSON 缓存文件
├── .env                    # Notion API 凭证
└── start.sh / stop.sh      # 启动/停止脚本
```

## 常用命令

```bash
# 启动服务
./start.sh                  # macOS/Linux
start.bat                   # Windows
# 或手动: conda activate dota2 && python app.py

# 停止服务
./stop.sh                   # macOS/Linux
stop.bat                    # Windows

# 数据抓取
python fetch_dota_stats.py                # 抓取最近 200 场比赛
python fetch_dota_stats.py --items        # 抓取物品数据 (慢，仅 20 场)
python fetch_dota_stats.py --advanced     # 回填高级数据 (金钱优势、Benchmark)
python fetch_dota_stats.py --fix-roles    # 修复历史比赛的位置检测
python fetch_dota_stats.py --backfill     # 回填历史比赛的物品数据

# 每日战报
python daily_report.py                    # 生成昨日战报
```

访问地址: http://127.0.0.1:5001

## 验证变更

修改代码后必须重启 Flask 服务器才能生效：

```bash
# macOS/Linux
./stop.sh && ./start.sh

# 或手动
pkill -f "python app.py" && python app.py
```

## 数据架构

### Notion 数据库 (4 个)

1. **Matches** - 比赛记录 (40+ 字段)
   - 基础: KDA, 英雄, 结果, 时长, 日期
   - 物品: 6 格物品 + 背包 3 格
   - 高级: 位置 (Pos 1-5), 影响力评分, 徽章, 金钱优势, Benchmark
   - 笔记: 用户自定义笔记

2. **Hero Stats** - 英雄统计
   - 胜率, 场次, KDA, 表现

3. **MMR History** - MMR 历史
   - 时间戳, MMR 值

4. **Profile** - 玩家档案
   - 用户名, 段位, MMR, 胜率

### 缓存策略

- **内存缓存**: 5 分钟 TTL，快速访问
- **文件缓存**: 持久化到 `cache/*.json`，故障降级
- **限流**: Notion API 3 请求/秒，指数退避重试

### 核心算法

**位置检测 (Pos 1-5)**:
- 基于队内 GPM 排名（最高 GPM = Pos 1，最低 = Pos 5）
- 回退到 `lane_role` 字段（仅前 10 分钟数据）

**影响力评分**:
```
(击杀*1.0 + 助攻*0.7 + 英雄伤害/1000*0.5 + 推塔伤害/1000*1.0) / (死亡+1)
归一化到 0-100，胜利 +20%，Benchmark 超 75% +10%
```

**徽章系统**:
- 🔥 高影响力 (评分 > 80)
- 📈 翻盘 (落后 >5k 金钱差后获胜)
- 💀 送分 (领先 >5k 金钱差后失败)
- ⭐ Carry (高伤害 + 胜利)
- 🛡️ Support (高助攻 + 低死亡)

## 重要约定

### OpenDota API

- **Steam ID**: 894447460
- **Base URL**: https://api.opendota.com/api
- **限流**: 比赛详情请求间隔 0.5 秒
- **刷新机制**: 更新前先调用 `/players/{STEAM_ID}/refresh` 触发解析，等待 3 秒
- **延迟**: 最新比赛需 1-2 分钟才能出现

### Flask 路由

- `GET /` - 主仪表盘 (支持英雄/位置/结果筛选)
- `POST /update_data` - 触发后台数据更新 (子进程)
- `POST /update_mmr` - 手动更新 MMR
- `POST /calibrate_mmr` - 校准 MMR
- `GET /api/matches` - JSON 比赛数据
- `GET /api/heroes` - JSON 英雄统计
- `GET /api/mmr_history` - JSON MMR 历史
- `GET/POST /api/match_notes` - 比赛笔记 CRUD

### Git 提交规则

**重要**: 不要在 commit message 中添加 "Co-Authored-By: Claude"。所有提交仅显示仓库所有者 (yueyifei0716) 为作者。

### 已知限制

1. **比赛延迟**: 最新比赛需 1-2 分钟才能出现（OpenDota 解析延迟）
2. **物品抓取**: 慢操作，默认仅抓 20 场新比赛
3. **翻盘/送分检测**: 仅适用于有 `radiant_gold_adv` 数据的比赛
4. **影响力评分**: 需要高级数据（`hero_damage`, `tower_damage`）
5. **更新超时**: 5 分钟超时限制

## 环境配置

### .env 文件

```
NOTION_TOKEN=ntn_***
NOTION_MATCHES_DB_ID=8626ca1a-2b3f-4ae6-95de-8d2dc1a6c2fc
NOTION_HERO_STATS_DB_ID=2ebf2e92-cf3a-4f77-821a-dee211961baf
NOTION_MMR_HISTORY_DB_ID=98bebcf0-9cf7-4c3d-83a5-0f429bfb6e5a
NOTION_PROFILE_DB_ID=d6888e4d-53a6-48a1-97d4-c273627cf704
```

### Conda 环境

```bash
conda activate dota2
```

如果 `conda activate` 不工作，使用完整 Python 路径：
```bash
/path/to/miniconda3/envs/dota2/bin/python script.py
```
