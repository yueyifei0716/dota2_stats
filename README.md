# 🎮 Dota 2 Stats Tracker v2.0

个人 Dota 2 战绩追踪系统 - Next.js + FastAPI 全栈重写版

## ✨ 特性

- 📊 **完整数据面板**: MMR 趋势、段位历史、位置表现、英雄统计
- 📈 **数据可视化**: Recharts 图表、胜率分析、时段统计
- 🎯 **智能分析**: 影响力评分、徽章系统、英雄克制
- 🔄 **实时更新**: 一键更新数据、自动缓存
- 📝 **比赛笔记**: 记录每场比赛的心得
- 🎨 **精美设计**: "Arcane Command Center" 主题

## 🚀 快速启动

### 一键启动 (推荐)

```bash
./start_all.sh
```

访问: http://localhost:3000

### 分别启动

```bash
# 终端 1: 启动后端
./start_api.sh

# 终端 2: 启动前端
./start_frontend.sh
```

## 📦 技术栈

- **后端**: FastAPI + Notion API + OpenDota API
- **前端**: Next.js 15 + TypeScript + Tailwind CSS + SWR + Recharts
- **缓存**: 内存 + 文件双层缓存 (5分钟 TTL)

## 📊 功能模块 (12个核心面板)

1. 玩家资料 | 2. MMR 趋势 | 3. 段位历史 | 4. 位置表现
5. 近期常用 | 6. 英雄排名 | 7. 英雄统计 | 8. 胜率分析
9. 近期趋势 | 10. 常见队友 | 11. 英雄克制 | 12. 比赛记录

## 📚 文档

- `GUIDE_V2.md` - 完整实施指南
- `COMPLETION_SUMMARY.md` - 完成总结
- `README_V2.md` - 详细说明

## 🎯 版本

**v2.0.0** (2026-03-12) - ✅ 全部完成，可投入使用

---

**Steam ID**: 894447460 | **作者**: yueyifei0716
