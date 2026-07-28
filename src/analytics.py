"""
analytics.py — thin, reusable query functions.
Includes CSV Fallback for Cloud Deployment without a live DB connection.
"""
import os
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

# Try importing database engine (Fallback if DB connection fails)
try:
    from src.db import engine
except Exception:
    engine = None

# Helper function to load local CSV safely
def load_csv_data() -> pd.DataFrame:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "rides.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if "request_ts" in df.columns:
            df["request_ts"] = pd.to_datetime(df["request_ts"])
        return df
    return pd.DataFrame()


# ==========================================
# 1. ORM Session-based Functions (For test_db.py)
# ==========================================

def get_ride_demand_patterns(db: Session):
    query = """
        SELECT 
            city,
            EXTRACT(HOUR FROM request_ts) as hour_of_day,
            COUNT(ride_id) as total_rides,
            COUNT(CASE WHEN ride_status = 'completed' THEN 1 END) as completed_rides,
            COUNT(CASE WHEN ride_status = 'cancelled' THEN 1 END) as cancelled_rides
        FROM rides
        GROUP BY city, hour_of_day
        ORDER BY city, hour_of_day;
    """
    result = db.execute(text(query))
    return result.fetchall()


def get_revenue_analytics(db: Session):
    query = """
        SELECT 
            city,
            SUM(final_fare) as total_revenue,
            AVG(final_fare) as avg_fare,
            AVG(driver_rating) as avg_driver_rating
        FROM rides
        WHERE ride_status = 'completed'
        GROUP BY city
        ORDER BY total_revenue DESC;
    """
    result = db.execute(text(query))
    return result.fetchall()


# ==========================================
# 2. Pandas Engine-based Functions (With CSV Fallback)
# ==========================================

def get_demand_by_hour(city: str | None = None, days: int = 30) -> pd.DataFrame:
    try:
        query = """
            SELECT city, EXTRACT(HOUR FROM request_ts)::int AS hour_of_day,
                   EXTRACT(DOW FROM request_ts)::int AS day_of_week,
                   COUNT(*) AS total_requests
            FROM rides
            WHERE request_ts >= NOW() - (:days || ' days')::interval
              AND (:city IS NULL OR city = :city)
            GROUP BY city, hour_of_day, day_of_week
            ORDER BY city, day_of_week, hour_of_day
        """
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn, params={"city": city, "days": days})
    except Exception:
        df = load_csv_data()
        if df.empty:
            return pd.DataFrame()
        if city and city != "All":
            df = df[df["city"] == city]
        df["hour_of_day"] = df["request_ts"].dt.hour
        df["day_of_week"] = df["request_ts"].dt.dayofweek
        result = df.groupby(["city", "hour_of_day", "day_of_week"]).size().reset_index(name="total_requests")
        return result


def get_surge_analysis(city: str | None = None) -> pd.DataFrame:
    try:
        query = """
            SELECT city, date_trunc('hour', request_ts) AS hour_bucket,
                   ROUND(AVG(surge_multiplier)::numeric, 2) AS avg_surge,
                   ROUND((COUNT(*) FILTER (WHERE ride_status='cancelled')::numeric
                          / NULLIF(COUNT(*), 0) * 100), 2) AS cancel_rate_pct
            FROM rides
            WHERE (:city IS NULL OR city = :city)
            GROUP BY city, hour_bucket
            ORDER BY hour_bucket DESC
            LIMIT 500
        """
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn, params={"city": city})
    except Exception:
        df = load_csv_data()
        if df.empty:
            return pd.DataFrame()
        if city and city != "All":
            df = df[df["city"] == city]
        df["hour_bucket"] = df["request_ts"].dt.floor("h")
        grouped = df.groupby(["city", "hour_bucket"]).agg(
            avg_surge=("surge_multiplier", "mean"),
            total_rides=("ride_id", "count"),
            cancelled_rides=("ride_status", lambda x: (x == "cancelled").sum())
        ).reset_index()
        grouped["cancel_rate_pct"] = (grouped["cancelled_rides"] / grouped["total_rides"]) * 100
        return grouped.sort_values(by="hour_bucket", ascending=False).head(500)


def get_driver_performance(city: str | None = None, top_n: int = 50) -> pd.DataFrame:
    try:
        query = """
            SELECT d.driver_id, d.driver_name, d.city,
                   COUNT(r.ride_id) AS total_rides,
                   ROUND(AVG(r.driver_rating)::numeric, 2) AS avg_rating,
                   SUM(r.final_fare) FILTER (WHERE r.ride_status='completed') AS total_earnings,
                   ROUND((COUNT(*) FILTER (WHERE r.ride_status='completed')::numeric
                          / NULLIF(COUNT(*), 0) * 100), 2) AS completion_rate_pct
            FROM drivers d
            LEFT JOIN rides r ON r.driver_id = d.driver_id
            WHERE (:city IS NULL OR d.city = :city)
            GROUP BY d.driver_id, d.driver_name, d.city
            ORDER BY total_earnings DESC NULLS LAST
            LIMIT :top_n
        """
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn, params={"city": city, "top_n": top_n})
    except Exception:
        df = load_csv_data()
        if df.empty:
            return pd.DataFrame()
        if city and city != "All":
            df = df[df["city"] == city]
        grouped = df.groupby(["driver_id", "city"]).agg(
            total_rides=("ride_id", "count"),
            avg_rating=("driver_rating", "mean"),
            total_earnings=("final_fare", lambda x: x[df.loc[x.index, "ride_status"] == "completed"].sum()),
            completed_rides=("ride_status", lambda x: (x == "completed").sum())
        ).reset_index()
        grouped["completion_rate_pct"] = (grouped["completed_rides"] / grouped["total_rides"]) * 100
        return grouped.sort_values(by="total_earnings", ascending=False).head(top_n)


def get_revenue_trend(city: str | None = None) -> pd.DataFrame:
    try:
        query = """
            WITH daily AS (
                SELECT date_trunc('day', request_ts) AS day, city,
                       SUM(final_fare) FILTER (WHERE ride_status='completed') AS revenue
                FROM rides
                WHERE (:city IS NULL OR city = :city)
                GROUP BY day, city
            )
            SELECT day, city, revenue,
                   ROUND(((revenue - LAG(revenue) OVER (PARTITION BY city ORDER BY day))
                          / NULLIF(LAG(revenue) OVER (PARTITION BY city ORDER BY day), 0) * 100)::numeric, 2
                   ) AS pct_growth_dod
            FROM daily
            ORDER BY city, day
        """
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn, params={"city": city})
    except Exception:
        df = load_csv_data()
        if df.empty:
            return pd.DataFrame()
        if city and city != "All":
            df = df[df["city"] == city]
        df_completed = df[df["ride_status"] == "completed"].copy()
        df_completed["day"] = df_completed["request_ts"].dt.floor("D")
        daily = df_completed.groupby(["day", "city"])["final_fare"].sum().reset_index(name="revenue")
        daily = daily.sort_values(by=["city", "day"])
        daily["pct_growth_dod"] = daily.groupby("city")["revenue"].pct_change() * 100
        return daily


def get_demand_hotspots(city: str | None = None, days: int = 7) -> pd.DataFrame:
    try:
        query = """
            SELECT city, ROUND(pickup_lat::numeric, 3) AS lat_bucket,
                   ROUND(pickup_lng::numeric, 3) AS lng_bucket,
                   COUNT(*) AS demand_count
            FROM rides
            WHERE request_ts >= NOW() - (:days || ' days')::interval
              AND (:city IS NULL OR city = :city)
            GROUP BY city, lat_bucket, lng_bucket
            ORDER BY demand_count DESC
            LIMIT 200
        """
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn, params={"city": city, "days": days})
    except Exception:
        df = load_csv_data()
        if df.empty:
            return pd.DataFrame()
        if city and city != "All":
            df = df[df["city"] == city]
        if "pickup_lat" in df.columns and "pickup_lng" in df.columns:
            df["lat_bucket"] = df["pickup_lat"].round(3)
            df["lng_bucket"] = df["pickup_lng"].round(3)
            result = df.groupby(["city", "lat_bucket", "lng_bucket"]).size().reset_index(name="demand_count")
            return result.sort_values(by="demand_count", ascending=False).head(200)
        return pd.DataFrame()