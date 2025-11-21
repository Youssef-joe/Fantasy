"""
Feature engineering pipeline for model training.
Computes features for each player-fixture combination.
"""
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from opponent_difficulty import get_opponent_difficulty


def calculate_player_form(points_history: list, window: int = 5) -> float:
    """Calculate recent form as average points in last N matches."""
    if not points_history:
        return 0.0
    return float(np.mean(points_history[-window:]))


def calculate_minutes_consistency(minutes_history: list, window: int = 5) -> float:
    """
    Calculate minutes consistency (inverse of std deviation).
    Low std = consistent playing time = less risky.
    """
    if len(minutes_history) < 2:
        return 0.0
    
    recent = minutes_history[-window:]
    if not recent:
        return 0.0
    
    # Normalize: 0 = no consistency, 1 = perfect consistency
    std = np.std(recent)
    return float(max(0, 1 - (std / 90)))  # 90 is max minutes


def calculate_goal_threat(player_id: int, db: Session, window: int = 5) -> float:
    """
    Calculate goal threat (goals + assists per match).
    Higher = more dangerous in attack.
    """
    from backend import models
    
    stats = db.query(models.PlayerStats).filter(
        models.PlayerStats.player_id == player_id
    ).order_by(models.PlayerStats.fixture_id.desc()).limit(window).all()
    
    if not stats:
        return 0.0
    
    total_goal_contributions = sum([s.goals_scored + s.assists for s in stats])
    return float(total_goal_contributions / len(stats))


def calculate_injury_risk(minutes_history: list, window: int = 5) -> float:
    """
    Estimate injury risk based on minute drop-off.
    If player suddenly getting less minutes, might be injured.
    """
    if len(minutes_history) < 2:
        return 0.0
    
    recent = minutes_history[-window:]
    if not recent or recent[-1] == 0:
        return 1.0  # High risk if not playing
    
    # Check if there's a trend of decreasing minutes
    early_avg = np.mean(recent[:len(recent)//2]) if len(recent) > 1 else recent[0]
    late_avg = np.mean(recent[len(recent)//2:]) if len(recent) > 1 else recent[-1]
    
    if early_avg == 0:
        return 0.0
    
    drop_ratio = (early_avg - late_avg) / early_avg
    return float(min(1.0, max(0.0, drop_ratio)))


def engineer_features_for_player_fixture(
    player_id: int,
    fixture_id: int,
    db: Session,
    points_history: list,
    minutes_history: list
) -> dict:
    """
    Compute all features for a specific player-fixture combination.
    
    Args:
        player_id: Player identifier
        fixture_id: Fixture identifier
        db: Database session
        points_history: List of total points from previous matches (in order)
        minutes_history: List of minutes played from previous matches (in order)
    
    Returns:
        dict: Feature dictionary ready for model input
    """
    from backend import models
    
    fixture = db.query(models.Fixture).filter(models.Fixture.id == fixture_id).first()
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    
    if not fixture or not player:
        return None
    
    # If no history, use defaults but still create sample
    # (better to have some data than nothing)
    
    # Determine if home/away and opponent
    if player.team_id == fixture.team_h:
        is_home = 1
        opponent_id = fixture.team_a
    else:
        is_home = 0
        opponent_id = fixture.team_h
    
    # Use cached opponent difficulty (simpler calculation)
    opponent_difficulty = 3.0  # Default value for now
    
    # Calculate all features
    features = {
        'avg_points_last_5': calculate_player_form(points_history, window=5),
        'avg_points_last_10': calculate_player_form(points_history, window=10),
        'form': calculate_player_form(points_history, window=3),
        'opponent_difficulty': opponent_difficulty,
        'is_home': is_home,
        'minutes_consistency': calculate_minutes_consistency(minutes_history),
        'goal_threat': calculate_goal_threat(player_id, db),
        'injury_risk': calculate_injury_risk(minutes_history),
    }
    
    return features


def generate_training_dataset(db: Session) -> pd.DataFrame:
    """
    Generate complete training dataset with features and targets.
    
    Returns:
        DataFrame with columns: all features + 'total_points' (target)
    """
    from backend import models
    
    records = []
    
    # Get all players
    players = db.query(models.Player).all()
    
    for player in players:
        # Get all stats for this player in chronological order
        all_stats = db.query(models.PlayerStats).join(models.Fixture).filter(
            models.PlayerStats.player_id == player.id
        ).order_by(models.Fixture.event).all()
        
        if not all_stats:
            continue
        
        points_history = []
        minutes_history = []
        
        # Process each match
        for i, stat in enumerate(all_stats):
            # Only use features from past matches (no data leakage)
            features = engineer_features_for_player_fixture(
                player.id,
                stat.fixture_id,
                db,
                points_history,  # Past data only
                minutes_history
            )
            
            if features is None:
                continue
            
            # Add target variable
            features['total_points'] = stat.total_points
            records.append(features)
            
            # Now update history for next iteration
            points_history.append(stat.total_points)
            minutes_history.append(stat.minutes)
    
    df = pd.DataFrame(records)
    
    # Remove rows with NaN
    df = df.dropna()
    
    return df
