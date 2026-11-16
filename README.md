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
python scraper/main.py                     # 1. scrape the FPL API into data/raw/
python -m backend.etl                      # 2. load into SQLite
python -m backend.features                 # 3. engineer features
python ml/train.py                         # 4. train the model (writes ml/metrics.json)
python ml/predict.py --top 20 --show-injured   # inspect predictions for the next gameweek
python ml/export_predictions.py            # 5. write the feed for the next gameweek
python ml/validate_feed.py                 # 6. check the feed
```

The season, the next gameweek and its deadline come from FPL's `bootstrap-static` data, so nothing needs changing between gameweeks or seasons. Pass a number (`python ml/export_predictions.py 12`) to export a specific gameweek.

Understat xG scraping is optional and not used by the model yet: `pip install -r scraper/requirements-understat.txt`, then `python scraper/main.py --understat`.

The same steps with the CLI:

```bash
fantasy-cli scrape
fantasy-cli etl
fantasy-cli features
fantasy-cli train
fantasy-cli predict --top 20 --show-injured
fantasy-cli export
fantasy-cli serve                          # view the site at http://localhost:3000
```

`export` checks the feed before writing it and exits with an error if anything is wrong (no predictions, wrong gameweek, missing fields). It never writes placeholder data over the existing feed.

## Frontend

- `frontend/index.html`: landing page and predictor
- `frontend/dashboard.html`: predictions table and injured list
- `frontend/data/predictions/`: `gwNN.json`, `latest.json`, `manifest.json`

Feed format (`feed_version: 2`):

| Field | Contents |
|---|---|
| `season`, `gameweek`, `deadline_time`, `generated_at` | from FPL / the export run |
| `model` | metrics measured by the last training run (`ml/metrics.json`), including a last-5-average baseline |
| `predictions[]` | one row per player, sorted by `predicted_points`: team, position, opponent(s), `fixtures[]` (two in a double gameweek), `avg_last_5`, `price`, `selected_by_percent`, `chance_of_playing`, `status`, `news` |
| `injured_players[]` | players FPL flags (injured, suspended, doubtful…) who have played this season, most-owned first |
| `fixtures_by_team` | next 5 gameweeks of fixtures per team with FPL difficulty (1-5) |

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
