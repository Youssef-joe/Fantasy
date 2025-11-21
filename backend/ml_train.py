import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

def train_model():
    db = SessionLocal()
    try:
        print("Fetching data for training...")
        
        # Join features and target
        # We want: ModelFeatures.*, PlayerStats.total_points
        query = db.query(
            models.ModelFeatures.avg_points_last_5,
            models.ModelFeatures.form,
            models.ModelFeatures.opponent_difficulty,
            models.ModelFeatures.is_home,
            models.ModelFeatures.minutes_consistency,
            models.PlayerStats.total_points
        ).join(
            models.PlayerStats,
            (models.ModelFeatures.player_id == models.PlayerStats.player_id) & 
            (models.ModelFeatures.fixture_id == models.PlayerStats.fixture_id)
        )
        
        data = query.all()
        
        if not data:
            print("No data found for training.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(data, columns=[
            'avg_points_last_5', 'form', 'opponent_difficulty', 
            'is_home', 'minutes_consistency', 'total_points'
        ])
        
        print(f"Training on {len(df)} records.")
        
        X = df.drop('total_points', axis=1)
        y = df['total_points']
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train
        print("Training Random Forest Regressor...")
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        import numpy as np
        # Evaluate
        predictions = model.predict(X_test)
        mae = mean_absolute_error(y_test, predictions)
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        
        print(f"Model Performance:")
        print(f"MAE: {mae:.4f}")
        print(f"RMSE: {rmse:.4f}")
        
        # Save
        model_path = os.path.join(os.path.dirname(__file__), 'model.joblib')
        joblib.dump(model, model_path)
        print(f"Model saved to {model_path}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    train_model()
