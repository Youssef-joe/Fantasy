"""
Understat API client for xG, xA, and advanced stats.
"""
import requests
import logging
import time

logger = logging.getLogger(__name__)


class UnderstatClient:
    """Client for fetching Understat data (xG, xA, etc.)"""
    
    BASE_URL = "https://understat.com/api/v1"
    
    def __init__(self, delay=0.5):
        """
        Initialize Understat client.
        
        Args:
            delay: Delay between requests in seconds (to avoid rate limiting)
        """
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.delay = delay
    
    def get_player_shot_data(self, player_id: int, season: int = 2024) -> dict:
        """
        Fetch player shot/xG data from Understat.
        
        Args:
            player_id: Understat player ID
            season: Season year
        
        Returns:
            dict with xG, shots, xA data
        """
        try:
            url = f"{self.BASE_URL}/player/{player_id}?json=1"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch Understat data for player {player_id}: {e}")
            return {}
    
    def get_team_stats(self, team_id: int, season: int = 2024) -> dict:
        """
        Fetch team xG/xGA stats.
        
        Args:
            team_id: Understat team ID
            season: Season year
        
        Returns:
            dict with team statistics
        """
        try:
            url = f"{self.BASE_URL}/team/{team_id}?json=1"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch team stats {team_id}: {e}")
            return {}
    
    def get_league_stats(self, season: int = 2024) -> dict:
        """
        Fetch league-wide statistics.
        
        Args:
            season: Season year
        
        Returns:
            dict with league stats
        """
        try:
            url = f"{self.BASE_URL}/league/epl?json=1"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch league stats: {e}")
            return {}
