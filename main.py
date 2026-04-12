from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import datetime

app = Flask(__name__)

# Configuration
API_KEY = os.getenv("API_KEY", "secret-transit-key-2024")

# Rate Limiter setup: 100 requests per minute per API Key
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Mock Database representing PostgreSQL + TimescaleDB state
# In production, these would be queried via SQLAlchemy/psycopg2
MOCK_DB = {
    "cities": {
        "nyc": {"id": "nyc", "name": "New York City", "routes": ["R1", "R2"]}
    },
    "routes": {
        "R1": {"id": "R1", "name": "Blue Line", "stops": ["S1", "S2", "S3"]},
        "R2": {"id": "R2", "name": "Red Line", "stops": ["S4", "S5"]}
    },
    "stops": {
        "S1": {"id": "S1", "name": "Central Station"},
        "S2": {"id": "S2", "name": "North Park"},
        "S3": {"id": "S3", "name": "East End"},
        "S4": {"id": "S4", "name": "West Gate"},
        "S5": {"id": "S5", "name": "South Pier"}
    },
    "vehicles": {
        "V123": {"id": "V123", "lat": 40.7128, "lng": -74.0060, "route": "R1"},
        "V456": {"id": "V456", "lat": 40.7306, "lng": -73.9352, "route": "R2"}
    }
}

def authenticate():
    """Helper to validate X-RapidAPI-Key header."""
    key = request.headers.get("X-RapidAPI-Key")
    if not key or key != API_KEY:
        return False
    return True

@app.before_request
def before_request_func():
    """Middleware to enforce authentication on all routes."""
    if not authenticate():
        return jsonify({"error": "Unauthorized", "message": "Invalid or missing API Key"}), 401

@app.route('/v1/cities/<city_id>/routes', methods=['GET'])
@limiter.limit("100 per minute")
def get_city_routes(city_id):
    """List all routes for a specific city."""
    city = MOCK_DB["cities"].get(city_id)
    if not city:
        return jsonify({"error": "City not found"}), 404
    
    routes_data = []
    for r_id in city["routes"]:
        routes_data.append(MOCK_DB["routes"][r_id])
    
    return jsonify({"city_id": city_id, "routes": routes_data}), 200

@app.route('/v1/routes/<route_id>/stops', methods=['GET'])
@limiter.limit("100 per minute")
def get_route_stops(route_id):
    """List all stops for a specific route."""
    route = MOCK_DB["routes"].get(route_id)
    if not route:
        return jsonify({"error": "Route not found"}), 404
    
    stops_data = []
    for s_id in route["stops"]:
        stops_data.append(MOCK_DB["stops"][s_id])
        
    return jsonify({"route_id": route_id, "stops": stops_data}), 200

@app.route('/v1/stops/<stop_id>/arrivals', methods=['GET'])
@limiter.limit("100 per minute")
def get_stop_arrivals(stop_id):
    """Get next n real-time arrivals for a stop."""
    stop = MOCK_DB["stops"].get(stop_id)
    if not stop:
        return jsonify({"error": "Stop not found"}), 404
    
    limit_param = request.args.get('limit', default=5, type=int)
    
    # Simulated GTFS-RT data
    arrivals = []
    base_time = datetime.datetime.utcnow()
    
    for i in range(limit_param):
        arrival_time = (base_time + datetime.timedelta(minutes=i * 5 + 2)).isoformat() + "Z"
        arrivals.append({
            "arrival_time": arrival_time,
            "status": "on_time" if i % 3 != 0 else "delayed",
            "vehicle_id": "V123" if i % 2 == 0 else "V456"
        })
        
    return jsonify({"stop_id": stop_id, "arrivals": arrivals}), 200

@app.route('/v1/vehicles/<vehicle_id>/location', methods=['GET'])
@limiter.limit("100 per minute")
def get_vehicle_location(vehicle_id):
    """Get latest lat/lng for a specific vehicle."""
    vehicle = MOCK_DB["vehicles"].get(vehicle_id)
    if not vehicle:
        return jsonify({"error": "Vehicle not found"}), 404
    
    return jsonify({
        "vehicle_id": vehicle["id"],
        "location": {
            "lat": vehicle["lat"],
            "lng": vehicle["lng"]
        },
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }), 200

@app.route('/v1/health', methods=['GET'])
def health_check():
    """System health check endpoint."""
    return jsonify({"status": "healthy", "database": "connected", "timescaledb": "active"}), 200

@app.route('/v1/system/status', methods=['GET'])
def system_status():
    """Returns status of ingestion workers."""
    return jsonify({
        "gtfs_static_ingestion": "idle",
        "gtfs_rt_ingestion": "running",
        "last_sync": datetime.datetime.utcnow().isoformat() + "Z"
    }), 200

if __name__ == '__main__':
    # In production, use gunicorn
    app.run(host='0.0.0.0', port=5000)