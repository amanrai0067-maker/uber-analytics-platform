"""
generate_data.py
----------------
Generates a realistic synthetic ride-hailing dataset (Uber-style) since the
real Uber dataset isn't public. Demand follows real-world patterns:
morning/evening rush hours, weekend nightlife spikes, and city-specific
base demand — so forecasting models trained on it behave like real ones.

Usage:
    python generate_data.py --rides 200000 --out data/rides.csv
"""
import argparse
import random
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

CITIES = {
    "Delhi":     {"center": (28.6139, 77.2090), "base_demand": 1.3},
    "Mumbai":    {"center": (19.0760, 72.8777), "base_demand": 1.5},
    "Bengaluru": {"center": (12.9716, 77.5946), "base_demand": 1.2},
    "Hyderabad": {"center": (17.3850, 78.4867), "base_demand": 1.0},
    "Pune":      {"center": (18.5204, 73.8567), "base_demand": 0.9},
}
VEHICLE_TYPES = ["Go", "Premier", "Auto", "Moto"]
PAYMENT_TYPES = ["UPI", "Card", "Cash", "Wallet"]


def hourly_demand_multiplier(hour: int, dow: int) -> float:
    """Rush hours (8-10am, 6-9pm) spike demand; weekends shift the pattern."""
    is_weekend = dow >= 5
    if is_weekend:
        if 20 <= hour <= 23:      # weekend nightlife
            return 2.0
        if 11 <= hour <= 14:      # weekend brunch/outing
            return 1.4
        return 0.7
    else:
        if 8 <= hour <= 10 or 18 <= hour <= 21:   # weekday commute
            return 2.2
        if 0 <= hour <= 5:
            return 0.2
        return 1.0


def surge_from_demand(demand_mult: float) -> float:
    """Surge kicks in once effective demand crosses a threshold, with noise."""
    if demand_mult > 1.8:
        return round(np.random.uniform(1.5, 2.8), 2)
    elif demand_mult > 1.3:
        return round(np.random.uniform(1.1, 1.6), 2)
    return round(np.random.uniform(1.0, 1.1), 2)


def generate(n_rides: int, start_date: datetime, days: int) -> pd.DataFrame:
    rows = []
    ride_id = 1
    for day_offset in range(days):
        day = start_date + timedelta(days=day_offset)
        dow = day.weekday()
        for city, meta in CITIES.items():
            lat0, lng0 = meta["center"]
            daily_target = int(n_rides / days / len(CITIES) * meta["base_demand"])
            for hour in range(24):
                mult = hourly_demand_multiplier(hour, dow)
                n_this_hour = max(0, int(np.random.poisson(daily_target / 24 * mult)))
                for _ in range(n_this_hour):
                    minute = random.randint(0, 59)
                    request_ts = day.replace(hour=hour, minute=minute, second=0)
                    distance_km = round(np.random.gamma(2.0, 2.2), 2)
                    surge = surge_from_demand(mult)
                    base_fare = round(35 + distance_km * 11, 2)
                    final_fare = round(base_fare * surge, 2)
                    status = np.random.choice(
                        ["completed", "cancelled", "no_driver"], p=[0.86, 0.10, 0.04]
                    )
                    rows.append({
                        "ride_id": ride_id,
                        "rider_id": random.randint(1, 5000),
                        "driver_id": random.randint(1, 800),
                        "city": city,
                        "pickup_lat": round(lat0 + np.random.uniform(-0.08, 0.08), 6),
                        "pickup_lng": round(lng0 + np.random.uniform(-0.08, 0.08), 6),
                        "drop_lat": round(lat0 + np.random.uniform(-0.12, 0.12), 6),
                        "drop_lng": round(lng0 + np.random.uniform(-0.12, 0.12), 6),
                        "request_ts": request_ts,
                        "distance_km": distance_km,
                        "base_fare": base_fare,
                        "surge_multiplier": surge,
                        "final_fare": final_fare,
                        "payment_type": random.choice(PAYMENT_TYPES),
                        "vehicle_type": random.choice(VEHICLE_TYPES),
                        "ride_status": status,
                        "rider_rating": round(np.random.uniform(3.5, 5.0), 1),
                        "driver_rating": round(np.random.uniform(3.8, 5.0), 1),
                    })
                    ride_id += 1
    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rides", type=int, default=200_000)
    parser.add_argument("--days", type=int, default=120)
    parser.add_argument("--out", type=str, default="data/rides.csv")
    args = parser.parse_args()

    # Make sure output directory exists
    out_dir = os.path.dirname(args.out)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    df = generate(args.rides, datetime(2026, 1, 1), args.days)
    df.to_csv(args.out, index=False)
    print(f"Generated {len(df):,} rides -> {args.out}")