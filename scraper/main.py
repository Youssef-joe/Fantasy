import os
import json
import logging
import asyncio
from fpl_client import FPLClient
from understat_scraper import UnderstatScraper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw')

def save_json(data, filename):
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Saved data to {filepath}")

def main():
    client = FPLClient()

    logger.info("Fetching bootstrap-static data...")
    bootstrap_data = client.get_bootstrap_static()
    save_json(bootstrap_data, 'bootstrap_static.json')

    logger.info("Fetching fixtures...")
    fixtures_data = client.get_fixtures()
    save_json(fixtures_data, 'fixtures.json')

    logger.info("Fetching team stats...")
    teams = bootstrap_data.get('teams', [])
    for team in teams:
        team_id = team['id']
        try:
            team_stats = client.get_team_stats(team_id)
            save_json(team_stats, f'team_{team_id}.json')
        except Exception as e:
            logger.error(f"Failed to fetch stats for team {team_id}: {e}")

    logger.info("Fetching player summaries...")
    players = bootstrap_data.get('elements', [])
    for player in players:
        player_id = player['id']
        try:
            player_summary = client.get_player_summary(player_id)
            save_json(player_summary, f'player_{player_id}.json')
        except Exception as e:
            logger.error(f"Failed to fetch summary for player {player_id}: {e}")

    # Scrape Understat xG data
    logger.info("Fetching Understat xG data...")
    try:
        asyncio.run(scrape_understat_data())
    except Exception as e:
        logger.error(f"Failed to fetch Understat data: {e}")

    logger.info("Scraping completed successfully.")

async def scrape_understat_data():
    """Fetch xG, xA, and minutes data from Understat"""
    scraper = UnderstatScraper()
    
    # Get player stats for the season
    logger.info("Fetching player shot map and stats from Understat...")
    player_stats = await scraper.get_player_stats()
    save_json(player_stats, 'understat_player_stats.json')
    
    # Get team stats
    logger.info("Fetching team stats from Understat...")
    team_stats = await scraper.get_team_stats()
    save_json(team_stats, 'understat_team_stats.json')

if __name__ == "__main__":
    main()
