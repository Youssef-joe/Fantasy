"""
Export ML predictions directly to static JSON files for Vercel Jamstack deployment (Option B).
"""

import os
import sys
import json
from datetime import datetime

# Setup paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "frontend", "data", "predictions")
os.makedirs(OUTPUT_DIR, exist_ok=True)

sys.path.insert(0, PROJECT_ROOT)

def export_predictions_for_gameweek(gameweek: int, top_n: int = 100):
    """
    Run the ML prediction pipeline and export the result to static JSON.
    Fails loudly instead of writing placeholder data, so a broken pipeline
    never overwrites the last good feed.
    """
    from backend.database import SessionLocal
    from ml.predict import predict_gameweek

    db = SessionLocal()
    try:
        predictions, injured_players = predict_gameweek(
            db, gameweek=gameweek, top_n=top_n, include_injured=False
        )
    finally:
        db.close()

    if not predictions:
        raise RuntimeError(
            f"No predictions produced for GW{gameweek}; refusing to overwrite the feed. "
            "Check that the database is populated and the model is trained."
        )
    print(f"✓ Retrieved {len(predictions)} predictions from ML model for GW{gameweek}")

    data = {
        "gameweek": gameweek,
        "season": "2024-2025",
        "model_type": "RandomForestRegressor(100)",
        "mae_benchmark": 1.02,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "predictions": predictions,
        "injured_players": injured_players
    }

    out_file = os.path.join(OUTPUT_DIR, f"gw{gameweek}.json")
    with open(out_file, "w") as f:
        json.dump(data, f, indent=2)

    latest_file = os.path.join(OUTPUT_DIR, "latest.json")
    with open(latest_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✓ Exported predictions to {out_file} and {latest_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python ml/export_predictions.py <gameweek>")
    export_predictions_for_gameweek(int(sys.argv[1]))
