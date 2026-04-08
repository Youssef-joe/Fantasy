# Fantasy Football Prediction System

A machine learning-powered system for predicting fantasy football player performance, featuring injury tracking and a modern web dashboard.

## Installation

### Python Dependencies
Ensure Python 3.9+ is installed, then install requirements:
```bash
pip install -r scraper/requirements.txt
pip install -r backend/requirements.txt
pip install -r ml/requirements.txt
```

### CLI Tool (Optional)
Install the CLI globally for easy command access:
```bash
npm install -g .
```

## Quick Start

Using Python directly:
```bash
# 1. Scrape fresh data from FPL API
python scraper/main.py

# 2. Load and process data
python -m backend.etl
python -m backend.features

# 3. Train the ML model
python ml/train.py

# 4. View predictions
python ml/predict.py --gameweek 37 --top 20 --show-injured

# 5. Start API server
python -m uvicorn backend.main:app --reload

# 6. Open dashboard in browser
frontend/dashboard.html
```

Using the CLI (after npm install -g):
```bash
# 1. Scrape data
fantasy-cli scrape

# 2. Run ETL and features
fantasy-cli etl
fantasy-cli features

# 3. Train model
fantasy-cli train

# 4. Get predictions
fantasy-cli predict --gameweek 37 --top 20 --show-injured

# 5. Start API
fantasy-cli api

# 6. Open dashboard
fantasy-cli dashboard
```

## Features

### Machine Learning Predictions
- Random Forest model trained on 8,063+ match records
- Predicts player points 1-2 gameweeks in advance
- Benchmark: MAE of 1.02 points (within 1 point accuracy on average)

### Injury Tracking
- Automatically scrapes FPL injury data
- Filters injured/unavailable players from predictions
- Shows expected return gameweek

### Interactive Dashboard
- Modern responsive web interface
- Real-time prediction fetching
- Player rankings and statistics
- Injury alerts and status

### REST API
- FastAPI backend with full documentation
- Endpoints for players, fixtures, teams, predictions
- CORS enabled for frontend integration

## Project Structure

- **scraper/** - FPL API data collection
- **backend/** - FastAPI server, database, ETL
- **ml/** - Feature engineering, model training, predictions
- **frontend/** - Interactive HTML dashboard
- **data/** - Raw JSON and processed data

## System Architecture

```
FPL API
  ↓
Scraper (Python) → data/raw/*.json
  ↓
ETL Pipeline → SQLite Database
  ↓
Feature Engineering (8 features per player-match)
  ↓
Model Training (Random Forest, 100 estimators)
  ↓
Predictions API ← Frontend Dashboard
```

## Model Benchmarks

### Performance Metrics
- **Training Samples**: 8,063
- **Mean Absolute Error (MAE)**: 1.02 points
- **Root Mean Squared Error (RMSE)**: 1.93 points
- **R-squared (R²)**: 0.32

### Feature Importance
- Form (43%) - Recent performance
- Goal Threat (16%) - Attacking contribution rate
- Minutes Consistency (12%) - Playing time stability
- Historical Averages (12%) - Past performance
- Injury Risk (8%) - Minute drop-off detection
- Home/Away (3%) - Location advantage
- Opponent Difficulty (6%) - Defense strength

## Documentation

- **QUICKSTART.md** - Setup and basic usage
- **PIPELINE.md** - Detailed pipeline explanation
- **FRONTEND_GUIDE.md** - Dashboard usage guide
- **STATUS.md** - Implementation status and features

## Usage Examples

### Get top 20 predictions
```bash
python ml/predict.py --gameweek 37 --top 20
# or
fantasy-cli predict --gameweek 37 --top 20
```

### Show injured players
```bash
python ml/predict.py --gameweek 37 --show-injured
# or
fantasy-cli predict --gameweek 37 --show-injured
```

### Retrain model
```bash
python -m backend.etl
python -m backend.features
python ml/train.py --model random_forest
# or
fantasy-cli etl && fantasy-cli features && fantasy-cli train
```

### Start API
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
# or
fantasy-cli api
```

## Requirements

- Python 3.9+
- pip packages: scikit-learn, pandas, numpy, fastapi, sqlalchemy
- Optional: Node.js for Next.js frontend (current: HTML only)

## Future Improvements

Priority enhancements:
1. Injury tracking integration (completed)
2. Interactive dashboard (completed)
3. Opponent difficulty dynamic calculation
4. Authentication and rate limiting
5. Real-time injury updates
6. Ensemble models (XGBoost, LightGBM)
7. Player watchlist and alerts
8. Historical performance tracking
