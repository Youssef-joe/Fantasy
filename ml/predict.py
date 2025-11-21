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
import os
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)
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


def predict_gameweek(db: Session, gameweek: int = None, top_n: int = 20, include_injured: bool = False):
    """
    Predict player points for a specific gameweek (or next upcoming).
    
    Args:
        db: Database session
        gameweek: Gameweek number (if None, predicts next gameweek)
        top_n: Number of top predictions to return
        include_injured: Include injured players in predictions
    
    Returns:
        tuple: (predictions list, injured_players list)
    """
    try:
        model, feature_names = load_model_and_features()
        
        # Determine gameweek to predict
        if gameweek is None:
            max_event = db.query(func.max(models.Fixture.event)).scalar()
            gameweek = (max_event or 0) + 1
        
        print(f"\nPredicting for Gameweek {gameweek}...")
        
        # Get fixtures for this gameweek
        fixtures = db.query(models.Fixture).filter(
            models.Fixture.event == gameweek
        ).all()
        
        if not fixtures:
            print(f"No fixtures found for gameweek {gameweek}")
            return [], []
        
        predictions = []
        injured_players = []
        
        for fixture in fixtures:
            # Get all players from both teams
            home_players = db.query(models.Player).filter(
                models.Player.team_id == fixture.team_h
            ).all()
            away_players = db.query(models.Player).filter(
                models.Player.team_id == fixture.team_a
            ).all()
            
            all_fixture_players = [
                (p, 1, fixture.team_a, fixture) for p in home_players
            ] + [
                (p, 0, fixture.team_h, fixture) for p in away_players
            ]
            
            for player, is_home, opponent_id, fixture in all_fixture_players:
                # Check injury status
                injury = db.query(models.InjuryStatus).filter(
                    models.InjuryStatus.player_id == player.id
                ).first()
                
                if injury and injury.is_injured:
                    if not include_injured:
                        injured_players.append({
                            'player_id': player.id,
                            'player_name': f"{player.first_name} {player.second_name}",
                            'status': injury.injury_status_name,
                            'expected_return': injury.expected_return
                        })
                        continue
                # Get player's historical stats
                historical_stats = db.query(models.PlayerStats).join(
                    models.Fixture
                ).filter(
                    models.PlayerStats.player_id == player.id,
                    models.Fixture.event < gameweek  # Only past matches
                ).order_by(models.Fixture.event).all()
                
                points_history = [s.total_points for s in historical_stats]
                minutes_history = [s.minutes for s in historical_stats]
                
                # Engineer features
                features = engineer_features_for_player_fixture(
                    player.id,
                    fixture.id,
                    db,
                    points_history,
                    minutes_history
                )
                
                if features is None:
                    continue
                
                # Prepare feature vector
                feature_dict = {k: v for k, v in features.items()}
                
                # Ensure features are in correct order
                if feature_names:
                    X = pd.DataFrame([feature_dict])[feature_names]
                else:
                    X = pd.DataFrame([feature_dict])
                
                # Make prediction
                predicted_points = float(model.predict(X)[0])
                
                # Ensure non-negative predictions
                predicted_points = max(0, predicted_points)
                
                # Get team info
                team = db.query(models.Team).filter(
                    models.Team.id == player.team_id
                ).first()
                opponent = db.query(models.Team).filter(
                    models.Team.id == opponent_id
                ).first()
                
                position_map = {1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD'}
                
                predictions.append({
                    'player_id': player.id,
                    'player_name': f"{player.first_name} {player.second_name}",
                    'team': team.short_name if team else 'UNK',
                    'opponent': opponent.short_name if opponent else 'UNK',
                    'position': position_map.get(player.position, 'UNK'),
                    'is_home': 'HOME' if is_home else 'AWAY',
                    'predicted_points': predicted_points,
                    'avg_last_5': round(np.mean(points_history[-5:]), 2) if points_history else 0,
                    'injury_status': None  # No injury
                })
        
        # Sort by predicted points
        predictions.sort(key=lambda x: x['predicted_points'], reverse=True)
        
        return predictions[:top_n], injured_players
    
    except Exception as e:
        print(f"Error during prediction: {e}")
        import traceback
        traceback.print_exc()
        return [], []


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
                print(f"  {inj['player_name']:<30} {inj['status']:<15} (Return: GW{inj['expected_return']})")
            print("=" * 100)
    finally:
        db.close()
