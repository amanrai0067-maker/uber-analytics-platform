"""
features.py — turns raw hourly demand into a supervised-learning feature set.
Approach: lag features + rolling stats + calendar features (classic, robust
for tabular gradient-boosted forecasting — easier to productionize than deep
sequence models for this data volume).
"""
import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

LAGS = [1, 2, 3, 24, 48, 168]        # hours: 1h, 2h, 3h, 1 day, 2 days, 1 week
ROLLING_WINDOWS = [3, 24, 168]


def build_feature_frame(hourly_df: pd.DataFrame, city: str) -> pd.DataFrame:
    """
    hourly_df: columns = [city, hour_bucket, ride_requests, completed_rides,
                           avg_surge, revenue]
    Returns a feature matrix + target `y` (ride_requests), sorted by time.
    """
    # 1. Filter city data
    df = hourly_df[hourly_df["city"] == city].copy()
    if df.empty:
        log.warning(f"No data found for city: {city}")
        return pd.DataFrame()

    df = df.sort_values("hour_bucket").reset_index(drop=True)
    df["hour_bucket"] = pd.to_datetime(df["hour_bucket"])

    # Ensure ride_requests is numeric
    df["ride_requests"] = pd.to_numeric(df["ride_requests"], errors="coerce").fillna(0)

    # 2. Calendar features (Time Cyclical Encodings)
    df["hour_of_day"] = df["hour_bucket"].dt.hour
    df["day_of_week"] = df["hour_bucket"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    
    df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    # 3. Lag features (past demand predicts future demand)
    for lag in LAGS:
        df[f"lag_{lag}h"] = df["ride_requests"].shift(lag)

    # 4. Rolling stats (using shift(1) to avoid target leakage)
    for w in ROLLING_WINDOWS:
        df[f"rolling_mean_{w}h"] = df["ride_requests"].shift(1).rolling(w).mean()
        df[f"rolling_std_{w}h"] = df["ride_requests"].shift(1).rolling(w).std()

    # Target assignment
    df["y"] = df["ride_requests"]

    # Drop NaNs created by 168h lags/rolling windows
    initial_len = len(df)
    df = df.dropna().reset_index(drop=True)
    log.info(f"Features built for {city}: {initial_len} rows -> {len(df)} rows after dropping NaNs.")

    return df


def feature_columns(df: pd.DataFrame) -> list:
    """Returns list of column names used purely as input features for ML model."""
    exclude = {
        "city", "hour_bucket", "ride_requests", "completed_rides",
        "avg_surge", "revenue", "y"
    }
    return [c for c in df.columns if c not in exclude]


if __name__ == "__main__":
    # Quick sanity check with dummy time-series data
    dates = pd.date_range(start="2026-01-01", periods=200, freq="h")
    dummy_df = pd.DataFrame({
        "city": ["Delhi"] * 200,
        "hour_bucket": dates,
        "ride_requests": np.random.randint(10, 100, size=200),
        "completed_rides": np.random.randint(5, 90, size=200),
        "avg_surge": np.random.uniform(1.0, 2.0, size=200),
        "revenue": np.random.uniform(100, 5000, size=200)
    })

    feat_df = build_feature_frame(dummy_df, city="Delhi")
    print("\n✅ Features Shape:", feat_df.shape)
    print("📊 Feature Columns Count:", len(feature_columns(feat_df)))
    print("✨ Sample Features Sample:\n", feat_df[feature_columns(feat_df)].head(2))