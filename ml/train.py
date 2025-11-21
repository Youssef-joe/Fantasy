"""
Model training pipeline.
Trains a Random Forest model on engineered features to predict player points.
"""
import os
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.database import SessionLocal
from feature_engineering import generate_training_dataset


def train_model(model_type: str = 'random_forest', test_size: float = 0.2):
    """
    Train the prediction model.
    
    Args:
        model_type: 'random_forest' or 'gradient_boosting'
        test_size: Fraction of data to use for testing
    """
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("FANTASY FOOTBALL PREDICTION MODEL TRAINING")
        print("=" * 60)
        
        print("\n[1/5] Generating training dataset...")
        df = generate_training_dataset(db)
        
        if df.empty:
            print("ERROR: No training data available. Please run ETL and feature engineering first.")
            return False
        
        print(f"✓ Dataset generated: {len(df)} records, {len(df.columns)} features")
        print(f"  Features: {', '.join(df.columns[:-1])}")
        
        print("\n[2/5] Preparing features and target...")
        X = df.drop('total_points', axis=1)
        y = df['total_points']
        
        print(f"✓ Input shape: {X.shape}")
        print(f"  Target distribution: min={y.min():.1f}, max={y.max():.1f}, mean={y.mean():.1f}")
        
        print("\n[3/5] Splitting train/test data...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        print(f"✓ Train: {len(X_train)} | Test: {len(X_test)}")
        
        print("\n[4/5] Training model...")
        if model_type == 'gradient_boosting':
            model = GradientBoostingRegressor(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=5,
                random_state=42,
                verbose=1
            )
        else:  # random_forest
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
        
        model.fit(X_train, y_train)
        print(f"✓ Model trained: {model_type}")
        
        print("\n[5/5] Evaluating performance...")
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)
        
        train_mae = mean_absolute_error(y_train, y_pred_train)
        test_mae = mean_absolute_error(y_test, y_pred_test)
        train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
        train_r2 = r2_score(y_train, y_pred_train)
        test_r2 = r2_score(y_test, y_pred_test)
        
        print("\n" + "=" * 60)
        print("MODEL PERFORMANCE METRICS")
        print("=" * 60)
        print(f"Train MAE:  {train_mae:.4f}")
        print(f"Test MAE:   {test_mae:.4f}")
        print(f"Train RMSE: {train_rmse:.4f}")
        print(f"Test RMSE:  {test_rmse:.4f}")
        print(f"Train R²:   {train_r2:.4f}")
        print(f"Test R²:    {test_r2:.4f}")
        
        # Feature importance
        if hasattr(model, 'feature_importances_'):
            print("\n" + "=" * 60)
            print("FEATURE IMPORTANCE")
            print("=" * 60)
            feature_importance = pd.DataFrame({
                'feature': X.columns,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            for idx, row in feature_importance.iterrows():
                print(f"{row['feature']:<25} {row['importance']:.4f}")
        
        # Save model
        model_dir = os.path.dirname(__file__)
        model_path = os.path.join(model_dir, 'model.joblib')
        joblib.dump(model, model_path)
        print(f"\n✓ Model saved to: {model_path}")
        
        # Save feature names
        features_path = os.path.join(model_dir, 'features.txt')
        with open(features_path, 'w') as f:
            f.write('\n'.join(X.columns))
        print(f"✓ Feature names saved to: {features_path}")
        
        print("\n" + "=" * 60)
        print("TRAINING COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        return True
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Train fantasy football prediction model')
    parser.add_argument('--model', type=str, default='random_forest',
                        choices=['random_forest', 'gradient_boosting'],
                        help='Model type to train')
    parser.add_argument('--test-size', type=float, default=0.2,
                        help='Fraction of data to use for testing')
    
    args = parser.parse_args()
    
    success = train_model(model_type=args.model, test_size=args.test_size)
    sys.exit(0 if success else 1)
