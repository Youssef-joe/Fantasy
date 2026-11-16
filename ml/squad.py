"""
Pick the best legal FPL squad for a budget with mixed-integer programming.

Rules enforced:
- 15 players: 2 GKP, 5 DEF, 5 MID, 3 FWD
- at most 3 players from any one club
- total price within the budget
- a starting XI of 1 GKP, 3-5 DEF, 2-5 MID, 1-3 FWD, and one captain from it

Objective: predicted points of the starting XI, plus the captain's points again
(captains score double), plus a small weight on the bench (cover for blanks and
injuries).
"""
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

SQUAD_SHAPE = {'GKP': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
START_RANGE = {'GKP': (1, 1), 'DEF': (3, 5), 'MID': (2, 5), 'FWD': (1, 3)}
MAX_PER_CLUB = 3
BENCH_WEIGHT = 0.1


def best_squad(players: list, budget: float = 100.0, points_key: str = 'points') -> dict:
    """
    players: dicts with player_id, position, team, price and `points_key`.
    Returns {'squad': [...], 'starting': [...ids], 'bench': [...ids], 'captain': id,
             'vice_captain': id, 'formation': 'D-M-F', 'cost': float, 'points': float}
    """
    players = [p for p in players if p.get('price') and p.get('position') in SQUAD_SHAPE]
    n = len(players)
    pts = np.array([float(p[points_key]) for p in players])
    price = np.array([float(p['price']) for p in players])

    # variable blocks: x (in squad), s (starts), c (captain), each length n
    X, S, C = 0, n, 2 * n
    nv = 3 * n
    c_obj = np.zeros(nv)
    c_obj[X:X + n] = -BENCH_WEIGHT * pts           # bench players count a little...
    c_obj[S:S + n] = -(1 - BENCH_WEIGHT) * pts     # ...starters count fully (x + s = 1 + ...)
    c_obj[C:C + n] = -pts                           # captain counted twice

    rows, lo, hi = [], [], []

    def add(coeffs, lower, upper):
        row = np.zeros(nv)
        for idx, v in coeffs:
            row[idx] += v
        rows.append(row); lo.append(lower); hi.append(upper)

    for i in range(n):
        add([(S + i, 1), (X + i, -1)], -np.inf, 0)   # start only if in squad
        add([(C + i, 1), (S + i, -1)], -np.inf, 0)   # captain only if starting
    for pos, count in SQUAD_SHAPE.items():
        idx = [i for i, p in enumerate(players) if p['position'] == pos]
        add([(X + i, 1) for i in idx], count, count)
        a, b = START_RANGE[pos]
        add([(S + i, 1) for i in idx], a, b)
    add([(S + i, 1) for i in range(n)], 11, 11)
    add([(C + i, 1) for i in range(n)], 1, 1)
    for club in {p['team'] for p in players}:
        add([(X + i, 1) for i, p in enumerate(players) if p['team'] == club], 0, MAX_PER_CLUB)
    add([(X + i, price[i]) for i in range(n)], 0, budget + 1e-6)

    res = milp(c_obj, constraints=LinearConstraint(np.array(rows), lo, hi),
               integrality=np.ones(nv), bounds=Bounds(0, 1), options={'time_limit': 60})
    if res.x is None:
        raise RuntimeError(f"No legal squad found within £{budget}m: {res.message}")

    x = res.x
    chosen = [i for i in range(n) if x[X + i] > 0.5]
    starters = [i for i in chosen if x[S + i] > 0.5]
    bench = [i for i in chosen if x[S + i] <= 0.5]
    captain = next(i for i in starters if x[C + i] > 0.5)
    vice = max((i for i in starters if i != captain), key=lambda i: pts[i])

    order = {'GKP': 0, 'DEF': 1, 'MID': 2, 'FWD': 3}
    starters.sort(key=lambda i: (order[players[i]['position']], -pts[i]))
    # FPL bench order: backup keeper first, then outfielders by expected points
    bench.sort(key=lambda i: (players[i]['position'] != 'GKP', -pts[i]))
    counts = {pos: sum(players[i]['position'] == pos for i in starters) for pos in ('DEF', 'MID', 'FWD')}

    return {
        'squad': [players[i]['player_id'] for i in chosen],
        'starting': [players[i]['player_id'] for i in starters],
        'bench': [players[i]['player_id'] for i in bench],
        'captain': players[captain]['player_id'],
        'vice_captain': players[vice]['player_id'],
        'formation': f"{counts['DEF']}-{counts['MID']}-{counts['FWD']}",
        'cost': round(float(price[chosen].sum()), 1),
        'points': round(float(pts[starters].sum() + pts[captain]), 2),
        'bench_points': round(float(pts[bench].sum()), 2),
    }
