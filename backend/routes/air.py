"""
air.py
Air quality prediction route -- three live-data behaviors:

  /api/air/predict-live  -- pulls real current data from OpenWeatherMap
                             for a chosen station, predicts, and SAVES it.
  /api/air/predict-demo  -- typed-in values, predicts, NEVER saved.
  /api/air/live-peek     -- used by the on-page polling widget (every
                             30s). Fetches + predicts like predict-live,
                             but does NOT save.
"""

import os
import joblib
import pandas as pd
from flask import Blueprint, request, jsonify
from database import save_reading, get_history
from live_fetch import get_live_air_features
from shap_utils import explain_instance

air_bp = Blueprint("air", __name__)

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models",
)
model = joblib.load(os.path.join(MODELS_DIR, "air_model.pkl"))
wd_encoder = joblib.load(os.path.join(MODELS_DIR, "wd_encoder.pkl"))

FEATURE_ORDER = ["SO2", "NO2", "CO", "O3", "TEMP", "PRES", "DEWP", "RAIN", "wd", "WSPM"]


def classify_pm25(pm25):
    if pm25 <= 12:
        return 1, "Good"
    elif pm25 <= 35.4:
        return 2, "Moderate"
    elif pm25 <= 55.4:
        return 3, "Unhealthy for Sensitive Groups"
    elif pm25 <= 150.4:
        return 4, "Unhealthy"
    elif pm25 <= 250.4:
        return 5, "Very Unhealthy"
    else:
        return 6, "Hazardous"


def build_features(raw):
    wd_encoded = wd_encoder.transform([raw["wd"]])[0]
    row = {**raw, "wd": wd_encoded}
    return pd.DataFrame([row], columns=FEATURE_ORDER).astype(float)


def run_model(raw):
    X = build_features(raw)
    predicted_pm25 = float(model.predict(X)[0])
    aqi_sl, category = classify_pm25(predicted_pm25)
    safe_outdoor = category in ("Good", "Moderate")

    return {
        "predicted_pm25": round(predicted_pm25, 1),
        "aqi_sl": aqi_sl,
        "category": category,
        "safe_for_outdoor_activity": safe_outdoor,
    }


@air_bp.route("/api/air/predict-live", methods=["POST"])
def predict_air_live():
    body = request.get_json(silent=True) or {}
    station = body.get("station", "colombo")

    try:
        raw = get_live_air_features(station)
    except Exception as e:
        return jsonify({"error": f"Could not fetch live data: {e}"}), 502

    raw["station"] = station
    prediction = run_model(raw)
    save_reading("air", "api", raw, prediction)

    return jsonify({"inputs": raw, "prediction": prediction, "source": "api"})


@air_bp.route("/api/air/predict-demo", methods=["POST"])
def predict_air_demo():
    data = request.get_json(force=True)
    raw = {k: data.get(k) for k in FEATURE_ORDER}

    prediction = run_model(raw)

    return jsonify({"inputs": raw, "prediction": prediction, "source": "demo"})


@air_bp.route("/api/air/live-peek", methods=["GET"])
def live_peek_air():
    station = request.args.get("station", "colombo")
    try:
        raw = get_live_air_features(station)
    except Exception as e:
        return jsonify({"error": f"Could not fetch live data: {e}"}), 502

    raw["station"] = station
    prediction = run_model(raw)

    return jsonify({"inputs": raw, "prediction": prediction, "source": "peek"})


@air_bp.route("/api/air/explain", methods=["POST"])
def explain_air():
    data = request.get_json(force=True)
    raw = {k: data.get(k) for k in FEATURE_ORDER}
    try:
        X = build_features(raw)
        contributions = explain_instance(model, X)
        return jsonify({"contributions": contributions})
    except Exception as e:
        return jsonify({"error": f"Could not compute explanation: {e}"}), 500


@air_bp.route("/api/air/history", methods=["GET"])
def air_history():
    return jsonify(get_history(domain="air"))


@air_bp.route("/api/air/feature-importance")
def air_feature_importance():
    importances = model.feature_importances_
    ranked = sorted(zip(FEATURE_ORDER, importances), key=lambda x: x[1], reverse=True)
    return jsonify([{"feature": f, "importance": round(float(i), 4)} for f, i in ranked])