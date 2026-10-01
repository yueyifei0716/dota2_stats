"""Verify every catalog hero through the actual teaching HTTP endpoints.

Only reads catalog/mechanics; it does not start 127 expensive build refreshes.
Usage: python api/scripts/verify_hero_teaching.py --base-url URL --output receipt.json
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

import requests


def verify(base_url):
    started = time.monotonic()
    catalog = requests.get(f"{base_url.rstrip('/')}/api/hero-guides/heroes", timeout=25)
    catalog.raise_for_status()
    heroes = catalog.json()["heroes"]
    if len({hero["hero_id"] for hero in heroes}) != 127:
        raise ValueError("Expected the actual 127-hero catalog")

    def check(hero):
        tick = time.monotonic()
        response = requests.get(f"{base_url.rstrip('/')}/api/hero-guides/{hero['hero_id']}", timeout=25)
        response.raise_for_status()
        data = response.json()
        guide = data.get("operating_guide") or {}
        build = guide.get("build_plan") or {}
        flows = guide.get("sequences") or []
        valid = (bool(data["hero"].get("hero_en")) and not data["source"]["stale"] and
                 len(build.get("steps", [])) >= 3 and len(build.get("branches", [])) >= 2 and
                 len(flows) >= 1 and all(len(flow["steps"]) >= 4 and len(flow["cautions"]) >= 2 for flow in flows))
        return {"hero_id": hero["hero_id"], "hero_cn": data["hero"]["hero_cn"],
                "hero_en": data["hero"]["hero_en"], "status": "pass" if valid else "fail",
                "http_status": response.status_code, "build_phases": len(build.get("steps", [])),
                "conditional_choices": len(build.get("branches", [])), "flows": len(flows),
                "seconds": round(time.monotonic() - tick, 3), "mechanics_fetched_at": data["source"]["fetched_at"]}

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(check, heroes))
    result = {"base_url": base_url, "checked_at": int(time.time()), "heroes": len(rows),
              "passed": sum(row["status"] == "pass" for row in rows),
              "flows": sum(row["flows"] for row in rows), "seconds": round(time.monotonic() - started, 3),
              "results": rows}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    receipt = verify(args.base_url)
    Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "results"}, ensure_ascii=False))
    raise SystemExit(0 if receipt["passed"] == 127 else 1)
