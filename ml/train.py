"""
Train the points model and measure it honestly.

    python ml/train.py

1. Builds player-match rows from this season (data/raw) plus any past seasons in
   data/raw/history (see scraper/history.py), with features from dataset.py.
2. Evaluates by gameweek: for each of the last few finished gameweeks of this
   season, trains only on matches played before it and predicts it. Reports average
   error, rank correlation and the average points of the top-20 predicted players,
   next to the same numbers for a simple baseline (average of the last 5 matches).
3. Fits the final model on every match with a known outcome and saves it to
   ml/model.joblib, with the metrics in ml/metrics.json.
"""
import json
import os
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dataset as ds  # noqa: E402

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
EVAL_GAMEWEEKS = 5   # how many recent finished gameweeks to test on
MIN_TRAIN_GAMEWEEKS = 3
TOP_N = 20


def make_model():
    # Poisson loss suits non-negative, count-like points (negative points are clipped to 0 for training).
    return HistGradientBoostingRegressor(
        loss='poisson', max_iter=400, learning_rate=0.05, max_leaf_nodes=31,
        min_samples_leaf=40, l2_regularization=1.0, random_state=42,
    )


def load_all():
    cur = ds.load_current_season()
    seasons = ds.available_past_seasons()
    frames = [cur] + [ds.load_past_season(s) for s in seasons]
    df = ds.add_features(pd.concat(frames, ignore_index=True))
    return df, cur['season'].iloc[0], seasons


def evaluation_rounds(df, season):
    """Recent finished gameweeks of this season, leaving a few earlier ones for training."""
    rounds = sorted(df.loc[df['season'] == season, 'round'].dropna().unique().astype(int))
    usable = [int(r) for r in rounds if r > MIN_TRAIN_GAMEWEEKS]
    return usable[-EVAL_GAMEWEEKS:]


def evaluate(df, season, rounds):
    per_round = []
    for r in rounds:
        is_cur = df['season'] == season
        train = df[~(is_cur & (df['round'] >= r))]
        test = df[is_cur & (df['round'] == r)]
        model = make_model().fit(train[ds.FEATURES], train['total_points'].clip(lower=0))
        pred = model.predict(test[ds.FEATURES])
        base = ds.baseline(test).to_numpy()
        actual = test['total_points'].to_numpy()
        per_round.append({
            'gameweek': int(r), 'n': len(test),
            'mae': float(np.abs(pred - actual).mean()),
            'base_mae': float(np.abs(base - actual).mean()),
            'spearman': float(spearmanr(actual, pred).correlation),
            'base_spearman': float(spearmanr(actual, base).correlation),
            'top': float(actual[np.argsort(-pred)[:TOP_N]].mean()),
            'base_top': float(actual[np.argsort(-base)[:TOP_N]].mean()),
            'oracle_top': float(np.sort(actual)[-TOP_N:].mean()),
        })
        print(f"  GW{r}: MAE {per_round[-1]['mae']:.3f} (baseline {per_round[-1]['base_mae']:.3f}), "
              f"top-{TOP_N} avg {per_round[-1]['top']:.2f} pts (baseline {per_round[-1]['base_top']:.2f})")
    return per_round


def weighted(per_round, key):
    n = np.array([r['n'] for r in per_round])
    return float(np.average([r[key] for r in per_round], weights=n))


def main():
    print("=" * 60)
    print("FANTASY FOOTBALL MODEL TRAINING")
    print("=" * 60)

    df, season, past = load_all()
    known = df.dropna(subset=['total_points'])
    print(f"Rows: {len(known):,} ({season} + past seasons: {', '.join(past) or 'none'})")

    rounds = evaluation_rounds(known, season)
    metrics = {'split': 'by gameweek', 'test_gameweeks': rounds, 'seasons_used': [season, *past]}
    if rounds:
        print(f"\nEvaluating on GW{rounds[0]}-{rounds[-1]} of {season}, training only on earlier matches each time:")
        per_round = evaluate(known, season, rounds)
        metrics.update({
            'n_test': int(sum(r['n'] for r in per_round)),
            'test_mae': round(weighted(per_round, 'mae'), 3),
            'baseline_mae_avg_last_5': round(weighted(per_round, 'base_mae'), 3),
            'test_spearman': round(float(np.mean([r['spearman'] for r in per_round])), 3),
            'baseline_spearman': round(float(np.mean([r['base_spearman'] for r in per_round])), 3),
            'top20_avg_points': round(float(np.mean([r['top'] for r in per_round])), 2),
            'baseline_top20_avg_points': round(float(np.mean([r['base_top'] for r in per_round])), 2),
            'oracle_top20_avg_points': round(float(np.mean([r['oracle_top'] for r in per_round])), 2),
            'per_gameweek': [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()} for r in per_round],
        })
        print(f"\nOverall: MAE {metrics['test_mae']} vs baseline {metrics['baseline_mae_avg_last_5']}; "
              f"top-{TOP_N} {metrics['top20_avg_points']} vs {metrics['baseline_top20_avg_points']} pts "
              f"(best possible {metrics['oracle_top20_avg_points']})")
    else:
        print("\nNot enough finished gameweeks this season to evaluate yet; skipping evaluation.")

    print("\nFitting final model on all matches...")
    model = make_model().fit(known[ds.FEATURES], known['total_points'].clip(lower=0))
    joblib.dump({'model': model, 'features': ds.FEATURES}, os.path.join(MODEL_DIR, 'model.joblib'))

    metrics.update({
        'model_type': 'HistGradientBoostingRegressor',
        'loss': 'poisson',
        'n_features': len(ds.FEATURES),
        'n_train': int(len(known)),
        'trained_at': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
    })
    path = os.path.join(MODEL_DIR, 'metrics.json')
    with open(path + '.tmp', 'w') as f:
        json.dump(metrics, f, indent=2)
    os.replace(path + '.tmp', path)
    print(f"✓ Saved ml/model.joblib and ml/metrics.json ({len(known):,} training rows, {len(ds.FEATURES)} features)")


if __name__ == '__main__':
    main()
