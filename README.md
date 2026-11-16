# Fantasy Football Prediction System

Predicts Fantasy Premier League (FPL) points per player per gameweek with a Random Forest model, and publishes the results as a static website.

## How it works

```
FPL API + Understat
  ↓  scraper/            raw JSON in data/raw/
  ↓  backend/etl.py      SQLite database (data/fantasy.db)
  ↓  backend/features.py engineered features per player-match
  ↓  ml/train.py         Random Forest → ml/model.joblib
  ↓  ml/predict.py       ranked predictions for a gameweek
  ↓  ml/export_predictions.py
frontend/data/predictions/*.json   ← static feed read by the site
  ↓
frontend/ (static HTML) deployed on Vercel
```

There is no backend server in production. The site reads the pre-generated JSON feed. `data/`, the database, and the trained model are local build artefacts and are not committed.

## Setup

Python 3.9+:

```bash
pip install -r scraper/requirements.txt -r backend/requirements.txt -r ml/requirements.txt
```

Optional CLI (Node.js):

```bash
npm install -g .
```

## Running the pipeline

```bash
python scraper/main.py                     # 1. scrape FPL + Understat
python -m backend.etl                      # 2. load into SQLite
python -m backend.features                 # 3. engineer features
python ml/train.py                         # 4. train the model
python ml/predict.py --gameweek 13 --top 20 --show-injured   # inspect predictions
python ml/export_predictions.py 13         # 5. write frontend/data/predictions/gw13.json + latest.json
```

The same steps with the CLI:

```bash
fantasy-cli scrape
fantasy-cli etl
fantasy-cli features
fantasy-cli train
fantasy-cli predict --gameweek 13 --top 20 --show-injured
fantasy-cli export --gameweek 13
fantasy-cli serve                          # view the site at http://localhost:3000
```

`export` fails with an error if the model produces no predictions. It never writes placeholder data over the existing feed.

## Frontend

- `frontend/index.html`: landing page and predictor
- `frontend/dashboard.html`: predictions table and injured list
- `frontend/data/predictions/`: `gwNN.json`, `latest.json`, `manifest.json`

To preview locally: `python -m http.server 3000 --directory frontend` (or `fantasy-cli serve`).

## Deployment

`vercel.json` serves `frontend/` as a static site (no build step, clean URLs, so `/dashboard` works). Pushing updated feed files to `main` triggers a redeploy.

## Model

- Random Forest regressor, 100 trees
- Features: rolling points (last 5 / last 10), form, opponent difficulty, home/away, minutes consistency, goal threat, injury risk
- `ml/train.py` prints MAE, RMSE, R² and feature importance on a held-out split

## Project structure

- `scraper/`: FPL and Understat clients
- `backend/`: SQLAlchemy models, ETL, feature engineering
- `ml/`: training, prediction, export
- `frontend/`: static site and prediction feed
- `bin/cli.js`: `fantasy-cli`
