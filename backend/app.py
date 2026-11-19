import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Hill Smart Agriculture System")
DB_PATH = Path("backend/agri_data.db")
MODEL_PATH = Path("backend/irrigation_model.pkl")

model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_id TEXT,
                elevation_tier INTEGER,
                slope_deg REAL,
                soil_moisture REAL,
                soil_temp REAL,
                humidity REAL,
                rain_forecast_mm REAL,
                irrigate INTEGER,
                confidence REAL,
                water_saved_liters REAL,
                advisory TEXT,
                created_at TEXT
            )
        """)


init_db()


class SensorPayload(BaseModel):
    zone_id: str = Field(default="Terrace-Upper-01")
    elevation_tier: int = Field(default=3, ge=1, le=3)
    slope_deg: float = Field(default=24.0, ge=0, le=60)
    soil_moisture: float = Field(..., ge=0, le=100)
    soil_temp: float = Field(default=24.5)
    humidity: float = Field(default=68.0, ge=0, le=100)
    rain_forecast_mm: float = Field(default=0.0, ge=0)


def evaluate_zone(data: SensorPayload):
    features = np.array([[
        data.soil_moisture,
        data.soil_temp,
        data.humidity,
        data.rain_forecast_mm,
        data.slope_deg,
        data.elevation_tier,
    ]])

    if model is not None:
        pred = int(model.predict(features)[0])
        prob = float(np.max(model.predict_proba(features)[0])) * 100
    else:
        pred = int(data.soil_moisture < 32 and data.rain_forecast_mm < 5)
        prob = 92.0

    # Advisory & water savings calculation vs traditional flood irrigation (120L/cycle)
    if pred == 1:
        water_saved = round(120.0 - 42.0, 1)  # Drip uses ~42L vs 120L flood
        advisory = f"VALVE OPEN (12 min drip): Low moisture ({data.soil_moisture}%) on {data.slope_deg}° slope."
    elif data.rain_forecast_mm >= 5.0:
        water_saved = 120.0
        advisory = f"VALVE LOCKED: {data.rain_forecast_mm}mm rain expected—preventing slope runoff & erosion."
    else:
        water_saved = 120.0
        advisory = f"OPTIMAL: Soil moisture ({data.soil_moisture}%) healthy. No irrigation needed."

    return pred, round(prob, 1), water_saved, advisory


@app.post("/api/telemetry")
def receive_telemetry(data: SensorPayload):
    irrigate, confidence, water_saved, advisory = evaluate_zone(data)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO telemetry (
                zone_id, elevation_tier, slope_deg, soil_moisture, soil_temp,
                humidity, rain_forecast_mm, irrigate, confidence, water_saved_liters,
                advisory, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.zone_id, data.elevation_tier, data.slope_deg, data.soil_moisture,
            data.soil_temp, data.humidity, data.rain_forecast_mm, irrigate,
            confidence, water_saved, advisory, ts
        ))

    return {
        "zone_id": data.zone_id,
        "irrigate": bool(irrigate),
        "confidence": confidence,
        "water_saved_liters": water_saved,
        "advisory": advisory,
        "timestamp": ts,
    }


@app.post("/api/simulate")
def simulate_hill_nodes():
    zones = [
        ("Terrace-Upper-01", 3, 28.0),
        ("Terrace-Mid-02", 2, 18.5),
        ("Terrace-Lower-03", 1, 9.0),
    ]
    results = []
    for z_name, tier, slope in zones:
        payload = SensorPayload(
            zone_id=z_name,
            elevation_tier=tier,
            slope_deg=slope,
            soil_moisture=round(random.uniform(18.0, 48.0), 1),
            soil_temp=round(random.uniform(19.0, 29.0), 1),
            humidity=round(random.uniform(52.0, 88.0), 1),
            rain_forecast_mm=round(random.choice([0.0, 0.5, 1.2, 8.5]), 1),
        )
        results.append(receive_telemetry(payload))
    return {"simulated": results}


@app.post("/api/disease-check")
def check_leaf_disease(leaf_spot_ratio: float = 0.18, yellowing_index: float = 0.25):
    # Lightweight screening rule simulating edge CV inference output
    risk_score = round((leaf_spot_ratio * 0.65 + yellowing_index * 0.35) * 100, 1)
    if risk_score > 35:
        status = "Early Fungal Blight Risk Detected"
        action = "Isolate terrace row & apply organic copper/neem bio-fungicide before evening dew."
    else:
        status = "Healthy Foliage"
        action = "No treatment required; continue routine 48-hour drone/mobile scan."
    return {"risk_score": risk_score, "diagnosis": status, "recommendation": action}


@app.get("/api/dashboard-data")
def dashboard_data():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM telemetry ORDER BY id DESC LIMIT 15").fetchall()
        total_saved = conn.execute("SELECT COALESCE(SUM(water_saved_liters), 0) FROM telemetry").fetchone()[0]
    return {
        "total_water_saved_liters": round(total_saved, 1),
        "records": [dict(r) for r in rows],
    }


@app.get("/", response_class=HTMLResponse)
def serve_ui():
    return Path("static/index.html").read_text(encoding="utf-8")