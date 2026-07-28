"""
train_forecast.py — trains one demand-forecasting model per city and logs
everything to MLflow (so you can show "experiment tracking" on your resume,
and so recruiters see a reproducible ML pipeline, not a one-off notebook).

Run:
    python src/train_forecast.py
"""
import os
import joblib
import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from sqlalchemy import text

# Updated relative imports to match project module structure
from src.db import engine
from src.features import build_feature_frame, feature_columns

MODEL_DIR = "models"
TEST_HOURS = 24 * 14   # hold out last 2 weeks for evaluation


def load_hourly_demand() -> pd.DataFrame:
    """Fetches pre-aggregated hourly demand metrics from the Materialized View."""
    query = """
        SELECT city, hour_bucket, ride_requests, completed_rides, avg_surge, revenue
        FROM mv_hourly_demand
        ORDER BY city, hour_bucket
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def train_one_city(hourly_df: pd.DataFrame, city: str):
    """Trains a LightGBM model for a specific city and logs metadata to MLflow."""
    feat_df = build_feature_frame(hourly_df, city)
    
    # Check if we have enough historical data to split into train & test
    min_required_rows = 48  # Minimum fallback rows if dataset is small
    if len(feat_df) < min_required_rows:
        print(f"⚠️ [skip] {city}: Not enough history ({len(feat_df)} rows)")
        return None

    # Dynamically adjust TEST_HOURS if dataset is smaller than 2 weeks
    actual_test_hours = TEST_HOURS if len(feat_df) > (TEST_HOURS + 100) else int(len(feat_df) * 0.2)

    cols = feature_columns(feat_df)
    train_df = feat_df.iloc[:-actual_test_hours]
    test_df = feat_df.iloc[-actual_test_hours:]

    model = LGBMRegressor(
        n_estimators=400,
        learning_rate=0.03,
        num_leaves=31,
        max_depth=-1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1  # Suppress internal warnings
    )
    model.fit(train_df[cols], train_df["y"])

    preds = np.clip(model.predict(test_df[cols]), 0, None)
    mae = mean_absolute_error(test_df["y"], preds)
    mape = mean_absolute_percentage_error(test_df["y"].clip(lower=1), preds.clip(min=1))

    # MLflow Experiment Tracking
    with mlflow.start_run(run_name=f"demand_forecast_{city}"):
        mlflow.log_param("city", city)
        mlflow.log_param("n_features", len(cols))
        mlflow.log_param("test_hours", actual_test_hours)
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("mape", mape)
        mlflow.lightgbm.log_model(model, artifact_path="model")

    # Ensure output model directory exists
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, f"demand_{city}.pkl")
    
    joblib.dump({"model": model, "features": cols}, model_path)
    print(f"✅ [{city}] MAE={mae:.2f}  MAPE={mape*100:.1f}%  -> {model_path}")
    
    return {"city": city, "mae": round(mae, 2), "mape": f"{mape*100:.1f}%"}

def main():
    # Fix for Windows spaces in username / path (%20 / PermissionError issue)
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mlflow_db_path = os.path.join(current_dir, "mlflow.db").replace("\\", "/")
    mlflow.set_tracking_uri(f"sqlite:///{mlflow_db_path}")

    mlflow.set_experiment("uber_demand_forecasting")
    print("🚀 Fetching hourly demand data from PostgreSQL...")
    
    hourly_df = load_hourly_demand()
    if hourly_df.empty:
        print("❌ No data found in `mv_hourly_demand`. Please run ETL first!")
        return

    results = []
    cities = hourly_df["city"].unique()
    print(f"📈 Found {len(cities)} cities: {list(cities)}. Training models...\n")
    
    for city in cities:
        res = train_one_city(hourly_df, city)
        if res:
            results.append(res)
            
    print("\n=== 🎯 ML Training Summary ===")
    for r in results:
        print(r)

if __name__ == "__main__":
    main()