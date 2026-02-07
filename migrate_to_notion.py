"""
One-time migration script: CSV data -> Notion databases.
Reads all CSV files, merges by match_id, and pushes to Notion.
"""

import csv
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import notion_db as nc

DATA_DIR = Path(__file__).parent / "data"


def load_csv(filename):
    """Load CSV file as list of dicts."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_csv_keyed(filename, key="match_id"):
    """Load CSV file as dict keyed by a field."""
    rows = load_csv(filename)
    return {row[key]: row for row in rows if key in row}


def load_profile():
    """Load profile CSV (key-value format)."""
    filepath = DATA_DIR / "profile.csv"
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["field"]: row["value"] for row in reader}


def migrate_profile():
    """Migrate profile data to Notion."""
    print("=== Migrating Profile ===")
    profile = load_profile()
    if not profile:
        print("  No profile data found, skipping")
        return

    nc.update_profile({
        "username": profile.get("username", ""),
        "steam_id": profile.get("steam_id"),
        "rank_tier": profile.get("rank_tier"),
        "current_mmr": profile.get("current_mmr"),
        "estimated_mmr": profile.get("estimated_mmr"),
        "country": profile.get("country", ""),
        "total_wins": profile.get("total_wins"),
        "total_losses": profile.get("total_losses"),
        "win_rate": profile.get("win_rate"),
    })
    print("  Profile migrated successfully")


def migrate_hero_stats():
    """Migrate hero stats to Notion."""
    print("=== Migrating Hero Stats ===")
    heroes = load_csv("hero_stats.csv")
    if not heroes:
        print("  No hero stats found, skipping")
        return

    total = len(heroes)
    for i, h in enumerate(heroes):
        print(f"  [{i+1}/{total}] {h.get('hero_cn', 'unknown')}")
        nc.upsert_hero_stat(h)
    print(f"  Migrated {total} hero stats")


def migrate_mmr_history():
    """Migrate MMR history to Notion."""
    print("=== Migrating MMR History ===")
    entries = load_csv("mmr_history.csv")
    if not entries:
        print("  No MMR history found, skipping")
        return

    total = len(entries)
    for i, e in enumerate(entries):
        print(f"  [{i+1}/{total}] MMR: {e.get('mmr')}")
        nc.append_mmr_history(
            mmr=e.get("mmr"),
            result=e.get("result", "")
        )
    print(f"  Migrated {total} MMR entries")


def migrate_matches():
    """Migrate matches (with items, advanced, notes merged) to Notion."""
    print("=== Migrating Matches ===")
    matches = load_csv("matches.csv")
    if not matches:
        print("  No matches found, skipping")
        return

    items = load_csv_keyed("match_items.csv")
    advanced = load_csv_keyed("match_advanced.csv")

    # Load notes if exists
    notes_file = DATA_DIR / "match_notes.csv"
    notes = {}
    if notes_file.exists():
        with open(notes_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                notes[row["match_id"]] = row.get("note", "")

    # Get already migrated match IDs to skip them
    print("  Checking for already migrated matches...")
    existing_matches = nc.query_matches()
    existing_ids = {str(m.get("match_id", "")) for m in existing_matches}
    print(f"  Found {len(existing_ids)} matches already in Notion")

    total = len(matches)
    print(f"  Total matches in CSV: {total}")
    print(f"  Items data available for: {len(items)} matches")
    print(f"  Advanced data available for: {len(advanced)} matches")

    migrated = 0
    skipped = 0
    for i, m in enumerate(matches):
        mid = m.get("match_id", "")

        # Skip if already migrated
        if mid in existing_ids:
            skipped += 1
            continue

        migrated += 1
        print(f"  [{migrated}] Match {mid} (CSV row {i+1}/{total})")

        # Build all properties at once to minimize API calls
        props = nc._build_match_properties(m)

        # Merge items if available
        if mid in items:
            item_data = items[mid]
            props.update(nc._build_item_properties({
                "items": [
                    int(item_data.get("item_0", 0) or 0),
                    int(item_data.get("item_1", 0) or 0),
                    int(item_data.get("item_2", 0) or 0),
                    int(item_data.get("item_3", 0) or 0),
                    int(item_data.get("item_4", 0) or 0),
                    int(item_data.get("item_5", 0) or 0),
                ],
                "item_neutral": int(item_data.get("item_neutral", 0) or 0),
            }))

        # Merge advanced data if available
        if mid in advanced:
            props.update(nc._build_advanced_properties(advanced[mid]))

        # Merge note if available
        if mid in notes and notes[mid]:
            props["Note"] = nc._rich_text(notes[mid])
            props["Note Updated At"] = nc._rich_text(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

        # Single create call with all properties
        nc._retry(lambda: nc.notion.pages.create(
            parent={"database_id": nc.MATCHES_DB_ID},
            properties=props
        ))

    print(f"  Migrated {migrated} matches, skipped {skipped} (already in Notion)")


def verify_migration():
    """Verify row counts after migration."""
    print("\n=== Verification ===")
    matches_csv = load_csv("matches.csv")
    heroes_csv = load_csv("hero_stats.csv")
    mmr_csv = load_csv("mmr_history.csv")

    matches_notion = nc.query_matches()
    heroes_notion = nc.query_hero_stats()
    mmr_notion = nc.query_mmr_history()
    profile_notion = nc.get_profile()

    print(f"  Matches:    CSV={len(matches_csv)}, Notion={len(matches_notion)}")
    print(f"  Hero Stats: CSV={len(heroes_csv)}, Notion={len(heroes_notion)}")
    print(f"  MMR History: CSV={len(mmr_csv)}, Notion={len(mmr_notion)}")
    print(f"  Profile:    {'OK' if profile_notion else 'MISSING'}")

    all_ok = (
        len(matches_notion) == len(matches_csv)
        and len(heroes_notion) == len(heroes_csv)
        and len(mmr_notion) == len(mmr_csv)
        and bool(profile_notion)
    )
    if all_ok:
        print("\n  All counts match!")
    else:
        print("\n  WARNING: Some counts don't match!")
    return all_ok


if __name__ == "__main__":
    print("Starting migration from CSV to Notion...\n")
    migrate_profile()
    migrate_hero_stats()
    migrate_mmr_history()
    migrate_matches()
    verify_migration()
    print("\nMigration complete!")
