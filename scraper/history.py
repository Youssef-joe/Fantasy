"""
Download past seasons' gameweek data for training, from the community dataset
https://github.com/vaastav/Fantasy-Premier-League (MIT licence; the underlying data
belongs to Fantasy Premier League).

    python scraper/history.py            # the 3 seasons before the current one
    python scraper/history.py 2          # the 2 seasons before the current one

Files go to data/raw/history/<season>/{merged_gw.csv,fixtures.csv}. Seasons already
downloaded are skipped, since finished seasons never change.
"""
import json
import logging
import os
import sys

import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, 'data', 'raw')
HISTORY_DIR = os.path.join(RAW_DIR, 'history')
BASE_URL = 'https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data'
FILES = {'merged_gw.csv': 'gws/merged_gw.csv', 'fixtures.csv': 'fixtures.csv'}


def current_season_start() -> int:
    with open(os.path.join(RAW_DIR, 'bootstrap_static.json')) as f:
        return int(json.load(f)['events'][0]['deadline_time'][:4])


def past_seasons(n: int) -> list:
    start = current_season_start()
    return [f"{y}-{str(y + 1)[-2:]}" for y in range(start - n, start)]


def download(season: str):
    target = os.path.join(HISTORY_DIR, season)
    os.makedirs(target, exist_ok=True)
    for name, path in FILES.items():
        dest = os.path.join(target, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            logger.info(f"{season}/{name}: already downloaded")
            continue
        url = f"{BASE_URL}/{season}/{path}"
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        tmp = dest + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(resp.content)
        os.replace(tmp, dest)
        logger.info(f"{season}/{name}: {len(resp.content) / 1e6:.1f} MB")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    for season in past_seasons(n):
        download(season)


if __name__ == '__main__':
    main()
