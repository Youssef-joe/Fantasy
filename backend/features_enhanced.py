"""
Enhanced feature engineering including:
- Minutes tracking and trends
- xG/xA analysis from Understat
- Playing time consistency
- Opponent defensive weakness analysis
"""

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
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r') as f:
        return json.load(f)


def get_team_strength_map():
    """Load team strengths from bootstrap static data"""
    try:
        data = load_json('bootstrap_static.json')
        teams = data.get('teams', [])
        return {t['id']: t.get('strength', 3) for t in teams}
    except Exception as e:
        print(f"Could not load team strengths: {e}")
        return {}


def get_understat_player_stats():
    """Load Understat player data indexed by player name"""
    try:
        data = load_json('understat_player_stats.json')
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Could not load Understat data: {e}")
        return {}


def get_team_xG_stats():
    """Load team xG/xGA stats from Understat"""
    try:
        data = load_json('understat_team_stats.json')
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Could not load team xG stats: {e}")
        return {}


def calculate_minutes_trend(minutes_history):
    """
    Calculate if minutes are increasing or decreasing.
    Positive = increasing minutes (good trend)
    Negative = decreasing minutes (injury/rotation risk)
    """
    if len(minutes_history) < 2:
        return 0.0
    
    # Simple linear regression trend
    x = np.arange(len(minutes_history))
    y = np.array(minutes_history)
    
    # Remove zeros to avoid skewing if player had games with 0 minutes
    non_zero_indices = y > 0
    if not any(non_zero_indices):
        return 0.0
    
    x_nonzero = x[non_zero_indices]
    y_nonzero = y[non_zero_indices]
    
    if len(y_nonzero) < 2:
        return 0.0
    
    # Calculate slope of trend line
    slope = np.polyfit(x_nonzero, y_nonzero, 1)[0]
    return float(slope)


def calculate_games_with_minutes(minutes_history, threshold=1):
    """Calculate percentage of games where player got significant minutes"""
    if not minutes_history:
        return 0.0
    
    games_with_minutes = sum(1 for m in minutes_history if m >= threshold)
    return float(games_with_minutes / len(minutes_history))


def calculate_features_for_player(db, player, team_strengths, understat_data, team_xg_data):
    """Calculate all features for a single player"""
    
    # Fetch stats for this player, ordered by fixture event
    stats = db.query(models.PlayerStats).join(models.Fixture).filter(
        models.PlayerStats.player_id == player.id
    ).order_by(models.Fixture.event).all()
    
    if not stats:
        return
    
    # Build history for feature calculation
    points_history = []
    minutes_history = []
    xg_history = []
    xa_history = []
    shots_history = []
    goals_history = []
    
    # Get player name for Understat lookup
    player_fullname = f"{player.first_name} {player.second_name}".strip()
    player_understat = understat_data.get(player_fullname, {})
    
    for stat in stats:
        fixture = db.query(models.Fixture).filter(models.Fixture.id == stat.fixture_id).first()
        if not fixture:
            continue
        
        # Determine home/away
        is_home = 1 if player.team_id == fixture.team_h else 0
        opponent_id = fixture.team_a if is_home else fixture.team_h
        
        opponent_difficulty = team_strengths.get(opponent_id, 3)
        
        # === CALCULATE FEATURES USING PAST DATA ONLY ===
        
        # 1. Traditional Features
        avg_points_last_5 = np.mean(points_history[-5:]) if points_history else 0.0
        form = avg_points_last_5
        minutes_consistency = np.std(minutes_history[-5:]) if len(minutes_history) > 1 else 0.0
        
        # 2. Minutes & Playing Time Features
        avg_minutes_last_5 = np.mean(minutes_history[-5:]) if minutes_history else 0.0
        minutes_trend = calculate_minutes_trend(minutes_history[-5:])
        minutes_variance = np.var(minutes_history[-5:]) if len(minutes_history) > 1 else 0.0
        games_with_minutes = calculate_games_with_minutes(minutes_history[-5:])
        
        # 3. Understat Features (xG, xA, etc.)
        avg_xG_last_5 = np.mean(xg_history[-5:]) if xg_history else None
        avg_xA_last_5 = np.mean(xa_history[-5:]) if xa_history else None
        avg_shots_last_5 = np.mean(shots_history[-5:]) if shots_history else None
        
        # xG outperformance: actual goals vs expected goals
        if xg_history:
            total_xg = sum(xg_history[-5:])
            total_goals = sum(goals_history[-5:])
            xG_outperformance = float(total_goals - total_xg) if total_xg > 0 else None
        else:
            xG_outperformance = None
        
        # 4. Team Context Features
        opponent_name = db.query(models.Team).filter(models.Team.id == opponent_id).first()
        opponent_team_stats = team_xg_data.get(opponent_name.name if opponent_name else '') if opponent_name else {}
        
        team_name = db.query(models.Team).filter(models.Team.id == player.team_id).first()
        team_stats = team_xg_data.get(team_name.name if team_name else '') if team_name else {}
        
        # Team's average xG (how attacking is the team)
        if team_stats and team_stats.get('matches_played', 0) > 0:
            team_xG = team_stats['xG_for'] / team_stats['matches_played']
        else:
            team_xG = None
        
        # Opponent's average xGA (how defensively weak they are)
        if opponent_team_stats and opponent_team_stats.get('matches_played', 0) > 0:
            opponent_xGA = opponent_team_stats['xG_against'] / opponent_team_stats['matches_played']
        else:
            opponent_xGA = None
        
        # Create feature record
        feature_in = schemas.ModelFeaturesCreate(
            player_id=player.id,
            fixture_id=stat.fixture_id,
            avg_points_last_5=float(avg_points_last_5),
            form=float(form),
            opponent_difficulty=opponent_difficulty,
            is_home=is_home,
            minutes_consistency=float(minutes_consistency),
            avg_minutes_last_5=float(avg_minutes_last_5) if avg_minutes_last_5 else None,
            minutes_trend=float(minutes_trend) if minutes_trend else None,
            minutes_variance=float(minutes_variance) if minutes_variance else None,
            games_with_minutes=float(games_with_minutes) if games_with_minutes else None,
            avg_xG_last_5=avg_xG_last_5,
            avg_xA_last_5=avg_xA_last_5,
            avg_shots_last_5=avg_shots_last_5,
            xG_outperformance=xG_outperformance,
            team_xG=team_xG,
            opponent_xGA=opponent_xGA
        )
        
        # Check if exists
        existing = db.query(models.ModelFeatures).filter(
            models.ModelFeatures.player_id == feature_in.player_id,
            models.ModelFeatures.fixture_id == feature_in.fixture_id
        ).first()
        
        if not existing:
            crud.create_model_features(db, feature_in)
        
        # === UPDATE HISTORY FOR NEXT ITERATION ===
        points_history.append(stat.total_points)
        minutes_history.append(stat.minutes)
        xg_history.append(stat.xG if stat.xG else 0.0)
        xa_history.append(stat.xA if stat.xA else 0.0)
        shots_history.append(stat.shots if stat.shots else 0)
        goals_history.append(stat.goals_scored)


def calculate_features():
    """Main feature calculation pipeline"""
    db = SessionLocal()
    try:
        print("Starting Enhanced Feature Engineering...")
        
        team_strengths = get_team_strength_map()
        understat_data = get_understat_player_stats()
        team_xg_data = get_team_xG_stats()
        
        print(f"Loaded {len(understat_data)} player records from Understat")
        print(f"Loaded {len(team_xg_data)} team records from Understat")
        
        # Fetch all players
        players = db.query(models.Player).all()
        
        for i, player in enumerate(players):
            try:
                if (i + 1) % 50 == 0:
                    print(f"Processing player {i + 1}/{len(players)}...")
                
                calculate_features_for_player(db, player, team_strengths, understat_data, team_xg_data)
            except Exception as e:
                print(f"Error processing features for player {player.id}: {e}")
        
        print("Enhanced Feature Engineering completed successfully.")
    
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    calculate_features()
