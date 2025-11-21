import json
import os
import sys
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models, schemas, crud

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw')

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'r') as f:
        return json.load(f)

def etl_process():
    db = SessionLocal()
    try:
        print("Starting ETL process...")

        # Load Bootstrap Static Data
        bootstrap_data = load_json('bootstrap_static.json')
        
        # Process Teams
        print("Processing Teams...")
        teams = bootstrap_data.get('teams', [])
        for team_data in teams:
            team_in = schemas.TeamCreate(
                id=team_data['id'],
                name=team_data['name'],
                short_name=team_data['short_name']
            )
            # Check if exists to avoid duplicates (simple check)
            existing = db.query(models.Team).filter(models.Team.id == team_in.id).first()
            if not existing:
                crud.create_team(db, team_in)
        
        # Process Players
        print("Processing Players...")
        players = bootstrap_data.get('elements', [])
        for player_data in players:
            player_in = schemas.PlayerCreate(
                id=player_data['id'],
                first_name=player_data['first_name'],
                second_name=player_data['second_name'],
                team_id=player_data['team'],
                position=player_data['element_type']
            )
            existing = db.query(models.Player).filter(models.Player.id == player_in.id).first()
            if not existing:
                crud.create_player(db, player_in)
            
            # Process injury status
            status = player_data.get('status', 'a')  # 'a'=available, 'd'=doubtful, 'i'=injured, 'u'=unavailable
            injury_status_map = {
                'a': None,
                'd': 'Doubtful',
                'i': 'Injured',
                'u': 'Unavailable'
            }
            injury_status_name = injury_status_map.get(status)
            is_injured = status != 'a'
            
            existing_injury = db.query(models.InjuryStatus).filter(
                models.InjuryStatus.player_id == player_data['id']
            ).first()
            
            if not existing_injury:
                injury_record = models.InjuryStatus(
                    player_id=player_data['id'],
                    is_injured=is_injured,
                    injury_status_name=injury_status_name,
                    expected_return=player_data.get('news_return_date')
                )
                db.add(injury_record)
                db.commit()
            else:
                # Update existing injury status
                existing_injury.is_injured = is_injured
                existing_injury.injury_status_name = injury_status_name
                existing_injury.expected_return = player_data.get('news_return_date')
                db.commit()

        # Load Fixtures Data
        fixtures_data = load_json('fixtures.json')
        
        # Process Fixtures
        print("Processing Fixtures...")
        for fixture_data in fixtures_data:
            try:
                fixture_in = schemas.FixtureCreate(
                    id=fixture_data['id'],
                    event=fixture_data['event'],
                    team_h=fixture_data['team_h'],
                    team_a=fixture_data['team_a'],
                    kickoff_time=fixture_data['kickoff_time']
                )
                existing = db.query(models.Fixture).filter(models.Fixture.id == fixture_in.id).first()
                if not existing:
                    crud.create_fixture(db, fixture_in)
            except Exception as e:
                print(f"Error processing fixture {fixture_data.get('id')}: {e}")

        # Process Player Stats (History)
        print("Processing Player Stats...")
        players = db.query(models.Player).all()
        for player in players:
            try:
                player_file = f"player_{player.id}.json"
                if not os.path.exists(os.path.join(DATA_DIR, player_file)):
                    continue
                
                player_data = load_json(player_file)
                history = player_data.get('history', [])
                
                for match in history:
                    stats_in = schemas.PlayerStatsCreate(
                        player_id=player.id,
                        fixture_id=match['fixture'],
                        minutes=match['minutes'],
                        goals_scored=match['goals_scored'],
                        assists=match['assists'],
                        total_points=match['total_points'],
                        xG=match.get('expected_goals'),
                        xA=match.get('expected_assists'),
                        shots=match.get('shots_on_target')
                    )
                    # Check if exists (composite key check would be better, but for now simple check)
                    # Assuming we don't have a unique constraint on player_id + fixture_id in models yet, 
                    # but we should probably check if we already loaded this match for this player.
                    existing_stats = db.query(models.PlayerStats).filter(
                        models.PlayerStats.player_id == stats_in.player_id,
                        models.PlayerStats.fixture_id == stats_in.fixture_id
                    ).first()
                    
                    if not existing_stats:
                        crud.create_player_stats(db, stats_in)
            except Exception as e:
                print(f"Error processing stats for player {player.id}: {e}")

        print("ETL process completed successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    etl_process()
