"""
Understat scraper using official understat library.
Fetches xG, xA, minutes, and advanced stats for players and teams.
"""

import logging
from understat import Understat

logger = logging.getLogger(__name__)


class UnderstatScraper:
    """Scraper for Understat data using the official library"""
    
    def __init__(self):
        """Initialize Understat scraper"""
        self.season = 2024
        
    async def get_player_stats(self):
        """
        Fetch player statistics including xG, xA, minutes, and shot data.
        
        Returns:
            dict with player stats indexed by player name
        """
        try:
            async with Understat() as understat:
                # Get shot map data for all players in EPL
                logger.info(f"Fetching player data for {self.season} season...")
                
                # Get player stats
                players_data = await understat.get_player_shots(team="")
                
                # Parse into structured format
                player_stats = {}
                for shot in players_data:
                    player_name = shot.get('player_name', '')
                    if player_name not in player_stats:
                        player_stats[player_name] = {
                            'name': player_name,
                            'team': shot.get('team_name', ''),
                            'position': shot.get('player_assisted_shot', {}).get('position', ''),
                            'shots': 0,
                            'xG': 0.0,
                            'xA': 0.0,
                            'minutes': 0,
                            'goals': 0,
                            'assists': 0,
                            'matches': 0,
                            'shot_data': []
                        }
                    
                    # Accumulate shot data
                    player_stats[player_name]['shots'] += 1
                    player_stats[player_name]['xG'] += float(shot.get('xG', 0))
                    player_stats[player_name]['xA'] += float(shot.get('xA', 0))
                    if int(shot.get('result', '')) == 1:  # Goal
                        player_stats[player_name]['goals'] += 1
                    
                    player_stats[player_name]['shot_data'].append({
                        'xG': float(shot.get('xG', 0)),
                        'result': shot.get('result', ''),
                        'minute': shot.get('minute', 0),
                        'match_id': shot.get('match_id', ''),
                        'date': shot.get('date', '')
                    })
                
                logger.info(f"Fetched data for {len(player_stats)} players")
                return player_stats
                
        except Exception as e:
            logger.error(f"Error fetching player shots from Understat: {e}")
            return {}
    
    async def get_team_stats(self):
        """
        Fetch team-level statistics including xG, xGA, and defensive metrics.
        
        Returns:
            dict with team stats indexed by team name
        """
        try:
            async with Understat() as understat:
                logger.info(f"Fetching team stats for {self.season} season...")
                
                # Get all matches/teams data
                # The library provides team data through matches
                team_stats = {}
                
                # Fetch match data to build team stats
                matches = await understat.get_matches("EPL")
                
                for match in matches:
                    home_team = match.get('home', {}).get('team_name', '')
                    away_team = match.get('away', {}).get('team_name', '')
                    
                    if home_team not in team_stats:
                        team_stats[home_team] = {
                            'name': home_team,
                            'xG_for': 0.0,
                            'xG_against': 0.0,
                            'matches_played': 0,
                            'matches_data': []
                        }
                    
                    if away_team not in team_stats:
                        team_stats[away_team] = {
                            'name': away_team,
                            'xG_for': 0.0,
                            'xG_against': 0.0,
                            'matches_played': 0,
                            'matches_data': []
                        }
                    
                    # Home team stats
                    home_xg = float(match.get('home', {}).get('xG', 0))
                    away_xg = float(match.get('away', {}).get('xG', 0))
                    
                    team_stats[home_team]['xG_for'] += home_xg
                    team_stats[home_team]['xG_against'] += away_xg
                    team_stats[home_team]['matches_played'] += 1
                    team_stats[home_team]['matches_data'].append({
                        'opponent': away_team,
                        'xG': home_xg,
                        'xG_against': away_xg,
                        'is_home': True,
                        'date': match.get('date', '')
                    })
                    
                    # Away team stats
                    team_stats[away_team]['xG_for'] += away_xg
                    team_stats[away_team]['xG_against'] += home_xg
                    team_stats[away_team]['matches_played'] += 1
                    team_stats[away_team]['matches_data'].append({
                        'opponent': home_team,
                        'xG': away_xg,
                        'xG_against': home_xg,
                        'is_home': False,
                        'date': match.get('date', '')
                    })
                
                logger.info(f"Fetched stats for {len(team_stats)} teams")
                return team_stats
                
        except Exception as e:
            logger.error(f"Error fetching team stats from Understat: {e}")
            return {}
