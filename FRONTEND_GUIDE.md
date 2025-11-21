# Frontend Dashboard Guide

## Overview

The Fantasy Football Predictions dashboard provides an interactive web interface to view:
- **Top player predictions** for upcoming gameweeks
- **Injury status** of unavailable players
- **Real-time statistics** and insights
- **Performance metrics** of the ML model

## Files

- **`frontend/dashboard.html`** - Single-page application (no build required)
  - Modern responsive design with Tailwind CSS
  - Real-time data fetching from FastAPI backend
  - Interactive tables with player predictions and injury reports

## How to Use

### Option 1: Open Directly in Browser

1. **Start the backend API:**
   ```bash
   cd /home/youssef/Desktop/Fantasy
   source venv/bin/activate
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```

2. **Open the dashboard:**
   - File → Open File → select `frontend/dashboard.html`
   - Or open the file directly: `file:///home/youssef/Desktop/Fantasy/frontend/dashboard.html`

### Option 2: Use Simple HTTP Server (Recommended)

1. **Start the backend API (Terminal 1):**
   ```bash
   cd /home/youssef/Desktop/Fantasy
   source venv/bin/activate
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```

2. **Start a simple HTTP server (Terminal 2):**
   ```bash
   cd /home/youssef/Desktop/Fantasy/frontend
   python -m http.server 3000
   ```

3. **Open browser:**
   - Navigate to: `http://localhost:3000/dashboard.html`

## Features

### Gameweek Selection
- Select any gameweek (1-38) to view predictions
- Choose how many top players to display (10, 20, 50, or 100)
- Click "Load Predictions" to fetch fresh data

### Statistics Dashboard
- **Gameweek**: Currently selected gameweek
- **Predictions**: Number of available predictions
- **Injured Players**: Count of unavailable players
- **Avg Prediction**: Average predicted points across top players

### Predictions Table
Shows ranked predictions with:
- **Rank**: Position in top rankings
- **Player**: Full name
- **Team**: Team abbreviation
- **Position**: GKP, DEF, MID, FWD
- **Opponent**: Opposing team
- **Location**: 🏠 Home or ✈️ Away
- **Predicted Pts**: ML model prediction (0-20 scale)
- **Recent Form**: Average points last 5 games

### Injury Report
Lists unavailable players with:
- **Player Name**: Full name
- **Status**: Injured, Doubtful, or Unavailable
- **Expected Return**: Estimated gameweek of return (if available)

## Color Coding

- **Position Badges:**
  - GKP (Goalkeeper): Blue background
  - DEF (Defender): Green background
  - MID (Midfielder): Yellow background
  - FWD (Forward): Red background

- **Location Badges:**
  - Home (🏠): Light blue
  - Away (✈️): Light purple

- **Injury Status:**
  - Red background indicating unavailable players

## API Endpoints Used

The dashboard communicates with the backend API:

```
GET /health/
  Returns: {"status": "ok", "message": "..."}

GET /predict/?gameweek=37&top_n=20
  Returns: {
    "gameweek": 37,
    "predictions": [...],
    "injured_players": [...]
  }

GET /predict/injured/?gameweek=37
  Returns: {
    "gameweek": 37,
    "injured_players": [...]
  }
```

## Troubleshooting

### Issue: "Failed to load predictions. Make sure the API is running..."

**Solution:**
1. Check if API is running: `curl http://localhost:8000/health/`
2. Start the API: `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
3. Ensure you're using the correct port (8000)

### Issue: No predictions appear for a gameweek

**Reasons:**
- Gameweek doesn't have fixtures in the database
- Model hasn't been trained yet
- Try gameweek 37 (has sample data)

**Solution:**
1. Train the model: `python ml/train.py`
2. Try a different gameweek (1-38)

### Issue: CORS (Cross-Origin) Error

**Cause:** Browser security blocking requests

**Solution:**
1. Use HTTP server method (Option 2 above)
2. Or run API with correct CORS headers (already configured)
3. Check browser console (F12) for details

## Performance Notes

- **Loading time:** 1-3 seconds depending on network
- **Predictions generated live:** Each request triggers feature engineering
- **Optimization tip:** Use "Top 20" for faster loading than "Top 100"

## Future Enhancements

- Add chart visualizations of player trends
- Filter by position or team
- Export predictions to CSV
- Compare predictions across gameweeks
- Add watchlist functionality
- Real-time injury updates
