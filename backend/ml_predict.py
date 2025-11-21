import os
import joblib
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import SessionLocal, engine
from . import models, schemas, crud

def get_team_strength_map():
    # Hardcoded for now or load from JSON if needed. 
    # Since we don't have easy access to JSON here without importing from features.py or duplicating code.
    # Let's just default to 3 for now to keep it simple, or try to load.
    return {} # defaulting to 3 in logic

def get_predictions(db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
        
    try:
        model_path = os.path.join(os.path.dirname(__file__), 'model.joblib')
        if not os.path.exists(model_path):
            return []

        model = joblib.load(model_path)
        
        # Determine next gameweek
        max_event = db.query(func.max(models.Fixture.event)).join(
            models.PlayerStats, models.Fixture.id == models.PlayerStats.fixture_id
        ).scalar()
        
        if max_event is None:
            next_event = 1
        else:
            next_event = max_event + 1
            
        # Get fixtures for next event
        fixtures = db.query(models.Fixture).filter(models.Fixture.event == next_event).all()
        
        if not fixtures:
            return []
            
        predictions = []
        
        for fixture in fixtures:
            # Get players for home team
            home_players = db.query(models.Player).filter(models.Player.team_id == fixture.team_h).all()
            # Get players for away team
            away_players = db.query(models.Player).filter(models.Player.team_id == fixture.team_a).all()
            
            all_players = [(p, 1, fixture.team_a) for p in home_players] + \
                          [(p, 0, fixture.team_h) for p in away_players]
            
            for player, is_home, opponent_id in all_players:
                # Calculate features based on history
                stats = db.query(models.PlayerStats).join(models.Fixture).filter(
                    models.PlayerStats.player_id == player.id
                ).order_by(models.Fixture.event).all()
                
                points_history = [s.total_points for s in stats]
                minutes_history = [s.minutes for s in stats]
                
                avg_points_last_5 = np.mean(points_history[-5:]) if points_history else 0
                minutes_consistency = np.std(minutes_history[-5:]) if len(minutes_history) > 1 else 0
                form = avg_points_last_5
                opponent_difficulty = 3 # Default
                
                features = pd.DataFrame([{
                    'avg_points_last_5': avg_points_last_5,
                    'form': form,
                    'opponent_difficulty': opponent_difficulty,
                    'is_home': is_home,
                    'minutes_consistency': minutes_consistency
                }])
                
                predicted_points = model.predict(features)[0]
                
                predictions.append({
                    'player_id': player.id,
                    'player_name': f"{player.first_name} {player.second_name}",
                    'team_id': player.team_id,
                    'position': player.position,
                    'predicted_points': float(predicted_points)
                })
        
        # Sort by predicted points
        predictions.sort(key=lambda x: x['predicted_points'], reverse=True)
        return predictions

    except Exception as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        if close_db:
            db.close()

def predict_next_gameweek():
    predictions = get_predictions()
    print("\nTop 20 Predicted Players:")
    print(f"{'Player':<30} {'Pos':<5} {'Points':<10}")
    print("-" * 50)
    for p in predictions[:20]:
        print(f"{p['player_name']:<30} {p['position']:<5} {p['predicted_points']:.2f}")

if __name__ == "__main__":
    predict_next_gameweek()
