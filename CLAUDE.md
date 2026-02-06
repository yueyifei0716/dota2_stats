# CLAUDE.md - Project Maintenance Log

## Project Overview
Dota 2 Stats Tracker - A Flask web application that fetches and displays Dota 2 match statistics from OpenDota API.

**Steam ID:** 894447460
**Tech Stack:** Python, Flask, OpenDota API
**Environment:** Miniconda (dota2 env)

---

## Recent Changes

### 2026-02-06: Added Advanced Analytics (Impact Score, Badges, Throw/Comeback)
**Features Added:**

1. **Advanced Match Data Fetching:**
   - Lane role (Pos 1-5)
   - Net worth, level, gold spent
   - Max gold lead/deficit for throw/comeback detection
   - Benchmark percentiles (GPM, XPM, damage, tower damage)
   - Ally/enemy hero IDs for matchup analysis

2. **Impact Score System:**
   - Formula: `(kills * 1.0 + assists * 0.7 + (hero_damage / 1000) * 0.5 + (tower_damage / 1000) * 1.0) / (deaths + 1)`
   - Normalized to 0-100 scale
   - Win bonus: +20%
   - Benchmark bonus: +10% if above 75th percentile

3. **Badge System:**
   - 🔥 **High Impact** - Impact score > 80
   - 📈 **Comeback** - Won after >5k gold deficit
   - 💀 **Throw** - Lost after >5k gold lead
   - ⭐ **Carry** - High damage + win
   - 🛡️ **Support** - High assists, low deaths

**New Files:**
- `data/match_advanced.csv` - Advanced match metrics

**CLI Commands:**
```bash
python fetch_dota_stats.py --advanced  # Backfill advanced data for all matches
```

**Files Modified:**
- `fetch_dota_stats.py` - Added `fetch_match_advanced_data()`, `backfill_advanced_data()`
- `app.py` - Added `calculate_impact_score()`, `get_match_badges()`, `read_match_advanced()`
- `templates/index.html` - Added impact score and badges columns to match table

---

### 2026-02-06: Added Item Backfill Feature
**Problem:** Previously fetched matches were missing item data because items were only fetched for new matches.

**Solution:** Added `backfill_items()` function to fetch items for all matches that don't have item data.

**Usage:**
```bash
python fetch_dota_stats.py --backfill
```

**Files Modified:**
- `fetch_dota_stats.py` - Added `backfill_items()` function and `--backfill` CLI option

---

### 2026-02-06: Added Clickable Hero Cards
**Feature:** Clicking on any hero card now filters the match history to show only that hero's matches.

**Works on:**
- Hero Statistics section (英雄数据)
- Best Heroes section (最佳英雄)
- Worst Heroes section (需要练习)
- Recent Heroes tags (最近常用英雄)

**Files Modified:**
- `templates/index.html` - Added `filterByHero()` function and onclick handlers

---

### 2026-02-06: Fixed Match Update Issue
**Problem:** Update button wasn't fetching recent matches - OpenDota API was returning cached data.

**Root Cause:** OpenDota doesn't automatically parse new matches. The API needs a refresh request to trigger parsing of new matches from Valve's servers.

**Solution:** Added OpenDota refresh endpoint call before fetching matches.

**Files Modified:**
- `fetch_dota_stats.py:103-116` - Added `refresh_player_data()` function
- `fetch_dota_stats.py:437-446` - Updated `update_all()` to call refresh endpoint first with 3-second wait

**Changes:**
```python
def refresh_player_data():
    """Request OpenDota to refresh/parse new matches for the player."""
    url = f"{BASE_URL}/players/{STEAM_ID}/refresh"
    try:
        response = requests.post(url)
        if response.status_code == 200:
            print("Requested match refresh from OpenDota")
            return True
        else:
            print(f"Refresh request returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"Failed to request refresh: {e}")
        return False
```

**Note:** Even with this fix, very recent matches may take 1-2 minutes to appear as OpenDota needs time to fetch and parse data from Valve's servers.

---

## Project Structure

```
dota2_stats/
├── app.py                  # Flask web server
├── fetch_dota_stats.py     # OpenDota API client & data fetcher
├── templates/
│   └── index.html          # Web UI
├── data/                   # CSV data files
│   ├── matches.csv
│   ├── hero_stats.csv
│   ├── profile.csv
│   ├── match_items.csv
│   └── mmr_history.csv
├── start.bat               # Windows startup script
├── start.sh                # Unix/Mac startup script
├── stop.bat                # Windows shutdown script
├── stop.sh                 # Unix/Mac shutdown script
└── CLAUDE.md               # This file
```

---

## How to Run

### Quick Start (Windows)
```bash
start.bat
```

### Quick Start (Unix/Mac/Git Bash)
```bash
./start.sh
```

### Manual Start
```bash
# Activate conda environment
conda activate dota2

# Run Flask app
python app.py
```

Access at: http://127.0.0.1:5000

### Shutdown
```bash
# Windows
stop.bat

# Unix/Mac/Git Bash
./stop.sh
```

---

## API Endpoints

### OpenDota API Endpoints Used
- `GET /players/{STEAM_ID}` - Player profile
- `GET /players/{STEAM_ID}/matches?limit={n}` - Match history
- `GET /players/{STEAM_ID}/recentMatches` - Recent 20 matches
- `GET /players/{STEAM_ID}/heroes` - Hero statistics
- `GET /players/{STEAM_ID}/wl` - Win/Loss record
- `GET /matches/{match_id}` - Detailed match data
- `POST /players/{STEAM_ID}/refresh` - **NEW** Trigger match parsing

### Flask Routes
- `GET /` - Main dashboard
- `POST /update_data` - Trigger data refresh
- `GET /api/matches` - JSON match data
- `GET /api/hero_stats` - JSON hero statistics
- `GET /api/profile` - JSON player profile
- `GET /api/mmr_history` - JSON MMR history

---

## Key Functions

### fetch_dota_stats.py
- `refresh_player_data()` - Request OpenDota to parse new matches
- `fetch_matches(limit)` - Fetch match history
- `fetch_match_details(match_id)` - Get detailed match data with items
- `update_all(match_limit, current_mmr, fetch_items)` - Main update function
- `save_matches_csv()` - Save matches to CSV
- `save_hero_stats_csv()` - Save hero stats to CSV

### app.py
- `@app.route("/update_data")` - Handles update button clicks
- Spawns subprocess to run `fetch_dota_stats.py`
- Default limit: 200 matches (or 500 with --items flag)

---

## Known Issues & Limitations

1. **Match Delay:** Very recent matches may take 1-2 minutes to appear even after refresh
2. **Rate Limiting:** OpenDota API has rate limits (0.5s delay between match detail requests)
3. **Item Fetching:** Fetching items for all matches is slow (only fetches 20 new matches by default)
4. **Timeout:** Update operation has 5-minute timeout
5. **Throw/Comeback Detection:** Only works for matches that have been fully parsed by OpenDota. Many matches don't have `radiant_gold_adv` data available, so throw/comeback badges won't appear for those matches.
6. **Impact Score Data:** Uses `hero_damage` and `tower_damage` from `match_advanced.csv` (detailed match API). If advanced data is missing, scores will be inaccurate.

---

## Future Improvements

- [ ] Add loading indicator with progress updates
- [ ] Cache OpenDota responses to reduce API calls
- [ ] Add error handling for network failures
- [ ] Implement retry logic for failed API calls
- [ ] Add match notifications for new games
- [ ] Store data in SQLite instead of CSV files

---

## Maintenance Notes

### Git Commit Rules
**IMPORTANT:** Do NOT add "Co-Authored-By: Claude" to commit messages. All commits should only show the repository owner (yueyifei0716) as the author. Claude assists with code but should not be listed as a co-author.

### When Adding New Features
1. Update this file with changes
2. Document new API endpoints used
3. Update project structure if files added
4. Test update functionality still works

### When Debugging Update Issues
1. Check OpenDota API status: https://www.opendota.com/status
2. Verify Steam ID is correct (894447460)
3. Check Flask logs in terminal
4. Verify CSV files are being updated in `data/` directory
5. Test refresh endpoint manually: `POST https://api.opendota.com/api/players/894447460/refresh`

---

**Last Updated:** 2026-02-06
**Maintained By:** Claude (Opus 4.5)
