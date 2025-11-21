from sqlalchemy.orm import Session
from .database import SessionLocal
from . import models

def verify_data():
    db = SessionLocal()
    try:
        num_teams = db.query(models.Team).count()
        num_players = db.query(models.Player).count()
        num_fixtures = db.query(models.Fixture).count()
        num_stats = db.query(models.PlayerStats).count()
        num_features = db.query(models.ModelFeatures).count()

        print(f"Teams: {num_teams}")
        print(f"Players: {num_players}")
        print(f"Fixtures: {num_fixtures}")
        print(f"Player Stats: {num_stats}")
        print(f"Model Features: {num_features}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_data()
