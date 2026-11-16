"""
Sanity checks for the static prediction feed.

    python ml/validate_feed.py                       # checks latest.json + manifest.json
    python ml/validate_feed.py path/to/gw11.json     # checks specific files

Exits non-zero and lists every problem found.
"""
import json
import math
import os
import re
import sys

MIN_PREDICTIONS = 100  # a full gameweek has several hundred players
POSITIONS = {'GKP', 'DEF', 'MID', 'FWD'}
PREDICTION_FIELDS = {
    'player_id': int, 'player_name': str, 'web_name': str, 'team': str,
    'position': str, 'opponent': str, 'is_home': str,
    'predicted_points': (int, float), 'avg_last_5': (int, float),
}


def validate_feed(feed: dict) -> list:
    errors = []
    if not re.fullmatch(r'\d{4}-\d{2}', str(feed.get('season', ''))):
        errors.append(f"season should look like '2026-27', got {feed.get('season')!r}")
    gw = feed.get('gameweek')
    if not isinstance(gw, int) or not 1 <= gw <= 38:
        errors.append(f"gameweek should be 1-38, got {gw!r}")
    for key in ('deadline_time', 'generated_at'):
        if not feed.get(key):
            errors.append(f"missing {key}")

    preds = feed.get('predictions') or []
    if len(preds) < MIN_PREDICTIONS:
        errors.append(f"only {len(preds)} predictions (expected at least {MIN_PREDICTIONS})")

    seen = set()
    for i, p in enumerate(preds):
        where = f"predictions[{i}] ({p.get('player_name', '?')})"
        for field, typ in PREDICTION_FIELDS.items():
            if not isinstance(p.get(field), typ):
                errors.append(f"{where}: {field} missing or wrong type")
        pts = p.get('predicted_points')
        if isinstance(pts, (int, float)) and (math.isnan(pts) or not 0 <= pts <= 40):
            errors.append(f"{where}: predicted_points out of range: {pts}")
        if p.get('position') not in POSITIONS:
            errors.append(f"{where}: unknown position {p.get('position')!r}")
        if p.get('player_id') in seen:
            errors.append(f"{where}: duplicate player_id {p.get('player_id')}")
        seen.add(p.get('player_id'))
        if len(errors) > 25:
            errors.append("... too many errors, stopping")
            return errors

    points = [p.get('predicted_points', 0) for p in preds]
    if points != sorted(points, reverse=True):
        errors.append("predictions are not sorted by predicted_points (descending)")
    return errors


def validate_manifest(manifest: dict, predictions_dir: str) -> list:
    errors = []
    for gw in manifest.get('available_gameweeks', []):
        if not os.path.exists(os.path.join(predictions_dir, f"gw{gw}.json")):
            errors.append(f"manifest lists GW{gw} but gw{gw}.json does not exist")
    return errors


def main(paths):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pred_dir = os.path.join(root, 'frontend', 'data', 'predictions')
    if not paths:
        paths = [os.path.join(pred_dir, 'latest.json')]
        with open(os.path.join(pred_dir, 'manifest.json')) as f:
            manifest_errors = validate_manifest(json.load(f), pred_dir)
    else:
        manifest_errors = []

    failed = bool(manifest_errors)
    for e in manifest_errors:
        print(f"✗ manifest.json: {e}")
    for path in paths:
        with open(path) as f:
            errors = validate_feed(json.load(f))
        if errors:
            failed = True
            print(f"✗ {path}")
            for e in errors:
                print(f"    - {e}")
        else:
            print(f"✓ {path}")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
