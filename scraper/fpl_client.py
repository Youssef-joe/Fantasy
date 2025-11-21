import requests
import logging

class FPLClient:
    BASE_URL = "https://fantasy.premierleague.com/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        })

    def get_bootstrap_static(self):
        """Fetches general data (players, teams, events, etc.)"""
        url = f"{self.BASE_URL}/bootstrap-static/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_fixtures(self):
        """Fetches all fixtures"""
        url = f"{self.BASE_URL}/fixtures/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_player_summary(self, player_id):
        """Fetches detailed data for a specific player"""
        url = f"{self.BASE_URL}/element-summary/{player_id}/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_team_stats(self, team_id):
        """Fetches detailed stats for a team"""
        url = f"{self.BASE_URL}/teams/{team_id}/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
