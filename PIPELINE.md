# ML Pipeline Setup & Usage

## Overview

This fantasy football prediction system uses a machine learning pipeline to predict player performance:

```
Scraper (FPL API) → Raw Data → ETL → Database → Feature Engineering → Model Training → Predictions
```

## Step-by-Step Execution

### 1. Scrape Data from FPL API

```bash
cd scraper
pip install -r requirements.txt
python main.py
```

This fetches:
- Bootstrap static data (players, teams, events)
- All fixtures (matches)
- Team stats (for opponent difficulty calculation)
- Individual player summaries (historical stats)

Data is saved to `data/raw/` folder.

### 2. Load Data into Database (ETL)

```bash
cd backend
pip install -r requirements.txt
python -m backend.etl
```

This processes raw JSON files and populates:
- Teams table
- Players table
- Fixtures table
- PlayerStats table (historical match data)

### 3. Engineer Features

Features are calculated based on player history and opponent context:

```bash
python -m backend.features
```

This computes features for each player-fixture combination:
- **avg_points_last_5**: Average points in last 5 matches
- **avg_points_last_10**: Average points in last 10 matches
- **form**: Recent form (last 3 matches)
- **opponent_difficulty**: How strong the opponent's defense (1-5 scale, considering home/away)
- **is_home**: Whether player is at home (1) or away (0)
- **minutes_consistency**: Consistency of playing time (0-1 scale)
- **goal_threat**: Goals + assists per match (attackers focus)
- **injury_risk**: Likelihood of injury based on minute drop-off

### 4. Train the Model

```bash
cd ml
python train.py --model random_forest --test-size 0.2
```

Options:
- `--model`: Choose `random_forest` (faster) or `gradient_boosting` (more accurate)
- `--test-size`: Fraction of data for testing (default: 0.2)

Output shows:
- Dataset size and feature statistics
- Training/testing split
- Model performance (MAE, RMSE, R²)
- Feature importance rankings

### 5. Make Predictions

```bash
cd ml
python predict.py --gameweek 10 --top 20
```

Options:
- `--gameweek`: Predict specific gameweek (default: next gameweek)
- `--top`: Show top N predictions (default: 20)

## API Integration

Once model is trained, use the backend API:

```bash
cd backend
python -m uvicorn main:app --reload
```

Available endpoints:

### Get all players
```
GET /players/?skip=0&limit=100
```

### Get specific player
```
GET /players/{player_id}
```

### Get fixtures
```
GET /fixtures/?skip=0&limit=100
```

### Get team list
```
GET /teams/?skip=0&limit=100
```

### Get predictions for next gameweek
```
GET /predict/
```

Returns top 20 predicted players sorted by predicted points.

## Data Flow

```
Player Historical Stats (from FPL)
        ↓
    Features Calculated
    - Recent form
    - Minutes consistency
    - Goal threat
    - Injury risk
    - Opponent difficulty (from team stats)
        ↓
    Training Data Created
        ↓
   Model Training
    (Random Forest / Gradient Boosting)
        ↓
    Model saved to ml/model.joblib
        ↓
    Predictions for next gameweek
    (using same feature engineering)
```

## Features Explained

### Opponent Difficulty

Calculated dynamically based on:
- How many points opponents scored against this team in past matches
- Home vs Away context (teams defend differently at home)
- Recent form of the defense

Formula:
```
difficulty = 1 to 5 scale
5 = conceded lots of goals (weak defense)
1 = conceded few goals (strong defense)
```

### Home/Away Impact

`is_home` feature captures:
- Home advantage in scoring (typically 10-15% higher)
- Home disadvantage in defense (typically more goals conceded)

### Minutes Consistency

Prevents selecting injured/benched players:
- 1.0 = plays full 90 mins every week (safe pick)
- 0.5 = inconsistent minutes (rotation or injury risk)
- 0.0 = never plays (avoid)

## Troubleshooting

### No data for training
- Check `data/raw/` folder for JSON files
- Run scraper again: `python scraper/main.py`

### Model not found for prediction
- Train the model first: `python ml/train.py`

### Database errors
- Delete `backend/fantasy.db` and re-run ETL

### API connection issues
- Ensure `pip install -r requirements.txt` in backend folder
- Check FPL API is accessible: `curl https://fantasy.premierleague.com/api/bootstrap-static/`
