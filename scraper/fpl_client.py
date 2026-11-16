import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

REQUEST_TIMEOUT = 30  # seconds


class FPLClient:
    BASE_URL = "https://fantasy.premierleague.com/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        })
        # Retry rate limits and transient server errors (FPL returns 503 while
        # it updates between gameweeks), backing off 2s, 4s, 8s, 16s, 32s.
        retry = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _get(self, path):
        response = self.session.get(f"{self.BASE_URL}/{path}", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def get_bootstrap_static(self):
        """Fetches general data (players, teams, events, etc.)"""
        return self._get("bootstrap-static/")

    def get_fixtures(self):
        """Fetches all fixtures"""
        return self._get("fixtures/")

    def get_player_summary(self, player_id):
        """Fetches detailed data for a specific player"""
        return self._get(f"element-summary/{player_id}/")
