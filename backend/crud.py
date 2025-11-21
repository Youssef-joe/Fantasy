from sqlalchemy.orm import Session
from . import models, schemas

def get_player(db: Session, player_id: int):
    return db.query(models.Player).filter(models.Player.id == player_id).first()

def get_players(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Player).offset(skip).limit(limit).all()

def create_player(db: Session, player: schemas.PlayerCreate):
    db_player = models.Player(
        id=player.id,
        first_name=player.first_name,
        second_name=player.second_name,
        team_id=player.team_id,
        position=player.position
    )
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player

def get_fixtures(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Fixture).offset(skip).limit(limit).all()

def create_fixture(db: Session, fixture: schemas.FixtureCreate):
    db_fixture = models.Fixture(
        id=fixture.id,
        event=fixture.event,
        team_h=fixture.team_h,
        team_a=fixture.team_a,
        kickoff_time=fixture.kickoff_time
    )
    db.add(db_fixture)
    db.commit()
    db.refresh(db_fixture)
    return db_fixture

def get_teams(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Team).offset(skip).limit(limit).all()

def create_team(db: Session, team: schemas.TeamCreate):
    db_team = models.Team(
        id=team.id,
        name=team.name,
        short_name=team.short_name
    )
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team

def create_player_stats(db: Session, stats: schemas.PlayerStatsCreate):
    db_stats = models.PlayerStats(
        player_id=stats.player_id,
        fixture_id=stats.fixture_id,
        minutes=stats.minutes,
        goals_scored=stats.goals_scored,
        assists=stats.assists,
        total_points=stats.total_points
    )
    db.add(db_stats)
    db.commit()
    db.refresh(db_stats)
    return db_stats

def create_model_features(db: Session, features: schemas.ModelFeaturesCreate):
    db_features = models.ModelFeatures(
        player_id=features.player_id,
        fixture_id=features.fixture_id,
        avg_points_last_5=features.avg_points_last_5,
        form=features.form,
        opponent_difficulty=features.opponent_difficulty,
        is_home=features.is_home,
        minutes_consistency=features.minutes_consistency
    )
    db.add(db_features)
    db.commit()
    db.refresh(db_features)
    return db_features
