from pydantic import BaseModel
from typing import List, Optional

class PlayerBase(BaseModel):
    first_name: str
    second_name: str
    position: int

class PlayerCreate(PlayerBase):
    id: int
    team_id: int

class Player(PlayerBase):
    id: int
    team_id: int

    class Config:
        orm_mode = True

class TeamBase(BaseModel):
    name: str
    short_name: str

class TeamCreate(TeamBase):
    id: int

class Team(TeamBase):
    id: int
    
    class Config:
        orm_mode = True

class FixtureBase(BaseModel):
    event: Optional[int] = None
    team_h: int
    team_a: int
    kickoff_time: Optional[str] = None

class FixtureCreate(FixtureBase):
    id: int

class Fixture(FixtureBase):
    id: int

    class Config:
        orm_mode = True

class PlayerStatsBase(BaseModel):
    player_id: int
    fixture_id: int
    minutes: int
    goals_scored: int
    assists: int
    total_points: int

class PlayerStatsCreate(PlayerStatsBase):
    pass

class PlayerStats(PlayerStatsBase):
    id: int

    class Config:
        orm_mode = True

class ModelFeaturesBase(BaseModel):
    player_id: int
    fixture_id: int
    avg_points_last_5: float
    form: float
    opponent_difficulty: int
    is_home: int
    minutes_consistency: float

class ModelFeaturesCreate(ModelFeaturesBase):
    pass

class ModelFeatures(ModelFeaturesBase):
    id: int

    class Config:
        orm_mode = True

class InjuryStatusBase(BaseModel):
    is_injured: bool
    injury_status_name: Optional[str] = None
    expected_return: Optional[int] = None

class InjuryStatusCreate(InjuryStatusBase):
    player_id: int

class InjuryStatus(InjuryStatusBase):
    id: int
    player_id: int

    class Config:
        orm_mode = True
