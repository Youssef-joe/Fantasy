"""
Export ML predictions to the static JSON feed served by the site
(frontend/data/predictions/).

    python ml/export_predictions.py          # next gameweek according to FPL
    python ml/export_predictions.py 12       # a specific gameweek

Writes gwNN.json, latest.json and manifest.json. The feed is checked before
anything is written, and the script exits non-zero instead of writing
placeholder data, so a broken run never replaces the last good feed.
"""
import glob
import json
import os
import sys
from datetime import datetime, timezone

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "frontend", "data", "predictions")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
FEED_VERSION = 2
FIXTURES_AHEAD = 5
BUDGET = 100.0     # FPL starting budget, £m
HORIZON = 3        # gameweeks for the planning squad

sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, CURRENT_DIR)

from season import load_bootstrap, load_season_info  # noqa: E402
from validate_feed import validate_feed  # noqa: E402

STATUS_LABELS = {
    'd': 'Doubtful',
    'i': 'Injured',
    's': 'Suspended',
    'u': 'Unavailable',
    'n': 'Not eligible',
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def load_metrics():
    path = os.path.join(CURRENT_DIR, 'metrics.json')
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def fixtures_by_team(bootstrap: dict, from_gameweek: int) -> dict:
    """Next FIXTURES_AHEAD gameweeks of fixtures per team, with FPL difficulty (1-5)."""
    with open(os.path.join(RAW_DIR, 'fixtures.json')) as f:
        fixtures = json.load(f)
    short = {t['id']: t['short_name'] for t in bootstrap['teams']}
    last_gw = from_gameweek + FIXTURES_AHEAD - 1
    out = {name: [] for name in short.values()}
    for fx in sorted(fixtures, key=lambda x: (x['event'] or 99, x['kickoff_time'] or '')):
        gw = fx.get('event')
        if gw is None or not (from_gameweek <= gw <= last_gw):
            continue
        h, a = fx['team_h'], fx['team_a']
        out[short[h]].append({'gameweek': gw, 'opponent': short[a], 'is_home': True,
                              'difficulty': fx['team_h_difficulty'], 'kickoff_time': fx['kickoff_time']})
        out[short[a]].append({'gameweek': gw, 'opponent': short[h], 'is_home': False,
                              'difficulty': fx['team_a_difficulty'], 'kickoff_time': fx['kickoff_time']})
    return out


def enrich(predictions: list, elements: dict) -> list:
    """Add price, ownership and availability from FPL to each prediction."""
    for p in predictions:
        el = elements.get(p['player_id'], {})
        p['web_name'] = el.get('web_name', p['player_name'])
        p['price'] = el['now_cost'] / 10 if 'now_cost' in el else None
        p['selected_by_percent'] = float(el['selected_by_percent']) if el.get('selected_by_percent') else None
        p['chance_of_playing'] = el.get('chance_of_playing_next_round')
        p['news'] = el.get('news') or None
    return predictions


def unavailable_players(bootstrap: dict) -> list:
    """Flagged players who have played this season, straight from FPL status/news."""
    short = {t['id']: t['short_name'] for t in bootstrap['teams']}
    positions = {1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    owned = {el['id']: float(el.get('selected_by_percent') or 0) for el in bootstrap['elements']}
    out = []
    for el in bootstrap['elements']:
        if el['status'] == 'a' or el.get('minutes', 0) == 0:
            continue
        out.append({
            'player_id': el['id'],
            'player_name': f"{el['first_name']} {el['second_name']}",
            'web_name': el['web_name'],
            'team': short.get(el['team'], 'UNK'),
            'position': positions.get(el['element_type'], 'UNK'),
            'status': STATUS_LABELS.get(el['status'], 'Unavailable'),
            'chance_of_playing': el.get('chance_of_playing_next_round'),
            'news': el.get('news') or None,
            'return_date': el.get('news_return_date'),
        })
    # Most-owned first: those are the ones managers care about
    out.sort(key=lambda x: owned.get(x['player_id'], 0), reverse=True)
    return out


def write_json(path: str, data: dict):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def build_manifest(season: str, latest_gameweek: int, deadline_time: str) -> dict:
    """List the gameweek files that belong to the current season."""
    gameweeks = []
    for path in glob.glob(os.path.join(OUTPUT_DIR, 'gw*.json')):
        try:
            with open(path) as f:
                feed = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if feed.get('season') == season and isinstance(feed.get('gameweek'), int):
            gameweeks.append(feed['gameweek'])
    return {
        'feed_version': FEED_VERSION,
        'season': season,
        'latest_gameweek': latest_gameweek,
        'available_gameweeks': sorted(set(gameweeks)),
        'deadline_time': deadline_time,
        'updated_at': utc_now(),
    }


def build_squads(feed: dict, predict_gameweek, budget: float = BUDGET) -> dict:
    """
    Best legal squads for the budget: one for the coming gameweek, one for the
    next HORIZON gameweeks added together (better for planning, since transfers
    are limited). Prices are today's.
    """
    from squad import best_squad

    gw = feed['gameweek']
    by_id = {p['player_id']: p for p in feed['predictions']}
    horizon_gws = [g for g in range(gw, gw + HORIZON) if g <= 38]
    totals = {pid: p['predicted_points'] for pid, p in by_id.items()}
    for g in horizon_gws[1:]:
        later, _ = predict_gameweek(g, top_n=None)
        for p in later:
            if p['player_id'] in totals:
                totals[p['player_id']] += p['predicted_points']

    horizons = []
    for key, label, gws, points in (
        ('gw', f"GW{gw}", [gw], {pid: p['predicted_points'] for pid, p in by_id.items()}),
        ('multi', f"GW{horizon_gws[0]}–{horizon_gws[-1]}", horizon_gws, totals),
    ):
        if key == 'multi' and len(gws) < 2:
            continue
        pool = [dict(p, points=points[pid]) for pid, p in by_id.items()]
        sq = best_squad(pool, budget=budget)
        sq.update({
            'key': key, 'label': label, 'gameweeks': gws,
            'players': {
                str(pid): {'web_name': by_id[pid]['web_name'], 'team': by_id[pid]['team'],
                           'position': by_id[pid]['position'], 'price': by_id[pid]['price'],
                           'points': round(points[pid], 2), 'points_this_gw': by_id[pid]['predicted_points']}
                for pid in sq['squad']
            },
        })
        horizons.append(sq)
    return {'season': feed['season'], 'gameweek': gw, 'budget': budget,
            'generated_at': feed['generated_at'], 'horizons': horizons}


def export_predictions_for_gameweek(gameweek: int = None):
    from predict import predict_gameweek

    bootstrap = load_bootstrap()
    info = load_season_info()
    if gameweek is None:
        gameweek = info['next_gameweek']
        if gameweek is None:
            raise RuntimeError("FPL reports no upcoming gameweek (season finished?)")

    events = {e['id']: e for e in bootstrap['events']}
    if gameweek not in events:
        raise ValueError(f"GW{gameweek} is not a gameweek of the {info['season']} season")

    predictions, _ = predict_gameweek(gameweek, top_n=None)

    if not predictions:
        raise RuntimeError(
            f"No predictions produced for GW{gameweek}; refusing to overwrite the feed. "
            "Check that data/raw is scraped and the model is trained."
        )
    print(f"✓ Retrieved {len(predictions)} predictions from ML model for GW{gameweek}")

    elements = {el['id']: el for el in bootstrap['elements']}
    feed = {
        'feed_version': FEED_VERSION,
        'season': info['season'],
        'gameweek': gameweek,
        'deadline_time': events[gameweek]['deadline_time'],
        'generated_at': utc_now(),
        'data_source': 'FPL API',
        'model': load_metrics(),
        'predictions': enrich(predictions, elements),
        'injured_players': unavailable_players(bootstrap),
        'fixtures_by_team': fixtures_by_team(bootstrap, gameweek),
    }

    errors = validate_feed(feed)
    if errors:
        raise RuntimeError("Feed failed validation; nothing written:\n  - " + "\n  - ".join(errors))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(OUTPUT_DIR, f"gw{gameweek}.json")
    write_json(out_file, feed)
    if gameweek == info['next_gameweek']:
        write_json(os.path.join(OUTPUT_DIR, 'latest.json'), feed)
        squads = build_squads(feed, predict_gameweek)
        write_json(os.path.join(OUTPUT_DIR, 'squad.json'), squads)
        for h in squads['horizons']:
            print(f"✓ £{squads['budget']}m squad for {h['label']}: {h['formation']}, "
                  f"£{h['cost']}m, {h['points']} predicted pts")
    latest = info['next_gameweek'] or gameweek
    write_json(os.path.join(OUTPUT_DIR, 'manifest.json'),
               build_manifest(info['season'], latest, info['deadline_time']))
    print(f"✓ Exported {len(predictions)} predictions to {out_file} (season {info['season']})")


if __name__ == "__main__":
    export_predictions_for_gameweek(int(sys.argv[1]) if len(sys.argv) > 1 else None)
