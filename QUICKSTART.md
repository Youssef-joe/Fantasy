# Quick Start Guide

## Installation

```bash
# Install all dependencies
pip install -r backend/requirements.txt
pip install -r scraper/requirements.txt
pip install -r ml/requirements.txt
```

## Run Full Pipeline (One Time)

```bash
# 1. Scrape data from FPL API (~5-10 minutes)
cd scraper
python main.py
cd ..

# 2. Load data into database
cd backend
python -m backend.etl
cd ..

# 3. Calculate features
cd backend
python -m backend.features
cd ..

# 4. Train the ML model
cd ml
python train.py --model random_forest
cd ..
```

## Make Predictions

```bash
cd ml
python predict.py --gameweek 10 --top 20
```

## Run Backend API

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

Then visit: http://localhost:8000/docs for interactive API documentation

## What Each Component Does

| Component | Purpose | Input | Output |
|-----------|---------|-------|--------|
| **Scraper** | Fetch data from FPL API | FPL servers | `data/raw/*.json` |
| **ETL** | Parse JSON and load into DB | `data/raw/*.json` | SQLite database |
| **Features** | Engineer ML features | Database | ModelFeatures table |
| **Train** | Train prediction model | ModelFeatures + PlayerStats | `ml/model.joblib` |
| **Predict** | Make predictions for next week | Model + Database | Top player predictions |
| **API** | Serve predictions to frontend | Database + Model | REST endpoints |

## Key Features

- **Opponent Difficulty**: Dynamically calculated from historical data, considers home/away context
- **Minutes Consistency**: Identifies injury risk and rotation players
- **Form Tracking**: Recent performance helps weight newer data
- **Goal Threat**: Extra feature for attacking players
- **Injury Risk**: Detects sudden drops in playing time

## Example Workflow

```bash
# After training once, you can:

# 1. Get top 20 predictions for next gameweek
python ml/predict.py --top 20

# 2. Check predictions for specific gameweek
python ml/predict.py --gameweek 15 --top 10

# 3. Use API to integrate with frontend
curl http://localhost:8000/predict/

# 4. Query individual players
curl http://localhost:8000/players/
```

## Notes

- Initial scraping takes time (100+ player files)
- Model accuracy improves with more historical data (more gameweeks)
- Features are calculated on-the-fly during prediction for up-to-date results
- Opponent difficulty uses actual historical performance, not ratings
