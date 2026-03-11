"""Data update action endpoint."""

import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter

import notion_cache as cache

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@router.post("/update_data")
def update_data(data: dict = None):
    try:
        fetch_items = (data or {}).get("fetch_items", False)
        script_path = PROJECT_ROOT / "fetch_dota_stats.py"

        args = [sys.executable, str(script_path)]
        if fetch_items:
            args.append("--items")
        else:
            args.append("200")

        result = subprocess.run(args, capture_output=True, text=True, timeout=300)
        cache.invalidate()

        if result.returncode == 0:
            return {"success": True, "message": "数据更新成功!"}
        else:
            return {"success": False, "message": f"更新失败: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "更新超时，请稍后重试"}
    except Exception as e:
        return {"success": False, "message": f"错误: {str(e)}"}
