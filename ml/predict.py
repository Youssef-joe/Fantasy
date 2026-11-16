"""
Predict points for an upcoming gameweek.

    python ml/predict.py                 # next gameweek according to FPL
    python ml/predict.py --gameweek 12 --top 30 --show-injured

Upcoming fixtures are appended to this season's match history as rows without an
outcome, and run through the same feature code used for training (dataset.py).
Predictions are then scaled by FPL's chance of playing (e.g. 75% for a doubtful
player); players ruled out (injured, suspended, unavailable or chance 0%) are
listed separately instead of predicted.
"""
import json
import os
import sys

import joblib
import numpy as np
import pandas as pd

ML_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ML_DIR)
import dataset as ds  # noqa: E402
from season import load_season_info  # noqa: E402

RULED_OUT = {'i': 'Injured', 's': 'Suspended', 'u': 'Unavailable', 'n': 'Not eligible'}


def load_model():
    path = os.path.join(ML_DIR, 'model.joblib')
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found. Run `python ml/train.py` first.")
    bundle = joblib.load(path)
    return bundle['model'], bundle['features']


def _upcoming_rows(bootstrap: dict, fixtures: list, gameweek: int, season: str) -> pd.DataFrame:
    players_by_team = {}
    for el in bootstrap['elements']:
        if el['element_type'] in ds.POSITION_BY_TYPE:
            players_by_team.setdefault(el['team'], []).append(el)
    rows = []
    for fx in fixtures:
        if fx.get('event') != gameweek:
            continue
        for team, opp, home, fdr in ((fx['team_h'], fx['team_a'], True, fx['team_h_difficulty']),
                                     (fx['team_a'], fx['team_h'], False, fx['team_a_difficulty'])):
            for el in players_by_team.get(team, []):
                rows.append({
                    'season': season, 'element': el['id'], 'position': ds.POSITION_BY_TYPE[el['element_type']],
                    'round': gameweek, 'fixture': fx['id'], 'kickoff_time': fx['kickoff_time'],
                    'was_home': home, 'team': team, 'opponent': opp, 'fdr': fdr,
                    'value': el['now_cost'],
                })
    df = pd.DataFrame(rows)
    df['kickoff_time'] = pd.to_datetime(df['kickoff_time'], utc=True)
    return df


def predict_gameweek(gameweek: int = None, top_n: int = 20):
    """
    Returns (predictions, injured_players). Predictions are one row per player
    (double-gameweek fixtures added together), sorted by predicted points;
    top_n=None returns every player.
    """
    info = load_season_info()
    if gameweek is None:
        gameweek = info['next_gameweek']
        if gameweek is None:
            raise RuntimeError("FPL reports no upcoming gameweek (season finished?)")

    with open(os.path.join(ds.RAW_DIR, 'bootstrap_static.json')) as f:
        bootstrap = json.load(f)
    with open(os.path.join(ds.RAW_DIR, 'fixtures.json')) as f:
        fixtures = json.load(f)

    model, features = load_model()
    history = ds.load_current_season()
    history = history[history['round'] < gameweek]
    upcoming = _upcoming_rows(bootstrap, fixtures, gameweek, info['season'])
    if upcoming.empty:
        print(f"No fixtures found for gameweek {gameweek}")
        return [], []

    df = ds.add_features(pd.concat([history, upcoming], ignore_index=True))
    rows = df[df['total_points'].isna() & (df['round'] == gameweek)].copy()
    rows['predicted'] = np.clip(model.predict(rows[features]), 0, None)

    elements = {el['id']: el for el in bootstrap['elements']}
    teams = {t['id']: t['short_name'] for t in bootstrap['teams']}
    last5 = (history.sort_values('kickoff_time').groupby('element')['total_points']
             .apply(lambda s: round(float(s.tail(5).mean()), 2)).to_dict())

    predictions, injured = {}, {}
    for r in rows.sort_values('kickoff_time').itertuples():
        el = elements[r.element]
        name = f"{el['first_name']} {el['second_name']}"
        chance = el.get('chance_of_playing_next_round')
        if el['status'] in RULED_OUT or chance == 0:
            injured[r.element] = {'player_id': r.element, 'player_name': name, 'team': teams.get(el['team'], 'UNK'),
                                  'position': r.position, 'status': RULED_OUT.get(el['status'], 'Unavailable')}
            continue
        points = float(r.predicted) * (chance / 100 if chance is not None else 1.0)
        fixture = {'opponent': teams.get(int(r.opponent), 'UNK'), 'is_home': 'HOME' if r.was_home else 'AWAY',
                   'predicted_points': round(points, 2)}
        p = predictions.get(r.element)
        if p is None:
            predictions[r.element] = {
                'player_id': r.element, 'player_name': name, 'team': teams.get(el['team'], 'UNK'),
                'position': r.position, 'opponent': fixture['opponent'], 'is_home': fixture['is_home'],
                'fixtures': [fixture], 'predicted_points': points,
                'avg_last_5': last5.get(r.element, 0.0),
                'status': 'Doubtful' if el['status'] == 'd' else None,
            }
        else:  # double gameweek
            p['fixtures'].append(fixture)
            p['predicted_points'] += points
            p['opponent'] = ', '.join(f['opponent'] for f in p['fixtures'])
            p['is_home'] = '/'.join(f['is_home'] for f in p['fixtures'])

    out = sorted(predictions.values(), key=lambda p: p['predicted_points'], reverse=True)
    for p in out:
        p['predicted_points'] = round(p['predicted_points'], 2)
    return (out if top_n is None else out[:top_n]), list(injured.values())


def print_predictions(predictions, title):
    print("\n" + "=" * 92)
    print(f"{title:^92}")
    print("=" * 92)
    print(f"{'Player':<28} {'Team':<5} {'Pos':<4} {'Opponent':<14} {'Predicted':>9} {'Last 5':>8}")
    print("-" * 92)
    for p in predictions:
        print(f"{p['player_name'][:27]:<28} {p['team']:<5} {p['position']:<4} {p['opponent'][:13]:<14} "
              f"{p['predicted_points']:>9.2f} {p['avg_last_5']:>8.2f}")
    print("=" * 92)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Predict fantasy points for a gameweek')
    parser.add_argument('--gameweek', type=int, default=None, help='Gameweek (default: next gameweek)')
    parser.add_argument('--top', type=int, default=20, help='Number of players to show')
    parser.add_argument('--show-injured', action='store_true', help='List ruled-out players')
    args = parser.parse_args()

    preds, ruled_out = predict_gameweek(args.gameweek, top_n=args.top)
    print_predictions(preds, f"TOP {args.top} PREDICTIONS FOR GAMEWEEK {args.gameweek or 'NEXT'}")
    if args.show_injured and ruled_out:
        print("\nRULED OUT")
        for p in ruled_out[:20]:
            print(f"  {p['player_name']:<30} {p['team']:<5} {p['status']}")
