# Quick Reference Card

## Start the System (3 Simple Steps)

### Step 1: Start API Server
```bash
cd /home/youssef/Desktop/Fantasy
source venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
➜ Opens: http://localhost:8000

### Step 2: View Predictions (Optional)
```bash
python ml/predict.py --gameweek 37 --top 20 --show-injured
```
➜ Prints top 20 players + injured list

### Step 3: Open Dashboard
```
file:///home/youssef/Desktop/Fantasy/frontend/dashboard.html
```
➜ Beautiful interactive interface

---

## Common Commands

### Get Predictions
```bash
python ml/predict.py --gameweek 37 --top 20
```

### Get Predictions + Show Injured
```bash
python ml/predict.py --gameweek 37 --top 20 --show-injured
```

### Get Top 50
```bash
python ml/predict.py --gameweek 37 --top 50
```

### Retrain Model
```bash
python ml/train.py --model random_forest
```

### Update Data
```bash
python scraper/main.py          # Scrape from FPL
python -m backend.etl           # Load to database
python -m backend.features      # Engineer features
python ml/train.py              # Retrain model
```

### API Health Check
```bash
curl http://localhost:8000/health/
```

### Get API Predictions (JSON)
```bash
curl "http://localhost:8000/predict/?gameweek=37&top_n=20"
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health/` | GET | Check system status |
| `/players/` | GET | List all players |
| `/players/{id}` | GET | Get player details |
| `/fixtures/` | GET | List all fixtures |
| `/teams/` | GET | List all teams |
| `/predict/` | GET | Get predictions |
| `/predict/injured/` | GET | Get injured players |
| `/docs` | GET | Swagger documentation |

---

## Query Parameters

### /predict/
- `gameweek` (optional): Gameweek number (1-38)
- `top_n` (optional): Number of top predictions (default: 20)

Example:
```
GET /predict/?gameweek=37&top_n=50
```

### /players/
- `skip` (optional): Skip first N records (default: 0)
- `limit` (optional): Max records to return (default: 100)

Example:
```
GET /players/?skip=0&limit=50
```

---

## Dashboard Usage

1. **Select Gameweek**: Input box at top
2. **Select Top N**: Dropdown (10, 20, 50, 100)
3. **Load Predictions**: Click button
4. **View Results**: 
   - Stats cards at top
   - Predictions table in middle
   - Injured players at bottom

---

## File Locations

| Component | Location |
|-----------|----------|
| API Server | `backend/main.py` |
| ML Model | `ml/model.joblib` |
| Dashboard | `frontend/dashboard.html` |
| Database | `backend/fantasy.db` |
| Features | `ml/features.txt` |
| Data | `data/raw/` |

---

## Useful Imports

```python
from ml.predict import predict_gameweek
from backend.database import SessionLocal
from backend import models, schemas

# Usage
db = SessionLocal()
predictions, injured = predict_gameweek(db, gameweek=37, top_n=20)
db.close()
```

---

## Troubleshooting

### API won't start
```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill the process
kill -9 <PID>
```

### No predictions appear
```bash
# Check if model exists
ls ml/model.joblib
# Retrain if missing
python ml/train.py
```

### CORS errors
- API has CORS enabled by default
- Use HTTP server for dashboard (not file://)
- Check browser console (F12) for details

### Database errors
```bash
# Reset database
rm backend/fantasy.db
python -m backend.etl
python -m backend.features
python ml/train.py
```

---

## Performance Tips

1. **Faster startup**: Use `--gameweek 37` in predict script
2. **Faster API**: Use `--workers 4` with uvicorn
3. **Faster predictions**: Cache fixture data
4. **Faster dashboard**: Use "Top 20" not "Top 100"

---

## System Architecture

```
Browser (dashboard.html)
    ↓
Fetch API /predict/?gw=37
    ↓
FastAPI (backend/main.py)
    ↓
Load Model (ml/model.joblib)
    ↓
Query DB (backend/fantasy.db)
    ↓
Engineer Features (ml/feature_engineering.py)
    ↓
Generate Predictions
    ↓
Filter Injured Players
    ↓
Return JSON
    ↓
Display in Dashboard
```

---

## Database Schema

```
Teams (20)
├─ Players (752)
│  ├─ PlayerStats (8,063)
│  ├─ InjuryStatus (752)
│  └─ ModelFeatures (8,063)
└─ Fixtures (380)
```

---

## Model Details

- **Type**: Random Forest Regressor
- **Trees**: 100
- **Features**: 8
- **Training samples**: 8,063
- **MAE**: 1.02 points
- **R²**: 0.32
- **File size**: 5.2 MB

---

## Key Features

✅ Injury tracking
✅ Real-time predictions  
✅ REST API
✅ Interactive dashboard
✅8 engineered features
✅ No data leakage
✅ Production-ready code
✅ Full documentation

---

## Contact / Issues

If predictions look off:
1. Check injury status (some players unavailable)
2. Verify gameweek has fixtures
3. Check recent player transfers
4. Consider retraining model with new data

---

**Last Updated**: 2025-11-21
**Status**: Production Ready ✅
