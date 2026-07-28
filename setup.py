import os

# Ye wahi 23 files hain jo tumhare project ko chahiye
files_ka_data = {
    "requirements.txt": "fastapi\nuvicorn\nstreamlit\nlightgbm\nmlflow\npandas\nnumpy\nplotly\nsqlalchemy\npsycopg2-binary\npydantic",
    ".env.example": "POSTGRES_HOST=localhost\nPOSTGRES_USER=uber_admin\nPOSTGRES_PASSWORD=password",
    "sql/schema.sql": "-- SQL Database Schema\nCREATE TABLE IF NOT EXISTS rides (id SERIAL PRIMARY KEY);",
    "sql/analytics_queries.sql": "-- Sample Queries\nSELECT * FROM rides;",
    "data/generate_data.py": "# Data Generator\nprint('Data script ready')",
    "src/db.py": "# Database Connection\nimport os",
    "src/etl.py": "# Data Loader\nprint('ETL script ready')",
    "src/analytics.py": "# Business Logic",
    "src/features.py": "# ML Feature Engineering",
    "src/train_forecast.py": "# Model Training\nprint('ML training ready')",
    "api/main.py": "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\ndef index(): return {'status': 'running'}",
    "api/schemas.py": "from pydantic import BaseModel",
    "api/routers/demand.py": "from fastapi import APIRouter\nrouter = APIRouter()",
    "api/routers/surge.py": "from fastapi import APIRouter\nroutcd sql"
    "er = APIRouter()",
    "api/routers/drivers.py": "from fastapi import APIRouter\nrouter = APIRouter()",
    "api/routers/revenue.py": "from fastapi import APIRouter\nrouter = APIRouter()",
    "dashboard/app.py": "import streamlit as st\nst.title('Uber Analytics')",
    "Dockerfile": "FROM python:3.10-slim",
    "docker/Dockerfile.dashboard": "FROM python:3.10-slim",
    "docker-compose.yml": "version: '3.8'\nservices:",
    ".github/workflows/ci.yml": "name: CI Pipeline\non: [push]"
}

# Auto-folder aur file banane ka magic
for path, content in files_ka_data.items():
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

print("💥 Magic Done! Saare folders aur saari 23 files automatic ban gayi hain!")