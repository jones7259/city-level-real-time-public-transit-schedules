## TRANSIT API SERVICE
A Flask‑based microservice that authenticates callers with an API key, provides real‑time transit data (routes, stops, arrivals, vehicle locations) and periodically ingests GTFS static and GTFS‑RT feeds.

---

## MAIN FILE
```python
# main.py
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import threading
import time
import json
from datetime import datetime, timedelta

# ----------------------------------------------------------------------
# App & Limiter setup
# ----------------------------------------------------------------------
app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per minute"],
    storage_uri="memory://",
)

# Expected API key – in production load from a secret manager or .env
EXPECTED_API_KEY = os.getenv("TRANSIT_API_KEY", "dev-key-123")

# ----------------------------------------------------------------------
# Mock data stores (would be replaced by PostgreSQL + TimescaleDB queries)
# ----------------------------------------------------------------------
CITIES = {
    "city-1": {"name": "Metropolis"},
    "city-2": {"name": "Gotham"},
}

ROUTES = {
    "route-101": {"city_id": "city-1", "route_id": "route-101", "short_name": "10", "long_name": "Downtown Uptown"},
    "route-102": {"city_id": "city-1", "route_id": "route-102", "short_name": "12", "long_name": "Cross Town"},
    "route-201": {"city_id": "city-2", "route_id": "route-201", "short_name": "7", "long_name": "Uptown Downtown"},
}

STOPS = {
    "stop-A": {"stop_id": "stop-A", "stop_name": "Central Station", "lat": 40.7128, "lng": -74.0060},
    "stop-B": {"stop_id": "stop-B", "stop_name": "West Side", "lat": 40.7300, "lng": -73.9900},
    "stop-C": {"stop_id": "stop-C", "stop_name": "East Side", "lat": 40.7000, "lng": -74.0100},
    "stop-D": {"stop_id": "stop-D", "stop_name": "North Hub", "lat": 40.7500, "lng": -73.9800},
}

# Which stops belong to which route (ordered)
ROUTE_STOPS = {
    "route-101": ["stop-A", "stop-B", "stop-C"],
    "route-102": ["stop-B", "stop-D"],
    "route-201": ["stop-C", "stop-A"],
}

# Mock vehicle positions (lat, lng, heading, timestamp)
VEHICLES = {
    "V123": {"vehicle_id": "V123", "lat": 40.7180, "lng": -74.0010, "heading": 90, "updated_at": datetime.utcnow()},
    "V456": {"vehicle_id": "V456", "lat": 40.7250, "lng": -73.9950, "heading": 180, "updated_at": datetime.utcnow()},
}

# Mock upcoming arrivals per stop (list of dicts sorted by arrival_time)
STOP_ARRIVALS = {
    "stop-A": [
        {"arrival_time": (datetime.utcnow() + timedelta(seconds=30)).isoformat() + "Z",
         "status": "on_time",
         "vehicle_id": "V123"},
        {"arrival_time": (datetime.utcnow() + timedelta(minutes=2)).isoformat() + "Z",
         "status": "delayed",
         "vehicle_id": "V456"},
    ],
    "stop-B": [
        {"arrival_time": (datetime.utcnow() + timedelta(seconds=45)).isoformat() + "Z",
         "status": "on_time",
         "vehicle_id": "V123"},
    ],
}

# ----------------------------------------------------------------------
# Helper: API key authentication
# ----------------------------------------------------------------------
def require_api_key():
    """Check for X-RapidAPI-Key header; abort with 401 if missing/invalid."""
    key = request.headers.get("X-RapidAPI-Key")
    if not key or key != EXPECTED_API_KEY:
        return jsonify({"error": "Unauthorized – invalid or missing API key"}), 401
    return None

# ----------------------------------------------------------------------
# Background GTFS ingestion (mock)
# ----------------------------------------------------------------------
def _ingest_gtfs_static():
    """Simulate nightly GTFS static load."""
    while True:
        app.logger.info("Starting GTFS static ingest (mock)…")
        # In real code: download static ZIP, parse, upsert into PostgreSQL.
        time.sleep(60 * 60 * 24)  # 24 hours

def _ingest_gtfs_rt():
    """Simulate GTFS‑RT feed polling every 30 seconds."""
    while True:
        app.logger.info("Polling GTFS‑RT feed (mock)…")
        # In real code: fetch protobuf, parse, update vehicle positions & arrivals.
        # For demo we just jitter vehicle positions slightly.
        for vid, v in VEHICLES.items():
            v["lat"] += (0.0001 * (-1) ** int(vid[-1]))
            v["lng"] += (0.0001 * (-1) ** int(vid[-1]))
            v["updated_at"] = datetime.utcnow()
        time.sleep(30)

def start_background_threads():
    threading.Thread(target=_ingest_gtfs_static, daemon=True).start()
    threading.Thread(target=_ingest_gtfs_rt, daemon=True).start()

# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.before_request
def enforce_auth_and_limits():
    """Run API‑key check before every request; limiter is applied globally."""
    auth_resp = require_api_key()
    if auth_resp:
        return auth_resp

@app.route("/v1/health", methods=["GET"])
@limiter.exempt  # health checks often excluded from strict limits
def health():
    """Simple liveness probe."""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}), 200

@app.route("/v1/cities/<city_id>/routes", methods=["GET"])
def list_city_routes(city_id):
):
