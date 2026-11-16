# Fantasy Football Prediction System

Predicts Fantasy Premier League (FPL) points per player per gameweek with a gradient-boosted model, and publishes the results as a static website.

## How it works

```
FPL API ──────────────► scraper/main.py     this season: data/raw/*.json
vaastav/FPL dataset ──► scraper/history.py  past seasons: data/raw/history/<season>/
                          ↓
                        ml/dataset.py       player-match rows + leak-free rolling features
                          ↓
                        ml/train.py         evaluate by gameweek, fit → ml/model.joblib
                          ↓
                        ml/predict.py       next gameweek, scaled by chance of playing
                          ↓
                        ml/export_predictions.py → frontend/data/predictions/*.json
                          ↓
                        frontend/ (static) deployed on Vercel
```

There is no backend server or database. The site reads the pre-generated JSON feed. `data/` and the trained model are local build artefacts and are not committed.

## Setup

Python 3.10+:

```bash
pip install -r scraper/requirements.txt -r ml/requirements.txt
```

Optional CLI (Node.js):

```bash
npm install -g .
```

## Running the pipeline

```bash
python scraper/main.py                     # 1. scrape the FPL API into data/raw/
python scraper/history.py                  # 2. download the 3 previous seasons (once; cached)
python ml/train.py                         # 3. evaluate and train (writes ml/model.joblib, ml/metrics.json)
python ml/predict.py --top 20 --show-injured   # inspect predictions for the next gameweek
python ml/export_predictions.py            # 4. write the feed for the next gameweek
python ml/validate_feed.py                 # 5. check the feed
```

The season, the next gameweek and its deadline come from FPL's `bootstrap-static` data, so nothing needs changing between gameweeks or seasons. Pass a number (`python ml/export_predictions.py 12`) to export a specific gameweek.

Understat xG scraping is optional and not used by the model yet: `pip install -r scraper/requirements-understat.txt`, then `python scraper/main.py --understat`.

The same steps with the CLI:

```bash
fantasy-cli scrape
fantasy-cli history
fantasy-cli train
fantasy-cli predict --top 20 --show-injured
fantasy-cli export
fantasy-cli serve                          # view the site at http://localhost:3000
```

`export` checks the feed before writing it and exits with an error if anything is wrong (no predictions, wrong gameweek, missing fields). It never writes placeholder data over the existing feed.

## Frontend

A single page, plain HTML/CSS/JS with no build step and no third-party scripts (only Google Fonts), so it runs under a strict Content-Security-Policy. Every number on it comes from `latest.json`.

- `frontend/index.html`: the page. Sections:
  - hero: gameweek, deadline countdown, rotating top-5 spotlight
  - availability wire: scrolling injury news
  - captain / differential / value picks
  - best XI on a 3D pitch, with a formation switcher
  - fixture difficulty heatmap
  - searchable player board with a detail drawer
  - model accuracy against the baseline
- `frontend/assets/js/app.js`: loads the feed and renders every section
- `frontend/assets/js/pitch.js`: the animated floodlit pitch behind the hero (canvas; pauses off-screen)
- `frontend/assets/js/teams.js`: club names and kit colours by FPL short name
- `frontend/assets/css/site.css`: all styles; honours `prefers-reduced-motion`
- `frontend/dashboard.html`: redirects to `/#players` (old URL)
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

## Automatic updates

[`.github/workflows/update-predictions.yml`](.github/workflows/update-predictions.yml) runs the whole pipeline (scrape → past seasons (cached) → train → export → validate):

- **Daily at 06:00 UTC** and on demand (Actions → *Update predictions* → *Run workflow*, optionally with a gameweek). If the feed changed, it commits it to `main`, which triggers a Vercel deploy.
- **On pull requests** that touch `scraper/` or `ml/`, as a check. Nothing is committed; the generated feed is attached to the run as an artifact.

Each run's summary shows the gameweek, the model's test results against the baseline, and the top 15 players. A failed run commits nothing, so the site keeps the last good feed, and GitHub emails the repo owner.

## Deployment

`vercel.json` serves `frontend/` as a static site (no build step, clean URLs, so `/dashboard` works). Pushing updated feed files to `main` triggers a redeploy.

## Model

**What it predicts:** FPL points for each player-fixture.

**Model:** `HistGradientBoostingRegressor` with Poisson loss. Negative points are clipped to 0 for training.

**Training data:** this season from the FPL API, plus the three previous seasons (about 93,000 player-matches). Past seasons come from [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League) (MIT licence; the data belongs to Fantasy Premier League).

**Features** (`ml/dataset.py`, 26 in total). Every rolling stat uses only matches before the one being predicted:

| Group | Features |
|---|---|
| Points form | averages over the last 3, 5 and 10 matches; points per 90 |
| Minutes | averages over the last 3 and 5 matches, last match, start rate, appearance rate |
| Underlying stats | xG, xA, xG conceded, bonus-point score; xG involvement per 90 |
| Fixture | FPL difficulty, home or away |
| Team strength | rolling xG for and against, for the player's team and the opponent |
| Player | position, price |

**Availability:** predictions are multiplied by FPL's chance of playing. Players ruled out (injured, suspended, unavailable, 0%) are listed separately.

**Evaluation** (`ml/train.py`): for each of the last 5 finished gameweeks, the model trains only on earlier matches and predicts that gameweek. The baseline is each player's average over their last 5 matches.

| Tested on GW6–10, 2026-27 | Model | Baseline |
|---|---|---|
| Average error (points) | 1.09 | 1.20 |
| Rank correlation with actual points | 0.71 | 0.68 |
| Average points of the top-20 predicted players | 4.7 | 4.4 |

The best possible top-20 score is 10.5. The numbers from each run are written to `ml/metrics.json` and published in the feed.

## Project structure

- `scraper/`: FPL API client and past-season downloader
- `ml/`: dataset and features, training, prediction, export, feed validation
- `frontend/`: static site and prediction feed
- `bin/cli.js`: `fantasy-cli`
