"""
Minutes analysis for players - tracks playing time trends and patterns.
"""
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session


def calculate_minutes_trend(minutes_history: list, window: int = 5) -> float:
    """
    Calculate minutes trend (increasing or decreasing).
    
    Positive = getting more minutes
    Negative = getting fewer minutes
    
    Args:
        minutes_history: List of minutes from past matches (chronological)
        window: Number of recent matches to consider
    
    Returns:
        float: Trend value (-1 to 1, where 1 = increasing minutes)
    """
    if len(minutes_history) < 2:
        return 0.0
    
    recent = minutes_history[-window:]
    if not recent or all(m == 0 for m in recent):
        return -1.0  # Not playing = negative trend
    
    # Compare first half vs second half
    mid = len(recent) // 2
    if mid == 0:
        return 0.0
    
    first_half_avg = np.mean([m for m in recent[:mid] if m > 0]) if any(m > 0 for m in recent[:mid]) else 0
    second_half_avg = np.mean([m for m in recent[mid:] if m > 0]) if any(m > 0 for m in recent[mid:]) else 0
    
    if first_half_avg == 0:
        return 0.5 if second_half_avg > 0 else 0.0
    
    trend = (second_half_avg - first_half_avg) / first_half_avg
    return float(np.clip(trend, -1.0, 1.0))


def calculate_minutes_per_90(minutes_history: list, matches_played: int) -> float:
    """
    Calculate minutes per 90 minutes of play.
    
    Shows how many 90-min matches the player could complete.
    
    Args:
        minutes_history: List of minutes from past matches
        matches_played: Total matches in period
    
    Returns:
        float: Minutes per 90 (0-1.0 where 1.0 = full matches)
    """
    if not minutes_history or matches_played == 0:
        return 0.0
    
    total_minutes = sum(minutes_history)
    potential_minutes = matches_played * 90
    
    if potential_minutes == 0:
        return 0.0
    
    return float(min(1.0, total_minutes / potential_minutes))


def calculate_playing_time_reliability(minutes_history: list, window: int = 5) -> float:
    """
    Calculate reliability of playing time.
    
    High = consistent starts/minutes
    Low = inconsistent/benched
    
    Args:
        minutes_history: List of minutes from past matches
        window: Recent matches to consider
    
    Returns:
        float: Reliability score (0-1.0)
    """
    if not minutes_history:
        return 0.0
    
    recent = minutes_history[-window:]
    
    # Count starts (>0 minutes) vs non-starts
    starts = sum(1 for m in recent if m > 0)
    start_rate = starts / len(recent) if recent else 0
    
    # Consistency (low variance = reliable)
    if len(recent) > 1:
        non_zero_minutes = [m for m in recent if m > 0]
        if non_zero_minutes:
            variance = np.var(non_zero_minutes)
            consistency = 1.0 / (1.0 + variance / 45)  # Normalize around 45 min variance
        else:
            consistency = 0.0
    else:
        consistency = 1.0 if recent[0] > 0 else 0.0
    
    # Average of start rate and consistency
    reliability = (start_rate + consistency) / 2
    return float(np.clip(reliability, 0.0, 1.0))


def calculate_rotation_risk(minutes_history: list, window: int = 5) -> float:
    """
    Calculate rotation risk (likelihood of being benched).
    
    High risk = often benched or getting less time
    Low risk = regular starter
    
    Args:
        minutes_history: List of minutes from past matches
        window: Recent matches to consider
    
    Returns:
        float: Risk score (0-1.0, where 1.0 = high rotation risk)
    """
    if not minutes_history:
        return 0.5  # Unknown = medium risk
    
    recent = minutes_history[-window:]
    
    # Check for bench appearances (0 minutes)
    bench_games = sum(1 for m in recent if m == 0)
    bench_rate = bench_games / len(recent) if recent else 0
    
    # Check for reduced minutes (sub appearances)
    sub_games = sum(1 for m in recent if 0 < m < 45)
    sub_rate = sub_games / len(recent) if recent else 0
    
    # Combine: bench rate (weighted more) + partial sub appearances
    rotation_risk = (bench_rate * 0.7) + (sub_rate * 0.3)
    return float(np.clip(rotation_risk, 0.0, 1.0))


def calculate_minutes_momentum(minutes_history: list, window: int = 3) -> float:
    """
    Calculate short-term minutes momentum (very recent trend).
    
    Args:
        minutes_history: List of minutes from past matches
        window: Number of very recent matches
    
    Returns:
        float: Momentum score (-1 to 1)
    """
    if len(minutes_history) < 2:
        return 0.0
    
    recent = minutes_history[-window:]
    if not recent:
        return 0.0
    
    # Check if player is getting more minutes recently
    if len(recent) >= 2:
        latest = recent[-1]
        previous = recent[-2]
        
        if previous == 0:
            momentum = 0.5 if latest > 0 else 0.0
        else:
            momentum = (latest - previous) / previous
    else:
        momentum = 1.0 if recent[0] > 0 else 0.0
    
    return float(np.clip(momentum, -1.0, 1.0))


def calculate_starter_probability(minutes_history: list, window: int = 5) -> float:
    """
    Probability that player will start next match.
    
    Args:
        minutes_history: List of minutes from past matches
        window: Recent matches to consider
    
    Returns:
        float: Start probability (0-1.0)
    """
    if not minutes_history:
        return 0.5  # Unknown
    
    recent = minutes_history[-window:]
    
    # Starters typically play 60+ minutes
    starts = sum(1 for m in recent if m >= 60)
    start_prob = starts / len(recent) if recent else 0
    
    return float(np.clip(start_prob, 0.0, 1.0))


def analyze_player_minutes(player_id: int, db: Session) -> dict:
    """
    Complete minutes analysis for a player.
    
    Args:
        player_id: Player ID
        db: Database session
    
    Returns:
        dict with all minutes metrics
    """
    from backend import models
    
    # Get all stats for player in chronological order
    stats = db.query(models.PlayerStats).join(
        models.Fixture
    ).filter(
        models.PlayerStats.player_id == player_id
    ).order_by(models.Fixture.event).all()
    
    if not stats:
        return {
            'minutes_trend': 0.0,
            'minutes_per_90': 0.0,
            'playing_time_reliability': 0.0,
            'rotation_risk': 0.5,
            'minutes_momentum': 0.0,
            'starter_probability': 0.5,
            'total_minutes': 0,
            'average_minutes': 0.0,
            'recent_minutes': 0
        }
    
    minutes_history = [s.minutes for s in stats]
    
    return {
        'minutes_trend': calculate_minutes_trend(minutes_history),
        'minutes_per_90': calculate_minutes_per_90(minutes_history, len(stats)),
        'playing_time_reliability': calculate_playing_time_reliability(minutes_history),
        'rotation_risk': calculate_rotation_risk(minutes_history),
        'minutes_momentum': calculate_minutes_momentum(minutes_history),
        'starter_probability': calculate_starter_probability(minutes_history),
        'total_minutes': sum(minutes_history),
        'average_minutes': float(np.mean(minutes_history)) if minutes_history else 0.0,
        'recent_minutes': minutes_history[-1] if minutes_history else 0
    }


def get_minutes_features_for_prediction(minutes_history: list) -> dict:
    """
    Get minutes-based features for ML prediction.
    
    Args:
        minutes_history: List of minutes from past matches
    
    Returns:
        dict with features ready for model input
    """
    if not minutes_history:
        return {
            'minutes_trend': 0.0,
            'minutes_per_90': 0.0,
            'rotation_risk': 0.5,
            'starter_probability': 0.5,
            'recent_avg_minutes': 0.0
        }
    
    return {
        'minutes_trend': calculate_minutes_trend(minutes_history),
        'minutes_per_90': calculate_minutes_per_90(minutes_history, len(minutes_history)),
        'rotation_risk': calculate_rotation_risk(minutes_history),
        'starter_probability': calculate_starter_probability(minutes_history),
        'recent_avg_minutes': float(np.mean(minutes_history[-5:] if len(minutes_history) >= 5 else minutes_history))
    }
