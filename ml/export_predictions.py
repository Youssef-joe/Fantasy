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

def export_predictions_for_gameweek(gameweek: int = 38, top_n: int = 100):
    """
    Attempt to run the ML prediction pipeline and export to static JSON.
    If database is not available, uses fallback data.
    """
    predictions = []
    injured_players = []

    try:
        from backend.database import SessionLocal
        from ml.predict import predict_gameweek

        db = SessionLocal()
        try:
            preds, inj = predict_gameweek(db, gameweek=gameweek, top_n=top_n, include_injured=False)
            predictions = preds
            injured_players = inj
            print(f"✓ Retrieved {len(predictions)} live predictions from ML model for GW{gameweek}")
        finally:
            db.close()
    except Exception as e:
        print(f"ℹ Database/model not ready ({e}). Generating static feed via build-static-data.js")
        # Run node fallback generator
        import subprocess
        subprocess.run(["node", os.path.join(PROJECT_ROOT, "bin", "build-static-data.js")], check=True)
        return

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
    gw = int(sys.argv[1]) if len(sys.argv) > 1 else 38
    export_predictions_for_gameweek(gw)

