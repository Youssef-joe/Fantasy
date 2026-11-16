"""
Inference pipeline for making predictions on future matches.
"""
import os
import sys
import joblib
import pandas as pd
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.database import SessionLocal
from backend import models

# Import from same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feature_engineering import engineer_features_for_player_fixture


def load_model_and_features(model_dir: str = None):
    """Load trained model and feature names."""
    if model_dir is None:
        model_dir = os.path.dirname(__file__)
    
    model_path = os.path.join(model_dir, 'model.joblib')
    features_path = os.path.join(model_dir, 'features.txt')
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}")
    
    model = joblib.load(model_path)
    
    if os.path.exists(features_path):
        with open(features_path, 'r') as f:
            features = [line.strip() for line in f.readlines()]
    else:
        features = None
    
    return model, features


POSITION_MAP = {1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD'}


def predict_gameweek(db: Session, gameweek: int = None, top_n: int = 20, include_injured: bool = False):
    """
    Predict player points for a gameweek.

    Args:
        db: Database session
        gameweek: Gameweek number. If None, uses the next gameweek according to
            FPL (bootstrap-static `is_next`).
        top_n: Number of top predictions to return (None = all players)
        include_injured: Include unavailable players in predictions

    Returns:
        tuple: (predictions list, injured_players list)

    Players with two fixtures in the gameweek (a double gameweek) get one row
    with the points of both fixtures added together.
    Errors are raised rather than swallowed, so callers never mistake a
    failure for an empty gameweek.
    """
    from season import load_season_info

    model, feature_names = load_model_and_features()

    if gameweek is None:
        gameweek = load_season_info()['next_gameweek']
        if gameweek is None:
            raise RuntimeError("FPL reports no upcoming gameweek (season finished?)")

    print(f"\nPredicting for Gameweek {gameweek}...")

    fixtures = db.query(models.Fixture).filter(models.Fixture.event == gameweek).all()
    if not fixtures:
        print(f"No fixtures found for gameweek {gameweek}")
        return [], []

    teams = {t.id: t for t in db.query(models.Team).all()}
    injuries = {i.player_id: i for i in db.query(models.InjuryStatus).all()}

    by_player = {}
    injured_players = {}

    for fixture in fixtures:
        home_players = db.query(models.Player).filter(models.Player.team_id == fixture.team_h).all()
        away_players = db.query(models.Player).filter(models.Player.team_id == fixture.team_a).all()

        fixture_players = (
            [(p, 1, fixture.team_a) for p in home_players]
            + [(p, 0, fixture.team_h) for p in away_players]
        )

        for player, is_home, opponent_id in fixture_players:
            team = teams.get(player.team_id)
            opponent = teams.get(opponent_id)
            injury = injuries.get(player.id)

            if injury and injury.is_injured and not include_injured:
                injured_players[player.id] = {
                    'player_id': player.id,
                    'player_name': f"{player.first_name} {player.second_name}",
                    'team': team.short_name if team else 'UNK',
                    'position': POSITION_MAP.get(player.position, 'UNK'),
                    'status': injury.injury_status_name,
                }
                continue

            historical_stats = db.query(models.PlayerStats).join(models.Fixture).filter(
                models.PlayerStats.player_id == player.id,
                models.Fixture.event < gameweek,  # only past matches
            ).order_by(models.Fixture.event).all()

            points_history = [s.total_points for s in historical_stats]
            minutes_history = [s.minutes for s in historical_stats]

            features = engineer_features_for_player_fixture(
                player.id, fixture.id, db, points_history, minutes_history
            )
            if features is None:
                continue

            X = pd.DataFrame([features])
            if feature_names:
                X = X[feature_names]
            predicted_points = max(0.0, float(model.predict(X)[0]))

            opp_label = opponent.short_name if opponent else 'UNK'
            venue = 'HOME' if is_home else 'AWAY'

            row = by_player.get(player.id)
            if row is None:
                by_player[player.id] = {
                    'player_id': player.id,
                    'player_name': f"{player.first_name} {player.second_name}",
                    'team': team.short_name if team else 'UNK',
                    'position': POSITION_MAP.get(player.position, 'UNK'),
                    'opponent': opp_label,
                    'is_home': venue,
                    'fixtures': [{'opponent': opp_label, 'is_home': venue, 'predicted_points': round(predicted_points, 2)}],
                    'predicted_points': predicted_points,
                    'avg_last_5': round(float(np.mean(points_history[-5:])), 2) if points_history else 0.0,
                    'status': injury.injury_status_name if injury else None,
                }
            else:
                # Double gameweek: add the second fixture to the same row
                row['fixtures'].append({'opponent': opp_label, 'is_home': venue, 'predicted_points': round(predicted_points, 2)})
                row['predicted_points'] += predicted_points
                row['opponent'] = ', '.join(f['opponent'] for f in row['fixtures'])
                row['is_home'] = '/'.join(f['is_home'] for f in row['fixtures'])

    predictions = list(by_player.values())
    for p in predictions:
        p['predicted_points'] = round(p['predicted_points'], 2)
    predictions.sort(key=lambda x: x['predicted_points'], reverse=True)

    if top_n is not None:
        predictions = predictions[:top_n]
    return predictions, list(injured_players.values())


def print_predictions(predictions, title: str = "PREDICTIONS"):
    """Pretty print predictions table."""
    if not predictions:
        print("No predictions available")
        return
    
    print("\n" + "=" * 100)
    print(f"{title:^100}")
    print("=" * 100)
    print(f"{'Player':<25} {'Team':<6} {'Opp':<6} {'Pos':<5} {'H/A':<4} {'Predicted':<12} {'Form':<8}")
    print("-" * 100)
    
    for p in predictions:
        print(f"{p['player_name']:<25} {p['team']:<6} {p['opponent']:<6} "
              f"{p['position']:<5} {p['is_home']:<4} {p['predicted_points']:<12.2f} {p['avg_last_5']:<8.2f}")
    
    print("=" * 100)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Make predictions for fantasy football')
    parser.add_argument('--gameweek', type=int, default=None,
                        help='Gameweek to predict (default: next gameweek)')
    parser.add_argument('--top', type=int, default=20,
                        help='Number of top predictions to show')
    parser.add_argument('--show-injured', action='store_true',
                        help='Show injured players')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        predictions, injured = predict_gameweek(db, gameweek=args.gameweek, top_n=args.top)
        print_predictions(predictions, f"TOP {args.top} PREDICTIONS FOR GAMEWEEK {args.gameweek or 'NEXT'}")
        
        if args.show_injured and injured:
            print("\n" + "=" * 100)
            print("INJURED/UNAVAILABLE PLAYERS")
            print("=" * 100)
            for inj in injured[:10]:
                print(f"  {inj['player_name']:<30} {inj['team']:<5} {inj['status'] or '':<15}")
            print("=" * 100)
    finally:
        db.close()
