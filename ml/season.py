"""
Season and gameweek information taken from the scraped FPL bootstrap data,
so nothing about the season is hardcoded.
"""
import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, 'data', 'raw')


def load_bootstrap(raw_dir: str = RAW_DIR) -> dict:
    path = os.path.join(raw_dir, 'bootstrap_static.json')
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found. Run `python scraper/main.py` first.")
    with open(path) as f:
        return json.load(f)


def season_label(events: list) -> str:
    """'2026-27' from the first gameweek deadline (seasons start in August)."""
    start_year = int(events[0]['deadline_time'][:4])
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def load_season_info(raw_dir: str = RAW_DIR) -> dict:
    """
    Returns:
        dict with season, current_gameweek, next_gameweek and the next
        gameweek's deadline_time (ISO 8601, UTC). next_gameweek is None once
        the season is over.
    """
    events = load_bootstrap(raw_dir)['events']
    current = next((e for e in events if e.get('is_current')), None)
    upcoming = next((e for e in events if e.get('is_next')), None)
    return {
        'season': season_label(events),
        'current_gameweek': current['id'] if current else None,
        'next_gameweek': upcoming['id'] if upcoming else None,
        'deadline_time': upcoming['deadline_time'] if upcoming else None,
    }
