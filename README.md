# Fantasy Football Prediction System

🔮 ML-powered fantasy football player performance predictions with injury tracking and a modern web dashboard.

## ⚡ Quick Start

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

## 📊 Features

✅ **Machine Learning Predictions**
- Random Forest model trained on 8,063+ match records
- Predicts player points 1-2 gameweeks in advance
- MAE: 1.02 points (within 1 point accuracy)

✅ **Injury Tracking**
- Automatically scrapes FPL injury data
- Filters injured/unavailable players from predictions
- Shows expected return gameweek

✅ **Interactive Dashboard**
- Modern responsive web interface
- Real-time prediction fetching
- Player rankings and statistics
- Injury alerts and status

✅ **REST API**
- FastAPI backend with full documentation
- Endpoints for players, fixtures, teams, predictions
- CORS enabled for frontend integration

## 📁 Structure

- **scraper/** - FPL API data collection
- **backend/** - FastAPI server, database, ETL
- **ml/** - Feature engineering, model training, predictions
- **frontend/** - Interactive HTML dashboard
- **data/** - Raw JSON and processed data

## 🚀 System Architecture

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

## 📈 Model Details

**Features Used:**
- Form (43% importance) - Recent performance
- Goal Threat (16%) - Attacking contribution rate
- Minutes Consistency (12%) - Playing time stability
- Historical Averages (12%) - Past performance
- Injury Risk (8%) - Minute drop-off detection
- Home/Away (3%) - Location advantage
- Opponent Difficulty (6%) - Defense strength

**Performance:**
- Training samples: 8,063
- MAE: 1.02 points
- RMSE: 1.93 points
- R²: 0.32

## 📖 Documentation

- **QUICKSTART.md** - Setup and basic usage
- **PIPELINE.md** - Detailed pipeline explanation
- **FRONTEND_GUIDE.md** - Dashboard usage guide
- **STATUS.md** - Implementation status and features

## 🎮 Usage Examples

### Get top 20 predictions
```bash
python ml/predict.py --gameweek 37 --top 20
```

### Show injured players
```bash
python ml/predict.py --gameweek 37 --show-injured
```

### Retrain model
```bash
python -m backend.etl
python -m backend.features
python ml/train.py --model random_forest
```

### Start API
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 🔧 Requirements

- Python 3.9+
- pip packages: scikit-learn, pandas, numpy, fastapi, sqlalchemy
- Optional: Node.js for Next.js frontend (current: HTML only)

## 📝 Next Steps

Priority improvements:
1. ✓ Injury tracking integration
2. ✓ Interactive dashboard
3. Opponent difficulty dynamic calculation
4. Authentication & rate limiting
5. Real-time injury updates
6. Ensemble models (XGBoost, LightGBM)
7. Player watchlist & alerts
8. Historical performance tracking
