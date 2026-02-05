# Dota 2 Stats Tracker

A Flask web application that fetches and displays Dota 2 match statistics from the OpenDota API.

## Features

- View match history with detailed statistics
- Hero performance tracking (win rates, games played)
- MMR history tracking
- Item builds for recent matches
- Chinese hero names support

## Requirements

- Python 3.8+
- Miniconda/Anaconda (recommended)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/dota2_stats.git
cd dota2_stats
```

2. Create conda environment:
```bash
conda create -n dota2 python=3.10
conda activate dota2
pip install flask requests
```

3. Create data directory:
```bash
mkdir data
```

4. Update Steam ID in `fetch_dota_stats.py` (line 13):
```python
STEAM_ID = YOUR_STEAM_ID
```

## Usage

### Start the server

**Windows:**
```bash
start.bat
```

**Unix/Mac/Git Bash:**
```bash
./start.sh
```

Then open http://127.0.0.1:5000 in your browser.

### Stop the server

**Windows:**
```bash
stop.bat
```

**Unix/Mac/Git Bash:**
```bash
./stop.sh
```

## Project Structure

```
dota2_stats/
├── app.py                  # Flask web server
├── fetch_dota_stats.py     # OpenDota API client
├── templates/
│   └── index.html          # Web UI
├── data/                   # CSV data files (gitignored)
├── start.bat / start.sh    # Startup scripts
├── stop.bat / stop.sh      # Shutdown scripts
├── CLAUDE.md               # Development log
└── README.md               # This file
```

## API

The app uses the [OpenDota API](https://docs.opendota.com/) to fetch match data.

## License

MIT
