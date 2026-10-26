
"""
Main entry point for the Environmental Pollution Prediction
and Monitoring System.

This file initializes the Flask application, connects the database,
registers the air, water, and soil routes, and serves the frontend.

The individual route files load their respective machine learning
models. The application also supports forecasting and admin functions.

The background process collects air quality readings for Colombo
and Kandy every 15 minutes. Water sensor readings are saved when
received through the relevant route.

To run the application:
    python app.py

Run this command from the backend folder and open:
    http://127.0.0.1:5000
"""


import os
import threading
import time
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from database import init_db, get_all_history, clear_domain, clear_all, delete_reading, save_reading
from routes.air import air_bp
from routes.water import water_bp
from routes.soil import soil_bp
from forecast import get_forecast

load_dotenv()

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

app.register_blueprint(air_bp)
app.register_blueprint(water_bp)
app.register_blueprint(soil_bp)

init_db()

FETCH_INTERVAL_SECONDS = 15 * 60


def background_live_collector():
    from routes.air import run_model
    from live_fetch import get_live_air_features

    while True:
        for station in ["colombo", "kandy"]:
            try:
                raw = get_live_air_features(station)
                raw["station"] = station
                prediction = run_model(raw)
                save_reading("air", "api", raw, prediction)
                print(f"[auto-collect] {station}: {prediction['category']}")
            except Exception as e:
                print(f"[auto-collect] failed for {station}: {e}")

        time.sleep(FETCH_INTERVAL_SECONDS)


def require_admin_key(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        expected = os.getenv("ADMIN_KEY")
        provided = request.headers.get("X-Admin-Key")
        if not expected or provided != expected:
            return jsonify({"error": "Invalid or missing admin key"}), 401
        return view_func(*args, **kwargs)
    return wrapped


@app.route("/")
def serve_home():
    return app.send_static_file("index.html")


@app.route("/<path:filename>")
def serve_frontend_file(filename):
    return app.send_static_file(filename)


@app.route("/api/status")
def status():
    return jsonify({"status": "ok", "message": "Pollution prediction API is running"})


@app.route("/api/<domain>/forecast")
def forecast_route(domain):
    periods = int(request.args.get("periods", 2))
    return jsonify(get_forecast(domain, periods=periods))


@app.route("/api/admin/all")
def admin_all():
    return jsonify(get_all_history(limit=None))


@app.route("/api/admin/clear/<domain>", methods=["DELETE"])
@require_admin_key
def admin_clear_domain(domain):
    clear_domain(domain)
    return jsonify({"status": "ok", "message": f"Cleared all {domain} readings"})


@app.route("/api/admin/clear-all", methods=["DELETE"])
@require_admin_key
def admin_clear_all():
    clear_all()
    return jsonify({"status": "ok", "message": "Cleared all readings, all domains"})


@app.route("/api/admin/delete/<domain>/<int:reading_id>", methods=["DELETE"])
@require_admin_key
def admin_delete_one(domain, reading_id):
    delete_reading(domain, reading_id)
    return jsonify({"status": "ok", "message": f"Deleted {domain} reading {reading_id}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=background_live_collector, daemon=True).start()
    app.run(debug=True, host="0.0.0.0", port=port)
