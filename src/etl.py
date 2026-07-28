"""
etl.py — loads generated CSV into Postgres and refreshes the materialized view.
Run after data/generate_data.py, or schedule it (cron/Airflow) for "new data daily".
"""
import logging
import os
import pandas as pd
from sqlalchemy import text
from src.db import engine  # Relative import fix for project structure

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)


def load_dimension_tables(df: pd.DataFrame):
    """Extracts riders and drivers from main rides DataFrame and populates dimension tables."""
    # 1. Populate Riders Table
    riders = df[["rider_id"]].drop_duplicates().rename(columns={"rider_id": "rider_id"})
    riders["rider_name"] = "Rider_" + riders["rider_id"].astype(str)
    riders["city"] = "Delhi"          # Placeholder — riders can move across cities
    riders["signup_date"] = "2025-01-01"

    # 2. Populate Drivers Table
    drivers = df[["driver_id", "vehicle_type", "city"]].drop_duplicates("driver_id")
    drivers["driver_name"] = "Driver_" + drivers["driver_id"].astype(str)
    drivers["rating"] = 4.5
    drivers["joined_date"] = "2025-01-01"

    riders.to_sql("riders", engine, if_exists="append", index=False, method="multi", chunksize=5000)
    drivers[["driver_id", "driver_name", "city", "vehicle_type", "rating", "joined_date"]]\
        .to_sql("drivers", engine, if_exists="append", index=False, method="multi", chunksize=5000)
    
    log.info("Loaded %d riders, %d drivers", len(riders), len(drivers))


def load_rides(df: pd.DataFrame):
    """Loads ride transaction data into the rides table."""
    ride_cols = [
        "ride_id", "rider_id", "driver_id", "city", "pickup_lat", "pickup_lng",
        "drop_lat", "drop_lng", "request_ts", "distance_km", "base_fare",
        "surge_multiplier", "final_fare", "payment_type", "vehicle_type", "ride_status",
        "rider_rating", "driver_rating",
    ]
    
    # Filter columns that are present in the dataframe to avoid KeyErrors
    available_cols = [col for col in ride_cols if col in df.columns]
    
    df[available_cols].to_sql("rides", engine, if_exists="append", index=False,
                             method="multi", chunksize=5000)
    log.info("Loaded %d rides", len(df))


def refresh_materialized_view():
    """Refreshes the materialized view for hourly demand analytics."""
    with engine.begin() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW mv_hourly_demand;"))
    log.info("Refreshed mv_hourly_demand")


def run_etl(csv_path: str = None):
    """Main ETL runner with fallback path logic."""
    if csv_path is None:
        csv_path = "data/rides.csv" if os.path.exists("data/rides.csv") else "../data/rides.csv"
        
    if not os.path.exists(csv_path):
        log.warning("CSV file not found at path: %s. ETL execution skipped.", csv_path)
        return

    log.info("Reading dataset from %s ...", csv_path)
    df = pd.read_csv(csv_path, parse_dates=["request_ts"])
    
    # Load dimensions first, then fact table
    try:
        load_dimension_tables(df)
    except Exception as e:
        log.warning("Dimension load skipped or already existing: %s", e)
        
    load_rides(df)
    refresh_materialized_view()
    log.info("ETL complete: %d rows processed", len(df))


if __name__ == "__main__":
    run_etl()