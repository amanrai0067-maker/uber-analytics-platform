# File: api/main.py
import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Root directory added to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics import (
    get_demand_by_hour,
    get_surge_analysis,
    get_driver_performance,
    get_revenue_trend,
    get_demand_hotspots
)

app = FastAPI(
    title="Uber Analytics & Demand Forecasting API",
    description="REST API for ride demand, surge, and revenue analytics.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "uber-analytics-api"}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}

@app.get("/demand/hourly", tags=["Analytics"])
def demand_hourly(city: str = None):
    return get_demand_by_hour(city=city)

@app.get("/surge/analysis", tags=["Analytics"])
def surge_analysis(city: str = None):
    return get_surge_analysis(city=city)

@app.get("/drivers/performance", tags=["Analytics"])
def driver_performance(city: str = None):
    return get_driver_performance(city=city)

@app.get("/revenue/trend", tags=["Analytics"])
def revenue_trend(city: str = None):
    return get_revenue_trend(city=city)

@app.get("/demand/hotspots", tags=["Analytics"])
def demand_hotspots(city: str = None):
    return get_demand_hotspots(city=city)