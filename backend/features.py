import os
import json
import numpy as np
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models, schemas, crud

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw')

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'r') as f:
        return json.load(f)

def get_team_strength_map():
    # Load bootstrap static to get team strengths
    try:
        data = load_json('bootstrap_static.json')
        teams = data.get('teams', [])
        # Map team ID to strength (using 'strength' field from API, usually 1-5)
        # If not available, default to 3
        return {t['id']: t.get('strength', 3) for t in teams}
    except Exception as e:
        print(f"Could not load team strengths: {e}")
        return {}

def calculate_features():
    db = SessionLocal()
    try:
        print("Starting Feature Engineering...")
        
        team_strengths = get_team_strength_map()
        
        # Fetch all players
        players = db.query(models.Player).all()
        
        for player in players:
            # Fetch stats for this player, ordered by fixture? 
            # We need to order by event/date. Fixture has 'event'.
            # Join with Fixture to sort by event.
            stats = db.query(models.PlayerStats).join(models.Fixture).filter(
                models.PlayerStats.player_id == player.id
            ).order_by(models.Fixture.event).all()
            
            if not stats:
                continue
                
            # Calculate rolling features
            # We need to store history to calculate rolling averages
            points_history = []
            minutes_history = []
            
            for stat in stats:
                fixture = db.query(models.Fixture).filter(models.Fixture.id == stat.fixture_id).first()
                if not fixture:
                    continue
                
                # Determine opponent and is_home
                if player.team_id == fixture.team_h:
                    is_home = 1
                    opponent_id = fixture.team_a
                else:
                    is_home = 0
                    opponent_id = fixture.team_h
                
                opponent_difficulty = team_strengths.get(opponent_id, 3)
                
                # Rolling features (using past data only)
                # For the FIRST match, history is empty.
                avg_points_last_5 = np.mean(points_history[-5:]) if points_history else 0
                minutes_consistency = np.std(minutes_history[-5:]) if len(minutes_history) > 1 else 0
                form = avg_points_last_5 # Simple form definition
                
                # Update history AFTER calculating features for THIS match (to avoid leakage if we were predicting this match)
                # BUT, wait. 
                # If we are training a model to predict 'total_points' for THIS match, 
                # we must use features available BEFORE the match.
                # So yes, calculate using history, THEN append current match stats to history.
                
                feature_in = schemas.ModelFeaturesCreate(
                    player_id=player.id,
                    fixture_id=stat.fixture_id,
                    avg_points_last_5=float(avg_points_last_5),
                    form=float(form),
                    opponent_difficulty=opponent_difficulty,
                    is_home=is_home,
                    minutes_consistency=float(minutes_consistency)
                )
                
                # Check if exists
                existing = db.query(models.ModelFeatures).filter(
                    models.ModelFeatures.player_id == feature_in.player_id,
                    models.ModelFeatures.fixture_id == feature_in.fixture_id
                ).first()
                
                if not existing:
                    crud.create_model_features(db, feature_in)
                
                points_history.append(stat.total_points)
                minutes_history.append(stat.minutes)

        print("Feature Engineering completed successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    calculate_features()
