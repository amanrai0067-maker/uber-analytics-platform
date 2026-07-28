# File: api/routers/drivers.py (ya main.py)
from fastapi import APIRouter
import pandas as pd

router = APIRouter(prefix="/drivers", tags=["drivers"])

@router.get("/performance")
def get_driver_performance(city: str = None):
    # Aggregated query ya mock data format jo dashboard expect kar raha hai:
    data = [
        {"driver_id": 1, "rating": 4.8, "earnings": 1250.50, "completion_rate": 0.95},
        {"driver_id": 2, "rating": 4.5, "earnings": 980.00, "completion_rate": 0.88},
        {"driver_id": 3, "rating": 4.9, "earnings": 1500.00, "completion_rate": 0.98},
        {"driver_id": 4, "rating": 4.2, "earnings": 820.00, "completion_rate": 0.82},
        {"driver_id": 5, "rating": 4.7, "earnings": 1100.00, "completion_rate": 0.91},
    ]
    return data