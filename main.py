## API NAME
TransitInfo Service – Real‑time public transport data with API key auth and rate limiting

## MAIN FILE
```python
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv
import requests
import datetime
import random

# Load environment variables (e.g., API_KEY for validation)
load_dotenv()

app = Flask(__name__)

# ----------------------------------------------------------------------
# Helper: extract API key from header for rate limiting and auth
# ----------------------------------------------------------------------
def get_api_key():
    """
    Returns the API key from the X-RapidAPI-Key header.
    If missing, returns an empty string so limiter treats it as a separate bucket.
    """
    return request.headers.get('X-RapidAPI-Key', '')

# ----------------------------------------------------------------------
# Limiter: 100 requests per minute per API key
# ----------------------------------------------------------------------
limiter = Limiter(
    key_func=get_api_key,
    default_limits=["100 per minute"],
    app_app=app
)

# ----------------------------------------------------------------------
# Simple in‑memory mock data (would normally come from Postgres/TimescaleDB)
# ----------------------------------------------------------------------
CITIES = {
    "c1": {"name": "Metropolis"},
    "c2": {"name": "Gotham"}
}

ROUTES = {
    "r1": {"city_id": "c1", "name": "Downtown Loop"},
    "r2": {"city_id": "c1", "name": "Uptown Express"},
    "r3": {"city_id": "c2", "name": "Gotham Circle"}
}

STOPS = {
    "s1": {"route_id": "r1", "name": "Central Station", "seq": 1},
    "s2": {"route_id": "r1", "name": "Riverfront", "seq": 2},
    "s3": {"route_id": "r2", "name": "Uptown Hub", "seq": 1},
    "s4": {"route_id": "r2", "name": "Tech Park", "seq": 2},
    "s5": {"route_id": "r3", "name": "Gotham Central", "seq": 1},
    "s6": {"route_id": "r3", "name": "East End", "seq": 2}
}

# Mock arrivals: each stop has a list of future arrival times (UTC)
def _generate_mock_arrivals(stop_id, limit=5):
    now = datetime.datetime.utcnow()
    arrivals = []
    for i in range(limit):
        arrival_time = now + datetime.timedelta(minutes=random.randint(2, 30) + i*5)
        status = random.choice(["on_time", "delayed", "early"])
        vehicle_id = f"V{random.randint(100, 999)}"
        arrivals.append({
            "arrival_time": arrival_time.isoformat() + "Z",
            "status": status,
            "vehicle_id": vehicle_id
        })
    return arrivals

VEHICLES = {
    "V123": {"lat": 40.7128, "lng": -74.0060, "last_update": datetime.datetime.utcnow().isoformat() + "Z"},
    "V456": {"lat": 34.0522, "lng": -118.2437, "last_update": datetime.datetime.utcnow().isoformat() + "Z"},
}

# ----------------------------------------------------------------------
# Authentication decorator
# ----------------------------------------------------------------------
def require_api_key(func):
    def wrapper(*args, **kwargs):
        if not request.headers.get('X-RapidAPI-Key'):
            return jsonify({"error": "Missing X-RapidAPI-Key header"}), 401
        # Optionally validate against a secret stored in env
        # expected_key = os.getenv("RAPIDAPI_KEY")
        # if request.headers.get('X-RapidAPI-Key') != expected_key:
        #     return jsonify({"error": "Invalid API key"}), 401
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# ----------------------------------------------------------------------
# OpenAPI spec (simple static definition)
# ----------------------------------------------------------------------
@app.route("/openapi.json")
def openapi_spec():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "TransitInfo API", "version": "1.0.0"},
        "paths": {
            "/v1/cities/{city_id}/routes": {
                "get": {
                    "summary": "List all routes for a city",
                    "parameters": [
                        {"name": "city_id", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "X-RapidAPI-Key", "in": "header", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "A list of routes"}}
                }
            },
            "/v1/routes/{route_id}/stops": {
                "get": {
                    "summary": "List stops for a route",
                    "parameters": [
                        {"name": "route_id", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "X-RapidAPI-Key", "in": "header", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "A list of stops"}}
                }
            },
            "/v1/stops/{stop_id}/arrivals": {
                "get": {
                    "summary": "Next n real‑time arrivals for a stop",
                    "parameters": [
                        {"name": "stop_id", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "default": 5}},
                        {"name": "X-RapidAPI-Key", "in": "header", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "Arrival predictions"}}
                }
            },
            "/v1/vehicles/{vehicle_id}/location": {
                "get": {
                    "summary": "Latest latitude/longitude for a vehicle",
                    "parameters": [
                        {"name": "vehicle_id", "in": "path", " "