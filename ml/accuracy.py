"""
Score published predictions against what actually happened.

    python ml/accuracy.py

For every frontend/data/predictions/gwNN.json of the current season whose gameweek
FPL has finished, compares the published predictions (frozen at the deadline) with
the points players actually scored, from data/raw/player_<id>.json. Also carries the
by-gameweek backtest from ml/metrics.json, so the site has something honest to show
before the first live gameweek is scored.

Writes frontend/data/predictions/accuracy.json.
"""
import glob
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

ML_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ML_DIR)
RAW_DIR = os.path.join(ROOT, 'data', 'raw')
PRED_DIR = os.path.join(ROOT, 'frontend', 'data', 'predictions')
TOP_N = 20
SHOW_N = 10


def actual_points(raw_dir: str = RAW_DIR) -> dict:
    """{(player_id, gameweek): points}, double gameweeks summed"""
    out = {}
    for path in glob.glob(os.path.join(raw_dir, 'player_*.json')):
        pid = int(os.path.basename(path)[7:-5])
        with open(path) as f:
            for h in json.load(f).get('history', []):
                key = (pid, h['round'])
                out[key] = out.get(key, 0) + h['total_points']
    return out


def finished_gameweeks(raw_dir: str = RAW_DIR) -> set:
    with open(os.path.join(raw_dir, 'bootstrap_static.json')) as f:
        events = json.load(f)['events']
    # data_checked: FPL has confirmed final points, including bonus
    return {e['id'] for e in events if e.get('finished') and e.get('data_checked')}


def score_feed(feed: dict, actual: dict) -> dict:
    gw = feed['gameweek']
    preds = feed['predictions']
    pred = np.array([p['predicted_points'] for p in preds])
    base = np.array([p.get('avg_last_5') or 0 for p in preds])
    act = np.array([actual.get((p['player_id'], gw), 0) for p in preds])

    def top(scores):
        return float(act[np.argsort(-scores, kind='stable')[:TOP_N]].mean())

    captain = preds[0]
    return {
        'gameweek': gw,
        'n': len(preds),
        'mae': round(float(np.abs(pred - act).mean()), 3),
        'baseline_mae': round(float(np.abs(base - act).mean()), 3),
        'top20_avg_points': round(top(pred), 2),
        'baseline_top20_avg_points': round(top(base), 2),
        'oracle_top20_avg_points': round(float(np.sort(act)[-TOP_N:].mean()), 2),
        'captain': {
            'player_id': captain['player_id'], 'web_name': captain.get('web_name', captain['player_name']),
            'team': captain['team'], 'predicted': captain['predicted_points'],
            'actual': int(actual.get((captain['player_id'], gw), 0)),
        },
        'top_predicted': [
            {'player_id': p['player_id'], 'web_name': p.get('web_name', p['player_name']), 'team': p['team'],
             'position': p['position'], 'predicted': p['predicted_points'],
             'actual': int(actual.get((p['player_id'], gw), 0))}
            for p in preds[:SHOW_N]
        ],
    }


def build(pred_dir: str = PRED_DIR, raw_dir: str = RAW_DIR, metrics_path: str = os.path.join(ML_DIR, 'metrics.json')) -> dict:
    sys.path.insert(0, ML_DIR)
    from season import load_season_info
    season = load_season_info(raw_dir)['season']
    done = finished_gameweeks(raw_dir)
    actual = actual_points(raw_dir)

    live = []
    for path in sorted(glob.glob(os.path.join(pred_dir, 'gw*.json'))):
        with open(path) as f:
            feed = json.load(f)
        if feed.get('season') == season and feed.get('gameweek') in done:
            live.append(score_feed(feed, actual))
    live.sort(key=lambda r: r['gameweek'])

    backtest = []
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            m = json.load(f)
        for r in m.get('per_gameweek', []):
            backtest.append({
                'gameweek': r['gameweek'], 'n': r['n'],
                'mae': r['mae'], 'baseline_mae': r['base_mae'],
                'top20_avg_points': r['top'], 'baseline_top20_avg_points': r['base_top'],
                'oracle_top20_avg_points': r['oracle_top'],
            })

    def summary(rows):
        if not rows:
            return None
        return {
            'gameweeks': len(rows),
            'top20_avg_points': round(float(np.mean([r['top20_avg_points'] for r in rows])), 2),
            'baseline_top20_avg_points': round(float(np.mean([r['baseline_top20_avg_points'] for r in rows])), 2),
            'oracle_top20_avg_points': round(float(np.mean([r['oracle_top20_avg_points'] for r in rows])), 2),
            'mae': round(float(np.mean([r['mae'] for r in rows])), 3),
            'baseline_mae': round(float(np.mean([r['baseline_mae'] for r in rows])), 3),
        }

    return {
        'season': season,
        'updated_at': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'top_n': TOP_N,
        'live': live,
        'live_summary': summary(live),
        'backtest': backtest,
        'backtest_summary': summary(backtest),
    }


def main():
    report = build()
    path = os.path.join(PRED_DIR, 'accuracy.json')
    with open(path + '.tmp', 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    os.replace(path + '.tmp', path)
    live = ', '.join(f"GW{r['gameweek']}" for r in report['live']) or 'none yet'
    print(f"✓ accuracy.json: live gameweeks scored: {live}; backtest gameweeks: {len(report['backtest'])}")


if __name__ == '__main__':
    main()
