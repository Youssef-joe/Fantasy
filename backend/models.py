from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    short_name = Column(String)
    
    players = relationship("Player", back_populates="team")

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    second_name = Column(String)
    team_id = Column(Integer, ForeignKey("teams.id"))
    position = Column(Integer) # 1=GKP, 2=DEF, 3=MID, 4=FWD

    team = relationship("Team", back_populates="players")
    stats = relationship("PlayerStats", back_populates="player")
    injury_status = relationship("InjuryStatus", back_populates="player", uselist=False)

class Fixture(Base):
    __tablename__ = "fixtures"

    id = Column(Integer, primary_key=True, index=True)
    event = Column(Integer) # Gameweek
    team_h = Column(Integer)
    team_a = Column(Integer)
    kickoff_time = Column(String)

class PlayerStats(Base):
    __tablename__ = "player_stats"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    fixture_id = Column(Integer, ForeignKey("fixtures.id"))
    minutes = Column(Integer)
    goals_scored = Column(Integer)
    assists = Column(Integer)
    total_points = Column(Integer)
    
    player = relationship("Player", back_populates="stats")

class ModelFeatures(Base):
    __tablename__ = "model_features"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    fixture_id = Column(Integer, ForeignKey("fixtures.id"))
    
    # Features
    avg_points_last_5 = Column(Float)
    form = Column(Float)
    opponent_difficulty = Column(Integer)
    is_home = Column(Integer) # 1 for home, 0 for away
    minutes_consistency = Column(Float)
    
    player = relationship("Player")
    fixture = relationship("Fixture")

class InjuryStatus(Base):
    __tablename__ = "injury_status"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), unique=True)
    is_injured = Column(Boolean, default=False)
    injury_status_name = Column(String)  # e.g., "Doubtful", "Out", "Unavailable"
    expected_return = Column(Integer, nullable=True)  # Expected gameweek of return
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    player = relationship("Player", back_populates="injury_status")
