#!/bin/bash
# Start Dota 2 Stats — FastAPI + Next.js
# 依赖缺失时自动补齐；不需要记住任何前置命令。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PYTHON_BIN="$VENV/bin/python"

# --- Python 环境 -----------------------------------------------------------
# 这里早先在 .venv 缺失时回退到系统 python3。系统 python3 没有 fastapi，
# 后端于是在后台静默失败，报错还混在前端日志里——看起来像「网站坏了」。
# 宁可先把环境装好再启动。
if [ ! -x "$PYTHON_BIN" ]; then
    echo "· 未找到 .venv，正在创建..."
    python3 -m venv "$VENV" || { echo "✗ 创建 .venv 失败，请确认 python3 可用"; exit 1; }
fi

if ! "$PYTHON_BIN" -c "import fastapi, uvicorn, dotenv, requests, notion_client" >/dev/null 2>&1; then
    echo "· 正在安装 Python 依赖..."
    "$PYTHON_BIN" -m pip install --quiet --upgrade pip >/dev/null 2>&1
    "$PYTHON_BIN" -m pip install --quiet -r "$SCRIPT_DIR/api/requirements.txt" \
        || { echo "✗ Python 依赖安装失败"; exit 1; }
fi

# --- 前端依赖 ---------------------------------------------------------------
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo "· 正在安装前端依赖（首次约 1 分钟）..."
    (cd "$SCRIPT_DIR/frontend" && npm install --no-audit --no-fund) \
        || { echo "✗ npm install 失败"; exit 1; }
fi

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "· 提示：未找到 .env，Notion 抓取与比赛笔记会不可用（OpenDota 部分正常）"
fi

echo ""
echo "Starting Dota 2 Stats..."
echo ""

# --- 启动 -------------------------------------------------------------------
echo "Starting FastAPI (port 8000)..."
cd "$SCRIPT_DIR/api"
"$PYTHON_BIN" -m uvicorn main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!
echo "  FastAPI PID: $FASTAPI_PID"

echo "Starting Next.js (port 3000)..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
NEXTJS_PID=$!
echo "  Next.js PID: $NEXTJS_PID"

trap 'kill $FASTAPI_PID $NEXTJS_PID 2>/dev/null; exit 0' INT TERM

# 后端起不来时要立刻看得见，而不是等打开页面发现数据是空的
for _ in $(seq 1 20); do
    sleep 0.5
    if curl -fsS -m 2 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
        BACKEND_OK=1
        break
    fi
    kill -0 "$FASTAPI_PID" 2>/dev/null || break
done

echo ""
if [ -n "$BACKEND_OK" ]; then
    echo "✓ 后端就绪"
else
    echo "✗ 后端未能启动 —— 上方 uvicorn 的报错就是原因"
fi
echo ""
echo "Dashboard: http://localhost:3000"
echo "API:       http://localhost:8000/api/health"
echo ""
echo "Press Ctrl+C to stop both services"

wait
