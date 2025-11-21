from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/players/", response_model=List[schemas.Player])
def read_players(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    players = crud.get_players(db, skip=skip, limit=limit)
    return players

@app.get("/players/{player_id}", response_model=schemas.Player)
def read_player(player_id: int, db: Session = Depends(get_db)):
    db_player = crud.get_player(db, player_id=player_id)
    if db_player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return db_player

@app.get("/fixtures/", response_model=List[schemas.Fixture])
def read_fixtures(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    fixtures = crud.get_fixtures(db, skip=skip, limit=limit)
    return fixtures

@app.get("/teams/", response_model=List[schemas.Team])
def read_teams(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    teams = crud.get_teams(db, skip=skip, limit=limit)
    return teams

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))
from predict import predict_gameweek

@app.get("/predict/")
def predict_points(gameweek: int = None, top_n: int = 20, db: Session = Depends(get_db)):
    """Get predictions for a specific gameweek"""
    predictions, injured = predict_gameweek(db, gameweek=gameweek, top_n=top_n, include_injured=False)
    return {
        "gameweek": gameweek,
        "predictions": predictions,
        "injured_players": injured
    }

@app.get("/predict/injured/")
def get_injured_players(gameweek: int = None, db: Session = Depends(get_db)):
    """Get list of injured/unavailable players for a gameweek"""
    predictions, injured = predict_gameweek(db, gameweek=gameweek, top_n=1000, include_injured=False)
    return {
        "gameweek": gameweek,
        "injured_players": injured
    }

@app.get("/health/")
def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Fantasy Football Prediction API is running"}
