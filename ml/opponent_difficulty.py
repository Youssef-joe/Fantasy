"""
Calculate opponent difficulty based on historical performance.
This module computes how strong each team is defensively and offensively,
considering home/away context.
"""
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func


def calculate_team_difficulty_rating(db: Session):
    """
    Calculate defensive difficulty rating for each team in each context (home/away).
    
    Returns:
        dict: {team_id: {'home': strength, 'away': strength, 'overall': strength}}
    """
    from backend import models
    
    # Fetch all fixtures with player stats
    fixtures = db.query(models.Fixture).all()
    team_stats = {}
    
    for team_id in range(1, 21):  # 20 teams in FPL
        team_stats[team_id] = {'home': [], 'away': []}
    
    for fixture in fixtures:
        # Get all player stats for this fixture
        home_stats = db.query(models.PlayerStats).join(
            models.Player,
            models.PlayerStats.player_id == models.Player.id
        ).filter(
            models.Player.team_id == fixture.team_h,
            models.PlayerStats.fixture_id == fixture.id
        ).all()
        
        away_stats = db.query(models.PlayerStats).join(
            models.Player,
            models.PlayerStats.player_id == models.Player.id
        ).filter(
            models.Player.team_id == fixture.team_a,
            models.PlayerStats.fixture_id == fixture.id
        ).all()
        
        # Aggregate points conceded (lower is better defense)
        home_points = sum([s.total_points for s in away_stats]) if away_stats else 0
        away_points = sum([s.total_points for s in home_stats]) if home_stats else 0
        
        # Store for calculation
        if fixture.team_a in team_stats:
            team_stats[fixture.team_a]['home'].append(home_points)
        if fixture.team_h in team_stats:
            team_stats[fixture.team_h]['away'].append(away_points)
    
    # Convert to ratings (invert: more conceded = harder to score against)
    difficulty_map = {}
    for team_id, context_stats in team_stats.items():
        home_avg = np.mean(context_stats['home']) if context_stats['home'] else 0
        away_avg = np.mean(context_stats['away']) if context_stats['away'] else 0
        overall_avg = np.mean(context_stats['home'] + context_stats['away']) if (context_stats['home'] or context_stats['away']) else 0
        
        # Normalize to 1-5 scale (5 = hardest defense)
        max_conceded = 10
        home_difficulty = min(5, max(1, 5 - (home_avg / max_conceded)))
        away_difficulty = min(5, max(1, 5 - (away_avg / max_conceded)))
        overall_difficulty = min(5, max(1, 5 - (overall_avg / max_conceded)))
        
        difficulty_map[team_id] = {
            'home': round(home_difficulty, 2),
            'away': round(away_difficulty, 2),
            'overall': round(overall_difficulty, 2)
        }
    
    return difficulty_map


def get_opponent_difficulty(db: Session, opponent_id: int, is_home: bool):
    """
    Get opponent difficulty rating considering home/away context.
    
    Args:
        opponent_id: Team ID of the opponent
        is_home: Whether the player's team is playing at home
    
    Returns:
        float: Difficulty rating (1-5, where 5 is hardest)
    """
    difficulty_map = calculate_team_difficulty_rating(db)
    
    if opponent_id not in difficulty_map:
        return 3.0  # Default if not found
    
    # From the opponent's perspective (their away/home defense)
    if is_home:
        # Player is at home, opponent is away
        return difficulty_map[opponent_id]['away']
    else:
        # Player is away, opponent is at home
        return difficulty_map[opponent_id]['home']
