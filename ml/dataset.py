"""
Player-match dataset and features, built straight from raw FPL data.

Sources:
- current season: data/raw/player_<id>.json (`history`), fixtures.json, bootstrap_static.json
  (written by scraper/main.py)
- past seasons (optional): data/raw/history/<season>/merged_gw.csv + fixtures.csv from
  github.com/vaastav/Fantasy-Premier-League (written by scraper/history.py)

Every rolling feature is shifted by one match, so a row only ever sees matches
played before it. The same code builds training rows and the rows for an upcoming
gameweek, so there is no separate (and drifting) inference path.
"""
import glob
import json
import os

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, 'data', 'raw')
HISTORY_DIR = os.path.join(RAW_DIR, 'history')

POSITIONS = ['GKP', 'DEF', 'MID', 'FWD']
POSITION_BY_TYPE = {1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD'}

FEATURES = [
    'pos_GKP', 'pos_DEF', 'pos_MID', 'pos_FWD',
    'is_home', 'fdr', 'price',
    'pts_mean_3', 'pts_mean_5', 'pts_mean_10',
    'mins_mean_3', 'mins_mean_5', 'last_minutes',
    'start_rate_5', 'played_rate_5',
    'xg_mean_5', 'xa_mean_5', 'xgc_mean_5', 'bps_mean_5',
    'xgi_per90_10', 'pts_per90_10',
    'games_so_far',
    'team_xg_6', 'team_xga_6', 'opp_xg_6', 'opp_xga_6',
]

NUMERIC = ['minutes', 'starts', 'total_points', 'expected_goals', 'expected_assists',
           'expected_goals_conceded', 'bps', 'value']


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def _fixture_info(fixtures: pd.DataFrame) -> dict:
    """fixture id -> (team_h, team_a, home difficulty, away difficulty)"""
    return {int(r.id): (int(r.team_h), int(r.team_a), r.team_h_difficulty, r.team_a_difficulty)
            for r in fixtures.itertuples()}


def _side(info: dict, fixture: int, was_home: bool) -> dict:
    """team, opponent and difficulty from the player's side of a fixture"""
    if fixture not in info:
        return {'team': np.nan, 'opponent': np.nan, 'fdr': np.nan}
    h, a, dh, da = info[fixture]
    return {'team': h, 'opponent': a, 'fdr': dh} if was_home else {'team': a, 'opponent': h, 'fdr': da}


def load_current_season(raw_dir: str = RAW_DIR) -> pd.DataFrame:
    with open(os.path.join(raw_dir, 'bootstrap_static.json')) as f:
        bootstrap = json.load(f)
    with open(os.path.join(raw_dir, 'fixtures.json')) as f:
        info = _fixture_info(pd.DataFrame(json.load(f)))
    season = _season_label(bootstrap)
    types = {el['id']: el['element_type'] for el in bootstrap['elements']}

    rows = []
    for path in glob.glob(os.path.join(raw_dir, 'player_*.json')):
        element = int(os.path.basename(path)[7:-5])
        position = POSITION_BY_TYPE.get(types.get(element))
        if position is None:
            continue  # left the game, or a non-player element type
        with open(path) as f:
            history = json.load(f).get('history', [])
        for h in history:
            rows.append({
                'season': season, 'element': element, 'position': position,
                'round': h['round'], 'fixture': h['fixture'], 'kickoff_time': h['kickoff_time'],
                'was_home': bool(h['was_home']), **_side(info, h['fixture'], bool(h['was_home'])),
                **{k: h.get(k) for k in NUMERIC},
            })
    return _clean(pd.DataFrame(rows))


def load_past_season(season: str, history_dir: str = HISTORY_DIR) -> pd.DataFrame:
    gw = pd.read_csv(os.path.join(history_dir, season, 'merged_gw.csv'))
    fx = pd.read_csv(os.path.join(history_dir, season, 'fixtures.csv'))
    info = _fixture_info(fx)
    gw = gw[gw['position'].isin(['GK', 'GKP', 'DEF', 'MID', 'FWD'])].copy()
    gw['position'] = gw['position'].replace({'GK': 'GKP'})
    gw['was_home'] = gw['was_home'].astype(str).str.lower().isin(['true', '1'])
    sides = pd.DataFrame([_side(info, int(f), h) for f, h in zip(gw['fixture'], gw['was_home'])], index=gw.index)
    gw[['team', 'opponent', 'fdr']] = sides
    gw['season'] = season
    for col in NUMERIC:
        if col not in gw:
            gw[col] = np.nan
    cols = ['season', 'element', 'position', 'round', 'fixture', 'kickoff_time', 'was_home',
            'team', 'opponent', 'fdr', *NUMERIC]
    return _clean(gw[cols])


def available_past_seasons(history_dir: str = HISTORY_DIR) -> list:
    if not os.path.isdir(history_dir):
        return []
    return sorted(s for s in os.listdir(history_dir) if os.path.exists(os.path.join(history_dir, s, 'merged_gw.csv')))


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    for col in NUMERIC + ['fdr', 'round']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['kickoff_time'] = pd.to_datetime(df['kickoff_time'], utc=True, errors='coerce')
    return df.dropna(subset=['kickoff_time', 'total_points'])


def _season_label(bootstrap: dict) -> str:
    start = int(bootstrap['events'][0]['deadline_time'][:4])
    return f"{start}-{str(start + 1)[-2:]}"


# ---------------------------------------------------------------------------
# features
# ---------------------------------------------------------------------------

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add FEATURES to a player-match frame. Rows are grouped per player per season and
    ordered by kickoff; every rolling value is shifted one match back, so a row's
    features use only earlier matches. Rows with NaN outcomes (upcoming fixtures)
    get features from the player's full history.
    """
    df = df.sort_values(['season', 'element', 'kickoff_time', 'fixture']).reset_index(drop=True)
    g = df.groupby(['season', 'element'], sort=False)

    def past(col, window, how='mean'):
        shifted = g[col].shift(1)
        roll = shifted.groupby([df['season'], df['element']]).rolling(window, min_periods=1)
        out = roll.mean() if how == 'mean' else roll.sum()
        return out.reset_index(level=[0, 1], drop=True)

    df['started'] = (df['starts'].fillna((df['minutes'] >= 60).astype(float)) > 0).astype(float)
    df.loc[df['minutes'].isna(), 'started'] = np.nan
    df['played'] = (df['minutes'] > 0).astype(float)
    df.loc[df['minutes'].isna(), 'played'] = np.nan
    df['xgi'] = df['expected_goals'] + df['expected_assists']

    df['pts_mean_3'] = past('total_points', 3)
    df['pts_mean_5'] = past('total_points', 5)
    df['pts_mean_10'] = past('total_points', 10)
    df['mins_mean_3'] = past('minutes', 3)
    df['mins_mean_5'] = past('minutes', 5)
    df['last_minutes'] = g['minutes'].shift(1)
    df['start_rate_5'] = past('started', 5)
    df['played_rate_5'] = past('played', 5)
    df['xg_mean_5'] = past('expected_goals', 5)
    df['xa_mean_5'] = past('expected_assists', 5)
    df['xgc_mean_5'] = past('expected_goals_conceded', 5)
    df['bps_mean_5'] = past('bps', 5)

    mins_10 = past('minutes', 10, 'sum')
    per90 = 90 / mins_10.where(mins_10 >= 90)
    df['xgi_per90_10'] = past('xgi', 10, 'sum') * per90
    df['pts_per90_10'] = past('total_points', 10, 'sum') * per90
    df['games_so_far'] = g.cumcount().clip(upper=15)

    df['is_home'] = df['was_home'].astype(float)
    df['price'] = df['value'] / 10
    for p in POSITIONS:
        df[f'pos_{p}'] = (df['position'] == p).astype(float)
    return _add_team_strength(df)


def _add_team_strength(df: pd.DataFrame, window: int = 6) -> pd.DataFrame:
    """
    Rolling attack and defence strength per team, from the expected goals of its
    players over its previous `window` matches: how much the player's team creates
    and concedes, and the same for the opponent.
    """
    tm = (df.groupby(['season', 'fixture', 'team'], dropna=True)
            .agg(kickoff_time=('kickoff_time', 'first'), opponent=('opponent', 'first'),
                 xg_for=('expected_goals', lambda s: s.sum(min_count=1)))
            .reset_index())
    against = tm[['season', 'fixture', 'team', 'xg_for']].rename(columns={'team': 'opponent', 'xg_for': 'xg_against'})
    tm = tm.merge(against, on=['season', 'fixture', 'opponent'], how='left')
    tm = tm.sort_values(['season', 'team', 'kickoff_time', 'fixture']).reset_index(drop=True)
    gt = tm.groupby(['season', 'team'], sort=False)
    for col, name in (('xg_for', 'att'), ('xg_against', 'def')):
        shifted = gt[col].shift(1)
        tm[name] = (shifted.groupby([tm['season'], tm['team']]).rolling(window, min_periods=1).mean()
                    .reset_index(level=[0, 1], drop=True))

    strength = tm[['season', 'fixture', 'team', 'att', 'def']]
    df = df.merge(strength.rename(columns={'att': 'team_xg_6', 'def': 'team_xga_6'}),
                  on=['season', 'fixture', 'team'], how='left')
    df = df.merge(strength.rename(columns={'team': 'opponent', 'att': 'opp_xg_6', 'def': 'opp_xga_6'}),
                  on=['season', 'fixture', 'opponent'], how='left')
    return df


def baseline(df: pd.DataFrame) -> pd.Series:
    """The comparison everyone can compute: average points over the last 5 matches."""
    return df['pts_mean_5'].fillna(0)
